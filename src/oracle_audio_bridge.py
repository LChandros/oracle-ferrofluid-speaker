#!/usr/bin/env python3
"""
Oracle Audio Bridge - Simple passthrough from loopback to speakers
Bridges audio from Raspotify (loopback hw:2,1) to WM8960 speakers (hw:4,0)
"""
import alsaaudio
import sys
import time

LOOPBACK_DEVICE = "plughw:2,1"
SPEAKER_DEVICE = "plughw:4,0"
SAMPLE_RATE = 44100  # Match Raspotify actual output
CHANNELS = 2
CHUNK_SIZE = 2048  # Larger chunks for smoother streaming

print("Oracle Audio Bridge starting...")
print(f"  Input: {LOOPBACK_DEVICE}")
print(f"  Output: {SPEAKER_DEVICE}")
print(f"  Rate: {SAMPLE_RATE} Hz")

try:
    # Open input (loopback capture)
    inp = alsaaudio.PCM(
        alsaaudio.PCM_CAPTURE,
        alsaaudio.PCM_NORMAL,
        device=LOOPBACK_DEVICE,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        format=alsaaudio.PCM_FORMAT_S16_LE,
        periodsize=CHUNK_SIZE
    )
    print("✓ Input ready")

    # Open output (speakers)
    out = alsaaudio.PCM(
        alsaaudio.PCM_PLAYBACK,
        alsaaudio.PCM_NORMAL,
        device=SPEAKER_DEVICE,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        format=alsaaudio.PCM_FORMAT_S16_LE,
        periodsize=CHUNK_SIZE
    )
    print("✓ Output ready")
    print("\n🔊 Audio bridge running - press Ctrl+C to stop\n")

    # Simple passthrough loop
    frame_count = 0
    while True:
        length, data = inp.read()
        if length > 0:
            out.write(data)
            frame_count += 1
            if frame_count % 1000 == 0:
                print(f"Frames: {frame_count}", end='\r')

except KeyboardInterrupt:
    print("\n\nAudio bridge stopped")
    sys.exit(0)
except Exception as e:
    print(f"\n✗ Error: {e}")
    sys.exit(1)
