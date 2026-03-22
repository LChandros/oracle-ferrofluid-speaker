#!/bin/bash
# Oracle Audio Fix Script
# Run this if audio stops working after reboot

echo "Setting WM8960 volumes to maximum..."
amixer -c 4 sset 'Headphone' 127
amixer -c 4 sset 'Speaker' 127
sudo alsactl store

echo "Checking audio status..."
cat /proc/asound/card4/pcm0p/sub0/status

echo ""
echo "✓ Volume fix complete!"
echo "If you still don't hear audio, check Spotify is connected to 'development-hub'"
