#!/usr/bin/env python3
"""Quick automated electromagnet interference test"""

import RPi.GPIO as GPIO
import subprocess
import time

MAGNET_PIN = 18  # GPIO 18 (Physical Pin 12)
TEST_AUDIO = "/home/tyahn/voice-test.wav"

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(MAGNET_PIN, GPIO.OUT)
GPIO.output(MAGNET_PIN, GPIO.LOW)

print("="*60)
print("ELECTROMAGNET INTERFERENCE TEST - AUTOMATED")
print("="*60)
print()
print("Test 1: Audio ONLY (baseline)")
print("-"*60)
subprocess.run(["aplay", "-D", "plughw:3,0", TEST_AUDIO])
print("✅ Baseline test complete")
print()

print("Test 2: Audio + Electromagnet STATIC ON")
print("-"*60)
GPIO.output(MAGNET_PIN, GPIO.HIGH)
print("Electromagnet ON")
time.sleep(0.5)
subprocess.run(["aplay", "-D", "plughw:3,0", TEST_AUDIO])
GPIO.output(MAGNET_PIN, GPIO.LOW)
print("Electromagnet OFF")
print("✅ Static test complete")
print()

print("Test 3: Audio + Electromagnet SLOW PULSE (1Hz)")
print("-"*60)
audio = subprocess.Popen(["aplay", "-D", "plughw:3,0", TEST_AUDIO])
time.sleep(0.5)
for i in range(3):
    GPIO.output(MAGNET_PIN, GPIO.HIGH)
    print(f"  Pulse {i+1}: ON", flush=True)
    time.sleep(1)
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    print(f"  Pulse {i+1}: OFF", flush=True)
    time.sleep(1)
audio.wait()
print("✅ Slow pulse test complete")
print()

print("Test 4: Audio + Electromagnet FAST PULSE (100ms)")
print("-"*60)
audio = subprocess.Popen(["aplay", "-D", "plughw:3,0", TEST_AUDIO])
time.sleep(0.5)
start = time.time()
count = 0
while time.time() - start < 3:
    GPIO.output(MAGNET_PIN, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    time.sleep(0.1)
    count += 1
audio.wait()
print(f"✅ Fast pulse test complete ({count} pulses)")
print()

GPIO.output(MAGNET_PIN, GPIO.LOW)
GPIO.cleanup()

print("="*60)
print("TEST COMPLETE")
print("="*60)
print()
print("Listen for interference:")
print("  - Clicks/pops when magnet switches?")
print("  - Hum or buzz during operation?")
print("  - Audio distortion?")
print()
print("If you heard interference, capacitors may help.")
print("If audio was clean, no capacitors needed!")
