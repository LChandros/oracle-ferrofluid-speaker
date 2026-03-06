#\!/bin/bash

echo "======================================"
echo "NEW HARDWARE AUDIO TEST"
echo "======================================"
echo ""
echo "Current Setup:"
echo "  ReSpeaker HAT → Cable → NEW DROK Amp → NEW Speaker"
echo "  MOSFET: UNPLUGGED"
echo ""
echo "Step 1: Verify DROK amp power"
echo "------------------------------"
read -p "Is the power LED lit on the new DROK amp? (y/n): " led_on

if [ "$led_on" \!= "y" ]; then
    echo "❌ Amp not powered - connect 5V to amp VIN"
    exit 1
fi

echo ""
echo "Step 2: Verify connections"
echo "---------------------------"
echo "CHECK:"
echo "  1. Cable from ReSpeaker headphone jack → DROK amp INPUT jack"
echo "  2. Speaker wires: Red/Black from amp OUTPUT terminals → speaker"
echo "  3. Volume knob on amp turned UP (clockwise)"
echo ""
read -p "All connections verified? (y/n): " connections_ok

if [ "$connections_ok" \!= "y" ]; then
    echo "⚠️  Fix connections first"
    exit 1
fi

echo ""
echo "Step 3: Audio test with maximum volume"
echo "----------------------------------------"
echo "Setting all software volumes to MAX..."

amixer -c 3 set Playback 255
amixer -c 3 set Speaker 127
amixer -c 3 set Headphone 127
amixer -c 3 cset numid=16 5
amixer -c 3 cset numid=15 5

echo ""
echo "Playing LOUD test tone (440Hz) for 5 seconds..."
echo "Turn DROK amp volume knob all the way UP\!"
echo ""
read -p "Press ENTER to start tone..."

timeout 5 speaker-test -D plughw:3,0 -c 2 -t sine -f 440 2>&1 | head -10 &
TONE_PID=$\!

sleep 2
echo ""
echo "⚡ TONE PLAYING NOW ⚡"
echo "Turn the amp volume knob while listening\!"

wait $TONE_PID

echo ""
read -p "Did you hear the 440Hz tone? (y/n): " heard_tone

if [ "$heard_tone" = "y" ]; then
    echo ""
    echo "✅ AUDIO IS WORKING\!"
    echo ""
    echo "Final test with music..."
    timeout 5 mpg123 -a plughw:3,0 test-music.mp3 2>&1 | head -5
    echo ""
    echo "🎉 SUCCESS\! Audio system operational\!"
else
    echo ""
    echo "❌ Still no audio - troubleshooting needed"
    echo ""
    echo "Possible issues:"
    echo "  1. Cable not fully inserted in amp INPUT jack"
    echo "  2. Speaker wires loose in amp OUTPUT terminals"
    echo "  3. Volume knob at zero"
    echo "  4. Wrong jack on amp (should be INPUT, not headphone out)"
    echo "  5. ReSpeaker HAT hardware issue"
fi
