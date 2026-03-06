#!/usr/bin/env python3
"""Check what Physical Pin 12 actually is"""

# Physical Pin 12 = GPIO 18 (BCM numbering)

import RPi.GPIO as GPIO
import time

# Physical pin 12 = GPIO 18
PIN = 18

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

print("="*60)
print("CHECKING PHYSICAL PIN 12 (GPIO 18)")
print("="*60)
print()

# Read current state without setting up
print("Reading pin state without setup...")
GPIO.setup(PIN, GPIO.IN)
state = GPIO.input(PIN)
print(f"Current state: {state} ({HIGH if state else LOW})")
print()

# Now set as output and test
print("Setting as OUTPUT and testing...")
GPIO.setup(PIN, GPIO.OUT)

print("\nTest 1: Set LOW")
GPIO.output(PIN, GPIO.LOW)
time.sleep(1)
print("  Pin is now LOW")

print("\nTest 2: Set HIGH")  
GPIO.output(PIN, GPIO.HIGH)
time.sleep(1)
print("  Pin is now HIGH")
print("  → MOSFET should turn ON electromagnet")

print("\nTest 3: Set LOW again")
GPIO.output(PIN, GPIO.LOW)
time.sleep(1)
print("  Pin is now LOW")
print("  → MOSFET should turn OFF electromagnet")

print()
print("="*60)
print("IMPORTANT:")
print("If MOSFET is ALWAYS ON regardless of this script,")
print("then the signal wire is not connected to the right pin!")
print("="*60)

GPIO.cleanup()
