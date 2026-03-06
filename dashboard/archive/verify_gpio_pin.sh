#!/bin/bash

echo "======================================"
echo "GPIO PIN VERIFICATION"
echo "======================================"
echo ""
echo "CRITICAL: We need to verify which physical pin"
echo "the MOSFET signal wire is connected to."
echo ""
echo "Physical Pin 12 = GPIO 18 (correct for electromagnet)"
echo "Physical Pin 32 = GPIO 12 (WRONG - that is LED strip!)"
echo ""
echo "Counting from the Pi edge:"
echo ""
echo "  Pin 1-2:   [3.3V] [5V]"
echo "  Pin 11-12: [GPIO17] [GPIO18] ← MOSFET should be here"
echo "  Pin 31-32: [GPIO6] [GPIO12]  ← LED strip is here"
echo ""
read -p "Which physical pin NUMBER is MOSFET SIG connected to? " pin_num

if [ "$pin_num" = "12" ]; then
    echo ""
    echo "✅ Correct! GPIO 18 (Pin 12)"
    echo "Testing GPIO 18..."
    python3 -c "
import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(18, GPIO.OUT)
print(\"Pulsing GPIO 18 for 3 seconds...\")
for i in range(6):
    GPIO.output(18, GPIO.HIGH)
    time.sleep(0.25)
    GPIO.output(18, GPIO.LOW)
    time.sleep(0.25)
GPIO.cleanup()
print(\"Done\")
"
elif [ "$pin_num" = "32" ]; then
    echo ""
    echo "❌ WRONG PIN!"
    echo "Pin 32 is GPIO 12 - that's the LED strip!"
    echo "This creates a conflict!"
    echo ""
    echo "SOLUTION: Move MOSFET signal to Pin 12 (GPIO 18)"
else
    echo ""
    echo "Pin $pin_num - checking what GPIO that is..."
fi
