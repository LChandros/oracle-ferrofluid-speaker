#!/usr/bin/env python3
"""
Oracle Ferrofluid Speaker - Web Dashboard
Voice Assistant with LED/Electromagnet Visualization
"""

from flask import Flask, render_template, request, jsonify
import requests
import os
import subprocess
import threading
import time
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
CONFIG_FILE = "/home/tyahn/oracle/dashboard/config.txt"
AUDIO_DIR = "/home/tyahn/oracle/dashboard/audio"
VISUALIZER_SCRIPT = "/home/tyahn/oracle/scripts/oracle_synced.py"

# API settings
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"
OPENAI_API_URL = "https://api.openai.com/v1"
MONEO_API_URL = "http://localhost:3002/api/voice"
MONEO_API_KEY = "moneo-voice-assistant-key"

# Global state
current_playback = None
is_playing = False

def load_config():
    """Load configuration from file"""
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    config[key] = value
    return config

def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        for key, value in config.items():
            f.write(f'{key}={value}\n')

def load_api_key():
    """Load ElevenLabs API key"""
    config = load_config()
    return config.get('ELEVENLABS_API_KEY')

def load_openai_key():
    """Load OpenAI API key"""
    config = load_config()
    return config.get('OPENAI_API_KEY')

def save_api_key(api_key):
    """Save ElevenLabs API key"""
    config = load_config()
    config['ELEVENLABS_API_KEY'] = api_key
    save_config(config)

def count_syllables(text):
    """Count syllables in text using vowel groups"""
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)

    vowels = 'aeiouy'
    syllable_count = 0
    previous_was_vowel = False

    for char in text:
        is_vowel = char in vowels
        if is_vowel and not previous_was_vowel:
            syllable_count += 1
        previous_was_vowel = is_vowel

    words = text.split()
    for word in words:
        if len(word) > 2 and word.endswith('e') and word[-2] not in vowels:
            syllable_count -= 1

    return max(1, syllable_count)

def transcribe_audio(audio_file):
    """Transcribe audio using OpenAI Whisper API"""
    api_key = load_openai_key()
    if not api_key:
        raise Exception("OpenAI API key not configured")

    url = f"{OPENAI_API_URL}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}

    with open(audio_file, 'rb') as f:
        files = {'file': f}
        data = {'model': 'whisper-1'}
        response = requests.post(url, headers=headers, files=files, data=data)

    if response.status_code != 200:
        raise Exception(f"Whisper API error: {response.status_code} - {response.text}")

    return response.json()['text']

def ask_moneo(text, session_id='oracle-dashboard'):
    """Send message to Moneo Core and get Claude's response"""
    url = f"{MONEO_API_URL}/chat"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": MONEO_API_KEY
    }
    data = {
        "message": text,
        "sessionId": session_id
    }

    response = requests.post(url, json=data, headers=headers, timeout=30)

    if response.status_code != 200:
        raise Exception(f"Moneo API error: {response.status_code} - {response.text}")

    result = response.json()
    return result.get('response', result.get('message', ''))

def get_available_voices():
    """Fetch available voices from ElevenLabs API"""
    api_key = load_api_key()
    if not api_key:
        return []

    try:
        headers = {"xi-api-key": api_key}
        response = requests.get(f"{ELEVENLABS_API_URL}/voices", headers=headers, timeout=5)

        if response.status_code == 200:
            voices_data = response.json()
            return voices_data.get('voices', [])
        else:
            return []
    except Exception as e:
        print(f"Error fetching voices: {e}")
        return []

def text_to_speech(text, voice_id):
    """Convert text to speech using ElevenLabs API"""
    api_key = load_api_key()
    if not api_key:
        raise Exception("ElevenLabs API key not configured")

    url = f"{ELEVENLABS_API_URL}/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 200:
        raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text}")

    timestamp = int(time.time())
    mp3_file = os.path.join(AUDIO_DIR, f"tts_{timestamp}.mp3")
    wav_file = os.path.join(AUDIO_DIR, f"tts_{timestamp}.wav")

    with open(mp3_file, 'wb') as f:
        f.write(response.content)

    subprocess.run([
        "ffmpeg", "-i", mp3_file, "-acodec", "pcm_s16le",
        "-ar", "44100", "-ac", "2", wav_file, "-y"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    os.remove(mp3_file)
    return str(wav_file)

def play_with_visualization(audio_file, syllable_count):
    """Play audio with LED/electromagnet visualization"""
    global is_playing

    try:
        is_playing = True
        subprocess.run(
            ["sudo", "python3", VISUALIZER_SCRIPT, audio_file, str(syllable_count)],
            check=True
        )
    except Exception as e:
        print(f"Playback error: {e}")
    finally:
        is_playing = False

@app.route('/')
def index():
    """Main dashboard page"""
    api_key_configured = load_api_key() is not None
    return render_template('index.html', api_key_configured=api_key_configured)

@app.route('/api/voices', methods=['GET'])
def voices():
    """Get available voices from ElevenLabs"""
    voices_list = get_available_voices()
    return jsonify({'voices': voices_list})

@app.route('/api/speak', methods=['POST'])
def speak():
    """Generate speech and play with visualization"""
    global current_playback, is_playing

    if is_playing:
        return jsonify({'error': 'Already playing'}), 400

    data = request.json
    text = data.get('text', '').strip()
    voice_id = data.get('voice_id')

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    if not voice_id:
        return jsonify({'error': 'No voice selected'}), 400

    try:
        syllable_count = count_syllables(text)
        print(f"Text: '{text}' -> {syllable_count} syllables")

        audio_file = text_to_speech(text, voice_id)

        playback_thread = threading.Thread(
            target=play_with_visualization,
            args=(audio_file, syllable_count)
        )
        playback_thread.daemon = True
        playback_thread.start()
        current_playback = playback_thread

        return jsonify({
            'success': True,
            'message': 'Playing...',
            'audio_file': os.path.basename(audio_file),
            'syllables': syllable_count
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/voice-chat', methods=['POST'])
def voice_chat():
    """Handle voice conversation: STT → Moneo → TTS → Play"""
    global current_playback, is_playing

    if is_playing:
        return jsonify({'error': 'Already playing'}), 400

    try:
        # Get uploaded audio file
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400

        audio_file = request.files['audio']
        voice_id = request.form.get('voice_id')

        if not voice_id:
            return jsonify({'error': 'No voice selected'}), 400

        # Save uploaded audio
        timestamp = int(time.time())
        temp_audio = os.path.join(AUDIO_DIR, f"recording_{timestamp}.webm")
        wav_audio = os.path.join(AUDIO_DIR, f"recording_{timestamp}.wav")

        audio_file.save(temp_audio)

        # Convert webm to wav for Whisper
        subprocess.run([
            "ffmpeg", "-i", temp_audio, "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1", wav_audio, "-y"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        os.remove(temp_audio)

        # Transcribe with Whisper
        print("Transcribing audio...")
        transcript = transcribe_audio(wav_audio)
        print(f"Transcript: {transcript}")

        # Clean up recording
        os.remove(wav_audio)

        # Ask Moneo (Claude)
        print("Asking Moneo...")
        response_text = ask_moneo(transcript)
        print(f"Moneo response: {response_text}")

        # Count syllables for visualization
        syllable_count = count_syllables(response_text)

        # Generate TTS
        print("Generating TTS...")
        response_audio = text_to_speech(response_text, voice_id)

        # Play with visualization
        playback_thread = threading.Thread(
            target=play_with_visualization,
            args=(response_audio, syllable_count)
        )
        playback_thread.daemon = True
        playback_thread.start()
        current_playback = playback_thread

        return jsonify({
            'success': True,
            'transcript': transcript,
            'response': response_text,
            'syllables': syllable_count
        })

    except Exception as e:
        print(f"Voice chat error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def status():
    """Get playback status"""
    return jsonify({
        'is_playing': is_playing,
        'api_key_configured': load_api_key() is not None
    })

@app.route('/api/config', methods=['POST'])
def configure():
    """Configure API key"""
    data = request.json
    api_key = data.get('api_key', '').strip()

    if not api_key:
        return jsonify({'error': 'No API key provided'}), 400

    save_api_key(api_key)
    return jsonify({'success': True, 'message': 'API key saved'})

if __name__ == '__main__':
    os.makedirs(AUDIO_DIR, exist_ok=True)

    print("=" * 60)
    print("Oracle Ferrofluid Speaker Dashboard")
    print("=" * 60)
    print(f"\nStarting server on http://0.0.0.0:5000")
    print("\nAccess from:")
    print("  - This machine: http://localhost:5000")
    print("  - Network: http://100.82.131.122:5000")
    print("\nVoice Features:")
    print("  - Whisper STT for transcription")
    print("  - Moneo Core AI (Claude) for responses")
    print("  - ElevenLabs TTS for voice")
    print("  - Syllable-synced visualization")
    print("\n" + "=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=False)
