#!/bin/bash

echo "======================================"
echo "AUDIO CHAIN DIAGNOSTIC"
echo "======================================"
echo ""
echo "Current wiring:"
echo "  Pi Pin 2 (5V) → Audio Amp VIN"
echo "  Pi Pin 9 (GND) → Audio Amp GND"
echo "  ReSpeaker 3.5mm → Audio Amp INPUT"
echo "  Audio Amp OUTPUT → Speaker"
echo ""

read -p "Is the Audio Amp power LED ON? (y/n): " led_on

if [ "$led_on" != "y" ]; then
    echo ""
    echo "❌ PROBLEM: Amp not powered"
    echo "Check:"
    echo "  - Wire from Pin 2 to amp VIN connected?"
    echo "  - Wire from Pin 9 to amp GND connected?"
    exit 1
fi

echo ""
echo "Amp is powered. Testing audio output from ReSpeaker..."
echo ""
read -p "Put your ear CLOSE to the ReSpeaker headphone jack. Press ENTER..."

aplay -D plughw:3,0 /home/tyahn/cough.wav &
sleep 1

echo ""
read -p "Did you hear ANYTHING from the ReSpeaker jack itself? (y/n): " heard_jack

if [ "$heard_jack" != "y" ]; then
    echo ""
    echo "❌ PROBLEM: ReSpeaker not outputting audio"
    echo "This is a SOFTWARE issue, not wiring!"
    echo ""
    echo "Try: sudo reboot"
    exit 1
fi

echo ""
echo "✅ ReSpeaker IS outputting audio"
echo ""
echo "Now checking amp connections..."
read -p "Is the 3.5mm cable FULLY inserted in amp INPUT jack? (y/n): " cable_in

if [ "$cable_in" != "y" ]; then
    echo "Push the cable in firmly and try again"
    exit 1
fi

read -p "Are speaker wires in amp OUTPUT terminals (screwed tight)? (y/n): " speaker_wires

if [ "$speaker_wires" != "y" ]; then
    echo "Tighten the speaker wire terminals"
    exit 1
fi

read -p "Is amp volume knob turned UP (clockwise)? (y/n): " volume_up

if [ "$volume_up" != "y" ]; then
    echo "Turn volume knob all the way UP"
    exit 1
fi

echo ""
echo "All connections verified. Playing test..."
aplay -D plughw:3,0 /home/tyahn/cough.wav

echo ""
echo "If you still only hear pops, the amp itself may be damaged."
