#!/usr/bin/env python3
"""
Music Visualizer with Dynamic Colors and Higher Sensitivity
"""

import pyaudio
import numpy as np
import time
import sys
import argparse
from rpi_ws281x import PixelStrip, Color

# LED strip configuration
LED_COUNT = 10          # Number of LED pixels
LED_PIN = 12            # GPIO pin
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0

# Audio configuration
CHUNK = 2048
RATE = 44100
SMOOTHING = 0.3         # Lower = more reactive
GAIN = 20.0              # Increased sensitivity (was 3.0)

# Frequency bands for 10 LEDs
FREQ_BANDS = [
    (20, 60),       # Sub-bass
    (60, 120),      # Bass
    (120, 250),     # Low bass
    (250, 500),     # Low-mid
    (500, 1000),    # Mid
    (1000, 2000),   # High-mid
    (2000, 4000),   # Presence
    (4000, 8000),   # Brilliance
    (8000, 12000),  # High
    (12000, 16000), # Air
]

def wheel(pos):
    """Generate rainbow colors across 0-255 positions"""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

class MusicVisualizer:
    def __init__(self, device_index=1):
        self.strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, 
                               LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
        self.strip.begin()
        
        self.levels = [0.0] * LED_COUNT
        self.hue_offset = 0  # For rainbow rotation
        
        self.p = pyaudio.PyAudio()
        
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=2,
            rate=RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=CHUNK
        )
        
        print(f"Music Visualizer - Dynamic Color Mode")
        print(f"LED Count: {LED_COUNT}")
        print(f"GAIN: {GAIN}x (high sensitivity)")
        print(f"Press Ctrl+C to stop")
    
    def analyze_frequencies(self, audio_data):
        samples = np.frombuffer(audio_data, dtype=np.int16)
        
        if len(samples) > CHUNK:
            samples = samples[::2]
        
        windowed = samples * np.hanning(len(samples))
        fft = np.fft.rfft(windowed)
        fft_magnitude = np.abs(fft)
        freq_bins = np.fft.rfftfreq(len(windowed), 1.0/RATE)
        
        band_levels = []
        for low_freq, high_freq in FREQ_BANDS[:LED_COUNT]:
            mask = (freq_bins >= low_freq) & (freq_bins < high_freq)
            
            if np.any(mask):
                level = np.mean(fft_magnitude[mask])
            else:
                level = 0
            
            band_levels.append(level)
        
        max_level = np.max(band_levels) if np.max(band_levels) > 0 else 1
        normalized = [min(1.0, (level / max_level) * GAIN) for level in band_levels]
        
        return normalized
    
    def update_leds(self, levels):
        """Update LEDs with dynamic rainbow colors based on intensity"""
        for i in range(LED_COUNT):
            target = levels[i] if i < len(levels) else 0
            self.levels[i] = (self.levels[i] * SMOOTHING) + (target * (1 - SMOOTHING))
            
            # Dynamic color: hue changes with position + overall rotation
            hue = int((i * 25.5 + self.hue_offset) % 256)
            color = wheel(hue)
            
            # Scale brightness by audio level
            r = int(((color >> 16) & 0xFF) * self.levels[i])
            g = int(((color >> 8) & 0xFF) * self.levels[i])
            b = int((color & 0xFF) * self.levels[i])
            
            self.strip.setPixelColor(i, Color(r, g, b))
        
        # Slowly rotate rainbow
        self.hue_offset = (self.hue_offset + 1) % 256
        
        self.strip.show()
    
    def run(self):
        try:
            while True:
                audio_data = self.stream.read(CHUNK, exception_on_overflow=False)
                levels = self.analyze_frequencies(audio_data)
                self.update_leds(levels)
                
        except KeyboardInterrupt:
            print("\nStopping visualizer...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        for i in range(LED_COUNT):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()
        
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        
        print("Cleanup complete")

def main():
    parser = argparse.ArgumentParser(description='Music Visualizer - Dynamic Colors')
    parser.add_argument('--device', type=int, default=1, help='Audio device index')
    
    args = parser.parse_args()
    
    visualizer = MusicVisualizer(device_index=args.device)
    visualizer.run()

if __name__ == '__main__':
    main()
