#!/usr/bin/env python3
"""
Electromagnet Control Script
Controls a 5V/50N electromagnet connected to physical pin 12 (GPIO18)
Turns on the electromagnet at full power indefinitely
"""

import RPi.GPIO as GPIO
import time
import signal
import sys

# Physical pin 12 = GPIO 18 (BCM numbering)
MAGNET_PIN = 18

def cleanup(signum=None, frame=None):
    """Clean up GPIO on exit"""
    print("\nCleaning up GPIO...")
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    GPIO.cleanup()
    print("Electromagnet turned OFF")
    sys.exit(0)

def main():
    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(MAGNET_PIN, GPIO.OUT)
    
    # Turn on electromagnet at full power
    GPIO.output(MAGNET_PIN, GPIO.HIGH)
    print("Electromagnet ON at full power")
    print("Physical Pin: 12 | GPIO Pin: 18")
    print("Press Ctrl+C to stop...")
    
    # Keep running indefinitely
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()
