#!/bin/bash
# Test script to play music and sync LEDs

echo "=== Moneo Voice Nexus - Music Sync Test ==="
echo ""
echo "This will:"
echo "  1. Play test-music.mp3 through the speaker"
echo "  2. LEDs will react to the music frequencies"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Kill any existing music processes
pkill -f mpg123 2>/dev/null
pkill -f music_visualizer 2>/dev/null

# Start LED visualizer in background
echo "Starting LED visualizer..."
sudo python3 ~/music_visualizer.py --scheme moneo &
VISUALIZER_PID=$!

# Give it a second to initialize
sleep 2

# Play music
echo "Playing music..."
mpg123 ~/test-music.mp3

# Cleanup
echo ""
echo "Stopping visualizer..."
sudo kill $VISUALIZER_PID 2>/dev/null

echo "Test complete!"
