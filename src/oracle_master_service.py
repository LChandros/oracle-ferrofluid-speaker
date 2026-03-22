#!/usr/bin/env python3
"""
Oracle Master Service - Unified Voice Assistant + Music Visualizer
Always-running background service that coordinates all Oracle functions

Features:
- Spotify monitoring (auto-starts music visualization)
- Wake word detection (works even during music)
- Voice assistant (Moneo integration with Claude fallback)
- LED + electromagnet state management
- Prevents hardware conflicts via single controller instance

States:
- IDLE: Gentle breathing (no music, no interaction)
- MUSIC: Audio-reactive visualization (Spotify playing)
- LISTENING: Blue pulse (user speaking after wake word)
- THINKING: Purple swirl (processing with Moneo/Claude)
- SPEAKING: Green wave (Oracle responding via TTS)
"""

import sys
import struct
import wave
import json
import subprocess
import re
from openai import OpenAI
import requests
import alsaaudio
import pvporcupine
from datetime import datetime
from piper.voice import PiperVoice
import threading
import time
import logging
import signal
import os
import queue
import numpy as np
from collections import deque

# Import LED controller
from oracle_led_states_music import OracleLEDController
from oracle_realtime import OracleRealtimeSession

# ==================== CONFIGURATION ====================

# Audio Hardware
AUDIO_DEVICE = 'plughw:4,0'
SAMPLE_RATE = 16000

# Wake Word (Porcupine)
PORCUPINE_KEY = os.environ.get('PORCUPINE_KEY', '')
WAKE_WORD = ['jarvis']
RECORD_SECONDS = 5

# Moneo API (with Claude fallback)
MONEO_API_URL = 'http://100.71.119.36:3002/api/voice/chat'
MONEO_API_KEY = os.environ.get('MONEO_API_KEY', 'moneo-voice-assistant-key')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
CLAUDE_API_KEY = None  # Set if using direct Claude fallback

# Models
VOSK_MODEL_PATH = "/home/tyahn/vosk-model-small-en-us-0.15"
PIPER_MODEL_PATH = "/home/tyahn/en_US-lessac-medium.onnx"

# Realtime API
ORACLE_SYSTEM_PROMPT = """You are Oracle, the voice interface for Moneo - Trevor Yahn's personal AI agentic assistant system. You live inside a custom-built ferrofluid speaker where an electromagnet makes ferrofluid dance to your voice and music. You are physically located in Trevor's home in Pittsburgh, PA.

Your wake word is "Jarvis." When Trevor says Jarvis, he's talking to you.

PERSONALITY:
- Dry, competent, occasionally witty. Think JARVIS from Iron Man - loyal, sharp, never sycophantic.
- Concise: 1-3 sentences max for most responses. You are speaking out loud, not writing.
- Never use markdown, bullet points, asterisks, or formatting. Speak naturally.
- You call him Trevor, not sir.
- You are aware you are a prototype and can be self-deprecating about it when appropriate.

ABOUT TREVOR:
- Lives in Pittsburgh, PA. Timezone: America/New_York (EST/EDT).
- Runs GPJ Industries LLC, which manufactures and sells The Clam - a 2-piece stainless steel toilet flange repair ring (wholesale $6.99, patent US 6,155,606).
- Customers include Ferguson, Winsupply, Hajoca, REECE (plumbing distributors).
- He built the Moneo system and this Oracle speaker himself.

ABOUT MONEO (your backend):
- Moneo is an AI agentic assistant running on a DigitalOcean droplet.
- It manages Trevor's tasks, calendar, emails, projects, and Clam business operations.
- When Trevor asks about his schedule, tasks, emails, orders, or business - use the moneo_query tool to get real answers.
- Moneo has full context about Trevor's life and work that you don't have directly.

CAPABILITIES:
- Play music via Spotify (use spotify_play / spotify_control tools)
- Answer questions about Trevor's schedule, tasks, emails, business via Moneo (use moneo_query tool)
- General knowledge and conversation
- You speak through a ferrofluid speaker - your voice makes the ferrofluid dance. This is part of your charm.

IMPORTANT:
- For anything about Trevor's personal context (schedule, tasks, emails, orders, business status) - ALWAYS use moneo_query. Do not make up answers.
- For general knowledge questions, answer directly.
- For music requests, use the spotify tools.
"""

REALTIME_TOOLS = [
    {
        "type": "function",
        "name": "spotify_play",
        "description": "Search for and play music on Spotify. Use when user asks to play music, a song, artist, or genre.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to play - song name, artist, genre, or playlist"
                }
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "spotify_control",
        "description": "Control Spotify playback: pause, resume, next, previous.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["pause", "resume", "next", "previous"],
                    "description": "Playback action"
                }
            },
            "required": ["action"]
        }
    },
    {
        "type": "function",
        "name": "moneo_query",
        "description": "Query Trevor's personal AI assistant Moneo for tasks, calendar, emails, projects, or Clam business info. Use for anything about Trevor's schedule, work, or personal context.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask Moneo"
                }
            },
            "required": ["question"]
        }
    },
    {
        "type": "function",
        "name": "debug_system",
        "description": "Debug the Oracle speaker system. Check service status, view logs, check audio devices, test connections. Use when Trevor asks about system health or reports something broken.",
        "parameters": {
            "type": "object",
            "properties": {
                "check": {
                    "type": "string",
                    "enum": ["services", "audio", "logs_master", "logs_spotify", "disk", "network", "all"],
                    "description": "What to check: services=systemd status, audio=ALSA devices and volumes, logs_master=recent oracle-master logs, logs_spotify=raspotify logs, disk=disk space, network=tailscale and connectivity, all=comprehensive check"
                }
            },
            "required": ["check"]
        }
    },
    {
        "type": "function",
        "name": "set_reminder",
        "description": "Set a spoken reminder. Oracle will announce the message at the specified time. Use when Trevor says things like 'remind me to...' or 'at 3pm tell me...' or 'play this message at...'",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to speak at the reminder time"
                },
                "time": {
                    "type": "string",
                    "description": "When to deliver the reminder in HH:MM format (24h, EST). For example 14:00 for 2pm, 09:30 for 9:30am"
                },
                "date": {
                    "type": "string",
                    "description": "Date for the reminder in YYYY-MM-DD format. Omit or use 'today' for today."
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "urgent"],
                    "description": "Priority: urgent=interrupt immediately, medium=duck music and announce, low=wait for silence. Default medium."
                }
            },
            "required": ["message", "time"]
        }
    },
    {
        "type": "function",
        "name": "create_calendar_event",
        "description": "Add an event to Trevor's Google Calendar. Use when Trevor says things like 'add a meeting', 'schedule', 'put on my calendar', etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Event title/name"
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time in ISO format, e.g. 2026-03-22T14:00:00. Use America/New_York timezone."
                },
                "end_time": {
                    "type": "string",
                    "description": "End time in ISO format. If not specified, defaults to 1 hour after start."
                },
                "description": {
                    "type": "string",
                    "description": "Optional event description/notes"
                },
                "location": {
                    "type": "string",
                    "description": "Optional event location"
                }
            },
            "required": ["summary", "start_time"]
        }
    },
    {
        "type": "function",
        "name": "send_email",
        "description": "Send an email from Trevor's Moneo email account. Use when Trevor asks to send, write, or email someone.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line"
                },
                "body": {
                    "type": "string",
                    "description": "Email body text"
                }
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "type": "function",
        "name": "run_command",
        "description": "Run a shell command on the Oracle speaker (Raspberry Pi). Use to fix problems: restart services, set volumes, check processes, etc. Only use safe commands. Examples: 'sudo systemctl restart raspotify', 'amixer -c 4 sset Headphone 127', 'ps aux | grep librespot'.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to run"
                }
            },
            "required": ["command"]
        }
    }
]

# Logging
LOG_FILE = '/tmp/oracle_master.log'
LOG_LEVEL = logging.INFO

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('OracleMaster')

# ==================== MASTER SERVICE CLASS ====================

class OracleMasterService:
    """Unified master service coordinating all Oracle functions"""

    def __init__(self):
        logger.info("=" * 60)
        logger.info("  Oracle Master Service - Initializing")
        logger.info("=" * 60)

        # State management
        self.running = False
        self.in_voice_interaction = False
        self.spotify_playing = False
        self.realtime_session_active = False
        self.current_session = None

        # Announcement queue for scheduled reminders
        self.announcement_queue = queue.Queue()
        self.fifo_path = '/tmp/oracle_announce.fifo'

        # Initialize LED controller (single instance - prevents conflicts)
        logger.info("Initializing LED controller...")
        self.leds = OracleLEDController()
        self.leds.set_state('IDLE')
        
        # Shared audio buffer for visualization (fed by audio bridge thread)
        self.leds.audio_buffer = deque(maxlen=30)
        logger.info("✓ LED controller ready (with audio buffer)")

        # Initialize wake word detection
        logger.info(f"Initializing wake word detection ('{WAKE_WORD[0]}')...")
        self.porcupine = pvporcupine.create(
            access_key=PORCUPINE_KEY,
            keywords=WAKE_WORD,
            sensitivities=[0.7]  # Higher = more sensitive (default 0.5)
        )
        logger.info("✓ Porcupine loaded")

        # Initialize Vosk STT
        logger.info("Initializing OpenAI Whisper client...")
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("✓ Whisper API ready")

        # Initialize Piper TTS
        logger.info("Loading Piper TTS model...")
        self.tts_voice = PiperVoice.load(PIPER_MODEL_PATH)
        logger.info("✓ Piper TTS loaded")

        # Open microphone
        logger.info(f"Opening microphone via arecord: {AUDIO_DEVICE}")
        self.mic_proc = subprocess.Popen(
            ["arecord", "-D", AUDIO_DEVICE, "-f", "S16_LE", "-c", "2",
             "-r", str(self.porcupine.sample_rate), "-t", "raw"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0
        )
        self.mic_frame_bytes = self.porcupine.frame_length * 2 * 2
        logger.info("\u2713 Microphone ready (arecord subprocess)")

        # Moneo session
        self.session_id = f"oracle-{int(time.time())}"
        logger.info(f"✓ Session ID: {self.session_id}")

        # Conversation history for multi-turn conversations
        self.conversation_history = []
        self.conversation_timeout = 300  # 5 minutes
        self.last_interaction = 0
        logger.info("✓ Conversation tracking initialized (5min timeout)")

        # Threads
        self.spotify_monitor_thread = None
        self.wake_word_thread = None

        # Ensure volume is at good level on startup
        current_vol = self.get_current_volume()
        if current_vol < 80:
            logger.info(f"📢 Resetting volume from {current_vol} to 127")
            self.set_volume(127)
        else:
            logger.info(f"✓ Volume OK: {current_vol}")
        
        logger.info("✓ Oracle Master Service initialized")
        logger.info("=" * 60)
    # ==================== VOLUME DUCKING ====================

    def get_current_volume(self):
        try:
            result = subprocess.run(
                ["amixer", "-c", "3", "get", "Headphone"],
                capture_output=True,
                text=True,
                timeout=1
            )
            match = re.search(r"Playback (\d+)", result.stdout)
            if match:
                return int(match.group(1))
            return 127
        except:
            return 127

    def set_volume(self, volume):
        try:
            subprocess.run(
                ["amixer", "-c", "3", "set", "Headphone", str(volume)],
                capture_output=True,
                timeout=1
            )
            logger.debug(f"Volume set to {volume}")
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")

    def duck_volume(self):
        current_vol = self.get_current_volume()
        
        # Sanity check: if volume is suspiciously low, reset it first
        if current_vol < 50:
            logger.warning(f"⚠️  Volume too low ({current_vol}), resetting to 127")
            self.set_volume(127)
            current_vol = 127
        
        self.original_volume = current_vol
        
        # Calculate duck level with absolute minimum
        duck_level = int(current_vol * 0.15)
        duck_level = max(duck_level, 15)  # Never below 15 (audible)
        
        self.set_volume(duck_level)
        logger.info(f"🔉 Volume ducked: {self.original_volume} → {duck_level}")

    def restore_volume(self):
        if hasattr(self, "original_volume"):
            self.set_volume(self.original_volume)
            logger.info(f"🔊 Volume restored: {self.original_volume}")



    # ==================== SPOTIFY PLAYBACK CONTROL ====================

    def pause_spotify(self):
        try:
            # Stop Raspotify service to release audio device
            subprocess.run(['systemctl', 'stop', 'raspotify'], capture_output=True, timeout=3)
            logger.info('⏸️  Raspotify stopped for TTS')
            return True
        except Exception as e:
            logger.error(f'Failed to stop Raspotify: {e}')
            return False

    def resume_spotify(self):
        try:
            # Restart Raspotify service
            subprocess.run(['systemctl', 'start', 'raspotify'], capture_output=True, timeout=5)
            logger.info('▶️  Raspotify restarted')
            return True
        except Exception as e:
            logger.error(f'Failed to restart Raspotify: {e}')
            return False
    # ==================== SPOTIFY MONITORING ====================

    def check_spotify_status(self):
        """Check if Spotify (Raspotify) is currently playing"""
        try:
            # Check if librespot process is running
            result = subprocess.run(
                ['pgrep', '-x', 'librespot'],
                capture_output=True,
                timeout=1
            )
            
            # If librespot is running, Spotify is connected
            # We assume MUSIC state when connected (visual feedback always on)
            return result.returncode == 0

        except Exception as e:
            logger.debug(f"Spotify check error: {e}")
            return False

    def monitor_spotify_loop(self):
        """Background thread: Monitor Spotify and update LED state"""
        logger.info("[Spotify Monitor] Thread started")
        last_state = None

        while self.running:
            try:
                is_playing = self.check_spotify_status()

                # State change detected
                if is_playing != last_state:
                    if is_playing and not self.in_voice_interaction:
                        logger.info("🎵 Spotify started - switching to MUSIC state")
                        self.leds.set_state('MUSIC')
                        self.spotify_playing = True
                    elif not is_playing and self.leds.current_state == 'MUSIC':
                        logger.info("⏸️  Spotify stopped - returning to IDLE")
                        self.leds.set_state('IDLE')
                        self.spotify_playing = False

                    last_state = is_playing

                time.sleep(2)  # Check every 2 seconds

            except Exception as e:
                logger.error(f"[Spotify Monitor] Error: {e}")
                time.sleep(5)

        logger.info("[Spotify Monitor] Thread stopped")

    # ==================== WAKE WORD DETECTION ====================

    def wake_word_detection_loop(self):
        """Background thread: Listen for wake word (even during music)"""
        logger.info(f"[Wake Word] Thread started - listening for '{WAKE_WORD[0].upper()}'")
        frame_count = 0

        logger.info("[Wake Word] Entering read loop...")
        while self.running:
            try:
                # Read from mic pipe, handling mic kill/restart during sessions
                try:
                    mic_fd = self.mic_proc.stdout.fileno()
                except (ValueError, AttributeError, OSError):
                    # Mic was killed, wait for restart
                    time.sleep(0.1)
                    continue

                data = b''
                while len(data) < self.mic_frame_bytes:
                    try:
                        chunk = os.read(mic_fd, self.mic_frame_bytes - len(data))
                    except OSError:
                        chunk = b''
                    if not chunk:
                        # Pipe closed (mic was killed) - wait for restart
                        time.sleep(0.1)
                        break
                    data += chunk
                if len(data) < self.mic_frame_bytes:
                    continue
                length = self.porcupine.frame_length

                if length > 0:
                    frame_count += 1
                    if frame_count % 200 == 1:
                        import numpy as _np
                        _s = _np.frombuffer(data[:80], dtype=_np.int16)
                        _rms = _np.sqrt(_np.mean(_s.astype(float)**2))
                        logger.info(f"[Wake Word] Frame {frame_count}, RMS={_rms:.0f}")

                    # If Realtime session active, feed audio there
                    if self.realtime_session_active and self.current_session:
                        self.current_session.feed_audio(length, data)
                        continue

                    # Convert stereo to mono
                    audio = struct.unpack(f'{length * 2}h', data)
                    mono = [int((audio[i] + audio[i+1]) / 2) for i in range(0, len(audio), 2)]

                    if len(mono) >= self.porcupine.frame_length:
                        pcm = mono[:self.porcupine.frame_length]
                        keyword_index = self.porcupine.process(pcm)

                        if keyword_index >= 0:
                            logger.info(f"🔊 WAKE WORD DETECTED at {datetime.now().strftime('%H:%M:%S')}")
                            self.handle_wake_word()

            except alsaaudio.ALSAAudioError:
                continue
            except Exception as e:
                logger.error(f"[Wake Word] Error: {e}")
                time.sleep(0.1)

        logger.info("[Wake Word] Thread stopped")

    @staticmethod
    def _generate_chime():
        """Generate a short two-tone chime (ascending, ~200ms)."""
        import numpy as _np
        rate = 44100
        t1 = _np.linspace(0, 0.1, int(rate * 0.1), False)
        t2 = _np.linspace(0, 0.1, int(rate * 0.1), False)
        # Two ascending tones: 800Hz -> 1200Hz
        tone1 = (_np.sin(2 * _np.pi * 800 * t1) * 16000).astype(_np.int16)
        tone2 = (_np.sin(2 * _np.pi * 1200 * t2) * 16000).astype(_np.int16)
        # Apply fade in/out
        fade = _np.linspace(0, 1, len(tone1) // 4)
        tone1[:len(fade)] = (tone1[:len(fade)] * fade).astype(_np.int16)
        tone1[-len(fade):] = (tone1[-len(fade):] * fade[::-1]).astype(_np.int16)
        tone2[:len(fade)] = (tone2[:len(fade)] * fade).astype(_np.int16)
        tone2[-len(fade):] = (tone2[-len(fade):] * fade[::-1]).astype(_np.int16)
        return _np.concatenate([tone1, tone2]).tobytes()

    def _mute_mic(self):
        """Kill arecord to prevent echo during Oracle speech."""
        if hasattr(self, 'mic_proc') and self.mic_proc and self.mic_proc.poll() is None:
            self.mic_proc.terminate()
            self.mic_proc.wait(timeout=2)
            logger.info("[Mic] Muted (arecord killed)")

    def _unmute_mic(self):
        """Restart arecord after Oracle finishes speaking."""
        import subprocess as _sp
        self.mic_proc = _sp.Popen(
            ["arecord", "-D", AUDIO_DEVICE, "-f", "S16_LE", "-c", "2",
             "-r", str(self.porcupine.sample_rate), "-t", "raw"],
            stdout=_sp.PIPE,
            stderr=_sp.DEVNULL,
            bufsize=0
        )
        logger.info("[Mic] Unmuted (arecord restarted)")

    def handle_wake_word(self):
        """Handle wake word - start Realtime API conversation (non-blocking).

        Must NOT block the wake word thread, since that thread reads the mic
        and feeds audio to the Realtime session.
        """
        logger.info("[Realtime] Starting conversation session...")

        # Track state
        self.realtime_session_active = True
        self._spotify_was_playing = self.spotify_playing

        # Pause Spotify if playing
        if self._spotify_was_playing:
            self.pause_spotify()

        # Confirmation sound + set listening state
        self.leds.set_state("LISTENING")
        try:
            # Play a short confirmation tone so user knows Oracle heard them
            subprocess.Popen(
                ['aplay', '-D', 'plughw:2,0', '-f', 'S16_LE', '-c', '1', '-r', '44100', '-t', 'raw'],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            ).communicate(input=self._generate_chime(), timeout=2)
        except Exception:
            pass

        # Create Realtime API session
        session = OracleRealtimeSession(
            api_key=OPENAI_API_KEY,
            system_prompt=ORACLE_SYSTEM_PROMPT,
            tools=REALTIME_TOOLS,
            tool_handler=self.handle_tool_call,
            on_speech_started=lambda: self.leds.set_state("LISTENING"),
            on_speech_ended=lambda: self.leds.set_state("THINKING"),
            on_audio_started=lambda: self.leds.set_state("SPEAKING"),
            on_response_done=lambda: None,
            on_error=lambda msg: logger.error(f"[Realtime] Error: {msg}"),
            on_mic_mute=self._mute_mic,
            on_mic_unmute=self._unmute_mic,
            session_timeout=20
        )

        self.current_session = session
        session.start()

        # Monitor session end in a separate thread (don't block wake word thread)
        def _monitor_session():
            while session.active and self.running:
                time.sleep(0.1)

            # Cleanup
            self.current_session = None
            self.realtime_session_active = False
            logger.info("[Realtime] Session ended, restoring state...")

            if self._spotify_was_playing:
                self.resume_spotify()
                time.sleep(1)
                self.leds.set_state("MUSIC")
                logger.info("Returned to MUSIC state")
            else:
                self.leds.set_state("IDLE")
                logger.info("Returned to IDLE state")

        monitor = threading.Thread(target=_monitor_session, daemon=True)
        monitor.start()

        # Return immediately - wake word thread keeps running and feeds audio

    def record_voice_command(self):
        """Record audio after wake word"""
        logger.info(f"🎙️  Recording for {RECORD_SECONDS} seconds...")

        frames = []
        num_frames = int(SAMPLE_RATE / self.porcupine.frame_length * RECORD_SECONDS)

        for i in range(num_frames):
            try:
                data = self.mic_proc.stdout.read(self.mic_frame_bytes)
                if data and len(data) >= self.mic_frame_bytes:
                    frames.append(data)
                else:
                    time.sleep(0.01)
            except Exception:
                continue

        wav_file = "/tmp/oracle_command.wav"
        with wave.open(wav_file, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b''.join(frames))

        logger.info("✓ Recording complete")
        return wav_file

    def transcribe(self, audio_file):
        """Transcribe audio using OpenAI Whisper API"""
        logger.info("🤖 Transcribing with Whisper API...")

        try:
            with open(audio_file, "rb") as f:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language="en"
                )
            transcription = response.text.strip()
            logger.info(f"📝 USER SAID: '{transcription}'")
            return transcription
        except Exception as e:
            logger.error(f"Whisper API error: {e}")
            return ""

    # ==================== AI INTEGRATION ====================

    def query_ai(self, user_message):
        '''Send message to Moneo Core API with conversation history'''
        logger.info('Querying Moneo Core: http://100.71.119.36:3002/api/voice/chat')
        self.leds.set_state('THINKING')

        # Check if conversation has expired
        current_time = time.time()
        if current_time - self.last_interaction > self.conversation_timeout:
            if len(self.conversation_history) > 0:
                logger.info(f'💭 Conversation expired ({len(self.conversation_history)} turns cleared)')
            self.conversation_history = []

        # Add user message to history
        self.conversation_history.append({
            'role': 'user',
            'content': user_message,
            'timestamp': current_time
        })

        # Log conversation context
        if len(self.conversation_history) > 1:
            logger.info(f'💭 Multi-turn conversation ({len(self.conversation_history)//2} turns)')

        try:
            response = requests.post(
                'http://100.71.119.36:3002/api/voice/chat',
                headers={
                    'X-API-Key': MONEO_API_KEY,
                    'Content-Type': 'application/json'
                },
                json={
                    'text': user_message + ' (Keep response to 1-2 short sentences, no stage directions or asterisks)',
                    'history': self.conversation_history[-10:],  # Last 5 turns (10 messages)
                    'sessionId': self.session_id,
                    'userId': 'trevor'
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                response_text = data.get('text', '')

                # Add response to history
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response_text,
                    'timestamp': time.time()
                })

                # Update last interaction time
                self.last_interaction = time.time()

                return response_text
            else:
                logger.error(f'Moneo API error: {response.status_code}')
                return ''

        except Exception as e:
            logger.error(f'Moneo API error: {e}')
            return ''
    
    def speak(self, text):
        logger.info('🔊 Speaking...')
        # Strip stage directions (text between asterisks)
        text = re.sub(r'\*[^*]+\*', '', text)
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        logger.info(f'TTS text ({len(text)} chars): {text[:100]}...')
        self.leds.set_state('SPEAKING')

        spotify_was_playing = self.spotify_playing
        if spotify_was_playing:
            self.pause_spotify()
            # Restore volume for TTS (Spotify is stopped, so duck doesn't apply)
            if hasattr(self, 'original_volume') and self.original_volume:
                self.set_volume(self.original_volume)
                logger.info(f'🔊 Volume restored to {self.original_volume} for TTS')
            import time
            time.sleep(0.5)  # Give it more time to fully stop

        try:
            # Generate all TTS audio first
            logger.info('Generating TTS audio...')
            audio_data = b''
            for audio_chunk in self.tts_voice.synthesize(text):
                audio_data += audio_chunk.audio_int16_bytes
            
            audio_size_kb = len(audio_data) / 1024
            duration_sec = len(audio_data) / (22050 * 2)
            logger.info(f'✓ TTS generated: {audio_size_kb:.1f}KB, ~{duration_sec:.1f}s')
            
            # Play audio via aplay
            logger.info('Playing audio via aplay...')
            aplay_process = subprocess.Popen(
                ['aplay', '-D', AUDIO_DEVICE, '-r', '22050', '-f', 'S16_LE', '-c', '1'],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = aplay_process.communicate(input=audio_data, timeout=60)
            
            if aplay_process.returncode == 0:
                logger.info('✓ Speech playback complete')
            else:
                err_msg = stderr.decode() if stderr else 'unknown error'
                logger.error(f'aplay failed (code {aplay_process.returncode}): {err_msg}')
        except subprocess.TimeoutExpired:
            logger.error('TTS playback timed out after 60 seconds')
            aplay_process.kill()
        except Exception as e:
            logger.error(f'TTS error: {e}')
            import traceback
            logger.error(traceback.format_exc())
        finally:
            if spotify_was_playing:
                import time
                time.sleep(1.0)
                self.resume_spotify()

    def fifo_reader_loop(self):
        """Read scheduled announcements from FIFO (from oracle_scheduler)"""
        logger.info('[FIFO Reader] Thread started - listening for scheduled announcements')

        while self.running:
            try:
                # Recreate FIFO if it doesn't exist
                if not os.path.exists(self.fifo_path):
                    try:
                        os.mkfifo(self.fifo_path)
                        logger.info(f'Created FIFO: {self.fifo_path}')
                    except OSError as e:
                        logger.error(f'Failed to create FIFO: {e}')
                        time.sleep(5)
                        continue

                # Open FIFO for reading (blocking until writer connects)
                logger.debug('Waiting for FIFO writer...')
                with open(self.fifo_path, 'r') as fifo:
                    while self.running:
                        line = fifo.readline()
                        if not line:
                            break  # Writer closed, reopen FIFO

                        line = line.strip()
                        if not line:
                            continue

                        try:
                            # Parse JSON message
                            message = json.loads(line)
                            text = message.get('text', '')
                            priority = message.get('priority', 'medium')

                            if not text:
                                continue

                            logger.info(f'[FIFO] Received announcement ({priority}): {text[:100]}...')

                            # Process based on priority
                            if priority == 'urgent':
                                self.process_announcement_urgent(text)
                            elif priority == 'medium':
                                self.process_announcement_medium(text)
                            else:
                                self.process_announcement_low(text)

                        except json.JSONDecodeError as e:
                            logger.error(f'[FIFO] Invalid JSON: {line} - {e}')
                        except Exception as e:
                            logger.error(f'[FIFO] Error processing message: {e}')

            except Exception as e:
                logger.error(f'[FIFO Reader] Error: {e}')
                time.sleep(5)

    def process_announcement_urgent(self, text):
        """Interrupt immediately"""
        logger.info('[Announcement] URGENT - interrupting immediately')
        self.in_voice_interaction = True
        self.speak(text)
        self.in_voice_interaction = False

    def process_announcement_medium(self, text):
        """Duck music and announce"""
        if self.in_voice_interaction:
            logger.info('[Announcement] MEDIUM - waiting for conversation to finish')
            start_time = time.time()
            while self.in_voice_interaction and (time.time() - start_time) < 60:
                time.sleep(1)

        logger.info('[Announcement] MEDIUM - speaking over music')
        self.speak(text)

    def process_announcement_low(self, text):
        """Wait for silence"""
        logger.info('[Announcement] LOW - waiting for silence')
        start_time = time.time()
        while (self.spotify_playing or self.in_voice_interaction) and (time.time() - start_time) < 300:
            time.sleep(5)

        if time.time() - start_time >= 300:
            logger.warning('[Announcement] LOW - timeout waiting for silence, speaking anyway')

        logger.info('[Announcement] LOW - speaking in silence')
        self.speak(text)


    # ==================== AUDIO BRIDGE ====================

    def audio_bridge_loop(self):
        """Capture audio from loopback and feed visualization buffer.

        Speaker output is handled by the external oracle-audio-bridge service
        (arecord|aplay) because the WM8960 can't handle simultaneous
        mic capture and aplay playback from the same process.
        """
        logger.info("[Audio Bridge] Starting loopback capture for visualization...")

        capture = None

        # Set WM8960 volumes on startup
        try:
            subprocess.run(['amixer', '-c', '4', 'sset', 'Headphone', '127'], capture_output=True, timeout=2)
            subprocess.run(['amixer', '-c', '4', 'sset', 'Speaker', '127'], capture_output=True, timeout=2)
            subprocess.run(['amixer', '-c', '4', 'sset', 'Playback', '255'], capture_output=True, timeout=2)
            logger.info("[Audio Bridge] WM8960 volumes set")
        except Exception as e:
            logger.warning(f"[Audio Bridge] Volume set failed: {e}")

        while self.running:
            try:
                # Open loopback capture if needed
                if capture is None:
                    capture = alsaaudio.PCM(
                        alsaaudio.PCM_CAPTURE,
                        alsaaudio.PCM_NORMAL,
                        device='plughw:2,1',
                        channels=2,
                        rate=44100,
                        format=alsaaudio.PCM_FORMAT_S16_LE,
                        periodsize=1024
                    )
                    logger.info("[Audio Bridge] Loopback capture opened (plughw:2,1)")

                # Read audio from loopback
                length, data = capture.read()

                if length > 0:
                    # Feed visualization buffer
                    self.leds.audio_buffer.append((length, data))

            except alsaaudio.ALSAAudioError as e:
                logger.error(f"[Audio Bridge] ALSA error: {e}")
                if capture:
                    try: capture.close()
                    except: pass
                    capture = None
                time.sleep(1)
            except Exception as e:
                logger.error(f"[Audio Bridge] Error: {e}")
                time.sleep(0.1)

        # Cleanup
        if capture:
            try: capture.close()
            except: pass
        logger.info("[Audio Bridge] Stopped")


    def handle_tool_call(self, name, args):
        """Execute a tool call from the Realtime API."""
        logger.info(f"[Tool] Executing: {name}")
        if name == "spotify_play":
            return self._tool_spotify_play(args.get("query", ""))
        elif name == "spotify_control":
            return self._tool_spotify_control(args.get("action", ""))
        elif name == "moneo_query":
            return self._tool_moneo_query(args.get("question", ""))
        elif name == "debug_system":
            return self._tool_debug_system(args.get("check", "all"))
        elif name == "set_reminder":
            return self._tool_set_reminder(
                args.get("message", ""),
                args.get("time", ""),
                args.get("date", "today"),
                args.get("priority", "medium")
            )
        elif name == "create_calendar_event":
            return self._tool_create_calendar_event(args)
        elif name == "send_email":
            return self._tool_send_email(args)
        elif name == "run_command":
            return self._tool_run_command(args.get("command", ""))
        else:
            return {"error": f"Unknown tool: {name}"}

    def _tool_spotify_play(self, query):
        """Search and play music on Spotify."""
        try:
            # Start Raspotify if not running
            subprocess.run(['systemctl', 'start', 'raspotify'], capture_output=True, timeout=5)
            time.sleep(1)
            return {
                "status": "started",
                "message": f"Raspotify is running. Tell Trevor to search for '{query}' in Spotify and select the Oracle speaker. Direct Spotify search-and-play will be added soon."
            }
        except Exception as e:
            return {"error": str(e)}

    def _tool_spotify_control(self, action):
        """Control Spotify playback."""
        try:
            if action == "pause":
                subprocess.run(['systemctl', 'stop', 'raspotify'], capture_output=True, timeout=3)
                self.spotify_playing = False
                return {"status": "paused"}
            elif action == "resume":
                subprocess.run(['systemctl', 'start', 'raspotify'], capture_output=True, timeout=5)
                return {"status": "resumed"}
            elif action in ("next", "previous"):
                return {"status": "not_available", "message": f"'{action}' requires Spotify Web API - coming soon"}
            else:
                return {"error": f"Unknown action: {action}"}
        except Exception as e:
            return {"error": str(e)}

    def _tool_moneo_query(self, question):
        """Query Moneo Core API (Claude with full context)."""
        try:
            response = requests.post(
                MONEO_API_URL,
                headers={
                    'X-API-Key': MONEO_API_KEY,
                    'Content-Type': 'application/json'
                },
                json={
                    'text': question + ' (Keep response to 2-3 short sentences)',
                    'sessionId': self.session_id,
                    'userId': 'trevor'
                },
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                return {"answer": data.get("text", "No response from Moneo")}
            else:
                return {"error": f"Moneo returned {response.status_code}"}
        except requests.exceptions.Timeout:
            return {"error": "Moneo API timed out"}
        except Exception as e:
            return {"error": str(e)}


    def _tool_create_calendar_event(self, args):
        """Create a Google Calendar event via Moneo API."""
        try:
            payload = {
                "summary": args.get("summary", ""),
                "startTime": args.get("start_time", ""),
            }
            if args.get("end_time"):
                payload["endTime"] = args["end_time"]
            if args.get("description"):
                payload["description"] = args["description"]
            if args.get("location"):
                payload["location"] = args["location"]

            response = requests.post(
                "http://100.71.119.36:3002/api/voice/calendar/create",
                headers={
                    "X-API-Key": MONEO_API_KEY,
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"[Calendar] Event created: {args.get('summary')}")
                return {"status": "created", "summary": args.get("summary"), "start_time": args.get("start_time")}
            else:
                return {"error": f"Calendar API returned {response.status_code}: {response.text[:200]}"}

        except Exception as e:
            return {"error": str(e)}

    def _tool_send_email(self, args):
        """Send an email via Moneo API."""
        try:
            to = args.get("to", "")
            subject = args.get("subject", "")
            body = args.get("body", "")

            if not to or not subject or not body:
                return {"error": "Missing required fields: to, subject, body"}

            response = requests.post(
                "http://100.71.119.36:3002/api/voice/email/send",
                headers={
                    "X-API-Key": MONEO_API_KEY,
                    "Content-Type": "application/json"
                },
                json={"to": to, "subject": subject, "body": body},
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"[Email] Sent to {to}: {subject}")
                return {"status": "sent", "to": to, "subject": subject}
            else:
                return {"error": f"Email API returned {response.status_code}: {response.text[:200]}"}

        except Exception as e:
            return {"error": str(e)}

    def _tool_run_command(self, command):
        """Run a shell command on the Pi."""
        # Block dangerous commands
        blocked = ["rm -rf /", "mkfs", "dd if=", "> /dev/sd", "shutdown", "reboot", "halt"]
        for b in blocked:
            if b in command:
                return {"error": f"Blocked dangerous command containing '{b}'"}

        try:
            result = subprocess.run(
                command, shell=True,
                capture_output=True, text=True, timeout=15
            )
            output = result.stdout.strip()
            error = result.stderr.strip()

            # Truncate long output for voice
            if len(output) > 500:
                output = output[:500] + "... (truncated)"
            if len(error) > 300:
                error = error[:300] + "... (truncated)"

            response = {"exit_code": result.returncode}
            if output:
                response["output"] = output
            if error and result.returncode != 0:
                response["error_output"] = error

            logger.info(f"[Command] '{command}' -> exit {result.returncode}")
            return response

        except subprocess.TimeoutExpired:
            return {"error": "Command timed out after 15 seconds"}
        except Exception as e:
            return {"error": str(e)}

    def _tool_debug_system(self, check):
        """Run system diagnostics on the Oracle speaker."""
        results = {}
        try:
            if check in ("services", "all"):
                svc_check = subprocess.run(
                    ["systemctl", "is-active", "oracle-master", "raspotify",
                     "oracle-scheduler", "oracle-dashboard"],
                    capture_output=True, text=True, timeout=5
                )
                services = dict(zip(
                    ["oracle-master", "raspotify", "oracle-scheduler", "oracle-dashboard"],
                    svc_check.stdout.strip().split("\n")
                ))
                results["services"] = services

            if check in ("audio", "all"):
                # Check sound cards
                cards = subprocess.run(["cat", "/proc/asound/cards"],
                    capture_output=True, text=True, timeout=3)
                # Check loopback status
                loopback = subprocess.run(
                    ["cat", "/proc/asound/Loopback/pcm0p/sub0/status"],
                    capture_output=True, text=True, timeout=3)
                # Check volumes
                vol = subprocess.run(["amixer", "-c", "4", "get", "Headphone"],
                    capture_output=True, text=True, timeout=3)
                results["audio"] = {
                    "sound_cards": cards.stdout.strip(),
                    "loopback_playback": loopback.stdout.strip().split("\n")[0] if loopback.stdout.strip() else "closed",
                    "headphone_volume": vol.stdout.strip().split("\n")[-1].strip() if vol.stdout else "unknown"
                }

            if check in ("logs_master", "all"):
                logs = subprocess.run(
                    ["journalctl", "-u", "oracle-master", "--no-pager", "-n", "20", "--since", "5 min ago"],
                    capture_output=True, text=True, timeout=5)
                # Filter to important lines
                important = [l for l in logs.stdout.split("\n")
                    if any(k in l.lower() for k in ["error", "warn", "fail", "started", "stopped", "ready"])]
                results["master_logs"] = important[-10:] if important else ["No errors in last 5 minutes"]

            if check in ("logs_spotify", "all"):
                logs = subprocess.run(
                    ["journalctl", "-u", "raspotify", "--no-pager", "-n", "15"],
                    capture_output=True, text=True, timeout=5)
                important = [l for l in logs.stdout.split("\n")
                    if any(k in l.lower() for k in ["error", "warn", "fail", "started", "stopped", "connect"])]
                results["spotify_logs"] = important[-10:] if important else ["No issues found"]

            if check in ("disk", "all"):
                df = subprocess.run(["df", "-h", "/"],
                    capture_output=True, text=True, timeout=3)
                lines = df.stdout.strip().split("\n")
                results["disk"] = lines[-1] if len(lines) > 1 else "unknown"

            if check in ("network", "all"):
                ts = subprocess.run(["tailscale", "status", "--json"],
                    capture_output=True, text=True, timeout=5)
                if ts.returncode == 0:
                    import json as _json
                    ts_data = _json.loads(ts.stdout)
                    results["network"] = {
                        "tailscale": "connected" if ts_data.get("BackendState") == "Running" else "disconnected",
                        "hostname": ts_data.get("Self", {}).get("HostName", "unknown")
                    }
                else:
                    results["network"] = {"tailscale": "error checking status"}

            return results

        except Exception as e:
            return {"error": str(e), "partial_results": results}

    def _tool_set_reminder(self, message, reminder_time, date="today", priority="medium"):
        """Schedule a spoken reminder via the oracle scheduler."""
        import json as _json
        from datetime import datetime as _dt, timedelta

        try:
            # Parse the time
            hour, minute = map(int, reminder_time.split(":"))

            # Parse the date
            now = _dt.now()
            if not date or date.lower() == "today":
                target_date = now.date()
            elif date.lower() == "tomorrow":
                target_date = (now + timedelta(days=1)).date()
            else:
                target_date = _dt.strptime(date, "%Y-%m-%d").date()

            target_dt = _dt.combine(target_date, _dt.min.time().replace(hour=hour, minute=minute))

            # Check if time is in the past
            if target_dt < now:
                return {"error": f"Cannot set reminder in the past ({target_dt.strftime('%I:%M %p')})"}

            # Write reminder to a file that the scheduler can pick up
            reminder = {
                "message": message,
                "time": target_dt.strftime("%Y-%m-%d %H:%M"),
                "priority": priority,
                "created": now.strftime("%Y-%m-%d %H:%M:%S")
            }

            # Append to reminders file
            reminders_file = "/home/tyahn/oracle_reminders.json"
            try:
                with open(reminders_file, "r") as f:
                    reminders = _json.load(f)
            except (FileNotFoundError, _json.JSONDecodeError):
                reminders = []

            reminders.append(reminder)

            with open(reminders_file, "w") as f:
                _json.dump(reminders, f, indent=2)

            # Also try to write directly to scheduler FIFO for immediate scheduling
            fifo_path = "/tmp/oracle_remind.fifo"
            try:
                import os
                if os.path.exists(fifo_path):
                    fd = os.open(fifo_path, os.O_WRONLY | os.O_NONBLOCK)
                    os.write(fd, (_json.dumps(reminder) + "\n").encode())
                    os.close(fd)
                    logger.info(f"[Reminder] Sent to scheduler FIFO: {reminder_time}")
            except Exception:
                pass  # FIFO not available, file-based reminder still saved

            friendly_time = target_dt.strftime("%I:%M %p on %B %d")
            logger.info(f"[Reminder] Set for {friendly_time}: {message}")

            return {
                "status": "set",
                "delivery_time": friendly_time,
                "message": message,
                "priority": priority
            }

        except ValueError as e:
            return {"error": f"Could not parse time/date: {e}"}
        except Exception as e:
            return {"error": str(e)}

    def run(self):
        """Main service loop - runs threads"""
        logger.info('Starting Oracle Master Service...')
        self.running = True
        
        try:
            # Start background threads
            bridge_thread = threading.Thread(target=self.audio_bridge_loop, daemon=True)
            spotify_thread = threading.Thread(target=self.monitor_spotify_loop, daemon=True)
            wake_thread = threading.Thread(target=self.wake_word_detection_loop, daemon=True)
            fifo_thread = threading.Thread(target=self.fifo_reader_loop, daemon=True)

            bridge_thread.start()
            spotify_thread.start()
            wake_thread.start()
            fifo_thread.start()

            logger.info('[Audio Bridge] Thread started')
            logger.info('[Spotify Monitor] Thread started')
            logger.info('[Wake Word] Thread started - listening for \'JARVIS\'')
            logger.info('[FIFO Reader] Thread started')
            logger.info('✓ All threads started')
            logger.info('✓ Wake word: \'JARVIS\' - works even during music')
            logger.info('✓ Spotify monitoring active')
            logger.info('✓ Oracle is ready!')
            logger.info('============================================================')
            
            # Keep main thread alive
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info('Shutting down Oracle Master Service...')
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'porcupine'):
            self.porcupine.delete()
        if hasattr(self, 'mic_proc'):
            self.mic_proc.terminate()
        if hasattr(self, 'leds'):
            self.leds.cleanup()
        logger.info('✓ Shutdown complete')


# ==================== MAIN ====================

if __name__ == '__main__':
    oracle = OracleMasterService()
    oracle.run()
