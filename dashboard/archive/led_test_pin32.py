#!/usr/bin/env python3
"""
LED Strip Test - Physical Pin 32 (GPIO 12)
Testing if soldering job works
"""

from rpi_ws281x import PixelStrip, Color
import time

# LED Strip Configuration
LED_COUNT = 10          # Number of LEDs
LED_PIN = 12            # Physical pin 32 = GPIO 12 (BCM)
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0

def main():
    print('🔧 Initializing LED strip on Pin 32 (GPIO 12)...')
    
    # Create LED strip object
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, 
                      LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()
    
    try:
        print('✅ LED strip initialized!')
        print('🌈 Running color test...\n')
        
        # Test 1: All Red
        print('🔴 RED...')
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(255, 0, 0))
        strip.show()
        time.sleep(2)
        
        # Test 2: All Green
        print('🟢 GREEN...')
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(0, 255, 0))
        strip.show()
        time.sleep(2)
        
        # Test 3: All Blue
        print('🔵 BLUE...')
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(0, 0, 255))
        strip.show()
        time.sleep(2)
        
        # Test 4: All White
        print('⚪ WHITE...')
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(255, 255, 255))
        strip.show()
        time.sleep(2)
        
        # Test 5: Rainbow cycle
        print('🌈 RAINBOW...')
        colors = [
            Color(255, 0, 0),    # Red
            Color(255, 127, 0),  # Orange
            Color(255, 255, 0),  # Yellow
            Color(0, 255, 0),    # Green
            Color(0, 0, 255),    # Blue
            Color(75, 0, 130),   # Indigo
            Color(148, 0, 211),  # Violet
        ]
        
        for color in colors:
            for i in range(LED_COUNT):
                strip.setPixelColor(i, color)
            strip.show()
            time.sleep(0.5)
        
        print('\n✅ Test complete!')
        
    except KeyboardInterrupt:
        print('\n⚠️  Interrupted!')
    
    finally:
        # Turn off all LEDs
        print('🔌 Turning off LEDs...')
        for i in range(LED_COUNT):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()
        print('✅ Done!\n')

if __name__ == '__main__':
    main()
