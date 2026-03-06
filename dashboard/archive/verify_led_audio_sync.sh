#!/bin/bash

echo "======================================"
echo "LED + AUDIO SYNC VERIFICATION"
echo "======================================"
echo ""
echo "The music visualizer is currently running."
echo "Music just played for 10 seconds."
echo ""
read -p "Did you HEAR the music from the speaker? (y/n): " heard_music
read -p "Did you SEE the LEDs reacting to the music? (y/n): " saw_leds

echo ""
if [ "$heard_music" = "y" ] && [ "$saw_leds" = "y" ]; then
    echo "🎉 SUCCESS! Both audio and LEDs working together!"
    echo ""
    echo "System Status:"
    echo "  ✅ Audio playback working"
    echo "  ✅ LED visualization working"
    echo "  ✅ Both synced to music"
    echo ""
    echo "Next: Ready to test electromagnet integration!"
elif [ "$heard_music" = "y" ]; then
    echo "⚠️  Audio works but LEDs not visible"
    echo "Check: LED strip power, wiring to GPIO12"
elif [ "$saw_leds" = "y" ]; then
    echo "⚠️  LEDs work but no audio"
    echo "Check: DROK amp power, volume, connections"
else
    echo "❌ Neither working - need troubleshooting"
fi

echo ""
read -p "Stop the LED visualizer? (y/n): " stop_viz

if [ "$stop_viz" = "y" ]; then
    echo "Stopping visualizer..."
    sudo pkill -f music_visualizer
    echo "✅ Visualizer stopped"
fi
