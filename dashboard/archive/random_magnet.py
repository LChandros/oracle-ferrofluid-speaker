#!/usr/bin/env python3
"""
Random Electromagnet Fluctuation
Physical Pin 12 (GPIO 18) randomly turns electromagnet ON/OFF
"""

import RPi.GPIO as GPIO
import time
import random

# Physical pin 12 = GPIO 18 (BCM numbering)
MAGNET_PIN = 18

def setup_gpio():
    """Initialize GPIO"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(MAGNET_PIN, GPIO.OUT)
    GPIO.output(MAGNET_PIN, GPIO.LOW)

def cleanup_gpio():
    """Clean up GPIO on exit"""
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    GPIO.cleanup()

def main():
    setup_gpio()
    
    print("=" * 60)
    print("  RANDOM ELECTROMAGNET FLUCTUATION - Physical Pin 12")
    print("=" * 60)
    print("\nElectromagnet will randomly turn ON/OFF")
    print("ON duration: 0.5 - 3 seconds (random)")
    print("OFF duration: 0.5 - 3 seconds (random)")
    print("\nPress Ctrl+C to stop\n")
    
    cycle = 0
    
    try:
        while True:
            # Random ON duration (0.5 to 3 seconds)
            on_time = random.uniform(0.5, 3.0)
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            print(f"[Cycle {cycle}] 🧲 MAGNET ON  - Duration: {on_time:.2f}s")
            time.sleep(on_time)
            
            # Random OFF duration (0.5 to 3 seconds)
            off_time = random.uniform(0.5, 3.0)
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            print(f"[Cycle {cycle}] ⚪ MAGNET OFF - Duration: {off_time:.2f}s")
            time.sleep(off_time)
            
            cycle += 1
            
    except KeyboardInterrupt:
        print("\n\nStopping random fluctuation...")
    finally:
        cleanup_gpio()
        print("Electromagnet turned OFF")
        print(f"Total cycles completed: {cycle}")
        print("GPIO cleaned up. Goodbye!\n")

if __name__ == "__main__":
    main()
