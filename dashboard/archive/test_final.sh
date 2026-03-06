#!/bin/bash

# Kill any existing GPIO processes
sudo pkill -f python3 2>/dev/null
sleep 1

echo 'Starting electromagnet on GPIO 23 (Physical Pin 16)...'

# Start electromagnet pulsing in background
python3 << 'PYEOF' &
import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)
print('Electromagnet pulsing...')
for i in range(20):
    GPIO.output(23, GPIO.HIGH)
    time.sleep(0.3)
    GPIO.output(23, GPIO.LOW)
    time.sleep(0.3)
GPIO.cleanup()
print('Electromagnet stopped')
PYEOF

# Wait for electromagnet to start
sleep 1

echo 'Playing audio while electromagnet is pulsing...'
aplay -D plughw:3,0 /home/tyahn/cough.wav

echo 'Test complete!'
