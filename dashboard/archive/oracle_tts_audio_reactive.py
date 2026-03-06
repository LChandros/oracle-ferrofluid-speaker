#!/usr/bin/env python3
"""
Oracle TTS Audio-Reactive Visualizer
Real-time audio analysis with envelope followers (FerroWave-inspired)

Usage: sudo python3 oracle_tts_audio_reactive.py <audio_file.mp3> [pulse_freq] [led_brightness] [led_wave_speed]
Example: sudo python3 oracle_tts_audio_reactive.py /tmp/audio.mp3 10 255 0.15
"""

import sys
import subprocess
import RPi.GPIO as GPIO
from rpi_ws281x import PixelStrip, Color
import time
import threading
import os
import numpy as np
import soundfile as sf

# ==========================================
# HARDWARE CONFIGURATION
# ==========================================

# GPIO Pins
MAGNET_PIN = 23  # Physical Pin 16
LED_PIN = 12     # Physical Pin 32

# LED Strip Config
LED_COUNT = 10
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_INVERT = False
LED_CHANNEL = 0

# Audio Config
AUDIO_DEVICE = "plughw:3,0"
SAMPLE_RATE = 44100
BLOCK_SIZE = 512  # Audio samples per block

# Default Visualization Parameters
PULSE_FREQ_HZ = 8
LED_BRIGHTNESS = 200
LED_WAVE_SPEED = 0.1

# Envelope Follower Parameters (FerroWave-inspired)
ATTACK_SPEED = 80   # 0-100, higher = faster attack
RELEASE_SPEED = 40  # 0-100, higher = faster release
BASE_DUTY = 0.2     # Minimum duty cycle (20%)
MAX_DUTY = 0.8      # Maximum duty cycle (80%)
SENSITIVITY = 1.5   # Audio sensitivity multiplier

# ==========================================
# GLOBAL STATE
# ==========================================

running = False
envelope_fast = 0.0
envelope_slow = 0.0
envelope_peak = 0.0
envelope_ultraslow = 0.0
current_duty_cycle = BASE_DUTY

# ==========================================
# HARDWARE INITIALIZATION
# ==========================================

def init_hardware():
    """Initialize GPIO and LED strip"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(MAGNET_PIN, GPIO.OUT)

    # Initialize PWM on magnet pin
    pwm = GPIO.PWM(MAGNET_PIN, 1000)  # 1000 Hz PWM frequency
    pwm.start(0)

    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                      LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

    return strip, pwm

def cleanup_hardware(strip, pwm):
    """Clean shutdown of hardware"""
    pwm.stop()
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    GPIO.cleanup()

# ==========================================
# AUDIO ANALYSIS (FerroWave-inspired)
# ==========================================

def calculate_rms(audio_block):
    """Calculate RMS (root mean square) of audio block"""
    return np.sqrt(np.mean(audio_block ** 2))

def update_envelopes(level):
    """Update envelope followers with attack/release characteristics"""
    global envelope_fast, envelope_slow, envelope_peak, envelope_ultraslow

    # Calculate attack and release alpha values (FerroWave algorithm)
    attack_alpha = (ATTACK_SPEED / 100.0) * 0.9 + 0.05
    release_alpha = (RELEASE_SPEED / 100.0) * 0.5 + 0.01

    # Fast envelope (responsive to quick changes)
    if level > envelope_fast:
        envelope_fast = (1.0 - attack_alpha) * envelope_fast + attack_alpha * level
    else:
        envelope_fast = (1.0 - release_alpha) * envelope_fast + release_alpha * level

    # Slow envelope (smoothed average)
    envelope_slow = 0.98 * envelope_slow + 0.02 * level

    # Ultraslow envelope (very smooth baseline)
    envelope_ultraslow = 0.995 * envelope_ultraslow + 0.005 * level

    # Peak envelope (tracks peaks)
    if level > envelope_peak:
        envelope_peak = level
    else:
        envelope_peak = 0.99 * envelope_peak

def calculate_duty_cycle():
    """Map envelope to PWM duty cycle (FerroWave algorithm)"""
    global current_duty_cycle

    # Use fast envelope for responsive magnet control
    # Normalize against ultraslow envelope for dynamic range
    if envelope_ultraslow > 0.01:
        normalized = envelope_fast / envelope_ultraslow
    else:
        normalized = envelope_fast

    # Apply sensitivity
    output = min(1.0, normalized * SENSITIVITY)

    # Map to duty cycle range
    current_duty_cycle = BASE_DUTY + output * (MAX_DUTY - BASE_DUTY)

    return current_duty_cycle

# ==========================================
# VISUALIZATION LOOP
# ==========================================

def visualization_loop(strip, pwm, audio_data, sample_rate):
    """Process audio and control electromagnet + LEDs"""
    global running

    # Calculate total duration
    duration = len(audio_data) / sample_rate
    start_time = time.time()

    # Convert stereo to mono if needed
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)

    block_index = 0
    wave_position = 0

    while running and block_index < len(audio_data):
        # Get current audio block
        end_index = min(block_index + BLOCK_SIZE, len(audio_data))
        audio_block = audio_data[block_index:end_index]

        # Calculate RMS level
        level = calculate_rms(audio_block)

        # Update envelope followers
        update_envelopes(level)

        # Calculate and apply duty cycle to electromagnet
        duty = calculate_duty_cycle()
        pwm.ChangeDutyCycle(duty * 100)  # Convert to 0-100 range

        # Animate LEDs based on envelope (multiple visualization patterns)
        for i in range(LED_COUNT):
            # Pattern 1: Wave effect with audio modulation
            offset = abs(i - wave_position)
            wave_intensity = max(0, 1.0 - (offset / (LED_COUNT / 2)))

            # Pattern 2: Pulsing based on audio level
            pulse_intensity = envelope_fast

            # Pattern 3: Gradient based on position
            position_gradient = i / LED_COUNT

            # Combine patterns: wave movement + audio pulsing + position gradient
            base_intensity = wave_intensity * 0.4 + pulse_intensity * 0.6
            intensity = base_intensity * (0.7 + position_gradient * 0.3)

            # Add peak highlighting (brighten during loud moments)
            if envelope_peak > 0.7:
                intensity = min(1.0, intensity * 1.3)

            # Oracle color scheme (cyan/blue/purple) with dynamic color shift
            # More cyan on peaks, more purple on quiet parts
            color_shift = envelope_fast
            r = int((80 + 50 * color_shift) * intensity)
            g = int((120 + 80 * color_shift) * intensity)
            b = int(255 * intensity)

            strip.setPixelColor(i, Color(g, r, b))
        strip.show()

        # Update wave position based on LED_WAVE_SPEED and audio energy
        # Move faster during louder parts
        wave_speed_dynamic = LED_WAVE_SPEED * (1.0 + envelope_fast * 0.5)
        wave_position = (wave_position + wave_speed_dynamic) % LED_COUNT

        # Advance audio block
        block_index = end_index

        # Small sleep to prevent CPU overload
        time.sleep(0.001)

# ==========================================
# MAIN FUNCTION
# ==========================================

def main():
    global running, PULSE_FREQ_HZ, LED_BRIGHTNESS, LED_WAVE_SPEED
    global ATTACK_SPEED, RELEASE_SPEED, SENSITIVITY, BASE_DUTY, MAX_DUTY

    if len(sys.argv) < 2:
        print("Usage: sudo python3 oracle_tts_audio_reactive.py <audio_file.mp3> [pulse_freq] [led_brightness] [led_wave_speed]")
        sys.exit(1)

    audio_file = sys.argv[1]
    if not os.path.exists(audio_file):
        print(f"Error: Audio file not found: {audio_file}")
        sys.exit(1)

    # Parse optional parameters
    if len(sys.argv) >= 3:
        PULSE_FREQ_HZ = int(sys.argv[2])
    if len(sys.argv) >= 4:
        LED_BRIGHTNESS = int(sys.argv[3])
    if len(sys.argv) >= 5:
        LED_WAVE_SPEED = float(sys.argv[4])

    print(f"Loading audio file: {audio_file}")

    # Load audio file
    try:
        audio_data, sample_rate = sf.read(audio_file)
    except Exception as e:
        print(f"Error loading audio file: {e}")
        sys.exit(1)

    print(f"Audio loaded: {len(audio_data)/sample_rate:.2f}s @ {sample_rate}Hz")

    strip, pwm = init_hardware()

    try:
        # Start visualization thread
        running = True
        viz_thread = threading.Thread(target=visualization_loop, args=(strip, pwm, audio_data, sample_rate))
        viz_thread.daemon = True
        viz_thread.start()

        # Play audio file with mpg123
        print("Playing audio with visualization...")
        subprocess.run([
            "mpg123",
            "-o", "alsa",
            "-a", AUDIO_DEVICE,
            "-q",
            audio_file
        ])

        # Stop visualization
        running = False
        time.sleep(0.2)

    except KeyboardInterrupt:
        pass

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        running = False
        time.sleep(0.1)
        cleanup_hardware(strip, pwm)

if __name__ == "__main__":
    main()
