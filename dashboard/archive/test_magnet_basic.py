#!/usr/bin/env python3
"""Test electromagnet without capacitors"""

import RPi.GPIO as GPIO
import time

# Determine which pin you're using - adjust if needed
MAGNET_PIN = 18  # GPIO 18 = Physical Pin 12

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(MAGNET_PIN, GPIO.OUT)

print("="*60)
print("ELECTROMAGNET TEST (No Capacitors)")
print("="*60)
print(f"Using GPIO {MAGNET_PIN}")
print()
print("Test 1: Short pulse (1 second)")

GPIO.output(MAGNET_PIN, GPIO.HIGH)
print("  → Electromagnet ON")
time.sleep(1)
GPIO.output(MAGNET_PIN, GPIO.LOW)
print("  → Electromagnet OFF")

print()
print("Test 2: Longer pulse (3 seconds)")
time.sleep(1)

GPIO.output(MAGNET_PIN, GPIO.HIGH)
print("  → Electromagnet ON")
time.sleep(3)
GPIO.output(MAGNET_PIN, GPIO.LOW)
print("  → Electromagnet OFF")

print()
print("Test 3: Rapid pulses (5x 0.5s on/off)")
time.sleep(1)

for i in range(5):
    GPIO.output(MAGNET_PIN, GPIO.HIGH)
    print(f"  Pulse {i+1}: ON")
    time.sleep(0.5)
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    print(f"  Pulse {i+1}: OFF")
    time.sleep(0.5)

GPIO.cleanup()

print()
print("="*60)
print("Did you observe:")
print("  - Magnetic field when ON?")
print("  - Coil getting warm after 3-second pulse?")
print("  - Any clicking/buzzing from coil?")
print("="*60)
