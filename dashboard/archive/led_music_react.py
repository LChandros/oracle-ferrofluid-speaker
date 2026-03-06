#!/usr/bin/env python3
"""Audio-reactive LED using ReSpeaker microphone - Fixed version"""

import pyaudio
import numpy as np
import RPi.GPIO as GPIO
import time
import sys

LED_PIN = 12
CHUNK = 2048
RATE = 16000

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
pwm = GPIO.PWM(LED_PIN, 1000)
pwm.start(0)

p = pyaudio.PyAudio()

# Find the ReSpeaker device
device_index = None
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if 'wm8960' in info['name'].lower() and info['maxInputChannels'] > 0:
        device_index = i
        print(f"Found ReSpeaker: {info['name']} (index {i})")
        break

if device_index is None:
    print("ERROR: Could not find ReSpeaker microphone!")
    print("\nAvailable input devices:")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            print(f"  [{i}] {info['name']}")
    sys.exit(1)

# Open microphone stream
try:
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=RATE,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=CHUNK
    )
    
    print("✅ Audio-reactive LEDs started!")
    print("🎵 Play music to see the LED effect.")
    print("Press Ctrl+C to stop.\n")
    
    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Calculate volume (RMS)
            rms = np.sqrt(np.mean(audio_data**2))
            
            # Map to 0-100 brightness (adjust sensitivity here)
            brightness = min(100, (rms / 800) * 100)
            
            pwm.ChangeDutyCycle(brightness)
            
        except IOError:
            continue
            
except KeyboardInterrupt:
    print("\n🛑 Stopping...")
except Exception as e:
    print(f"\n❌ Error: {e}")
finally:
    pwm.stop()
    GPIO.cleanup()
    if 'stream' in locals():
        stream.stop_stream()
        stream.close()
    p.terminate()
    print("✅ Cleanup complete.")
