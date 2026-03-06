#!/usr/bin/env python3
"""Quick test: Play audio while pulsing electromagnet"""

import RPi.GPIO as GPIO
import subprocess
import time

MAGNET_PIN = 21  # GPIO 21 (Pin 40)

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(MAGNET_PIN, GPIO.OUT)
GPIO.output(MAGNET_PIN, GPIO.LOW)

print("="*60)
print("AUDIO + ELECTROMAGNET INTERFERENCE TEST")
print("="*60)
print()
print("This will:")
print("1. Play cough.wav")
print("2. Pulse electromagnet at 1Hz (1 sec on/off)")
print()
print("Listen for clicks, pops, hum, or distortion")
print()
input("Press Enter to start test...")

# Start audio in background
audio = subprocess.Popen(["aplay", "-D", "plughw:3,0", "/home/tyahn/cough.wav"])

# Pulse magnet while audio plays
print("\nPulsing electromagnet...")
start = time.time()
pulse_count = 0

while audio.poll() is None and (time.time() - start) < 10:
    GPIO.output(MAGNET_PIN, GPIO.HIGH)
    print(f"  Pulse {pulse_count}: ON", flush=True)
    time.sleep(1)
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    print(f"  Pulse {pulse_count}: OFF", flush=True)
    time.sleep(1)
    pulse_count += 1

# Wait for audio to finish
audio.wait()

# Cleanup
GPIO.output(MAGNET_PIN, GPIO.LOW)
GPIO.cleanup()

print()
print("="*60)
print("TEST COMPLETE")
print("="*60)
print()
print("Did you hear any interference?")
print("  - Clicks when magnet switched on/off?")
print("  - Hum or buzz?")
print("  - Audio distortion?")
print()
