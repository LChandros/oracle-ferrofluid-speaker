#!/usr/bin/env python3
"""
Audio Test Script
Plays a test tone through the speakers
"""

import subprocess
import os

print("Testing audio output...")
print("Make sure your amplifier is connected to the Pi's audio jack")
print("(or we'll set up ReSpeaker after reboot)")
print()

# Generate a 1-second 440Hz test tone (A note)
print("Generating test tone (440Hz, 1 second)...")
subprocess.run([
    "speaker-test",
    "-t", "sine",
    "-f", "440",
    "-l", "1"
], check=False)

print("\n✅ Audio test complete!")
print("Did you hear a tone through your speakers?")
