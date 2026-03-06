#!/usr/bin/env python3
"""
Rainbow LED Strip Controller
Physical Pin 32 (GPIO 12) - WS2812B/NeoPixel LED Strip
"""

import time
from rpi_ws281x import PixelStrip, Color
import argparse

# LED strip configuration
LED_COUNT = 30          # Number of LED pixels (adjust to your strip length)
LED_PIN = 12            # GPIO pin connected to the pixels (physical pin 32)
LED_FREQ_HZ = 800000    # LED signal frequency in hertz
LED_DMA = 10            # DMA channel to use for generating signal
LED_BRIGHTNESS = 255    # Set to 0 for darkest and 255 for brightest
LED_INVERT = False      # True to invert the signal
LED_CHANNEL = 0         # PWM channel (0 or 1)

def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def rainbow_cycle(strip, iterations=5, wait_ms=20):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    print("🌈 Rainbow Cycle - Full spectrum flowing")
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        time.sleep(wait_ms / 1000.0)

def rainbow_chase(strip, iterations=5, wait_ms=50):
    """Rainbow colors chasing down the strip."""
    print("🎯 Rainbow Chase - Colors racing")
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((i + j) & 255))
        strip.show()
        time.sleep(wait_ms / 1000.0)

def rainbow_pulse(strip, iterations=3):
    """Pulse through rainbow colors on all LEDs simultaneously."""
    print("💫 Rainbow Pulse - Synchronized color waves")
    for j in range(256 * iterations):
        color = wheel(j & 255)
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color)
        strip.show()
        time.sleep(0.01)

def rainbow_theater_chase(strip, iterations=5, wait_ms=50):
    """Rainbow theater chase pattern."""
    print("🎭 Rainbow Theater Chase - Marquee style")
    for j in range(256 * iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, wheel((i + j) % 255))
            strip.show()
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, 0)

def rainbow_sparkle(strip, duration=10):
    """Random rainbow sparkles."""
    print("✨ Rainbow Sparkle - Random bursts")
    import random
    start = time.time()
    while time.time() - start < duration:
        # Random pixel, random color
        pixel = random.randint(0, strip.numPixels() - 1)
        color = wheel(random.randint(0, 255))
        strip.setPixelColor(pixel, color)
        strip.show()
        time.sleep(0.05)
        # Fade out
        strip.setPixelColor(pixel, Color(0, 0, 0))

def color_wipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)

def main():
    # Create NeoPixel object
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    
    # Initialize the library
    strip.begin()
    
    print("\n" + "="*60)
    print("  RAINBOW LED STRIP CONTROLLER")
    print(f"  Physical Pin 32 (GPIO 12) - {LED_COUNT} LEDs")
    print("="*60 + "\n")
    
    try:
        while True:
            print("\nAvailable Patterns:")
            print("  1. 🌈 Rainbow Cycle     - Smooth flowing rainbow")
            print("  2. 🎯 Rainbow Chase     - Colors racing down strip")
            print("  3. 💫 Rainbow Pulse     - All LEDs pulse together")
            print("  4. 🎭 Theater Chase     - Marquee style rainbow")
            print("  5. ✨ Sparkle           - Random rainbow bursts")
            print("  6. 🔄 Cycle All         - Run all patterns")
            print("  7. ⚫ Turn Off          - Clear all LEDs")
            print("  Q. Quit")
            
            choice = input("\nSelect pattern: ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == 1:
                rainbow_cycle(strip)
            elif choice == 2:
                rainbow_chase(strip)
            elif choice == 3:
                rainbow_pulse(strip)
            elif choice == 4:
                rainbow_theater_chase(strip)
            elif choice == 5:
                rainbow_sparkle(strip)
            elif choice == 6:
                print("\n--- Running all patterns ---")
                rainbow_cycle(strip, iterations=2)
                rainbow_chase(strip, iterations=2)
                rainbow_pulse(strip, iterations=1)
                rainbow_theater_chase(strip, iterations=2)
                rainbow_sparkle(strip, duration=5)
            elif choice == 7:
                print("⚫ Turning off all LEDs...")
                color_wipe(strip, Color(0, 0, 0), 10)
            else:
                print("❌ Invalid choice")
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
    finally:
        # Turn off all LEDs
        color_wipe(strip, Color(0, 0, 0), 10)
        print("\n✅ All LEDs off")
        print("Goodbye! 🌈\n")

if __name__ == '__main__':
    main()
