#!/bin/bash

echo "======================================"
echo "ORACLE AUDIO PHYSICAL DIAGNOSTIC"
echo "======================================"
echo ""

echo "Step 1: Check if audio plays on ReSpeaker headphone jack directly"
echo "---------------------------------------------------------------"
echo "ACTION REQUIRED:"
echo "1. Unplug the cable from ReSpeaker headphone jack"
echo "2. Plug headphones DIRECTLY into ReSpeaker"
echo "3. Press ENTER when ready"
read -p ""

echo "Testing with headphones..."
aplay -D plughw:3,0 cough.wav

echo ""
echo "QUESTION: Did you hear the cough sound clearly? (y/n)"
read -p "" headphone_test

if [ "$headphone_test" = "y" ]; then
    echo "✅ ReSpeaker audio output is WORKING"
    echo "   → Problem is in external amp/speaker chain"
else
    echo "❌ ReSpeaker audio output is BROKEN"
    echo "   → Software or ReSpeaker HAT issue"
    exit 1
fi

echo ""
echo "Step 2: Check Ground Loop Isolator"
echo "-----------------------------------"
echo "The ground loop isolator should have:"
echo "  - INPUT side (from ReSpeaker)"
echo "  - OUTPUT side (to DROK amp)"
echo ""
echo "ACTION REQUIRED:"
echo "1. Find the ground loop isolator"
echo "2. Check if it has INPUT/OUTPUT labels"
echo "3. Verify cable from ReSpeaker goes to INPUT"
echo "4. Verify cable to DROK amp comes from OUTPUT"
echo "5. Press ENTER when checked"
read -p ""

echo ""
echo "Step 3: Try bypassing Ground Loop Isolator"
echo "-------------------------------------------"
echo "ACTION REQUIRED:"
echo "1. Unplug both cables from ground loop isolator"
echo "2. Connect ReSpeaker headphone jack DIRECTLY to DROK amp INPUT"
echo "   (You may need a different cable)"
echo "3. Press ENTER when ready to test"
read -p ""

echo "Testing without ground loop isolator..."
aplay -D plughw:3,0 cough.wav

echo ""
echo "QUESTION: Did you hear the cough sound clearly? (y/n)"
read -p "" bypass_test

if [ "$bypass_test" = "y" ]; then
    echo "✅ Audio works WITHOUT ground loop isolator"
    echo "   → Ground loop isolator is faulty or reversed"
    echo ""
    echo "SOLUTION:"
    echo "  Option 1: Flip the ground loop isolator (swap input/output)"
    echo "  Option 2: Keep it bypassed for now (test electromagnet separately)"
else
    echo "⚠️  Audio still broken without ground loop isolator"
    echo "   → Check DROK amp and speaker connections next"
fi

echo ""
echo "Step 4: Check DROK Amp"
echo "----------------------"
echo "ACTION REQUIRED:"
echo "1. Check DROK amp has power (LED should be on)"
echo "2. Check volume knob is turned up"
echo "3. Verify 3.5mm cable is in INPUT jack (not speaker terminals)"
echo "4. Verify speaker wires are tight in OUTPUT terminals"
echo "   - Red wire = positive terminal"
echo "   - Black wire = negative terminal"
echo "5. Press ENTER when verified"
read -p ""

echo ""
echo "======================================"
echo "DIAGNOSTIC COMPLETE"
echo "======================================"
echo ""
echo "Next steps based on results:"
echo "  - If headphones worked: External amp/speaker issue"
echo "  - If bypass worked: Ground loop isolator reversed/faulty"
echo "  - If nothing worked: Check ReSpeaker HAT seating"
echo ""
