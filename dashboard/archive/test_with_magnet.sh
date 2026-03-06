#!/bin/bash
echo "Testing audio with electromagnet enabled/disabled"
echo ""

echo "Test 1: Electromagnet OFF (GPIO 12 = LOW)"
gpio -g mode 12 out 2>/dev/null
gpio -g write 12 0 2>/dev/null
echo "Playing audio..."
ffmpeg -i ~/test-elevenlabs.mp3 -ar 48000 -ac 2 -filter:a 'volume=0.7' -y /tmp/test-clean.wav 2>&1 | tail -3
aplay -D plughw:3,0 /tmp/test-clean.wav
echo ""

echo "Test 2: Electromagnet ON (GPIO 12 = HIGH)"
gpio -g write 12 1 2>/dev/null
echo "Playing audio..."
aplay -D plughw:3,0 /tmp/test-clean.wav
gpio -g write 12 0 2>/dev/null
echo ""

echo "Test complete. Was there a difference?"
