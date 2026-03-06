# Audio Issue - Reboot Required

## Current Status
- ✅ All software settings correct
- ✅ Audio commands execute successfully  
- ✅ DROK amp powered and connected
- ❌ **ReSpeaker HAT not outputting audio** (not even from headphone jack)
- ❌ Only hearing pops (DC on/off clicks)

## What This Means
The WM8960 audio codec on the ReSpeaker HAT is not actually playing PCM audio data.
This is a hardware/driver state issue, not a mixer setting problem.

## Most Likely Cause
The electromagnet testing may have caused:
1. Electrical noise that corrupted the HAT firmware state
2. GPIO interference that put the codec in a bad state
3. Ground loop that damaged something

## Solution: Power Cycle
Need to **fully power down** the Raspberry Pi to reset the ReSpeaker HAT hardware:

```bash
# Clean shutdown
sudo shutdown -h now

# Wait 10 seconds
# Unplug power
# Wait 10 more seconds  
# Plug power back in
```

## After Reboot
Test immediately:
```bash
aplay -D plughw:3,0 cough.wav
```

If still not working:
1. Check HAT is properly seated on GPIO pins
2. Power down, remove HAT, reseat, power up
3. Check for any visible damage to HAT

## Alternative: HAT May Be Damaged
If reboot doesnt fix it, the electromagnet interference may have permanently damaged:
