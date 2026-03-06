#!/bin/bash
echo "=== Audio Noise Diagnostic Test ==="
echo "This will test audio with different components enabled/disabled"
echo ""

# Get current state of GPIO pins
echo "Current GPIO states:"
gpio -g mode 32 out 2>/dev/null || echo "GPIO 32 (LED): Command not available"
gpio -g mode 12 out 2>/dev/null || echo "GPIO 12 (Electromagnet): Command not available"
echo ""

echo "Test 1: Playing audio with all components ON (baseline - should be staticky)"
read -p "Press Enter to start..."
mpg123 -w /tmp/test.wav ~/test-elevenlabs.mp3 && aplay -D plughw:3,0 /tmp/test.wav
echo ""

echo "Test 2: Disable LED strip (GPIO 32 LOW) and test audio"
read -p "Press Enter to start..."
gpio -g write 32 0 2>/dev/null || echo "Could not control GPIO 32"
mpg123 -w /tmp/test.wav ~/test-elevenlabs.mp3 && aplay -D plughw:3,0 /tmp/test.wav
echo ""

echo "Test 3: Disable electromagnet (GPIO 12 LOW) and test audio"  
read -p "Press Enter to start..."
gpio -g write 12 0 2>/dev/null || echo "Could not control GPIO 12"
mpg123 -w /tmp/test.wav ~/test-elevenlabs.mp3 && aplay -D plughw:3,0 /tmp/test.wav
echo ""

echo "Test 4: Both disabled - test audio"
read -p "Press Enter to start..."
mpg123 -w /tmp/test.wav ~/test-elevenlabs.mp3 && aplay -D plughw:3,0 /tmp/test.wav
echo ""

echo "=== Diagnostic complete ==="
echo "Which test had the least static?"
