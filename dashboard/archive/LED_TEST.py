#!/usr/bin/env python3
"""
LED Strip Test Script
Physical Pin 12 (GPIO 18) controls WS2812B LED strip
"""

from rpi_ws281x import PixelStrip, Color

# Configuration
LED_COUNT = 10          # 10 LEDs
LED_PIN = 18            # GPIO 18 = Physical pin 12
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0

print("Initializing LED strip on Physical Pin 12 (GPIO 18)...")

# Initialize strip
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

# Turn all LEDs WHITE
print("Turning on all 10 LEDs to WHITE...")
for i in range(LED_COUNT):
    strip.setPixelColor(i, Color(255, 255, 255))
strip.show()

print("✅ LEDs are ON (white)")
print("Press Enter to turn off and exit...")
input()

# Turn off
for i in range(LED_COUNT):
    strip.setPixelColor(i, Color(0, 0, 0))
strip.show()
print("✅ LEDs are OFF")
