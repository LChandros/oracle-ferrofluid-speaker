#!/bin/bash

echo "======================================"
echo "AUDIO ROUTING FIX"
echo "======================================"
echo ""

# Kill any processes using audio
sudo pkill -9 aplay
sudo pkill -9 mpg123
sleep 1

# Reload audio driver
echo "Reloading audio driver..."
sudo modprobe -r snd_soc_wm8960
sleep 1
sudo modprobe snd_soc_wm8960
sleep 2

# Restore critical mixer settings
echo "Setting mixer controls..."

# Main volumes
amixer -c 3 set Playback 255
amixer -c 3 set Speaker 127  # MAX instead of 96
amixer -c 3 set Headphone 127

# Output mixer switches - CRITICAL
amixer -c 3 cset numid=52 on  # Left Output Mixer PCM
amixer -c 3 cset numid=55 on  # Right Output Mixer PCM

# Speaker AC/DC volumes
amixer -c 3 cset numid=16 5  # Speaker AC Volume
amixer -c 3 cset numid=15 5  # Speaker DC Volume

echo ""
echo "Testing audio..."
aplay -D plughw:3,0 /home/tyahn/cough.wav

echo ""
echo "Did you hear audio? (y/n)"
read -p "" response

if [ "$response" = "y" ]; then
    echo "✅ AUDIO FIXED!"
else
    echo "⚠️ Still not working - may need HAT reboot"
fi
