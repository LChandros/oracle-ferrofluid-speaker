#!/usr/bin/env python3
"""Test ground isolation issue"""

import RPi.GPIO as GPIO
import time

LED_PIN = 12
MAGNET_PIN = 21

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(MAGNET_PIN, GPIO.OUT)

print("="*60)
print("GROUND ISOLATION TEST")
print("="*60)
print()
print("Watch LED brightness when MOSFET signal toggles")
print()

try:
    # Set LED to steady state
    GPIO.output(LED_PIN, GPIO.HIGH)
    print("LED ON (steady)")
    print()
    
    for i in range(5):
        print(f"Test {i+1}/5:")
        print("  MOSFET signal OFF")
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        time.sleep(2)
        
        print("  MOSFET signal ON → Watch for LED brightness change!")
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        time.sleep(2)
        print()
    
    print("="*60)
    print("Did LED brightness change when MOSFET toggled?")
    print("  YES = Ground loop confirmed")
    print("  NO = Different issue")
    print("="*60)

finally:
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    GPIO.output(LED_PIN, GPIO.LOW)
    GPIO.cleanup()
