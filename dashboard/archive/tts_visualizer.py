#!/usr/bin/env python3
"""
TTS Audio Visualizer - Synchronized LED + Electromagnet Control
Analyzes WAV audio and drives 10-LED strip + electromagnet in real-time
- Frequency analysis across 10 bands (bass → treble)
- Pitch-based color gradient (red → blue)
- Electromagnet pulses with amplitude
"""

import RPi.GPIO as GPIO
from rpi_ws281x import PixelStrip, Color
import numpy as np
import wave
import time
import threading
import subprocess
# from scipy import signal

# ============================================================
# HARDWARE CONFIGURATION
# ============================================================

# Electromagnet
MAGNET_PIN = 21  # GPIO 21 (Physical pin 40)

# LED Strip
LED_COUNT = 10
LED_PIN = 18  # GPIO 18 (Physical pin 12)
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0

# ============================================================
# AUDIO ANALYSIS CONFIGURATION
# ============================================================

CHUNK_SIZE = 2048       # FFT window size
SMOOTHING = 0.6         # LED smoothing (0-1, higher = smoother)
GAIN = 2.5              # Sensitivity multiplier
MAGNET_THRESHOLD = 0.3  # Min amplitude to activate magnet (0-1)

# Frequency bands for 10 LEDs (Hz)
FREQ_BANDS = [
    (20, 100),      # LED 0: Sub-bass (red)
    (100, 250),     # LED 1: Bass (orange)
    (250, 500),     # LED 2: Low-mid (yellow)
    (500, 1000),    # LED 3: Mid (yellow-green)
    (1000, 2000),   # LED 4: Mid-high (green)
    (2000, 3000),   # LED 5: Presence (cyan)
    (3000, 5000),   # LED 6: Brilliance (sky blue)
    (5000, 8000),   # LED 7: Air (blue)
    (8000, 12000),  # LED 8: Ultra-high (purple)
    (12000, 20000), # LED 9: Sparkle (violet)
]

# Pitch-based color gradient (bass=red, treble=purple)
COLOR_GRADIENT = [
    Color(255, 0, 0),      # Red (bass)
    Color(255, 64, 0),     # Red-orange
    Color(255, 128, 0),    # Orange
    Color(255, 192, 0),    # Yellow-orange
    Color(128, 255, 0),    # Yellow-green
    Color(0, 255, 128),    # Cyan
    Color(0, 192, 255),    # Sky blue
    Color(0, 64, 255),     # Blue
    Color(128, 0, 255),    # Purple
    Color(192, 0, 255),    # Violet (treble)
]

# ============================================================
# TTS VISUALIZER CLASS
# ============================================================

class TTSVisualizer:
    def __init__(self):
        """Initialize hardware"""
        self.strip = None
        self.levels = [0.0] * LED_COUNT
        self.running = False
        self.magnet_pwm = None
        
    def setup(self):
        """Initialize GPIO and LED strip"""
        print("🔧 Initializing visualization hardware...")
        
        # Setup GPIO for electromagnet with PWM
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(MAGNET_PIN, GPIO.OUT)
        self.magnet_pwm = GPIO.PWM(MAGNET_PIN, 100)  # 100 Hz PWM
        self.magnet_pwm.start(0)  # Start at 0% duty cycle
        
        # Initialize LED strip
        self.strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, 
                               LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
        self.strip.begin()
        
        # Clear LEDs
        for i in range(LED_COUNT):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()
        
        print("✅ Electromagnet ready (GPIO 21, Pin 40)")
        print("✅ LED strip ready (GPIO 18, Pin 12)")
        
    def cleanup(self):
        """Clean up GPIO and turn off LEDs"""
        self.running = False
        """Clean up GPIO and turn off LEDs"""
        if self.magnet_pwm:
            self.magnet_pwm.stop()
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        
        if self.strip:
            for i in range(LED_COUNT):
                self.strip.setPixelColor(i, Color(0, 0, 0))
            self.strip.show()
        
        GPIO.cleanup()
        print("✅ Hardware cleaned up")
        
    def analyze_chunk(self, audio_chunk, sample_rate):
        """Perform FFT and extract frequency band levels"""
        # Apply Hanning window
        windowed = audio_chunk * np.hanning(len(audio_chunk))
        
        # Perform FFT
        fft = np.fft.rfft(windowed)
        fft_magnitude = np.abs(fft)
        
        # Frequency bins
        freq_bins = np.fft.rfftfreq(len(windowed), 1.0/sample_rate)
        
        # Extract levels for each frequency band
        band_levels = []
        for low_freq, high_freq in FREQ_BANDS:
            mask = (freq_bins >= low_freq) & (freq_bins < high_freq)
            
            if np.any(mask):
                level = np.mean(fft_magnitude[mask])
            else:
                level = 0
            
            band_levels.append(level)
        
        # Normalize to 0-1 range
        max_level = np.max(band_levels) if np.max(band_levels) > 0 else 1
        normalized = [min(1.0, (level / max_level) * GAIN) for level in band_levels]
        
        # Calculate RMS amplitude for electromagnet
        rms = np.sqrt(np.maximum(0, np.mean(audio_chunk**2)))  # Prevent negative values
        rms_normalized = min(1.0, rms / 5000.0 * GAIN)
        
        return normalized, rms_normalized
        
    def update_hardware(self, levels, amplitude):
        """Update LEDs and electromagnet"""
        # Update LEDs with smoothing
        for i in range(LED_COUNT):
            target = levels[i] if i < len(levels) else 0
            self.levels[i] = (self.levels[i] * SMOOTHING) + (target * (1 - SMOOTHING))
            
            # Apply pitch-based color gradient
            color = COLOR_GRADIENT[i]
            r = int(((color >> 16) & 0xFF) * self.levels[i])
            g = int(((color >> 8) & 0xFF) * self.levels[i])
            b = int((color & 0xFF) * self.levels[i])
            
            self.strip.setPixelColor(i, Color(r, g, b))
        
        self.strip.show()
        
        # Update electromagnet (PWM duty cycle based on amplitude)
        if amplitude > MAGNET_THRESHOLD:
            duty_cycle = int(amplitude * 100)  # 0-100%
            self.magnet_pwm.ChangeDutyCycle(duty_cycle)
        else:
            self.magnet_pwm.ChangeDutyCycle(0)
    
    def visualize_audio(self, wav_path):
        """Main visualization: analyze and play WAV file with sync"""
        print(f"🎵 Visualizing: {wav_path}")
        
        # Open WAV file
        with wave.open(wav_path, 'rb') as wf:
            sample_rate = wf.getframerate()
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            n_frames = wf.getnframes()
            
            print(f"   Sample rate: {sample_rate} Hz")
            print(f"   Channels: {n_channels}")
            print(f"   Duration: {n_frames/sample_rate:.2f}s")
            
            # Start audio playback in background
            play_proc = subprocess.Popen(
                ["aplay", "-q", "-D", "plughw:3,0", wav_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.running = True
            start_time = time.time()
            
            # Read and analyze audio in chunks
            while self.running:
                # Read chunk
                frames = wf.readframes(CHUNK_SIZE)
                if len(frames) == 0:
                    break
                
                # Convert to numpy array
                audio_data = np.frombuffer(frames, dtype=np.int16)
                
                # Use mono (average channels if stereo)
                if n_channels == 2:
                    audio_data = audio_data.reshape(-1, 2).mean(axis=1)
                
                # Analyze frequencies
                levels, amplitude = self.analyze_chunk(audio_data, sample_rate)
                
                # Update hardware
                self.update_hardware(levels, amplitude)
                
                # Sync timing with actual playback
                expected_time = wf.tell() / sample_rate
                elapsed = time.time() - start_time
                sleep_time = expected_time - elapsed
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            # Wait for playback to finish
            play_proc.wait()
        
        # Fade out
        for i in range(10):
            self.update_hardware([0] * LED_COUNT, 0)
            time.sleep(0.05)
        
        print("✅ Visualization complete")
    
    def run(self, wav_path):
        """Setup, visualize, and cleanup"""
        try:
            self.setup()
            self.visualize_audio(wav_path)
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted!")
        finally:
            self.running = False
            self.cleanup()

# ============================================================
# CLI INTERFACE
# ============================================================

def main():
    """Test visualization from command line"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 tts_visualizer.py <audio.wav>")
        sys.exit(1)
    
    wav_path = sys.argv[1]
    
    visualizer = TTSVisualizer()
    visualizer.run(wav_path)

if __name__ == "__main__":
    main()
