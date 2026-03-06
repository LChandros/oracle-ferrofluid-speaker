#!/usr/bin/env python3
"""
Simple LED test script
Tests WS281x LED strip on GPIO12 (Physical Pin 32)

Usage: sudo python3 test_leds.py
"""

from rpi_ws281x import PixelStrip, Color
import time

# LED Strip Configuration
LED_PIN = 12        # GPIO12 (Physical Pin 32)
LED_COUNT = 10      # Number of LEDs
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0

def test_basic():
    """Test 1: Basic red/green/blue cycle"""
    print("Test 1: Basic RGB cycle (all LEDs)")

    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                      LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    try:
        # Red
        print("  Red...")
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(0, 255, 0))  # GRB format
        strip.show()
        time.sleep(2)

        # Green
        print("  Green...")
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(255, 0, 0))
        strip.show()
        time.sleep(2)

        # Blue
        print("  Blue...")
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(0, 0, 255))
        strip.show()
        time.sleep(2)

        # White
        print("  White...")
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(255, 255, 255))
        strip.show()
        time.sleep(2)

        # Off
        print("  Off...")
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()

    except KeyboardInterrupt:
        pass

def test_individual():
    """Test 2: Light up each LED individually"""
    print("\nTest 2: Individual LED test")

    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                      LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    try:
        for i in range(LED_COUNT):
            print(f"  LED {i}...")
            # Clear all
            for j in range(LED_COUNT):
                strip.setPixelColor(j, Color(0, 0, 0))
            # Light up this LED (cyan)
            strip.setPixelColor(i, Color(255, 100, 255))
            strip.show()
            time.sleep(0.5)

        # Clear all
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()

    except KeyboardInterrupt:
        pass

def test_wave():
    """Test 3: Wave animation"""
    print("\nTest 3: Wave animation (5 seconds)")

    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                      LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    try:
        start_time = time.time()
        wave_position = 0

        while time.time() - start_time < 5:
            for i in range(LED_COUNT):
                # Calculate wave intensity
                offset = abs(i - wave_position)
                intensity = max(0, 1.0 - (offset / (LED_COUNT / 2)))

                # Purple to cyan wave
                r = int(100 * intensity)
                g = int(150 * intensity)
                b = int(255 * intensity)

                strip.setPixelColor(i, Color(g, r, b))

            strip.show()
            wave_position = (wave_position + 0.2) % LED_COUNT
            time.sleep(0.05)

        # Clear all
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()

    except KeyboardInterrupt:
        pass

def test_rainbow():
    """Test 4: Rainbow cycle"""
    print("\nTest 4: Rainbow cycle (5 seconds)")

    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                      LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    def wheel(pos):
        """Generate rainbow colors across 0-255 positions."""
        if pos < 85:
            return Color(255 - pos * 3, pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return Color(0, 255 - pos * 3, pos * 3)
        else:
            pos -= 170
            return Color(pos * 3, 0, 255 - pos * 3)

    try:
        start_time = time.time()
        j = 0

        while time.time() - start_time < 5:
            for i in range(LED_COUNT):
                strip.setPixelColor(i, wheel((int(i * 256 / LED_COUNT) + j) & 255))
            strip.show()
            j = (j + 1) % 256
            time.sleep(0.02)

        # Clear all
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()

    except KeyboardInterrupt:
        pass

def main():
    print("=" * 50)
    print("LED Strip Test Script")
    print("=" * 50)
    print(f"Pin: GPIO{LED_PIN} (Physical Pin 32)")
    print(f"LED Count: {LED_COUNT}")
    print(f"Brightness: {LED_BRIGHTNESS}")
    print("=" * 50)

    try:
        test_basic()
        test_individual()
        test_wave()
        test_rainbow()

        print("\n" + "=" * 50)
        print("All tests complete!")
        print("=" * 50)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
