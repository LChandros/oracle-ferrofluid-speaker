#!/bin/bash
# Oracle Audio Fix Script
# Run this if you have no audio from the ferrofluid speaker

echo ======================================
echo  Oracle Audio Fix
echo ======================================
echo 

# Set all volumes to maximum
echo [1/3] Setting WM8960 volumes to maximum...
amixer -c 4 sset 'Headphone' 127 > /dev/null 2>&1
amixer -c 4 sset 'Speaker' 127 > /dev/null 2>&1
amixer -c 4 sset 'Playback' 255 > /dev/null 2>&1

# Save settings
echo [2/3] Saving ALSA settings...
sudo alsactl store

# Restart Raspotify to pick up new settings
echo [3/3] Restarting Raspotify...
sudo systemctl restart raspotify
sleep 2

echo 
echo ✓ Audio fix applied!
echo 
echo Current volume levels:
amixer -c 4 sget Headphone | grep -E 'Playback.*%'
amixer -c 4 sget Speaker | grep -E 'Playback.*%'
echo 
echo Now play music on Spotify and check if you hear audio.
echo ======================================
