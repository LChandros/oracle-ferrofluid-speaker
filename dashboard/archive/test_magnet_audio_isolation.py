#!/usr/bin/env python3
"""
Test electromagnet operation while playing audio
Goal: Verify no audio interference or noise injection
"""

import RPi.GPIO as GPIO
import subprocess
import time
import sys

MAGNET_PIN = 21  # GPIO 21 (Pin 40)
TEST_AUDIO = "/home/tyahn/voice-test.wav"

def setup():
    """Initialize GPIO"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(MAGNET_PIN, GPIO.OUT)
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    print("GPIO initialized - Electromagnet on GPIO 21")

def cleanup():
    """Clean up"""
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    GPIO.cleanup()
    print("Cleanup complete")

def test_baseline():
    """Test 1: Audio only (no electromagnet)"""
    print("\n=== TEST 1: Baseline Audio (No Electromagnet) ===")
    print("Playing audio WITHOUT electromagnet...")
    print("Listen for any existing noise or issues")
    input("Press Enter to start...")
    
    subprocess.run(["aplay", "-D", "plughw:3,0", TEST_AUDIO])
    
    response = input("Did audio play cleanly? (y/n): ")
    return response.lower() == 'y'

def test_magnet_static():
    """Test 2: Audio + Static electromagnet ON"""
    print("\n=== TEST 2: Audio + Static Electromagnet ON ===")
    print("Electromagnet will be turned ON (constant DC)")
    print("Playing audio while magnet is ON...")
    print("Listen for hum, buzz, or distortion")
    input("Press Enter to start...")
    
    # Turn magnet ON
    GPIO.output(MAGNET_PIN, GPIO.HIGH)
    print("Electromagnet ON")
    time.sleep(1)
    
    # Play audio
    subprocess.run(["aplay", "-D", "plughw:3,0", TEST_AUDIO])
    
    # Turn magnet OFF
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    print("Electromagnet OFF")
    
    response = input("Did you hear any interference/noise? (y/n): ")
    return response.lower() == 'n'  # No interference = good

def test_magnet_pwm_slow():
    """Test 3: Audio + Slow PWM (1Hz)"""
    print("\n=== TEST 3: Audio + Slow PWM (1Hz on/off) ===")
    print("Electromagnet will pulse slowly (1 second on, 1 second off)")
    print("Playing audio with slow magnet pulsing...")
    print("Listen for clicks, pops, or rhythmic interference")
    input("Press Enter to start...")
    
    # Start audio in background
    audio_process = subprocess.Popen(["aplay", "-D", "plughw:3,0", TEST_AUDIO])
    
    # Pulse magnet slowly during audio
    start = time.time()
    while audio_process.poll() is None and (time.time() - start) < 10:
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        time.sleep(1)
    
    # Wait for audio to finish
    audio_process.wait()
    
    response = input("Did you hear clicks/pops when magnet switched? (y/n): ")
    return response.lower() == 'n'

def test_magnet_pwm_fast():
    """Test 4: Audio + Fast PWM (simulated audio-reactive)"""
    print("\n=== TEST 4: Audio + Fast PWM (100ms pulses) ===")
    print("Electromagnet will pulse rapidly (simulating audio reaction)")
    print("This simulates the final audio-reactive behavior")
    print("Listen for high-frequency noise or distortion")
    input("Press Enter to start...")
    
    # Start audio in background
    audio_process = subprocess.Popen(["aplay", "-D", "plughw:3,0", TEST_AUDIO])
    
    # Fast pulse magnet
    start = time.time()
    while audio_process.poll() is None and (time.time() - start) < 10:
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        time.sleep(0.1)
    
    # Wait for audio to finish
    audio_process.wait()
    
    response = input("Did you hear high-frequency noise or distortion? (y/n): ")
    return response.lower() == 'n'

def main():
    print("="*60)
    print("ELECTROMAGNET + AUDIO ISOLATION TEST")
    print("="*60)
    print()
    print("This test will check if the electromagnet interferes")
    print("with audio playback on the ReSpeaker speaker.")
    print()
    print("Hardware setup:")
    print("  - Electromagnet on GPIO 21 (Pin 40)")
    print("  - Speaker on plughw:3,0 (ReSpeaker)")
    print("  - LED strip on GPIO 12 (Pin 32)")
    print()
    print("⚠️  IMPORTANT: Have headphones ready or be near speaker")
    print()
    
    setup()
    
    results = {
        "Baseline Audio": None,
        "Static Magnet": None,
        "Slow PWM (1Hz)": None,
        "Fast PWM (100ms)": None
    }
    
    try:
        # Run tests
        results["Baseline Audio"] = test_baseline()
        results["Static Magnet"] = test_magnet_static()
        results["Slow PWM (1Hz)"] = test_magnet_pwm_slow()
        results["Fast PWM (100ms)"] = test_magnet_pwm_fast()
        
        # Print results
        print("\n" + "="*60)
        print("TEST RESULTS")
        print("="*60)
        
        all_passed = True
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name:.<40} {status}")
            if not passed:
                all_passed = False
        
        print("="*60)
        
        if all_passed:
            print("\n🎉 ALL TESTS PASSED!")
            print("Electromagnet does NOT interfere with audio.")
            print("Safe to proceed with audio-reactive ferrofluid patterns.")
        else:
            print("\n⚠️  SOME TESTS FAILED")
            print("\nPossible solutions:")
            print("1. Use separate power supply for electromagnet")
            print("2. Add ground loop isolator to audio path")
            print("3. Add capacitor/filter to electromagnet circuit")
            print("4. Use optical isolation between Pi and magnet driver")
            print("5. Check for common ground issues")
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    finally:
        cleanup()

if __name__ == "__main__":
    main()
