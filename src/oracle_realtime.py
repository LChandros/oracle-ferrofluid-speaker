#!/usr/bin/env python3
"""
Oracle Realtime Agent - OpenAI Realtime API integration
Handles voice conversations via WebSocket with streaming audio I/O.
Audio output routes through ALSA loopback for ferrofluid visualization.
"""

import asyncio
import websockets
import json
import base64
import numpy as np
import threading
import queue
import time
import logging
from datetime import datetime
import subprocess

logger = logging.getLogger('OracleRealtime')

# Realtime API config
REALTIME_MODEL = "gpt-4o-mini-realtime-preview-2024-12-17"
REALTIME_URL = f"wss://api.openai.com/v1/realtime?model={REALTIME_MODEL}"
REALTIME_VOICE = "echo"

# Audio format constants
MIC_RATE = 16000       # Mic captures at 16kHz (Porcupine requirement)
API_RATE = 24000       # Realtime API uses 24kHz
SPEAKER_RATE = 44100   # Loopback/speakers use 44.1kHz


def resample_16k_stereo_to_24k_mono(pcm_16k_stereo):
    """Convert mic audio (16kHz stereo S16_LE) to API format (24kHz mono PCM16)"""
    samples = np.frombuffer(pcm_16k_stereo, dtype=np.int16)
    if len(samples) < 2:
        return b''
    # Stereo to mono
    mono = ((samples[0::2].astype(np.int32) + samples[1::2].astype(np.int32)) // 2).astype(np.int16)
    # Resample 16kHz to 24kHz
    n_out = int(len(mono) * API_RATE / MIC_RATE)
    if n_out < 1:
        return b''
    indices = np.linspace(0, len(mono) - 1, n_out)
    resampled = np.interp(indices, np.arange(len(mono)), mono.astype(np.float64)).astype(np.int16)
    return resampled.tobytes()


def resample_24k_mono_to_44k_stereo(pcm_24k_mono):
    """Convert API response audio (24kHz mono PCM16) to speaker format (44.1kHz stereo S16_LE)"""
    samples = np.frombuffer(pcm_24k_mono, dtype=np.int16)
    if len(samples) < 1:
        return b''
    # Resample 24kHz to 44.1kHz
    n_out = int(len(samples) * SPEAKER_RATE / API_RATE)
    if n_out < 1:
        return b''
    indices = np.linspace(0, len(samples) - 1, n_out)
    resampled = np.interp(indices, np.arange(len(samples)), samples.astype(np.float64)).astype(np.int16)
    # Mono to stereo
    stereo = np.empty(len(resampled) * 2, dtype=np.int16)
    stereo[0::2] = resampled
    stereo[1::2] = resampled
    return stereo.tobytes()


class OracleRealtimeSession:
    """Manages a single Realtime API conversation session."""

    def __init__(self, api_key, system_prompt, tools, tool_handler,
                 on_speech_started=None, on_speech_ended=None,
                 on_audio_started=None, on_response_done=None,
                 on_error=None, on_mic_mute=None, on_mic_unmute=None,
                 session_timeout=20):
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.tools = tools
        self.tool_handler = tool_handler
        self.on_speech_started = on_speech_started
        self.on_speech_ended = on_speech_ended
        self.on_audio_started = on_audio_started
        self.on_response_done = on_response_done
        self.on_error = on_error
        self.on_mic_mute = on_mic_mute      # Called to stop mic when Oracle speaks
        self.on_mic_unmute = on_mic_unmute  # Called to restart mic after drain
        self.session_timeout = session_timeout

        self.active = False
        self.audio_queue = queue.Queue()
        self.speaker_process = None
        self._thread = None
        self._last_activity = 0
        self._first_audio_in_response = True
        self._is_responding = False  # True while Oracle is speaking (mute mic to prevent echo)

    def start(self):
        """Start the session in a background thread."""
        self.active = True
        self._last_activity = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the session."""
        self.active = False
        if self._thread:
            self._thread.join(timeout=5)

    def feed_audio(self, length, data):
        """Feed mic audio into the session (called from wake word thread)."""
        if self.active and length > 0:
            self.audio_queue.put(data)

    def _run(self):
        """Run the async session in a new event loop."""
        try:
            asyncio.run(self._async_session())
        except Exception as e:
            logger.error(f"[Realtime] Session error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.active = False
            self._cleanup_speaker()

    async def _async_session(self):
        """Main async session loop."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }

        logger.info(f"[Realtime] Connecting to {REALTIME_MODEL}...")

        try:
            async with websockets.connect(
                REALTIME_URL,
                additional_headers=headers,
                max_size=None,
                ping_interval=20
            ) as ws:
                # Wait for session.created
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                if msg["type"] != "session.created":
                    logger.error(f"[Realtime] Unexpected: {msg['type']}")
                    return

                logger.info("[Realtime] Connected, configuring session...")

                # Configure session with current time injected
                now = datetime.now()
                time_context = f"\nCurrent date and time: {now.strftime('%A, %B %d, %Y at %I:%M %p')} EST.\n"
                session_config = {
                    "type": "session.update",
                    "session": {
                        "instructions": self.system_prompt + time_context,
                        "voice": REALTIME_VOICE,
                        "modalities": ["text", "audio"],
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.3,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 800
                        },
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "input_audio_transcription": {
                            "model": "whisper-1"
                        }
                    }
                }
                # Only add tools if we have any
                if self.tools:
                    session_config["session"]["tools"] = self.tools

                await ws.send(json.dumps(session_config))
                logger.info("[Realtime] Session configured")

                # Open speaker output to loopback
                self._open_speaker()

                # Run concurrently
                sender = asyncio.create_task(self._send_audio_loop(ws))
                receiver = asyncio.create_task(self._receive_events(ws))
                timeout_task = asyncio.create_task(self._check_timeout())

                done, pending = await asyncio.wait(
                    [sender, receiver, timeout_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        except Exception as e:
            logger.error(f"[Realtime] Connection error: {e}")
            import traceback
            traceback.print_exc()

        logger.info("[Realtime] Session ended")

    async def _send_audio_loop(self, ws):
        """Read mic audio from queue, convert, and send to API."""
        while self.active:
            try:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.audio_queue.get(timeout=0.1)
                )

                if data:
                    # Echo suppression: don't send mic audio while Oracle is speaking
                    if self._is_responding:
                        continue

                    converted = resample_16k_stereo_to_24k_mono(data)
                    if converted:
                        # Debug: log audio level every 50 chunks
                        if not hasattr(self, "_send_count"):
                            self._send_count = 0
                        self._send_count += 1
                        if self._send_count % 50 == 1:
                            samples = np.frombuffer(converted, dtype=np.int16)
                            rms = np.sqrt(np.mean(samples.astype(np.float64)**2))
                            logger.info(f"[Realtime] Sending audio chunk #{self._send_count}: {len(converted)} bytes, RMS={rms:.0f}")
                        
                        b64 = base64.b64encode(converted).decode()
                        await ws.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": b64
                        }))

            except queue.Empty:
                continue
            except Exception as e:
                if self.active:
                    logger.error(f"[Realtime] Send error: {e}")
                break

    async def _receive_events(self, ws):
        """Process events from the Realtime API."""
        async for msg_str in ws:
            if not self.active:
                break

            try:
                event = json.loads(msg_str)
                etype = event.get("type", "")

                if etype == "response.audio.delta":
                    # First audio chunk = mute mic, set SPEAKING state
                    if self._first_audio_in_response:
                        self._first_audio_in_response = False
                        self._is_responding = True
                        # IMMEDIATELY mute mic to prevent any echo
                        if self.on_mic_mute:
                            self.on_mic_mute()
                        # Flush any audio already queued
                        while not self.audio_queue.empty():
                            try: self.audio_queue.get_nowait()
                            except: break
                        # Tell API to discard any buffered audio
                        try:
                            asyncio.create_task(ws.send(json.dumps({"type": "input_audio_buffer.clear"})))
                        except: pass
                        if self.on_audio_started:
                            self.on_audio_started()

                    audio_b64 = event.get("delta", "")
                    if audio_b64:
                        pcm_24k = base64.b64decode(audio_b64)
                        pcm_speaker = resample_24k_mono_to_44k_stereo(pcm_24k)
                        self._write_speaker(pcm_speaker)
                    self._last_activity = time.time()

                elif etype == "input_audio_buffer.speech_started":
                    logger.info("[Realtime] User speaking...")
                    if self.on_speech_started:
                        self.on_speech_started()
                    self._last_activity = time.time()

                elif etype == "input_audio_buffer.speech_stopped":
                    logger.info("[Realtime] User stopped speaking")
                    if self.on_speech_ended:
                        self.on_speech_ended()
                    self._last_activity = time.time()

                elif etype == "response.audio_transcript.done":
                    transcript = event.get("transcript", "")
                    if transcript:
                        logger.info(f"[Realtime] Oracle: {transcript[:150]}")

                elif etype == "conversation.item.input_audio_transcription.completed":
                    transcript = event.get("transcript", "")
                    if transcript:
                        logger.info(f"[Realtime] Trevor: {transcript[:150]}")

                elif etype == "response.function_call_arguments.done":
                    call_id = event.get("call_id", "")
                    name = event.get("name", "")
                    args_str = event.get("arguments", "{}")

                    logger.info(f"[Realtime] Tool: {name}({args_str[:100]})")

                    try:
                        args = json.loads(args_str)
                        result = self.tool_handler(name, args)
                    except Exception as e:
                        result = {"error": str(e)}
                        logger.error(f"[Realtime] Tool error: {e}")

                    await ws.send(json.dumps({
                        "type": "conversation.item.create",
                        "item": {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": json.dumps(result)
                        }
                    }))
                    await ws.send(json.dumps({"type": "response.create"}))
                    self._last_activity = time.time()

                elif etype == "response.done":
                    self._first_audio_in_response = True
                    if self._is_responding:
                        # Audio was played - drain speaker and restart mic
                        logger.info("[Realtime] Audio response complete, draining speaker...")
                        self._ws_ref = ws
                        asyncio.create_task(self._drain_flush_unmute())
                    else:
                        # No audio (tool-call-only response) - no drain needed
                        logger.info("[Realtime] Response complete (no audio)")
                    if self.on_response_done:
                        self.on_response_done()
                    self._last_activity = time.time()

                elif etype == "error":
                    error = event.get("error", {})
                    error_msg = error.get("message", str(error))
                    logger.error(f"[Realtime] API error: {error_msg}")
                    if self.on_error:
                        self.on_error(error_msg)
                    break

                elif etype == "session.updated":
                    logger.info("[Realtime] Config updated")

            except Exception as e:
                logger.error(f"[Realtime] Event error: {e}")

    async def _drain_flush_unmute(self):
        """Wait for speaker to drain, then restart mic."""
        await asyncio.sleep(2.0)  # Let speaker buffer drain

        # Flush any leftover audio in queue
        flushed = 0
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
                flushed += 1
            except queue.Empty:
                break

        # Clear API input buffer
        if hasattr(self, '_ws_ref') and self._ws_ref:
            try:
                await self._ws_ref.send(json.dumps({"type": "input_audio_buffer.clear"}))
            except Exception:
                pass

        # Restart mic (was killed when Oracle started speaking)
        if self.on_mic_unmute:
            self.on_mic_unmute()

        self._is_responding = False
        logger.info(f"[Realtime] Mic restarted (flushed {flushed} chunks)")

    async def _check_timeout(self):
        """Close session after inactivity."""
        while self.active:
            await asyncio.sleep(2)
            if time.time() - self._last_activity > self.session_timeout:
                logger.info(f"[Realtime] Timeout ({self.session_timeout}s)")
                self.active = False
                break

    def _open_speaker(self):
        """Open aplay to loopback for visualization-enabled playback."""
        try:
            self.speaker_process = subprocess.Popen(
                ['aplay', '-D', 'plughw:2,0', '-f', 'S16_LE', '-c', '2',
                 '-r', '44100', '-t', 'raw', '--buffer-size', '4096'],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info("[Realtime] Speaker: loopback plughw:2,0")
        except Exception as e:
            logger.error(f"[Realtime] Speaker open failed: {e}")

    def _write_speaker(self, pcm_bytes):
        """Write audio to speaker subprocess."""
        if self.speaker_process and self.speaker_process.poll() is None:
            try:
                self.speaker_process.stdin.write(pcm_bytes)
                self.speaker_process.stdin.flush()
            except (BrokenPipeError, OSError):
                logger.warning("[Realtime] Speaker pipe broken, reopening")
                self._cleanup_speaker()
                self._open_speaker()

    def _cleanup_speaker(self):
        """Clean up speaker subprocess."""
        if self.speaker_process:
            try:
                self.speaker_process.stdin.close()
            except:
                pass
            try:
                self.speaker_process.terminate()
                self.speaker_process.wait(timeout=2)
            except:
                try:
                    self.speaker_process.kill()
                except:
                    pass
            self.speaker_process = None
