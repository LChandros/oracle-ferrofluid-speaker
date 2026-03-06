#!/bin/bash

echo '=================================================='
echo 'ORACLE AUDIO-REACTIVE SYSTEM TEST'
echo '=================================================='
echo
echo 'This will:'
echo '  1. Start the audio-reactive system (LEDs + electromagnet)'
echo '  2. Play music for 20 seconds'
echo '  3. LEDs and ferrofluid should react to the music!'
echo
echo 'Press Ctrl+C to stop early'
echo '=================================================='
echo
echo 'Starting audio-reactive system...'

# Kill any existing processes
sudo pkill -f oracle_audio_reactive.py 2>/dev/null
sudo pkill -f python3 2>/dev/null
sleep 1

# Start the audio-reactive system in background
sudo python3 /home/tyahn/oracle_audio_reactive.py &
ORACLE_PID=$!

echo "Audio-reactive system started (PID: $ORACLE_PID)"
echo
echo 'Waiting 3 seconds for initialization...'
sleep 3

echo
echo '=================================================='
echo 'PLAYING MUSIC - Watch the LEDs and ferrofluid!'
echo '=================================================='
echo

# Play music for 20 seconds
timeout 20 mpg123 -a plughw:3,0 /home/tyahn/test-music.mp3

echo
echo '=================================================='
echo 'Music finished!'
echo 'Stopping audio-reactive system...'
echo '=================================================='

# Stop the audio-reactive system
sudo kill $ORACLE_PID 2>/dev/null
sleep 2

# Cleanup any remaining processes
sudo pkill -f oracle_audio_reactive.py 2>/dev/null

echo
echo 'Test complete!'
