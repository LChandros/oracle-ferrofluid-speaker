#!/usr/bin/env python3
"""Test ground isolation issue - CORRECT PIN"""

import RPi.GPIO as GPIO
import time

LED_PIN = 12      # GPIO 12 (Physical Pin 32) - LED strip
MAGNET_PIN = 18   # GPIO 18 (Physical Pin 12) - MOSFET

print("="*60)
print("PIN MAPPING:")
print("  Physical Pin 32 = GPIO 12 = LED Strip")
print("  Physical Pin 12 = GPIO 18 = MOSFET")
print("="*60)
print()

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(MAGNET_PIN, GPIO.OUT)

print("GROUND ISOLATION TEST")
print("="*60)
print()
print("Watch LED brightness when MOSFET signal toggles")
print()

try:
    # Set LED to steady state
    pwm = GPIO.PWM(LED_PIN, 1000)
    pwm.start(50)  # 50% brightness
    print("LED at 50% brightness (steady)")
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
    pwm.stop()
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    GPIO.cleanup()
