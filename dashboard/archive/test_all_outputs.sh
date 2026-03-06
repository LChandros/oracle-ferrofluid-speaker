#!/bin/bash

echo "======================================"
echo "TEST ALL AUDIO OUTPUTS"
echo "======================================"
echo ""
echo "Testing if audio is coming from ReSpeaker..."
echo ""
echo "Test 1: Playing through default output"
echo "---------------------------------------"
aplay -D plughw:3,0 /home/tyahn/cough.wav

echo ""
echo "Did you hear pops? (y/n)"
read -p "" heard_pops

echo ""
echo "Test 2: Check if ReSpeaker headphone jack has audio"
echo "----------------------------------------------------"
echo "ACTION: Put your ear VERY CLOSE to the ReSpeaker headphone jack"
echo "        (the 3.5mm jack on top of the Pi HAT)"
echo "        You might hear VERY faint audio directly from jack"
echo ""
read -p "Press ENTER when ready..."

echo "Playing again..."
aplay -D plughw:3,0 /home/tyahn/cough.wav &
sleep 1

echo ""
read -p "Did you hear ANYTHING from the ReSpeaker jack itself? (y/n): " heard_from_jack

if [ "$heard_from_jack" = "y" ]; then
    echo ""
    echo "✅ ReSpeaker IS outputting audio!"
    echo "   → Problem is in external amp or speaker"
else
    echo ""
    echo "❌ ReSpeaker NOT outputting audio"
    echo "   → Software routing or HAT issue"
fi

echo ""
echo "Test 3: Try routing to headphone explicitly"
echo "--------------------------------------------"
echo "Enabling headphone output..."

# Try routing audio through headphone path instead of speaker
amixer -c 3 cset numid=60 on  # Headphone Switch if exists
amixer -c 3 set Headphone 127

echo "Playing with headphone routing..."
aplay -D plughw:3,0 /home/tyahn/cough.wav

echo ""
read -p "Any difference? (y/n): " difference

echo ""
echo "======================================"
echo "DIAGNOSTIC COMPLETE"
echo "======================================"
