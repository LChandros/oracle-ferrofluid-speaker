#!/bin/bash
# Launch TTS with visualization
# Must run with sudo for LED/electromagnet control

if [ "$EUID" -ne 0 ]; then 
    echo "🔐 Relaunching with sudo..."
    exec sudo "$0" "$@"
fi

cd ~
python3 ~/speak.py --visualize
