#!/usr/bin/env python3
"""
Electromagnet Pulse Controller
Pulses an electromagnet connected to GPIO 16 via MOSFET
On/Off cycle: 1 second each
"""

import RPi.GPIO as GPIO
import time
import signal
import sys

# Configuration
MAGNET_PIN = 16  # GPIO pin number (BCM numbering)
PULSE_INTERVAL = 1.0  # seconds

def cleanup(signum, frame):
    """Clean shutdown on Ctrl+C"""
    print("\n\nShutting down...")
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    GPIO.cleanup()
    sys.exit(0)

def main():
    # Set up GPIO
    GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
    GPIO.setup(MAGNET_PIN, GPIO.OUT)
    GPIO.output(MAGNET_PIN, GPIO.LOW)  # Start with magnet OFF

    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print(f"Electromagnet Pulse Controller")
    print(f"GPIO Pin: {MAGNET_PIN}")
    print(f"Pulse Interval: {PULSE_INTERVAL}s ON / {PULSE_INTERVAL}s OFF")
    print("Press Ctrl+C to stop\n")

    try:
        cycle = 0
        while True:
            cycle += 1

            # Turn magnet ON
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            print(f"[{cycle}] Magnet ON")
            time.sleep(PULSE_INTERVAL)

            # Turn magnet OFF
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            print(f"[{cycle}] Magnet OFF")
            time.sleep(PULSE_INTERVAL)

    except Exception as e:
        print(f"Error: {e}")
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        GPIO.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()
