#!/usr/bin/env python3
"""
Oracle Audio-Reactive System
Syncs LEDs and electromagnet to audio playback in real-time
"""

import pyaudio
import numpy as np
import RPi.GPIO as GPIO
from rpi_ws281x import PixelStrip, Color
import time
import threading

# ==========================================
# HARDWARE CONFIGURATION
# ==========================================

# GPIO Pins
MAGNET_PIN = 23  # Physical Pin 16 - CRITICAL: Do not use GPIO 18!
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
DEVICE_INDEX = 3  # plughw:3,0 (ReSpeaker)

# ==========================================
# AUDIO ANALYSIS PARAMETERS
# ==========================================

# Volume thresholds (0-32768 for 16-bit audio)
VOLUME_MIN = 100       # Noise floor
VOLUME_MAX = 15000     # Peak reference
MAGNET_THRESHOLD = 500 # Minimum volume to activate magnet

# LED response
LED_SMOOTHING = 0.3    # Lower = more responsive (0-1)

# Electromagnet response
MAGNET_MIN_PULSE = 0.05  # Minimum pulse duration (50ms)
MAGNET_MAX_PULSE = 0.5   # Maximum pulse duration (500ms)

# ==========================================
# GLOBAL STATE
# ==========================================

class AudioReactiveState:
    def __init__(self):
        self.running = False
        self.current_volume = 0
        self.smoothed_volume = 0
        self.magnet_state = False
        self.last_magnet_change = time.time()

state = AudioReactiveState()

# ==========================================
# HARDWARE INITIALIZATION
# ==========================================

def init_hardware():
    """Initialize GPIO and LED strip"""
    print("Initializing hardware...")

    # GPIO setup
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(MAGNET_PIN, GPIO.OUT)
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    print(f"✓ GPIO {MAGNET_PIN} initialized (electromagnet)")

    # LED strip setup
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                      LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()
    print(f"✓ LED strip initialized ({LED_COUNT} LEDs on GPIO {LED_PIN})")

    # Clear LEDs
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

    return strip

def cleanup_hardware(strip):
    """Clean shutdown of hardware"""
    print("\nCleaning up hardware...")

    # Turn off electromagnet
    GPIO.output(MAGNET_PIN, GPIO.LOW)

    # Clear LED strip
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

    # Cleanup GPIO
    GPIO.cleanup()
    print("✓ Hardware cleaned up")

# ==========================================
# AUDIO ANALYSIS
# ==========================================

def analyze_audio(data):
    """
    Analyze audio chunk and return normalized volume (0.0 - 1.0)
    """
    # Convert bytes to numpy array
    audio_data = np.frombuffer(data, dtype=np.int16)

    # Calculate RMS (root mean square) volume
    rms = np.sqrt(np.mean(audio_data**2))

    # Normalize to 0.0 - 1.0
    normalized = (rms - VOLUME_MIN) / (VOLUME_MAX - VOLUME_MIN)
    normalized = max(0.0, min(1.0, normalized))  # Clamp

    return normalized, rms

# ==========================================
# LED CONTROL
# ==========================================

def volume_to_color(volume):
    """
    Convert volume level to color
    Low volume = blue, medium = purple, high = red
    """
    if volume < 0.33:
        # Blue to purple
        ratio = volume / 0.33
        r = int(128 * ratio)
        g = 0
        b = 128 + int(127 * (1 - ratio))
    elif volume < 0.66:
        # Purple to pink
        ratio = (volume - 0.33) / 0.33
        r = 128 + int(127 * ratio)
        g = int(64 * ratio)
        b = 128 - int(64 * ratio)
    else:
        # Pink to red
        ratio = (volume - 0.66) / 0.34
        r = 255
        g = 64 - int(64 * ratio)
        b = 64 - int(64 * ratio)

    return Color(g, r, b)  # Note: Color is GRB format

def update_leds(strip, volume):
    """Update LED strip based on volume"""
    color = volume_to_color(volume)

    # Number of LEDs to light based on volume
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
    """
    Update electromagnet based on volume
    Uses PWM-like pulsing: higher volume = longer pulses
    """
    # Only activate if above threshold
    if raw_volume < MAGNET_THRESHOLD:
        if state.magnet_state:
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            state.magnet_state = False
        return

    # Map volume to pulse duration
    pulse_duration = MAGNET_MIN_PULSE + (volume * (MAGNET_MAX_PULSE - MAGNET_MIN_PULSE))

    # Time since last state change
    elapsed = time.time() - state.last_magnet_change

    # Toggle magnet based on pulse timing
    if state.magnet_state:
        # Currently ON - turn off after pulse duration
        if elapsed >= pulse_duration:
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            state.magnet_state = False
            state.last_magnet_change = time.time()
    else:
        # Currently OFF - turn on if enough time passed (brief gap)
        gap = pulse_duration * 0.2  # 20% gap between pulses
        if elapsed >= gap:
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            state.magnet_state = True
            state.last_magnet_change = time.time()

# ==========================================
# MAIN AUDIO PROCESSING LOOP
# ==========================================

def audio_callback(in_data, frame_count, time_info, status):
    """PyAudio callback - processes audio in real-time"""
    if not state.running:
        return (in_data, pyaudio.paComplete)

    # Analyze audio
    volume, raw_volume = analyze_audio(in_data)
    state.current_volume = volume

    # Smooth volume for LED display
    state.smoothed_volume = (LED_SMOOTHING * state.smoothed_volume +
                            (1 - LED_SMOOTHING) * volume)

    return (in_data, pyaudio.paContinue)

def update_loop(strip):
    """Separate thread for updating LEDs and electromagnet"""
    while state.running:
        # Update LEDs with smoothed volume
        update_leds(strip, state.smoothed_volume)

        # Update electromagnet with raw volume
        update_magnet(state.current_volume, state.current_volume * VOLUME_MAX)

        # Small delay to prevent CPU hogging
        time.sleep(0.01)  # 100 Hz update rate

# ==========================================
# MAIN FUNCTION
# ==========================================

def main():
    print("=" * 50)
    print("ORACLE AUDIO-REACTIVE SYSTEM")
    print("=" * 50)
    print()

    # Initialize hardware
    strip = init_hardware()

    # Initialize PyAudio
    p = pyaudio.PyAudio()

    try:
        # Open audio stream (loopback monitoring)
        print(f"Opening audio stream (device {DEVICE_INDEX})...")
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=DEVICE_INDEX,
            frames_per_buffer=CHUNK,
            stream_callback=audio_callback
        )

        print("✓ Audio stream opened")
        print()
        print("System Configuration:")
        print(f"  LED smoothing: {LED_SMOOTHING}")
        print(f"  Magnet threshold: {MAGNET_THRESHOLD}")
        print(f"  Pulse range: {MAGNET_MIN_PULSE*1000:.0f}ms - {MAGNET_MAX_PULSE*1000:.0f}ms")
        print()
        print("=" * 50)
        print("SYSTEM ACTIVE - Play audio to see response")
        print("Press Ctrl+C to stop")
        print("=" * 50)
        print()

        # Start processing
        state.running = True
        stream.start_stream()

        # Start update thread
        update_thread = threading.Thread(target=update_loop, args=(strip,))
        update_thread.daemon = True
        update_thread.start()

        # Keep running until interrupted
        while stream.is_active() and state.running:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nShutdown requested...")
        state.running = False

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        state.running = False

    finally:
        # Cleanup
        if 'stream' in locals():
            stream.stop_stream()
            stream.close()
        p.terminate()
        cleanup_hardware(strip)
        print("\nSystem stopped.")

if __name__ == "__main__":
    main()
