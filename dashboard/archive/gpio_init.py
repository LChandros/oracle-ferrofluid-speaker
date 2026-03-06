#!/usr/bin/env python3
# Initialize GPIO pins to safe default states at boot
import RPi.GPIO as GPIO
import sys

# Physical pin 12 = GPIO18 (BCM numbering)
MAGNET_PIN = 18

try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(MAGNET_PIN, GPIO.OUT)
    GPIO.output(MAGNET_PIN, GPIO.LOW)  # Ensure magnet is OFF
    print('GPIO initialized: Magnet pin set to LOW')
    # Keep the script running to hold the pin state
    # It will exit on system shutdown
    sys.exit(0)
except Exception as e:
    print(f'Error initializing GPIO: {e}')
    sys.exit(1)
