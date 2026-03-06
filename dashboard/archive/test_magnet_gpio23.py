#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

MAGNET_PIN = 23  # Physical Pin 16

GPIO.setmode(GPIO.BCM)
GPIO.setup(MAGNET_PIN, GPIO.OUT)

print('Testing electromagnet on GPIO 23 (Pin 16)')
print()

# Test 1: Turn electromagnet ON
print('Test 1: Turning electromagnet ON for 3 seconds...')
GPIO.output(MAGNET_PIN, GPIO.HIGH)
time.sleep(3)

# Test 2: Turn electromagnet OFF
print('Test 2: Turning electromagnet OFF for 2 seconds...')
GPIO.output(MAGNET_PIN, GPIO.LOW)
time.sleep(2)

# Test 3: Pulse test
print('Test 3: Pulsing electromagnet 5 times (0.5s on, 0.5s off)...')
for i in range(5):
    GPIO.output(MAGNET_PIN, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    time.sleep(0.5)

print('Test complete! Electromagnet is now OFF')
GPIO.cleanup()
