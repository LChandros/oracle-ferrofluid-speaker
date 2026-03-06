#!/bin/bash

echo "======================================"
echo "RECONNECT MOSFET GND AND TEST"
echo "======================================"
echo ""
echo "Reconnect: Breadboard GND → MOSFET GND terminal"
echo ""
read -p "Is MOSFET GND reconnected? (y/n): " connected

if [ "$connected" != "y" ]; then
    echo "Reconnect and run again"
    exit 1
fi

echo ""
echo "Testing with electromagnet OFF first..."
sudo python3 -c "
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(18, GPIO.OUT)
GPIO.output(18, GPIO.LOW)
" 2>/dev/null

aplay -D plughw:3,0 cough.wav
echo ""
read -p "How was audio? (good/interference/pops): " audio_off

echo ""
echo "Now testing with electromagnet STATIC ON..."
sudo python3 -c "
import RPi.GPIO as GPIO
import subprocess
import time
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(18, GPIO.OUT)
GPIO.output(18, GPIO.HIGH)
time.sleep(0.5)
subprocess.run([aplay, -D, plughw:3,0, cough.wav])
GPIO.output(18, GPIO.LOW)
GPIO.cleanup()
" 2>/dev/null

read -p "How was audio? (good/hum/clicks/bad): " audio_on

echo ""
echo "Results:"
echo "  Magnet OFF: $audio_off"
echo "  Magnet ON: $audio_on"
