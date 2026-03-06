#!/bin/bash

echo "======================================"
echo "AUDIO CHAIN DIAGNOSTIC"
echo "======================================"
echo ""
echo "Current setup:"
echo "  ReSpeaker → Ground Loop Isolator → DROK Amp → Speaker"
echo ""
echo "Step 1: Test ReSpeaker headphone output directly"
echo "------------------------------------------------"
echo ""
echo "ACTION REQUIRED:"
echo "1. Find headphones or earbuds"
echo "2. Locate the ReSpeaker HAT on top of Raspberry Pi"
echo "3. Find the 3.5mm headphone jack on the ReSpeaker"
echo "4. Unplug the cable going to ground loop isolator"
echo "5. Plug headphones DIRECTLY into ReSpeaker jack"
echo ""
read -p "Press ENTER when headphones are connected..."

echo ""
echo "Playing test tone (440Hz sine wave for 3 seconds)..."
timeout 3 speaker-test -D plughw:3,0 -c 2 -t sine -f 440 &>/dev/null

echo ""
read -p "Did you HEAR the tone in headphones? (y/n): " heard_tone

if [ "$heard_tone" = "y" ]; then
    echo "✅ ReSpeaker output is WORKING"
    echo "   Problem is downstream (cables/amp/speaker)"
else
    echo "❌ ReSpeaker output is NOT WORKING"
    echo "   Software or HAT hardware issue"
    exit 1
fi

echo ""
echo "Step 2: Check DROK amp power and connections"
echo "---------------------------------------------"
echo ""
echo "ACTION REQUIRED:"
echo "1. Unplug headphones from ReSpeaker"
echo "2. Reconnect cable from ReSpeaker to ground loop isolator"
echo "3. Check DROK amplifier:"
echo "   - Is power LED on?"
echo "   - Is volume knob turned up (clockwise)?"
echo "   - Is 3.5mm cable plugged into INPUT jack?"
echo "   - Are speaker wires in OUTPUT terminals?"
echo ""
read -p "Press ENTER when checked..."

echo ""
echo "Step 3: Test with music file"
echo "-----------------------------"
echo ""
echo "Playing cough.wav through full chain..."
aplay -D plughw:3,0 /home/tyahn/cough.wav

echo ""
read -p "Did you hear cough from speaker? (y/n): " heard_cough

if [ "$heard_cough" = "y" ]; then
    echo "✅ FULL AUDIO CHAIN WORKING!"
    echo "   Audio is fixed!"
else
    echo "⚠️  Still no sound from speaker"
    echo ""
    echo "Likely issues:"
    echo "  - DROK amp not powered"
    echo "  - Volume knob at zero"
    echo "  - Cable in wrong jack (should be INPUT)"
    echo "  - Speaker wires disconnected"
    echo "  - Ground loop isolator backwards"
fi

echo ""
echo "======================================"
echo "DIAGNOSTIC COMPLETE"
echo "======================================"
