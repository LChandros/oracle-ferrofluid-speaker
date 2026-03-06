#!/usr/bin/env python3
"""
Ferrofluid Pattern Controller
Physical Pin 12 (GPIO 18) - Electromagnet Driver
"""

import RPi.GPIO as GPIO
import time
import random
import sys

# Pin Configuration
MAGNET_PIN = 18  # Physical pin 12 = GPIO 18

def setup():
    """Initialize GPIO"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(MAGNET_PIN, GPIO.OUT)
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    print("✅ GPIO initialized - Electromagnet OFF")

def cleanup():
    """Clean up GPIO"""
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    GPIO.cleanup()
    print("\n✅ Electromagnet OFF")
    print("✅ GPIO cleaned up")

def pulse_pattern(duration=30):
    """Steady rhythmic pulses"""
    print("\n🫀 PULSE Pattern - Steady rhythm")
    start = time.time()
    cycle = 0
    while time.time() - start < duration:
        print(f"  [Cycle {cycle}] ON")
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        time.sleep(0.3)
        print(f"  [Cycle {cycle}] OFF")
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        time.sleep(0.3)
        cycle += 1

def wave_pattern(duration=30):
    """Gradual rise and fall using PWM"""
    print("\n🌊 WAVE Pattern - Gradual rise and fall")
    pwm = GPIO.PWM(MAGNET_PIN, 100)  # 100Hz
    pwm.start(0)
    start = time.time()
    cycle = 0
    try:
        while time.time() - start < duration:
            # Rise
            for duty in range(0, 101, 5):
                if time.time() - start >= duration:
                    break
                pwm.ChangeDutyCycle(duty)
                time.sleep(0.05)
            # Fall
            for duty in range(100, -1, -5):
                if time.time() - start >= duration:
                    break
                pwm.ChangeDutyCycle(duty)
                time.sleep(0.05)
            cycle += 1
            print(f"  [Cycle {cycle}] Complete")
    finally:
        pwm.stop()
        GPIO.output(MAGNET_PIN, GPIO.LOW)

def spike_pattern(duration=30):
    """Random sharp bursts"""
    print("\n⚡ SPIKE Pattern - Random bursts")
    start = time.time()
    spike = 0
    while time.time() - start < duration:
        wait = random.uniform(0.1, 2.0)
        time.sleep(wait)
        if time.time() - start >= duration:
            break
        pulse_len = random.uniform(0.05, 0.3)
        print(f"  [Spike {spike}] BURST! ({pulse_len:.2f}s)")
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        time.sleep(pulse_len)
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        spike += 1

def breathing_pattern(duration=30):
    """Slow inhale/exhale"""
    print("\n🫁 BREATHING Pattern - Slow inhale/exhale")
    pwm = GPIO.PWM(MAGNET_PIN, 100)
    pwm.start(0)
    start = time.time()
    cycle = 0
    try:
        while time.time() - start < duration:
            print(f"  [Breath {cycle}] Inhale...")
            # Inhale (slow rise)
            for duty in range(0, 101, 2):
                if time.time() - start >= duration:
                    break
                pwm.ChangeDutyCycle(duty)
                time.sleep(0.04)
            time.sleep(0.5)
            print(f"  [Breath {cycle}] Exhale...")
            # Exhale (slow fall)
            for duty in range(100, -1, -2):
                if time.time() - start >= duration:
                    break
                pwm.ChangeDutyCycle(duty)
                time.sleep(0.04)
            time.sleep(0.5)
            cycle += 1
    finally:
        pwm.stop()
        GPIO.output(MAGNET_PIN, GPIO.LOW)

def loading_pattern(duration=30):
    """Loading animation style"""
    print("\n⏳ LOADING Pattern - Dot sequence")
    start = time.time()
    cycle = 0
    while time.time() - start < duration:
        for i in range(3):
            if time.time() - start >= duration:
                break
            print(f"  [Loading {cycle}] {'.' * (i+1)}")
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            time.sleep(0.15)
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(0.15)
        time.sleep(0.5)
        cycle += 1

def heartbeat_pattern(duration=30):
    """Lub-dub heart rhythm"""
    print("\n💓 HEARTBEAT Pattern - Lub-dub")
    start = time.time()
    beat = 0
    while time.time() - start < duration:
        print(f"  [Beat {beat}] Lub")
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        time.sleep(0.15)
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        time.sleep(0.15)
        print(f"  [Beat {beat}] Dub")
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        time.sleep(0.15)
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        time.sleep(0.8)
        beat += 1

def ripple_pattern(duration=30):
    """Fast repeating pulses"""
    print("\n💫 RIPPLE Pattern - Fast repeating")
    start = time.time()
    ripple = 0
    while time.time() - start < duration:
        print(f"  [Ripple {ripple}]", end=" ")
        for i in range(5):
            if time.time() - start >= duration:
                break
            print("•", end="", flush=True)
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            time.sleep(0.08)
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(0.08)
        print()
        time.sleep(0.5)
        ripple += 1

def chaos_pattern(duration=30):
    """Complete randomness"""
    print("\n🌀 CHAOS Pattern - Complete randomness")
    start = time.time()
    event = 0
    while time.time() - start < duration:
        on_time = random.uniform(0.01, 0.5)
        off_time = random.uniform(0.01, 0.8)
        print(f"  [Event {event}] ON:{on_time:.2f}s OFF:{off_time:.2f}s")
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        time.sleep(on_time)
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        time.sleep(off_time)
        event += 1

def main():
    setup()
    
    patterns = {
        "1": ("🫀 Pulse", pulse_pattern),
        "2": ("🌊 Wave", wave_pattern),
        "3": ("⚡ Spike", spike_pattern),
        "4": ("🫁 Breathing", breathing_pattern),
        "5": ("⏳ Loading", loading_pattern),
        "6": ("💓 Heartbeat", heartbeat_pattern),
        "7": ("💫 Ripple", ripple_pattern),
        "8": ("🌀 Chaos", chaos_pattern),
    }
    
    print("\n" + "="*60)
    print("  FERROFLUID PATTERN CONTROLLER")
    print("  Physical Pin 12 (GPIO 18) - Electromagnet Driver")
    print("="*60)
    
    try:
        while True:
            print("\nAvailable Patterns:")
            for key, (name, _) in patterns.items():
                print(f"  {key}. {name:<12} - {_.__doc__}")
            print(f"  9. 🔄 Cycle All  - Run all patterns")
            print(f"  Q. Quit")
            print("\nEach pattern runs for 30 seconds")
            print("Press Ctrl+C during pattern to return to menu")
            
            choice = input("\nSelect pattern: ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == '9':
                for key, (name, func) in patterns.items():
                    print(f"\n--- Running {name} Pattern for 30 seconds ---")
                    try:
                        func(30)
                    except KeyboardInterrupt:
                        print("\n⏭️  Skipping to next pattern...")
                        GPIO.output(MAGNET_PIN, GPIO.LOW)
                        time.sleep(1)
            elif choice in patterns:
                name, func = patterns[choice]
                print(f"\n--- Running {name} Pattern for 30 seconds ---")
                try:
                    func(30)
                except KeyboardInterrupt:
                    print("\n⏹️  Pattern interrupted")
                    GPIO.output(MAGNET_PIN, GPIO.LOW)
            else:
                print("❌ Invalid choice. Try again.")
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
    finally:
        cleanup()
        print("\nGoodbye! 🧲\n")

if __name__ == "__main__":
    main()
