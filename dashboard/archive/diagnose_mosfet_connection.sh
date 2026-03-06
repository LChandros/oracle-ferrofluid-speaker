#\!/bin/bash

echo "======================================"
echo "MOSFET CONNECTION DIAGNOSTIC"
echo "======================================"
echo ""
echo "Current wiring (from MOSFET_WIRING_DIAGRAM.txt):"
echo "  Row 23: SIG ← GPIO 21 (Pin 40)"
echo ""
echo "But you said it's on Physical Pin 12..."
echo ""
echo "Let's figure out what's actually connected\!"
echo ""
echo "ACTION REQUIRED:"
echo "1. Look at your Pi GPIO header (40 pins)"
echo "2. Find Pin 1 (top-left, labeled 3.3V usually)"
echo "3. Count down to find where MOSFET signal wire is plugged"
echo ""
echo "Reference:"
echo "  Pin 1-2:   [3.3V] [5V]     ← Top left corner"
echo "  Pin 11-12: [GPIO17] [GPIO18]"
echo "  Pin 31-32: [GPIO6] [GPIO12] ← LED strip here"
echo "  Pin 39-40: [GND] [GPIO21]  ← Bottom right"
echo ""
read -p "Which physical pin NUMBER is the MOSFET signal wire? " pin_number

case $pin_number in
  12)
    echo ""
    echo "Pin 12 = GPIO 18"
    echo "Testing GPIO 18 control..."
    python3 check_pin12_fixed.py
    ;;
  32)
    echo ""
    echo "❌ PROBLEM FOUND\!"
    echo "Pin 32 = GPIO 12 = LED STRIP PIN"
    echo "This is why LEDs get brighter\!"
    echo ""
    echo "SOLUTION: Move MOSFET signal to Pin 12 (GPIO 18)"
    ;;
  40)
    echo ""
    echo "Pin 40 = GPIO 21"
    echo "This matches the wiring diagram"
    echo "Testing GPIO 21 control..."
    python3 -c "
import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(21, GPIO.OUT)
print(LOW for 3 sec)
GPIO.output(21, GPIO.LOW)
time.sleep(3)
print(HIGH for 3 sec)
GPIO.output(21, GPIO.HIGH)
time.sleep(3)
print(LOW again)
GPIO.output(21, GPIO.LOW)
GPIO.cleanup()
"
    ;;
  2|4)
    echo ""
    echo "❌ PROBLEM FOUND\!"
    echo "Pin $pin_number is a 5V POWER pin\!"
    echo "This would cause MOSFET to be always ON"
    echo "and backfeed power to other circuits"
    echo ""
    echo "SOLUTION: Move to Pin 12 (GPIO 18) or Pin 40 (GPIO 21)"
    ;;
  *)
    echo ""
    echo "Pin $pin_number is unusual for MOSFET"
    echo "Recommended pins: 12 (GPIO 18) or 40 (GPIO 21)"
    ;;
esac
