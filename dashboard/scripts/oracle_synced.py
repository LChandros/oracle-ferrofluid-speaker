#!/usr/bin/env python3
"""
Oracle - Text-based syllable pulsing
Pre-calculates pulse timing based on syllable count from text
"""

import sys
import subprocess
import RPi.GPIO as GPIO
from rpi_ws281x import PixelStrip, Color
import time
import threading
import numpy as np
import soundfile as sf

# Hardware config
MAGNET_PIN = 23
LED_PIN = 12
LED_COUNT = 19
LED_BRIGHTNESS = 255
AUDIO_DEVICE = "plughw:3,0"

# Audio processing
BLOCK_SIZE = 1024
SENSITIVITY = 25.0

# Pulse timing
PULSE_DURATION = 0.12  # Each pulse is 120ms (typical syllable duration)

running = False
pulse_schedule = []
current_pulse_index = 0

def init_hardware():
    strip = PixelStrip(LED_COUNT, LED_PIN, 800000, 10, False, LED_BRIGHTNESS, 0)
    strip.begin()

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(MAGNET_PIN, GPIO.OUT)
    GPIO.output(MAGNET_PIN, GPIO.LOW)

    return strip

def generate_pulse_schedule(num_syllables, audio_duration):
    """Generate pulse timing based on syllable count and audio duration"""
    schedule = []

    if num_syllables <= 0:
        return schedule

    # Calculate spacing between pulse starts
    # Reserve some time at beginning/end
    usable_duration = audio_duration * 0.95  # Use 95% of audio
    start_offset = audio_duration * 0.025  # Start at 2.5% into audio

    if num_syllables == 1:
        # Single pulse in the middle
        pulse_start = audio_duration / 2
        schedule.append({'start': pulse_start, 'end': pulse_start + PULSE_DURATION})
    else:
        # Evenly space pulses
        spacing = usable_duration / num_syllables

        for i in range(num_syllables):
            pulse_start = start_offset + (i * spacing)
            pulse_end = pulse_start + PULSE_DURATION
            schedule.append({'start': pulse_start, 'end': pulse_end})

    return schedule

def pulse_control_loop(audio_duration):
    """Control electromagnet based on pre-calculated schedule"""
    global running, pulse_schedule, current_pulse_index

    start_time = time.time()
    current_pulse_index = 0
    magnet_on = False

    print(f"\nPulse schedule ({len(pulse_schedule)} pulses):")
    for i, pulse in enumerate(pulse_schedule):
        print(f"  Pulse {i+1}: {pulse['start']:.2f}s - {pulse['end']:.2f}s")
    print()

    while running:
        elapsed = time.time() - start_time

        # Check if we should turn on
        if not magnet_on and current_pulse_index < len(pulse_schedule):
            pulse = pulse_schedule[current_pulse_index]
            if elapsed >= pulse['start']:
                GPIO.output(MAGNET_PIN, GPIO.HIGH)
                magnet_on = True
                print(f"[{elapsed:.2f}s] Pulse {current_pulse_index + 1} ON")

        # Check if we should turn off
        if magnet_on:
            pulse = pulse_schedule[current_pulse_index]
            if elapsed >= pulse['end']:
                GPIO.output(MAGNET_PIN, GPIO.LOW)
                magnet_on = False
                print(f"[{elapsed:.2f}s] Pulse {current_pulse_index + 1} OFF")
                current_pulse_index += 1

        time.sleep(0.005)  # 5ms update rate

    # Ensure magnet is off
    GPIO.output(MAGNET_PIN, GPIO.LOW)

def visualization_loop(strip, audio_data, sample_rate):
    global running

    # Convert stereo to mono
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)

    block_index = 0
    envelope = 0.0

    # Calculate timing
    block_duration = BLOCK_SIZE / sample_rate

    start_time = time.time()

    while running and block_index < len(audio_data):
        block_start = time.time()

        # Get audio chunk
        end_index = min(block_index + BLOCK_SIZE, len(audio_data))
        chunk = audio_data[block_index:end_index]

        # Calculate RMS
        rms = np.sqrt(np.mean(chunk**2))

        # Fast envelope follower
        if rms > envelope:
            envelope += 0.8 * (rms - envelope)
        else:
            envelope += 0.3 * (rms - envelope)

        # Amplify for LED visualization
        intensity = min(1.0, envelope * SENSITIVITY)

        # Update LEDs - Oracle cyan/blue theme
        r = int(100 * intensity)
        g = int(200 * intensity)
        b = int(255 * intensity)

        for i in range(LED_COUNT):
            # Add wave effect
            wave = (np.sin(i * 0.3 + time.time() * 2) + 1) / 2
            brightness = 0.3 + (wave * 0.7 * intensity)
            strip.setPixelColor(i, Color(int(g*brightness), int(r*brightness), int(b*brightness)))
        strip.show()

        block_index = end_index

        # Sleep to sync with audio playback
        processing_time = time.time() - block_start
        sleep_time = block_duration - processing_time
        if sleep_time > 0:
            time.sleep(sleep_time)

def cleanup(strip):
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    GPIO.cleanup()

def main():
    global running, pulse_schedule

    if len(sys.argv) < 3:
        print("Usage: sudo python3 oracle_synced.py <audio_file> <syllable_count>")
        sys.exit(1)

    audio_file = sys.argv[1]
    syllable_count = int(sys.argv[2])

    print("=" * 60)
    print("ORACLE - Text-Based Syllable Pulsing")
    print("=" * 60)
    print(f"\nLoading: {audio_file}")

    audio_data, sample_rate = sf.read(audio_file)
    duration = len(audio_data) / sample_rate
    print(f"✓ Loaded: {duration:.2f}s @ {sample_rate}Hz")
    print(f"✓ Syllables: {syllable_count}")

    # Generate pulse schedule
    pulse_schedule = generate_pulse_schedule(syllable_count, duration)

    print("\nInitializing hardware...")
    strip = init_hardware()
    print("✓ LEDs + Electromagnet ready")

    try:
        running = True

        # Start pulse control thread
        pulse_thread = threading.Thread(target=pulse_control_loop, args=(duration,))
        pulse_thread.daemon = True
        pulse_thread.start()

        # Start visualization thread
        viz_thread = threading.Thread(target=visualization_loop, args=(strip, audio_data, sample_rate))
        viz_thread.daemon = True
        viz_thread.start()

        # Small delay to let threads start
        time.sleep(0.1)

        # Play audio
        print("\n▶ Playing audio...\n")
        subprocess.run(["aplay", "-D", AUDIO_DEVICE, audio_file])

        # Wait for threads to finish
        running = False
        pulse_thread.join(timeout=1.0)
        viz_thread.join(timeout=2.0)

    except KeyboardInterrupt:
        print("\n\nInterrupted")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        running = False
        time.sleep(0.2)
        cleanup(strip)
        print("\n✓ Done")

if __name__ == "__main__":
    main()
