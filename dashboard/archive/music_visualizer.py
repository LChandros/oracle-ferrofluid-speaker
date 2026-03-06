#!/usr/bin/env python3
"""
Music Visualizer for Moneo Voice Nexus - Ferrofluid Speaker
Syncs 10-LED addressable strip to music playback with frequency analysis
Supports WS2812B/NeoPixel strips on GPIO12 (Pin 32)
"""

import pyaudio
import numpy as np
import time
import sys
import argparse
from rpi_ws281x import PixelStrip, Color

# LED strip configuration
LED_COUNT = 10          # Number of LED pixels
LED_PIN = 12            # GPIO pin connected to the pixels (BCM numbering, Pin 32)
LED_FREQ_HZ = 800000    # LED signal frequency in hertz
LED_DMA = 10            # DMA channel to use for generating signal
LED_BRIGHTNESS = 255    # Set to 0 for darkest and 255 for brightest
LED_INVERT = False      # True to invert the signal
LED_CHANNEL = 0         # PWM channel (0 or 1)

# Audio configuration
CHUNK = 2048            # Audio buffer size (power of 2 for FFT)
RATE = 44100            # Sample rate
SMOOTHING = 0.7         # LED smoothing factor (0-1, higher = smoother)
GAIN = 3.0              # Overall sensitivity multiplier

# Frequency bands for visualization (Hz)
# Bass, Low-Mid, Mid, High-Mid, Treble
FREQ_BANDS = [
    (20, 100),      # Sub-bass
    (100, 250),     # Bass
    (250, 500),     # Low-mid
    (500, 1000),    # Mid
    (1000, 2000),   # High-mid
    (2000, 4000),   # Presence
    (4000, 8000),   # Brilliance
    (8000, 16000),  # Air
]

# Color schemes
COLOR_SCHEMES = {
    'rainbow': [
        Color(255, 0, 0),      # Red
        Color(255, 127, 0),    # Orange
        Color(255, 255, 0),    # Yellow
        Color(0, 255, 0),      # Green
        Color(0, 255, 127),    # Cyan
        Color(0, 127, 255),    # Sky blue
        Color(0, 0, 255),      # Blue
        Color(127, 0, 255),    # Purple
        Color(255, 0, 255),    # Magenta
        Color(255, 0, 127),    # Pink
    ],
    'fire': [
        Color(255, 0, 0),      # Red
        Color(255, 50, 0),
        Color(255, 100, 0),    # Orange
        Color(255, 150, 0),
        Color(255, 200, 0),
        Color(255, 255, 0),    # Yellow
        Color(255, 255, 100),
        Color(255, 255, 150),
        Color(255, 255, 200),
        Color(255, 255, 255),  # White
    ],
    'ocean': [
        Color(0, 0, 100),
        Color(0, 0, 150),
        Color(0, 50, 200),
        Color(0, 100, 255),
        Color(0, 150, 255),
        Color(0, 200, 255),
        Color(50, 255, 255),
        Color(100, 255, 255),
        Color(150, 255, 255),
        Color(200, 255, 255),
    ],
    'moneo': [
        Color(75, 0, 130),     # Indigo
        Color(100, 0, 200),
        Color(138, 43, 226),   # Blue violet
        Color(147, 112, 219),  # Medium purple
        Color(153, 50, 204),   # Dark orchid
        Color(186, 85, 211),   # Medium orchid
        Color(148, 0, 211),    # Dark violet
        Color(138, 43, 226),   # Blue violet
        Color(123, 104, 238),  # Medium slate blue
        Color(106, 90, 205),   # Slate blue
    ]
}

class MusicVisualizer:
    def __init__(self, color_scheme='moneo', device_index=None):
        """Initialize LED strip and audio capture"""
        
        # Initialize LED strip
        self.strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, 
                               LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
        self.strip.begin()
        
        # Color scheme
        self.colors = COLOR_SCHEMES.get(color_scheme, COLOR_SCHEMES['moneo'])
        
        # Smoothing buffers
        self.levels = [0.0] * LED_COUNT
        
        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        
        # Find audio device
        if device_index is None:
            device_index = self._find_audio_device()
        
        # Open audio stream
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=2,
            rate=RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=CHUNK
        )
        
        print(f"Music Visualizer initialized")
        print(f"   LED Count: {LED_COUNT}")
        print(f"   Audio Rate: {RATE} Hz")
        print(f"   Color Scheme: {color_scheme}")
        print(f"   Press Ctrl+C to stop")
    
    def _find_audio_device(self):
        """Find ReSpeaker or default audio device"""
        # Try to find ReSpeaker first
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if 'wm8960' in info['name'].lower() and info['maxInputChannels'] > 0:
                print(f"Found ReSpeaker: {info['name']}")
                return i
        
        # Fall back to default input
        default_info = self.p.get_default_input_device_info()
        print(f"Using default device: {default_info['name']}")
        return default_info['index']
    
    def analyze_frequencies(self, audio_data):
        """Perform FFT and extract frequency band levels"""
        # Convert to numpy array
        samples = np.frombuffer(audio_data, dtype=np.int16)
        
        # Use only left channel if stereo
        if len(samples) > CHUNK:
            samples = samples[::2]
        
        # Apply Hanning window to reduce spectral leakage
        windowed = samples * np.hanning(len(samples))
        
        # Perform FFT
        fft = np.fft.rfft(windowed)
        fft_magnitude = np.abs(fft)
        
        # Frequency bins
        freq_bins = np.fft.rfftfreq(len(windowed), 1.0/RATE)
        
        # Extract levels for each frequency band
        band_levels = []
        for low_freq, high_freq in FREQ_BANDS[:LED_COUNT]:
            # Find bins in this frequency range
            mask = (freq_bins >= low_freq) & (freq_bins < high_freq)
            
            # Calculate average magnitude in this band
            if np.any(mask):
                level = np.mean(fft_magnitude[mask])
            else:
                level = 0
            
            band_levels.append(level)
        
        # Normalize levels to 0-1 range
        max_level = np.max(band_levels) if np.max(band_levels) > 0 else 1
        normalized = [min(1.0, (level / max_level) * GAIN) for level in band_levels]
        
        return normalized
    
    def update_leds(self, levels):
        """Update LED strip based on frequency levels"""
        for i in range(LED_COUNT):
            # Apply smoothing
            target = levels[i] if i < len(levels) else 0
            self.levels[i] = (self.levels[i] * SMOOTHING) + (target * (1 - SMOOTHING))
            
            # Scale color brightness
            color = self.colors[i]
            r = int(((color >> 16) & 0xFF) * self.levels[i])
            g = int(((color >> 8) & 0xFF) * self.levels[i])
            b = int((color & 0xFF) * self.levels[i])
            
            self.strip.setPixelColor(i, Color(r, g, b))
        
        self.strip.show()
    
    def run(self):
        """Main visualization loop"""
        try:
            while True:
                # Read audio data
                audio_data = self.stream.read(CHUNK, exception_on_overflow=False)
                
                # Analyze frequencies
                levels = self.analyze_frequencies(audio_data)
                
                # Update LEDs
                self.update_leds(levels)
                
        except KeyboardInterrupt:
            print("\nStopping visualizer...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        # Turn off all LEDs
        for i in range(LED_COUNT):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()
        
        # Close audio
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        
        print("Cleanup complete")

def main():
    parser = argparse.ArgumentParser(description='Music Visualizer for Moneo Voice Nexus')
    parser.add_argument('--scheme', choices=list(COLOR_SCHEMES.keys()), 
                       default='moneo', help='Color scheme')
    parser.add_argument('--device', type=int, help='Audio device index')
    
    args = parser.parse_args()
    
    visualizer = MusicVisualizer(color_scheme=args.scheme, device_index=args.device)
    visualizer.run()

if __name__ == '__main__':
    main()
