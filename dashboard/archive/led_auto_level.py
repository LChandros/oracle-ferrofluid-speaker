#!/usr/bin/env python3
"""
Auto-Leveling Volume-Reactive LED Strip
Automatically adjusts so max volume always hits max brightness
"""

import pyaudio
import numpy as np
import time
import sys
from rpi_ws281x import PixelStrip, Color

# LED strip configuration
LED_COUNT = 10
LED_PIN = 12
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0

# Audio configuration
CHUNK = 1024
RATE = 44100
SMOOTHING = 0.2
GAIN = 10.0
MAX_DECAY = 0.95        # How fast the reference max volume decays (slower = smoother auto-level)

def wheel(pos):
    """Rainbow color wheel"""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

class AutoLevelVisualizer:
    def __init__(self, device_index=1):
        self.strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, 
                               LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
        self.strip.begin()
        
        self.current_brightness = 0.0
        self.hue_offset = 0
        
        # Auto-leveling: track recent max volume
        self.reference_max = 0.01  # Start small, will adapt
        
        self.p = pyaudio.PyAudio()
        
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=2,
            rate=RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=CHUNK
        )
        
        print(f"Auto-Leveling Volume Visualizer")
        print(f"LEDs always hit max brightness relative to current volume")
        print(f"Press Ctrl+C to stop")
    
    def get_volume(self, audio_data):
        """Calculate RMS volume"""
        samples = np.frombuffer(audio_data, dtype=np.int16)
        
        if len(samples) > CHUNK:
            samples = samples[::2]
        
        rms = np.sqrt(np.mean(samples.astype(np.float32)**2))
        
        # Raw level (not normalized yet)
        level = (rms / 32768.0) * GAIN
        
        return level
    
    def auto_level(self, volume):
        """Auto-level the volume so max always hits 1.0"""
        # Update reference max (slowly decay, quickly rise)
        if volume > self.reference_max:
            # New peak - jump up quickly
            self.reference_max = volume
        else:
            # Slowly decay the reference max
            self.reference_max *= MAX_DECAY
            
            # Don't let it get too small
            if self.reference_max < 0.01:
                self.reference_max = 0.01
        
        # Normalize to reference max
        normalized = min(1.0, volume / self.reference_max)
        
        return normalized
    
    def update_leds(self, volume):
        """Update all LEDs with same brightness based on auto-leveled volume"""
        # Auto-level the volume
        leveled_volume = self.auto_level(volume)
        
        # Smooth the brightness changes
        self.current_brightness = (self.current_brightness * SMOOTHING) + (leveled_volume * (1 - SMOOTHING))
        
        # Update all LEDs with rainbow colors at current brightness
        for i in range(LED_COUNT):
            hue = int((i * 25.5 + self.hue_offset) % 256)
            color = wheel(hue)
            
            r = int(((color >> 16) & 0xFF) * self.current_brightness)
            g = int(((color >> 8) & 0xFF) * self.current_brightness)
            b = int((color & 0xFF) * self.current_brightness)
            
            self.strip.setPixelColor(i, Color(r, g, b))
        
        self.hue_offset = (self.hue_offset + 2) % 256
        
        self.strip.show()
    
    def run(self):
        try:
            while True:
                audio_data = self.stream.read(CHUNK, exception_on_overflow=False)
                volume = self.get_volume(audio_data)
                self.update_leds(volume)
                
        except KeyboardInterrupt:
            print("\nStopping...")
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
    visualizer = AutoLevelVisualizer(device_index=1)
    visualizer.run()

if __name__ == '__main__':
    main()
