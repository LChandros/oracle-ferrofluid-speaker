#!/usr/bin/env python3
"""Check what Physical Pin 12 actually is"""

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

# Now set as output and test
print("Setting as OUTPUT and testing...")
GPIO.setup(PIN, GPIO.OUT)

print("\nTest 1: Set LOW for 3 seconds")
GPIO.output(PIN, GPIO.LOW)
print("  Pin is LOW - MOSFET should be OFF")
time.sleep(3)

print("\nTest 2: Set HIGH for 3 seconds")  
GPIO.output(PIN, GPIO.HIGH)
print("  Pin is HIGH - MOSFET should be ON")
print("  → Check if electromagnet turns ON!")
time.sleep(3)

print("\nTest 3: Set LOW again for 3 seconds")
GPIO.output(PIN, GPIO.LOW)
print("  Pin is LOW - MOSFET should be OFF")
time.sleep(3)

print()
print("="*60)
print("Question: Did the electromagnet turn on/off?")
print("  YES = Pin is working correctly")
print("  NO = Signal wire on wrong pin or MOSFET issue")
print("="*60)

GPIO.cleanup()
