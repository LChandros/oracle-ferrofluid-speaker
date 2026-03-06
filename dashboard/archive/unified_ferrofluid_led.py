#!/usr/bin/env python3
"""
Unified Ferrofluid + LED Controller - Dynamic Pattern Switching
Synchronizes electromagnet pulses with LED strip colors
Switch patterns on-the-fly with keyboard input
- Physical Pin 40 (GPIO 21) - Electromagnet
- Physical Pin 12 (GPIO 18) - WS2812B LED Strip
"""

import RPi.GPIO as GPIO
from rpi_ws281x import PixelStrip, Color
import time
import random
import sys
import threading
import select

# ============================================================
# CONFIGURATION
# ============================================================

# Electromagnet
MAGNET_PIN = 21  # Physical pin 40 (GPIO 21, BCM)

# LED Strip
LED_COUNT = 10
LED_PIN = 18  # Physical pin 12 (GPIO 18, BCM)
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0

# Global state
current_pattern = None
running = True
strip = None

# ============================================================
# SETUP & CLEANUP
# ============================================================

def setup():
    """Initialize GPIO and LED strip"""
    global strip
    print("🔧 Initializing hardware...")
    
    # Setup GPIO for electromagnet
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(MAGNET_PIN, GPIO.OUT)
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    
    # Initialize LED strip
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, 
                      LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()
    
    # Turn off all LEDs
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    
    print("✅ Electromagnet ready (Pin 40, GPIO 21)")
    print("✅ LED strip ready (Pin 12, GPIO 18)")

def cleanup():
    """Clean up GPIO and turn off LEDs"""
    global strip
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    GPIO.cleanup()

def set_all_leds(color):
    """Set all LEDs to a specific color"""
    global strip
    for i in range(LED_COUNT):
        strip.setPixelColor(i, color)
    strip.show()

def set_led_brightness(color, brightness):
    """Set LEDs with variable brightness (0.0 to 1.0)"""
    r = int((color >> 16 & 0xFF) * brightness)
    g = int((color >> 8 & 0xFF) * brightness)
    b = int((color & 0xFF) * brightness)
    adjusted_color = Color(r, g, b)
    set_all_leds(adjusted_color)

def should_continue():
    """Check if we should continue running current pattern"""
    return running and current_pattern is not None

# ============================================================
# UNIFIED PATTERNS
# ============================================================

def pattern_pulse():
    """Rhythmic pulses with blue LEDs"""
    pattern_name = "Pulse"
    while should_continue() and current_pattern == pattern_name:
        # ON - Bright blue + electromagnet
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        set_all_leds(Color(0, 0, 255))  # Blue
        time.sleep(0.3)
        
        # OFF - Dim blue + electromagnet off
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        set_all_leds(Color(0, 0, 50))  # Dim blue
        time.sleep(0.3)

def pattern_wave():
    """Wave pattern with gradient green LEDs"""
    pattern_name = "Wave"
    while should_continue() and current_pattern == pattern_name:
        # Rising intensity
        for i in range(10):
            if not should_continue() or current_pattern != pattern_name:
                break
            brightness = i / 10.0
            on_time = 0.05 + (i * 0.02)
            
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            set_led_brightness(Color(0, 255, 0), brightness)  # Green
            time.sleep(on_time)
            
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(0.05)
        
        # Falling intensity
        for i in range(10, 0, -1):
            if not should_continue() or current_pattern != pattern_name:
                break
            brightness = i / 10.0
            on_time = 0.05 + (i * 0.02)
            
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            set_led_brightness(Color(0, 255, 0), brightness)
            time.sleep(on_time)
            
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(0.05)

def pattern_spike():
    """Sharp bursts with white flashes"""
    pattern_name = "Spike"
    # Dim ambient purple
    set_all_leds(Color(50, 0, 50))
    
    while should_continue() and current_pattern == pattern_name:
        time.sleep(random.uniform(0.2, 1.5))
        
        if not should_continue() or current_pattern != pattern_name:
            break
        
        # Quick spike - bright white
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        set_all_leds(Color(255, 255, 255))
        time.sleep(random.uniform(0.05, 0.2))
        
        # Back to ambient
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        set_all_leds(Color(50, 0, 50))

def pattern_breathing():
    """Breathing with cyan LEDs"""
    pattern_name = "Breathing"
    while should_continue() and current_pattern == pattern_name:
        # Inhale - cyan fading in
        for i in range(20):
            if not should_continue() or current_pattern != pattern_name:
                break
            brightness = i / 20.0
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            set_led_brightness(Color(0, 255, 255), brightness)  # Cyan
            time.sleep(0.05 + (i * 0.01))
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(0.02)
        
        # Hold - full bright
        if should_continue() and current_pattern == pattern_name:
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            set_all_leds(Color(0, 255, 255))
            time.sleep(0.5)
        
        # Exhale - cyan fading out
        for i in range(20, 0, -1):
            if not should_continue() or current_pattern != pattern_name:
                break
            brightness = i / 20.0
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            set_led_brightness(Color(0, 255, 255), brightness)
            time.sleep(0.05 + (i * 0.01))
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            time.sleep(0.02)
        
        # Rest - dim
        if should_continue() and current_pattern == pattern_name:
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            set_all_leds(Color(0, 50, 50))
            time.sleep(0.5)

def pattern_heartbeat():
    """Heartbeat with red pulses"""
    pattern_name = "Heartbeat"
    while should_continue() and current_pattern == pattern_name:
        # Lub - red pulse
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        set_all_leds(Color(255, 0, 0))  # Red
        time.sleep(0.15)
        
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        set_all_leds(Color(50, 0, 0))  # Dim red
        time.sleep(0.15)
        
        if not should_continue() or current_pattern != pattern_name:
            break
        
        # Dub - red pulse
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        set_all_leds(Color(255, 0, 0))
        time.sleep(0.15)
        
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        set_all_leds(Color(50, 0, 0))
        time.sleep(0.8)

def pattern_ripple():
    """Fast ripples with purple pulses"""
    pattern_name = "Ripple"
    while should_continue() and current_pattern == pattern_name:
        # Burst of quick pulses
        for i in range(5):
            if not should_continue() or current_pattern != pattern_name:
                break
            GPIO.output(MAGNET_PIN, GPIO.HIGH)
            set_all_leds(Color(255, 0, 255))  # Magenta
            time.sleep(0.05)
            
            GPIO.output(MAGNET_PIN, GPIO.LOW)
            set_all_leds(Color(50, 0, 50))
            time.sleep(0.05)
        
        time.sleep(0.5)

def pattern_chaos():
    """Complete chaos with random colors"""
    pattern_name = "Chaos"
    while should_continue() and current_pattern == pattern_name:
        on_time = random.uniform(0.01, 0.5)
        off_time = random.uniform(0.01, 0.5)
        
        # Random color
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        set_all_leds(Color(r, g, b))
        time.sleep(on_time)
        
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        set_all_leds(Color(r//5, g//5, b//5))  # Dim version
        time.sleep(off_time)

def pattern_rainbow():
    """Rainbow cycling with synchronized pulses"""
    pattern_name = "Rainbow"
    hue = 0
    
    while should_continue() and current_pattern == pattern_name:
        # Convert HSV to RGB (simple approximation)
        h = hue % 360
        c = 255
        x = int(c * (1 - abs((h / 60) % 2 - 1)))
        
        if h < 60:
            r, g, b = c, x, 0
        elif h < 120:
            r, g, b = x, c, 0
        elif h < 180:
            r, g, b = 0, c, x
        elif h < 240:
            r, g, b = 0, x, c
        elif h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        # Pulse ON
        GPIO.output(MAGNET_PIN, GPIO.HIGH)
        set_all_leds(Color(r, g, b))
        time.sleep(0.2)
        
        # Pulse OFF (dim)
        GPIO.output(MAGNET_PIN, GPIO.LOW)
        set_all_leds(Color(r//5, g//5, b//5))
        time.sleep(0.2)
        
        hue += 15  # Color shift

def pattern_off():
    """Turn everything off"""
    pattern_name = "Off"
    GPIO.output(MAGNET_PIN, GPIO.LOW)
    set_all_leds(Color(0, 0, 0))
    while should_continue() and current_pattern == pattern_name:
        time.sleep(0.1)

# ============================================================
# PATTERN RUNNER
# ============================================================

PATTERNS = {
    '1': ('Pulse', pattern_pulse, '🫀', 'Blue rhythmic pulses'),
    '2': ('Wave', pattern_wave, '🌊', 'Green gradient'),
    '3': ('Spike', pattern_spike, '⚡', 'White bursts'),
    '4': ('Breathing', pattern_breathing, '🫁', 'Cyan breathing'),
    '5': ('Heartbeat', pattern_heartbeat, '💓', 'Red lub-dub'),
    '6': ('Ripple', pattern_ripple, '💫', 'Purple ripples'),
    '7': ('Chaos', pattern_chaos, '🌀', 'Random chaos'),
    '8': ('Rainbow', pattern_rainbow, '🌈', 'Color cycling'),
    '0': ('Off', pattern_off, '⬛', 'Lights off'),
}

def run_pattern():
    """Main pattern execution thread"""
    global current_pattern
    
    while running:
        if current_pattern and current_pattern in [p[0] for p in PATTERNS.values()]:
            # Find and run the pattern function
            for key, (name, func, emoji, desc) in PATTERNS.items():
                if name == current_pattern:
                    func()
                    break
        else:
            time.sleep(0.1)

# ============================================================
# INPUT HANDLER
# ============================================================

def input_handler():
    """Handle keyboard input for pattern switching"""
    global current_pattern, running
    
    print("\n" + "=" * 70)
    print("  🧲 UNIFIED FERROFLUID + LED CONTROLLER - DYNAMIC MODE 💡")
    print("  Electromagnet: Pin 40 (GPIO 21) | LEDs: Pin 12 (GPIO 18)")
    print("=" * 70)
    print("\n🎮 DYNAMIC PATTERN SWITCHING - Press keys to switch instantly!\n")
    print("Available Patterns:")
    for key, (name, func, emoji, desc) in PATTERNS.items():
        print(f"  {key}. {emoji} {name:<12} - {desc}")
    print("  Q. Quit\n")
    print("💡 Press a number key (1-8, 0) to instantly switch patterns!")
    print("   No need to stop or return to menu - just press and go!\n")
    print("=" * 70 + "\n")
    
    # Start with pattern off
    current_pattern = "Off"
    print("▶️  Starting in OFF mode. Press a number to begin!\n")
    
    while running:
        try:
            # Use select to check for input without blocking
            if select.select([sys.stdin], [], [], 0.1)[0]:
                choice = sys.stdin.read(1).strip().lower()
                
                if choice == 'q':
                    print("\n🛑 Shutting down...")
                    running = False
                    break
                
                if choice in PATTERNS:
                    name, func, emoji, desc = PATTERNS[choice]
                    current_pattern = name
                    print(f"▶️  Switched to: {emoji} {name} - {desc}")
                elif choice:
                    print(f"❌ Invalid key '{choice}'. Use 0-8 or Q to quit.")
            
            time.sleep(0.05)
            
        except Exception as e:
            print(f"Input error: {e}")
            break

# ============================================================
# MAIN
# ============================================================

def main():
    global running
    
    setup()
    
    # Start pattern execution thread
    pattern_thread = threading.Thread(target=run_pattern, daemon=True)
    pattern_thread.start()
    
    try:
        # Run input handler in main thread
        input_handler()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted!")
    finally:
        running = False
        time.sleep(0.2)  # Give pattern thread time to stop
        cleanup()
        print("\n✅ Electromagnet OFF")
        print("✅ LEDs OFF")
        print("✅ GPIO cleaned up")
        print("\nGoodbye! 🧲💡\n")

if __name__ == "__main__":
    main()
