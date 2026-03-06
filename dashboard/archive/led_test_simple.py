#!/usr/bin/env python3
"""Simple LED test - cycles through colors"""

import time
from rpi_ws281x import PixelStrip, Color

# LED Configuration
LED_PIN = 12          # GPIO12 = Physical pin 32
LED_COUNT = 24        # Number of LEDs
LED_BRIGHTNESS = 128  # Medium brightness

# Initialize
strip = PixelStrip(LED_COUNT, LED_PIN, brightness=LED_BRIGHTNESS)
strip.begin()

print(f'Testing {LED_COUNT} LEDs on GPIO{LED_PIN} (Pin 32)')
print('If LEDs work, you should see:')
print('1. All RED')
print('2. All GREEN')
print('3. All BLUE')
print('4. Rainbow')
print('Press Ctrl+C to exit')
print()

try:
    # Test 1: All RED
    print('RED...')
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(255, 0, 0))
    strip.show()
    time.sleep(2)
    
    # Test 2: All GREEN
    print('GREEN...')
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 255, 0))
    strip.show()
    time.sleep(2)
    
    # Test 3: All BLUE
    print('BLUE...')
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 255))
    strip.show()
    time.sleep(2)
    
    # Test 4: Rainbow
    print('RAINBOW...')
    colors = [
        Color(255, 0, 0),    # Red
        Color(255, 127, 0),  # Orange
        Color(255, 255, 0),  # Yellow
        Color(0, 255, 0),    # Green
        Color(0, 0, 255),    # Blue
        Color(75, 0, 130),   # Indigo
        Color(148, 0, 211)   # Violet
    ]
    
    for i in range(LED_COUNT):
        color_idx = (i * len(colors)) // LED_COUNT
        strip.setPixelColor(i, colors[color_idx])
    strip.show()
    time.sleep(3)
    
    print('Test complete! LEDs are working.')
    
except KeyboardInterrupt:
    print('\nStopped.')
finally:
    # Turn off all LEDs
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    print('LEDs off')

