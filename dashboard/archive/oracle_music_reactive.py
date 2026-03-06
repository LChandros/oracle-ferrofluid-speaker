#!/usr/bin/env python3
"""
Oracle Music-Reactive System
Analyzes music file and syncs LEDs + electromagnet to playback
"""

import numpy as np
import RPi.GPIO as GPIO
from rpi_ws281x import PixelStrip, Color
import time
import wave
import threading
import subprocess
import sys

# ==========================================
# HARDWARE CONFIGURATION
# ==========================================

# GPIO Pins
MAGNET_PIN = 23  # Physical Pin 16
LED_PIN = 12     # Physical Pin 32

# LED Strip Config
LED_COUNT = 10
LED_BRIGHTNESS = 255
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_INVERT = False
LED_CHANNEL = 0

# ==========================================
# AUDIO ANALYSIS PARAMETERS
# ==========================================

# Volume thresholds
VOLUME_MIN = 100
VOLUME_MAX = 15000
MAGNET_THRESHOLD = 800

# LED response
LED_SMOOTHING = 0.3

# Electromagnet response
MAGNET_MIN_PULSE = 0.05
MAGNET_MAX_PULSE = 0.3

# ==========================================
# GLOBAL STATE
# ==========================================

class State:
    def __init__(self):
        self.running = False
        self.audio_data = []
        self.current_index = 0
        self.sample_rate = 44100

state = State()

# ==========================================
# HARDWARE INITIALIZATION
# ==========================================

def init_hardware():
    """Initialize GPIO and LED strip"""
    print("Initializing hardware...")

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(MAGNET_PIN, GPIO.OUT)
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    print(f"✓ GPIO {MAGNET_PIN} (electromagnet)")

    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                      LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()
    print(f"✓ LED strip ({LED_COUNT} LEDs)")

    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

    return strip

def cleanup_hardware(strip):
    """Clean shutdown"""
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    GPIO.cleanup()

# ==========================================
# AUDIO FILE LOADING
# ==========================================

def load_wav_file(filename):
    """Load WAV file and extract audio data"""
    print(f"Loading audio file: {filename}")

    try:
        with wave.open(filename, 'rb') as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            framerate = wav.getframerate()
            n_frames = wav.getnframes()

            print(f"  Channels: {channels}")
            print(f"  Sample rate: {framerate} Hz")
            print(f"  Duration: {n_frames/framerate:.1f} seconds")

            # Read all audio data
            audio_bytes = wav.readframes(n_frames)

            # Convert to numpy array
            if sample_width == 2:  # 16-bit
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
            else:
                print(f"Unsupported sample width: {sample_width}")
                return None, framerate

            # Convert stereo to mono if needed
            if channels == 2:
                audio_data = audio_data.reshape(-1, 2).mean(axis=1).astype(np.int16)

            print(f"✓ Loaded {len(audio_data)} samples")
            return audio_data, framerate

    except Exception as e:
        print(f"Error loading WAV file: {e}")
        return None, 44100

# ==========================================
# LED CONTROL
# ==========================================

def volume_to_color(volume):
    """Convert volume to color (blue -> purple -> red)"""
    if volume < 0.33:
        ratio = volume / 0.33
        r = int(128 * ratio)
        g = 0
        b = 128 + int(127 * (1 - ratio))
    elif volume < 0.66:
        ratio = (volume - 0.33) / 0.33
        r = 128 + int(127 * ratio)
        g = int(64 * ratio)
        b = 128 - int(64 * ratio)
    else:
        ratio = (volume - 0.66) / 0.34
        r = 255
        g = 64 - int(64 * ratio)
        b = 64 - int(64 * ratio)

    return Color(g, r, b)

def update_leds(strip, volume):
    """Update LED strip"""
    color = volume_to_color(volume)
    num_lit = int(volume * LED_COUNT)

    for i in range(LED_COUNT):
        if i < num_lit:
            strip.setPixelColor(i, color)
        else:
            strip.setPixelColor(i, Color(0, 0, 0))

    strip.show()

# ==========================================
# ELECTROMAGNET CONTROL
# ==========================================

def update_magnet(volume, raw_volume):
    """Update electromagnet with pulsing"""
    if raw_volume < MAGNET_THRESHOLD:
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        return

    # Pulse based on volume (simple on/off)
    pulse_duration = MAGNET_MIN_PULSE + (volume * (MAGNET_MAX_PULSE - MAGNET_MIN_PULSE))

    # Pulse pattern: ON for pulse_duration, OFF briefly
    GPIO.output(MAGNET_PIN, GPIO.HIGH)
    time.sleep(pulse_duration)
    GPIO.output(MAGNET_PIN, GPIO.LOW)

# ==========================================
# VISUALIZATION LOOP
# ==========================================

def visualization_loop(strip, audio_data, sample_rate):
    """Main loop that syncs visuals to audio"""
    chunk_size = int(sample_rate * 0.05)  # 50ms chunks
    num_chunks = len(audio_data) // chunk_size

    smoothed_volume = 0.0

    for i in range(num_chunks):
        if not state.running:
            break

        # Get audio chunk
        start = i * chunk_size
        end = start + chunk_size
        chunk = audio_data[start:end]

        # Calculate RMS volume
        rms = np.sqrt(np.mean(chunk**2))
        normalized = (rms - VOLUME_MIN) / (VOLUME_MAX - VOLUME_MIN)
        normalized = max(0.0, min(1.0, normalized))

        # Smooth for LEDs
        smoothed_volume = (LED_SMOOTHING * smoothed_volume +
                          (1 - LED_SMOOTHING) * normalized)

        # Update visuals
        update_leds(strip, smoothed_volume)
        update_magnet(normalized, rms)

        # Small sleep to stay synced (most time is in magnet pulse)
        time.sleep(0.01)

# ==========================================
# MUSIC PLAYBACK
# ==========================================

def play_audio_file(filename):
    """Play audio file using aplay"""
    print(f"Starting playback: {filename}")
    subprocess.run(['aplay', '-D', 'plughw:3,0', filename])

# ==========================================
# MAIN
# ==========================================

def main():
    if len(sys.argv) < 2:
        print("Usage: sudo python3 oracle_music_reactive.py <audio_file.wav>")
        print("Example: sudo python3 oracle_music_reactive.py /home/tyahn/cough.wav")
        sys.exit(1)

    audio_file = sys.argv[1]

    print("=" * 60)
    print("ORACLE MUSIC-REACTIVE SYSTEM")
    print("=" * 60)
    print()

    # Load audio file
    audio_data, sample_rate = load_wav_file(audio_file)
    if audio_data is None:
        print("Failed to load audio file")
        sys.exit(1)

    state.audio_data = audio_data
    state.sample_rate = sample_rate

    # Initialize hardware
    strip = init_hardware()

    print()
    print("=" * 60)
    print("STARTING SYNCHRONIZED PLAYBACK")
    print("=" * 60)
    print()

    try:
        state.running = True

        # Start playback in background thread
        playback_thread = threading.Thread(target=play_audio_file, args=(audio_file,))
        playback_thread.daemon = True
        playback_thread.start()

        # Wait a moment for playback to start
        time.sleep(0.5)

        # Run visualization
        visualization_loop(strip, audio_data, sample_rate)

        # Wait for playback to finish
        playback_thread.join()

    except KeyboardInterrupt:
        print("\n\nStopping...")
        state.running = False

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

    finally:
        cleanup_hardware(strip)
        print("\nSystem stopped.")

if __name__ == "__main__":
    main()
