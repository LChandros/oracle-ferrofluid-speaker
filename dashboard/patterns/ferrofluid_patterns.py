#!/usr/bin/env python3
"""
Ferrofluid Pattern Controller
Physical Pin 16 (GPIO 23) drives electromagnet with various patterns
Designed for ferrofluid visualization and eventually audio-reactive display
"""

import RPi.GPIO as GPIO
import time
import random
import sys

# Physical pin 16 = GPIO 23 (BCM numbering)
MAGNET_PIN = 23  # Physical pin 16

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

# ============================================================
# PATTERN FUNCTIONS
# ============================================================

def pattern_pulse(duration=30):
    """Regular rhythmic pulses - Like a heartbeat"""
    print("🫀 PULSE Pattern - Steady rhythm")
    start = time.time()
    cycle = 0
    while time.time() - start < duration:
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        print(f"  [Cycle {cycle}] ON")
        time.sleep(0.3)
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        print(f"  [Cycle {cycle}] OFF")
        time.sleep(0.3)
        cycle += 1

def pattern_wave(duration=30):
    """Wave pattern - Varying intensity simulation"""
    print("🌊 WAVE Pattern - Gradual rise and fall")
    start = time.time()
    cycle = 0
    while time.time() - start < duration:
        # Rising intensity (faster pulses)
        for i in range(10):
            on_time = 0.05 + (i * 0.02)
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            time.sleep(on_time)
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(0.05)
        
        # Falling intensity (slower pulses)
        for i in range(10, 0, -1):
            on_time = 0.05 + (i * 0.02)
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            time.sleep(on_time)
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(0.05)
        
        cycle += 1
        print(f"  [Cycle {cycle}] Wave complete")

def pattern_spike(duration=30):
    """Sharp quick bursts - Random spikes"""
    print("⚡ SPIKE Pattern - Random sharp bursts")
    start = time.time()
    spike_count = 0
    while time.time() - start < duration:
        # Random pause
        time.sleep(random.uniform(0.2, 1.5))
        
        # Quick spike
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        print(f"  [Spike {spike_count}] ⚡ BURST!")
        time.sleep(random.uniform(0.05, 0.2))
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        spike_count += 1

def pattern_breathing(duration=30):
    """Slow breathing pattern - Inhale/exhale"""
    print("🫁 BREATHING Pattern - Slow inhale/exhale")
    start = time.time()
    cycle = 0
    while time.time() - start < duration:
        # Inhale (gradually ON)
        print(f"  [Cycle {cycle}] Inhale...")
        for i in range(20):
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            time.sleep(0.05 + (i * 0.01))
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(0.02)
        
        # Hold
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        time.sleep(0.5)
        
        # Exhale (gradually OFF)
        print(f"  [Cycle {cycle}] Exhale...")
        for i in range(20, 0, -1):
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            time.sleep(0.05 + (i * 0.01))
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(0.02)
        
        # Rest
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        time.sleep(0.5)
        cycle += 1

def pattern_loading(duration=30):
    """Loading animation - Repeating sequence"""
    print("⏳ LOADING Pattern - Repeating sequence")
    start = time.time()
    cycle = 0
    while time.time() - start < duration:
        # Three dot pattern
        for i in range(3):
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            print(f"  [Cycle {cycle}] {'.' * (i+1)}")
            time.sleep(0.2)
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(0.2)
        
        # Pause
        time.sleep(0.5)
        cycle += 1

def pattern_heartbeat(duration=30):
    """Heartbeat pattern - Lub-dub"""
    print("💓 HEARTBEAT Pattern - Lub-dub")
    start = time.time()
    beat_count = 0
    while time.time() - start < duration:
        # Lub
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        print(f"  [Beat {beat_count}] LUB", end='')
        time.sleep(0.15)
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        time.sleep(0.15)
        
        # Dub
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        print("-DUB")
        time.sleep(0.15)
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        time.sleep(0.8)  # Rest between beats
        beat_count += 1

def pattern_ripple(duration=30):
    """Ripple pattern - Fast repeating pulses"""
    print("💫 RIPPLE Pattern - Fast repeating pulses")
    start = time.time()
    cycle = 0
    while time.time() - start < duration:
        # Burst of quick pulses
        for i in range(5):
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            time.sleep(0.05)
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(0.05)
        
        print(f"  [Cycle {cycle}] Ripple")
        time.sleep(0.5)
        cycle += 1

def pattern_chaos(duration=30):
    """Complete chaos - Random everything"""
    print("🌀 CHAOS Pattern - Complete randomness")
    start = time.time()
    event_count = 0
    while time.time() - start < duration:
        on_time = random.uniform(0.01, 0.5)
        off_time = random.uniform(0.01, 0.5)
        
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        time.sleep(on_time)
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        time.sleep(off_time)
        
        if event_count % 10 == 0:
            print(f"  [Event {event_count}] Chaos continues...")
        event_count += 1

# ============================================================
# MAIN MENU
# ============================================================

def show_menu():
    print("\n" + "=" * 60)
    print("  FERROFLUID PATTERN CONTROLLER")
    print("  Physical Pin 16 (GPIO 23) - Electromagnet Driver")
    print("=" * 60)
    print("\nAvailable Patterns:")
    print("  1. 🫀 Pulse      - Steady rhythmic pulses")
    print("  2. 🌊 Wave       - Gradual rise and fall")
    print("  3. ⚡ Spike      - Random sharp bursts")
    print("  4. 🫁 Breathing  - Slow inhale/exhale")
    print("  5. ⏳ Loading    - Repeating dot sequence")
    print("  6. 💓 Heartbeat  - Lub-dub pattern")
    print("  7. 💫 Ripple     - Fast repeating pulses")
    print("  8. 🌀 Chaos      - Complete randomness")
    print("  9. 🔄 Cycle All  - Run all patterns")
    print("  Q. Quit")
    print("\nEach pattern runs for 30 seconds")
    print("Press Ctrl+C during pattern to return to menu\n")

def main():
    setup_gpio()
    
    patterns = {
        '1': ('Pulse', pattern_pulse),
        '2': ('Wave', pattern_wave),
        '3': ('Spike', pattern_spike),
        '4': ('Breathing', pattern_breathing),
        '5': ('Loading', pattern_loading),
        '6': ('Heartbeat', pattern_heartbeat),
        '7': ('Ripple', pattern_ripple),
        '8': ('Chaos', pattern_chaos),
    }
    
    try:
        while True:
            show_menu()
            choice = input("Select pattern: ").strip()
            
            if choice.lower() == 'q':
                print("\nExiting...")
                break
            
            if choice == '9':
                print("\n🔄 CYCLING THROUGH ALL PATTERNS (10 seconds each)\n")
                for num, (name, func) in patterns.items():
                    try:
                        print(f"\n--- {name} Pattern ---")
                        func(duration=10)
                        GPIO.output(MAGNET_PIN, GPIO.LOW)
                        time.sleep(1)
                    except KeyboardInterrupt:
                        print("\nSkipping to next pattern...")
                        GPIO.output(MAGNET_PIN, GPIO.LOW)
                        time.sleep(0.5)
                continue
            
            if choice in patterns:
                name, func = patterns[choice]
                print(f"\n--- Running {name} Pattern for 30 seconds ---\n")
                try:
                    func(duration=30)
                except KeyboardInterrupt:
                    print("\n\nPattern interrupted")
                finally:
                    GPIO.output(MAGNET_PIN, GPIO.LOW)
                    time.sleep(0.5)
            else:
                print("\n❌ Invalid choice! Please try again.")
                
    except KeyboardInterrupt:
        print("\n\nProgram interrupted")
    finally:
        cleanup_gpio()
        print("\n✅ Electromagnet OFF")
        print("✅ GPIO cleaned up")
        print("\nGoodbye! 🧲\n")

if __name__ == "__main__":
    main()
