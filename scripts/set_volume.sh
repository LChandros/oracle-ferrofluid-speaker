#!/bin/bash
# Set volume for WM8960 sound card - address by NAME not index
# (card index changes across reboots; index-based -c 3 broke after 2026-05-21 reboot)
CARD=wm8960soundcard
amixer -c $CARD sset Speaker 127
amixer -c $CARD sset Headphone 120
amixer -c $CARD sset Playback 255
amixer -c $CARD sset Capture 30   # mic gain - 63 (+30dB) clips the wake-word mic
