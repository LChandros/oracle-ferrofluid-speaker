#!/usr/bin/env python3
"""
WS2812B LED Strip Control Script
Controls a 10-LED addressable LED strip on PHYSICAL PIN 32 (GPIO 12)
"""

from rpi_ws281x import PixelStrip, Color
import time

# LED strip configuration
LED_COUNT = 10          # Number of LED pixels
LED_PIN = 12            # GPIO pin (BCM) - Physical pin 32 = GPIO 12
LED_FREQ_HZ = 800000    # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10            # DMA channel to use for generating signal
LED_BRIGHTNESS = 255    # Set to 0 for darkest and 255 for brightest
LED_INVERT = False      # True to invert the signal
LED_CHANNEL = 0         # PWM channel

def setup_strip():
    """Initialize the LED strip"""
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()
    print(f"LED strip initialized: {LED_COUNT} LEDs on GPIO {LED_PIN} (Physical pin 32)")
    return strip

def turn_on_white(strip):
    """Turn on all LEDs to white"""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(255, 255, 255))
    strip.show()
    print("All LEDs turned ON (white)")

def turn_off(strip):
    """Turn off all LEDs"""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    print("All LEDs turned OFF")

if __name__ == "__main__":
    strip = None
    try:
        strip = setup_strip()
        turn_on_white(strip)
        
        print("LEDs are ON. Press Ctrl+C to turn off and exit.")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        if strip:
            turn_off(strip)
            print("Cleanup complete")
