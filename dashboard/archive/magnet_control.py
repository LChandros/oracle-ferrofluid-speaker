#!/usr/bin/env python3
"""
Interactive Electromagnet Control
Physical Pin 12 (GPIO 18) controls IRF520 MOSFET module
Press keys to turn electromagnet ON/OFF
"""

import RPi.GPIO as GPIO
import sys
import termios
import tty

# Physical pin 12 = GPIO 18 (BCM numbering)
MAGNET_PIN = 18

def getch():
    """Get single character from keyboard without Enter"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

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
    magnet_on = False
    
    print("=" * 50)
    print("  ELECTROMAGNET CONTROL - Physical Pin 12")
    print("=" * 50)
    print("\nControls:")
    print("  [1] or [ON]  - Turn electromagnet ON")
    print("  [0] or [OFF] - Turn electromagnet OFF")
    print("  [Q] - Quit\n")
    print("Electromagnet is currently: OFF")
    print("\nWaiting for command...\n")
    
    try:
        while True:
            char = getch().lower()
            
            if char == '1' or char == 'n':  # '1' or 'n' from 'on'
                GPIO.output(MAGNET_PIN, GPIO.HIGH)
                magnet_on = True
                print("\r🧲 ELECTROMAGNET: ON  ", end='', flush=True)
                
            elif char == '0' or char == 'f':  # '0' or 'f' from 'off'
                GPIO.output(MAGNET_PIN, GPIO.LOW)
                magnet_on = False
                print("\r⚪ ELECTROMAGNET: OFF ", end='', flush=True)
                
            elif char == 'q':
                print("\n\nShutting down...")
                break
                
    except KeyboardInterrupt:
        print("\n\nInterrupted by Ctrl+C")
    finally:
        cleanup_gpio()
        print("Electromagnet turned OFF")
        print("GPIO cleaned up. Goodbye!\n")

if __name__ == "__main__":
    main()
