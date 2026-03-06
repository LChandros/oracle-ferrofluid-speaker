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

# Import LED controller
from oracle_led_states_music import OracleLEDController

# ==================== CONFIGURATION ====================

# Audio Hardware
AUDIO_DEVICE = 'plughw:4,0'
SAMPLE_RATE = 16000

# Wake Word (Porcupine)
PORCUPINE_KEY = 'CVkoeHnOG0NKFpiT3LDBgyS9tSuuC6cV1p2bZJSMO9d27u0ECO0gjA=='
WAKE_WORD = ['jarvis']
RECORD_SECONDS = 5

# Moneo API (with Claude fallback)
MONEO_API_URL = os.getenv('MONEO_API_URL', 'http://100.71.119.36:3002/api/voice/chat')
MONEO_API_KEY = os.getenv('MONEO_API_KEY', 'moneo-voice-assistant-key')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # Required for Claude fallback
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')  # Optional: direct Claude API fallback

# Models
VOSK_MODEL_PATH = "/home/tyahn/vosk-model-small-en-us-0.15"
PIPER_MODEL_PATH = "/home/tyahn/en_US-lessac-medium.onnx"

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

        # Announcement queue for scheduled reminders
        self.announcement_queue = queue.Queue()
        self.fifo_path = '/tmp/oracle_announce.fifo'

        # Initialize LED controller (single instance - prevents conflicts)
        logger.info("Initializing LED controller...")
        self.leds = OracleLEDController()
        self.leds.set_state('IDLE')
        logger.info("✓ LED controller ready")

        # Initialize wake word detection
        logger.info(f"Initializing wake word detection ('{WAKE_WORD[0]}')...")
        self.porcupine = pvporcupine.create(
            access_key=PORCUPINE_KEY,
            keywords=WAKE_WORD
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
        logger.info(f"Opening microphone: {AUDIO_DEVICE}")
        self.mic = alsaaudio.PCM(
            alsaaudio.PCM_CAPTURE,
            alsaaudio.PCM_NORMAL,
            device=AUDIO_DEVICE,
            channels=2,
            rate=self.porcupine.sample_rate,
            format=alsaaudio.PCM_FORMAT_S16_LE,
            periodsize=self.porcupine.frame_length
        )
        logger.info("✓ Microphone ready")

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

        while self.running:
            try:
                length, data = self.mic.read()

                if length > 0:
                    frame_count += 1

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

    def handle_wake_word(self):
        """Handle wake word detection and process voice command"""
        # Mark as in voice interaction (prevents Spotify state override)
        self.in_voice_interaction = True

        # Duck the volume (Alexa-style)
        self.duck_volume()

        # Set LISTENING state
        self.leds.set_state('LISTENING')

        # Record command
        audio_file = self.record_voice_command()
        
        # Transcribe
        user_text = self.transcribe(audio_file)

        if user_text:
            logger.info(f"📝 USER SAID: '{user_text}'")

            # Query Moneo/Claude
            response = self.query_ai(user_text)

            if response:
                logger.info(f"🤖 ORACLE RESPONSE: {response[:100]}...")
                self.speak(response)
        else:
            logger.warning("⚠️  No speech detected")

        # Restore volume
        self.restore_volume()

        # Return to appropriate state
        self.in_voice_interaction = False
        if self.spotify_playing:
            logger.info("🎵 Returning to MUSIC state")
            self.leds.set_state('MUSIC')
        else:
            logger.info("💤 Returning to IDLE state")
            self.leds.set_state('IDLE')

    def record_voice_command(self):
        """Record audio after wake word"""
        logger.info(f"🎙️  Recording for {RECORD_SECONDS} seconds...")

        frames = []
        num_frames = int(SAMPLE_RATE / self.porcupine.frame_length * RECORD_SECONDS)

        for i in range(num_frames):
            try:
                length, data = self.mic.read()
                if length > 0:
                    frames.append(data)
            except alsaaudio.ALSAAudioError:
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

    def run(self):
        """Main service loop - runs threads"""
        logger.info('Starting Oracle Master Service...')
        self.running = True
        
        try:
            # Start background threads
            spotify_thread = threading.Thread(target=self.monitor_spotify_loop, daemon=True)
            wake_thread = threading.Thread(target=self.wake_word_detection_loop, daemon=True)
            fifo_thread = threading.Thread(target=self.fifo_reader_loop, daemon=True)

            spotify_thread.start()
            wake_thread.start()
            fifo_thread.start()

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
        if hasattr(self, 'mic'):
            self.mic.close()
        if hasattr(self, 'leds'):
            self.leds.cleanup()
        logger.info('✓ Shutdown complete')


# ==================== MAIN ====================

if __name__ == '__main__':
    oracle = OracleMasterService()
    oracle.run()
