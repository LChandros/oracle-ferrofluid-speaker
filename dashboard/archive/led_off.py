#!/usr/bin/env python3
from rpi_ws281x import PixelStrip, Color

# Physical pin 12 = GPIO 18
strip = PixelStrip(10, 18, 800000, 10, False, 255, 0)
strip.begin()

# Turn all LEDs off
for i in range(10):
    strip.setPixelColor(i, Color(0, 0, 0))
strip.show()

print("LEDs OFF")
