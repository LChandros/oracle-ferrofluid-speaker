#!/usr/bin/env python3
"""
Oracle TTS Visualizer
Plays audio file while controlling LEDs and electromagnet in real-time

Usage: python3 oracle_tts_visualizer.py <audio_file.mp3>
"""

import sys
import subprocess
import pyaudio
import numpy as np
import RPi.GPIO as GPIO
from rpi_ws281x import PixelStrip, Color
import time
import threading
import os

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

# Audio Config
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
DEVICE_INDEX = 3  # plughw:3,0 (WM8960)
AUDIO_DEVICE = "plughw:3,0"

# ==========================================
# AUDIO ANALYSIS PARAMETERS
# ==========================================

# Volume thresholds (0-32768 for 16-bit audio)
VOLUME_MIN = 100
VOLUME_MAX = 15000
MAGNET_THRESHOLD = 300  # Lower threshold for TTS sensitivity

# LED response
LED_SMOOTHING = 0.4  # Smoother for speech

# Electromagnet response
MAGNET_MIN_PULSE = 0.08  # Minimum pulse duration (80ms)
MAGNET_MAX_PULSE = 0.4   # Maximum pulse duration (400ms)

# ==========================================
# GLOBAL STATE
# ==========================================

class VisualizerState:
    def __init__(self):
        self.running = False
        self.current_volume = 0
        self.smoothed_volume = 0
        self.magnet_state = False
        self.last_magnet_change = time.time()

state = VisualizerState()

# ==========================================
# HARDWARE INITIALIZATION
# ==========================================

def init_hardware():
    """Initialize GPIO and LED strip"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(MAGNET_PIN, GPIO.OUT)
    GPIO.output(MAGNET_PIN, GPIO.LOW)

    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                      LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

    return strip

def cleanup_hardware(strip):
    """Clean shutdown of hardware"""
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    GPIO.cleanup()

# ==========================================
# AUDIO ANALYSIS
# ==========================================

def analyze_audio(data):
    """Analyze audio chunk and return normalized volume"""
    audio_data = np.frombuffer(data, dtype=np.int16)
    rms = np.sqrt(np.mean(audio_data**2))
    normalized = (rms - VOLUME_MIN) / (VOLUME_MAX - VOLUME_MIN)
    normalized = max(0.0, min(1.0, normalized))
    return normalized, rms

# ==========================================
# LED CONTROL
# ==========================================

def volume_to_color(volume):
    """Convert volume to color - Oracle theme (blue -> purple -> cyan)"""
    if volume < 0.33:
        # Deep blue to electric blue
        ratio = volume / 0.33
        r = 0
        g = int(100 * ratio)
        b = 150 + int(105 * ratio)
    elif volume < 0.66:
        # Electric blue to purple
        ratio = (volume - 0.33) / 0.33
        r = int(150 * ratio)
        g = 100 - int(50 * ratio)
        b = 255
    else:
        # Purple to bright cyan
        ratio = (volume - 0.66) / 0.34
        r = 150 - int(50 * ratio)
        g = 50 + int(205 * ratio)
        b = 255

    return Color(g, r, b)

def update_leds(strip, volume):
    """Update LED strip based on volume"""
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
    """Update electromagnet with pulsing based on audio"""
    if raw_volume < MAGNET_THRESHOLD:
        if state.magnet_state:
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            state.magnet_state = False
        return

    pulse_duration = MAGNET_MIN_PULSE + (volume * (MAGNET_MAX_PULSE - MAGNET_MIN_PULSE))
    elapsed = time.time() - state.last_magnet_change

    if state.magnet_state:
        if elapsed >= pulse_duration:
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            state.magnet_state = False
            state.last_magnet_change = time.time()
    else:
        gap = pulse_duration * 0.15
        if elapsed >= gap:
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            state.magnet_state = True
            state.last_magnet_change = time.time()

# ==========================================
# AUDIO PROCESSING
# ==========================================

def audio_callback(in_data, frame_count, time_info, status):
    """Process audio in real-time"""
    if not state.running:
        return (in_data, pyaudio.paComplete)

    volume, raw_volume = analyze_audio(in_data)
    state.current_volume = volume
    state.smoothed_volume = (LED_SMOOTHING * state.smoothed_volume +
                            (1 - LED_SMOOTHING) * volume)

    return (in_data, pyaudio.paContinue)

def update_loop(strip):
    """Update LEDs and electromagnet"""
    while state.running:
        update_leds(strip, state.smoothed_volume)
        update_magnet(state.current_volume, state.current_volume * VOLUME_MAX)
        time.sleep(0.01)

# ==========================================
# MAIN FUNCTION
# ==========================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 oracle_tts_visualizer.py <audio_file.mp3>")
        sys.exit(1)

    audio_file = sys.argv[1]
    if not os.path.exists(audio_file):
        print(f"Error: Audio file not found: {audio_file}")
        sys.exit(1)

    print(f"🧲 Oracle TTS Visualizer")
    print(f"   Audio: {audio_file}")
    print(f"   Device: {AUDIO_DEVICE}")
    print()

    strip = init_hardware()
    p = pyaudio.PyAudio()

    try:
        # Open audio stream for monitoring
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=DEVICE_INDEX,
            frames_per_buffer=CHUNK,
            stream_callback=audio_callback
        )

        state.running = True
        stream.start_stream()

        # Start visualization thread
        update_thread = threading.Thread(target=update_loop, args=(strip,))
        update_thread.daemon = True
        update_thread.start()

        # Play audio file with mpg123
        print("▶️  Playing...")
        subprocess.run([
            "mpg123",
            "-o", "alsa",
            "-a", AUDIO_DEVICE,
            "-q",  # Quiet mode
            audio_file
        ])

        # Give visualization a moment to finish
        time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\nInterrupted")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

    finally:
        state.running = False
        time.sleep(0.1)  # Let threads finish

        if 'stream' in locals():
            stream.stop_stream()
            stream.close()
        p.terminate()
        cleanup_hardware(strip)
        print("✓ Done")

if __name__ == "__main__":
    main()
