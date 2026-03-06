#!/bin/bash

echo '========================================='
echo 'Testing Audio + Electromagnet on GPIO 23'
echo '========================================='
echo

# Kill any existing GPIO processes
sudo pkill -f test_gpio23.py 2>/dev/null
sudo pkill -f test_magnet 2>/dev/null
sleep 1

echo 'Test 1: Audio ONLY (baseline)'
echo '------------------------------'
aplay -D plughw:3,0 /home/tyahn/cough.wav
sleep 1

echo
echo 'Test 2: Audio WHILE electromagnet is ON'
echo '----------------------------------------'
# Start electromagnet ON in background
python3 << 'PYEOF' &
import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)
GPIO.output(23, GPIO.HIGH)
time.sleep(5)
GPIO.output(23, GPIO.LOW)
GPIO.cleanup()
PYEOF

# Wait for electromagnet to turn on
sleep 0.5

# Play audio while electromagnet is on
aplay -D plughw:3,0 /home/tyahn/cough.wav

# Wait for electromagnet to finish
sleep 2

echo
echo 'Test 3: Audio WHILE electromagnet is PULSING'
echo '--------------------------------------------'
# Start electromagnet pulsing in background
python3 << 'PYEOF' &
import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)
for i in range(10):
    GPIO.output(23, GPIO.HIGH)
    time.sleep(0.2)
    GPIO.output(23, GPIO.LOW)
    time.sleep(0.2)
GPIO.cleanup()
PYEOF

# Wait for pulsing to start
sleep 0.5

# Play audio while pulsing
aplay -D plughw:3,0 /home/tyahn/cough.wav

echo
echo '========================================='
echo 'Test complete!'
echo '========================================='
