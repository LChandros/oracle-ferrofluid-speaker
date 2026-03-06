#!/usr/bin/env python3
"""
Oracle TTS Simple Visualizer
Plays audio while pulsing electromagnet and LEDs
Simpler version - no audio monitoring, just rhythmic pulsing

Usage: sudo python3 oracle_tts_simple.py <audio_file.mp3> [pulse_freq] [led_brightness] [led_wave_speed]
Example: sudo python3 oracle_tts_simple.py /tmp/audio.mp3 10 255 0.15
"""

import sys
import subprocess
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
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_INVERT = False
LED_CHANNEL = 0

# Audio Config
AUDIO_DEVICE = "plughw:3,0"

# Default Visualization Parameters (can be overridden by command-line args)
PULSE_FREQ_HZ = 8  # Pulses per second (matches typical speech rhythm)
LED_BRIGHTNESS = 200
LED_WAVE_SPEED = 0.1  # LED animation speed

# ==========================================
# GLOBAL STATE
# ==========================================

running = False

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
# VISUALIZATION LOOP
# ==========================================

def visualization_loop(strip):
    """Pulse electromagnet and animate LEDs while audio plays"""
    global running

    pulse_period = 1.0 / PULSE_FREQ_HZ
    pulse_on_time = pulse_period * 0.6  # 60% duty cycle
    pulse_off_time = pulse_period * 0.4

    wave_position = 0

    while running:
        # Pulse electromagnet
        GPIO.output(MAGNET_PIN, GPIO.HIGH)

        # Animate LEDs (wave effect)
        for i in range(LED_COUNT):
            # Calculate wave intensity for this LED
            offset = abs(i - wave_position)
            intensity = max(0, 1.0 - (offset / LED_COUNT))

            # Oracle color scheme (cyan/blue/purple)
            r = int(100 * intensity)
            g = int(150 * intensity)
            b = int(255 * intensity)

            strip.setPixelColor(i, Color(g, r, b))
        strip.show()

        time.sleep(pulse_on_time)

        # Magnet off
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        time.sleep(pulse_off_time)

        # Update wave position
        wave_position = (wave_position + 1) % LED_COUNT

# ==========================================
# MAIN FUNCTION
# ==========================================

def main():
    global running, PULSE_FREQ_HZ, LED_BRIGHTNESS, LED_WAVE_SPEED

    if len(sys.argv) < 2:
        print("Usage: sudo python3 oracle_tts_simple.py <audio_file.mp3> [pulse_freq] [led_brightness] [led_wave_speed]")
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

    strip = init_hardware()

    try:
        # Start visualization thread
        running = True
        viz_thread = threading.Thread(target=visualization_loop, args=(strip,))
        viz_thread.daemon = True
        viz_thread.start()

        # Play audio file with mpg123
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
        cleanup_hardware(strip)

if __name__ == "__main__":
    main()
