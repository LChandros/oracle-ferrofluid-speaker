#!/usr/bin/env python3
"""
LED Strip Control Script
Controls an LED strip connected to GPIO pin 12 (Physical pin 32)
"""

import RPi.GPIO as GPIO
import time

# Configuration
LED_PIN = 12  # Physical pin 32 (GPIO 12 BCM)

def setup():
    """Initialize GPIO"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    print(f"GPIO pin {LED_PIN} configured as output")

def turn_on():
    """Turn on the LED strip"""
    GPIO.output(LED_PIN, GPIO.HIGH)
    print("LED strip turned ON")

def turn_off():
    """Turn off the LED strip"""
    GPIO.output(LED_PIN, GPIO.LOW)
    print("LED strip turned OFF")

def cleanup():
    """Clean up GPIO"""
    GPIO.cleanup()
    print("GPIO cleanup complete")

if __name__ == "__main__":
    try:
        setup()
        turn_on()
        
        # Keep the LEDs on
        print("LEDs are ON. Press Ctrl+C to turn off and exit.")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        turn_off()
        cleanup()
