#!/usr/bin/env python3
"""
Electromagnet Test - Physical Pin 12 (GPIO 18)
Testing MOSFET control for electromagnet
"""

import RPi.GPIO as GPIO
import time

# Electromagnet Configuration
MAGNET_PIN = 18  # Physical pin 12 = GPIO 18 (BCM)

def setup():
    """Initialize GPIO for electromagnet"""
    print('🔧 Initializing electromagnet on Pin 12 (GPIO 18)...')
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(MAGNET_PIN, GPIO.OUT)
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    print('✅ Electromagnet GPIO initialized!')

def cleanup():
    """Clean up GPIO"""
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    GPIO.cleanup()
    print('✅ GPIO cleaned up')

def main():
    setup()
    
    try:
        print('\n🧲 Running electromagnet test...\n')
        
        # Test 1: Simple ON/OFF pulses
        print('Test 1: Simple pulses (5 cycles)')
        for i in range(5):
            print(f'  Cycle {i+1}/5: ON')
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            time.sleep(1)
            
            print(f'  Cycle {i+1}/5: OFF')
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(1)
        
        print('\n✅ Simple pulse test complete!\n')
        time.sleep(1)
        
        # Test 2: Fast pulses
        print('Test 2: Fast pulses (10 quick bursts)')
        for i in range(10):
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            time.sleep(0.2)
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(0.2)
        
        print('\n✅ Fast pulse test complete!\n')
        time.sleep(1)
        
        # Test 3: Variable timing
        print('Test 3: Variable timing (wave pattern)')
        for i in range(10):
            on_time = 0.1 + (i * 0.05)
            print(f'  Pulse {i+1}/10: {on_time:.2f}s ON')
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            time.sleep(on_time)
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(0.1)
        
        print('\n✅ Variable timing test complete!\n')
        time.sleep(1)
        
        # Test 4: Sustained hold
        print('Test 4: Sustained hold (5 seconds)')
        print('  Electromagnet ON...')
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        time.sleep(5)
        print('  Electromagnet OFF...')
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        
        print('\n✅ All tests complete!')
        print('🧲 Electromagnet should have cycled through different patterns')
        
    except KeyboardInterrupt:
        print('\n⚠️  Interrupted!')
    
    finally:
        cleanup()
        print('\n✅ Done!\n')

if __name__ == '__main__':
    main()
