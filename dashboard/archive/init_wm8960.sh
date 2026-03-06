#!/bin/bash
# WM8960 Audio HAT Initialization Script
# Proper mixer configuration for headphone output

CARD=3

echo "Initializing WM8960 Audio HAT (Card $CARD)..."

# Set playback volume (Digital)
amixer -c $CARD sset 'Playback' 255

# Set headphone volume (Analog)
amixer -c $CARD sset 'Headphone' 127

# Enable headphone zero-cross detection
amixer -c $CARD sset 'Headphone Playback ZC' on

# Set speaker volume
amixer -c $CARD sset 'Speaker' 127

# Enable speaker zero-cross
amixer -c $CARD sset 'Speaker Playback ZC' on

# Enable PCM to output mixers (CRITICAL for audio path)
amixer -c $CARD sset 'Left Output Mixer PCM' on
amixer -c $CARD sset 'Right Output Mixer PCM' on

# Disable boost bypass (use direct PCM path)
amixer -c $CARD sset 'Left Output Mixer Boost Bypass' off 2>/dev/null || true
amixer -c $CARD sset 'Right Output Mixer Boost Bypass' off 2>/dev/null || true

# Set DAC to stereo mode
amixer -c $CARD sset 'DAC Mono Mix' 'Stereo' 2>/dev/null || true

# Disable mono output mixers (we want stereo)
amixer -c $CARD sset 'Mono Output Mixer Left' off 2>/dev/null || true
amixer -c $CARD sset 'Mono Output Mixer Right' off 2>/dev/null || true

# Disable PCM -6dB attenuation
amixer -c $CARD sset 'PCM Playback -6dB' off 2>/dev/null || true

echo "WM8960 initialization complete!"
echo ""
echo "Current settings:"
amixer -c $CARD sget 'Headphone'
amixer -c $CARD sget 'Playback'
