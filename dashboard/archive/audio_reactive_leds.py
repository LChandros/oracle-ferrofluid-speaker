#!/usr/bin/env python3
"""
Audio-reactive LED strip controller for ferrofluid speaker
Reads audio from ALSA loopback and controls LED strip on GPIO12 (Pin 32)
"""

import pyaudio
import numpy as np
import RPi.GPIO as GPIO
import time
import sys
import threading

# Configuration
LED_PIN = 12  # GPIO12 (Physical Pin 32)
CHUNK = 1024  # Audio buffer size
RATE = 44100  # Sample rate
SMOOTHING = 0.3  # LED brightness smoothing (0-1, lower = smoother)
MIN_BRIGHTNESS = 0  # Minimum LED brightness (0-100)
MAX_BRIGHTNESS = 100  # Maximum LED brightness (0-100)
GAIN = 2.0  # Audio sensitivity multiplier

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
pwm = GPIO.PWM(LED_PIN, 1000)  # 1kHz PWM frequency
pwm.start(0)

# Global variables
current_brightness = 0
running = True

def get_audio_level(audio_data):
    """Calculate RMS volume from audio data"""
    try:
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Calculate RMS (Root Mean Square) amplitude
        rms = np.sqrt(np.mean(np.square(audio_array.astype(np.float32))))
        
        # Normalize to 0-1 range (approximate max is 32768 for int16)
        level = min(1.0, (rms / 32768.0) * GAIN)
        
        return level
    except Exception as e:
        print(f"Error calculating audio level: {e}")
        return 0

def audio_capture_thread():
    """Capture audio and update LED brightness"""
    global current_brightness, running
    
    try:
        # Initialize PyAudio
        p = pyaudio.PyAudio()
        
        # Open audio stream (monitor audio output via ALSA loopback or direct capture)
        stream = p.open(
            format=pyaudio.paInt16,
            channels=2,
            rate=RATE,
            input=True,
            input_device_index=None,  # Default input device
            frames_per_buffer=CHUNK
        )
        
        print("Audio capture started. LED strip will react to audio...")
        print("Press Ctrl+C to stop.")
        
        while running:
            try:
                # Read audio data
                audio_data = stream.read(CHUNK, exception_on_overflow=False)
                
                # Calculate audio level
                level = get_audio_level(audio_data)
                
                # Map to brightness range with smoothing
                target_brightness = MIN_BRIGHTNESS + (level * (MAX_BRIGHTNESS - MIN_BRIGHTNESS))
                current_brightness = (current_brightness * SMOOTHING) + (target_brightness * (1 - SMOOTHING))
                
                # Update LED PWM
                pwm.ChangeDutyCycle(current_brightness)
                
            except IOError as e:
                # Handle buffer overflow
                continue
                
    except Exception as e:
        print(f"Error in audio capture: {e}")
        print("Note: This requires audio input device. Running demo mode...")
        demo_mode()
    finally:
        if 'stream' in locals():
            stream.stop_stream()
            stream.close()
        if 'p' in locals():
            p.terminate()

def demo_mode():
    """Demo mode with pulsing LED (no audio capture)"""
    global current_brightness, running
    print("Running in DEMO mode - LED will pulse rhythmically")
    print("Press Ctrl+C to stop.")
    
    pulse_speed = 0.05
    direction = 1
    
    while running:
        current_brightness += direction * 2
        
        if current_brightness >= MAX_BRIGHTNESS:
            direction = -1
        elif current_brightness <= MIN_BRIGHTNESS:
            direction = 1
            
        pwm.ChangeDutyCycle(current_brightness)
        time.sleep(pulse_speed)

def cleanup():
    """Clean up GPIO and PWM"""
    global running
    running = False
    time.sleep(0.1)
    pwm.stop()
    GPIO.cleanup()
    print("Cleanup complete. LEDs off.")

if __name__ == "__main__":
    try:
        # Start audio capture in thread
        audio_thread = threading.Thread(target=audio_capture_thread, daemon=True)
        audio_thread.start()
        
        # Keep main thread alive
        while True:
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("Stopping...")
        cleanup()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        cleanup()
        sys.exit(1)
