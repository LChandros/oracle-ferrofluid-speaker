#!/usr/bin/env python3
from rpi_ws281x import PixelStrip, Color

# Physical pin 12 = GPIO 18
strip = PixelStrip(10, 18, 800000, 10, False, 255, 0)
strip.begin()

# Turn all LEDs white
for i in range(10):
    strip.setPixelColor(i, Color(255, 255, 255))
strip.show()

print("LEDs ON - Press Ctrl+C to exit")
input()
