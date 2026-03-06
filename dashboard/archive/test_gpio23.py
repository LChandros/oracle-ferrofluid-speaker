#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

# Use GPIO 23 (Physical Pin 16) instead of GPIO 18
MAGNET_PIN = 23

GPIO.setmode(GPIO.BCM)
GPIO.setup(MAGNET_PIN, GPIO.OUT)
GPIO.output(MAGNET_PIN, GPIO.LOW)

print(f'GPIO {MAGNET_PIN} (Physical Pin 16) initialized LOW')
print('Electromagnet should be OFF')
print('Try playing audio now')
print()
print('Press Ctrl+C to exit')

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()
    print('\nGPIO cleaned up')
