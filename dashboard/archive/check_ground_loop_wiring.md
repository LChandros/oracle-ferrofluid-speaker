# Ground Loop Isolator Wiring Check

## Your Description
"jack from the pi hat into the female end of the ground loop isolator"
"male end of the ground loop isolator into the audio amplifier"

## This means:
```
ReSpeaker HAT
    ↓
[Cable with male 3.5mm plug]
    ↓
Ground Loop Isolator FEMALE end (input)
    ↓
Ground Loop Isolator MALE end (output)
    ↓
DROK Amp INPUT jack (female)
```

## Potential Issues

### Issue 1: Is the cable actually plugged into the amp?
The male end of the isolator needs to plug into the DROK amp INPUT jack.

Check:
- Is the isolator male plug FULLY inserted into DROK amp?
- Not just touching, but clicked in?

### Issue 2: Which jack on DROK amp?
DROK amps usually have TWO jacks:
1. INPUT jack (3.5mm) - for audio signal IN
2. SPEAKER terminals (screw terminals) - for speaker OUT

The isolator male plug should go into INPUT jack, NOT speaker terminals.

### Issue 3: Is DROK amp powered?
- Check for power LED
- If no LED, check 5V power connection

### Issue 4: Volume knob
- Is volume knob turned up?
- Turn it clockwise to increase

### Issue 5: Ground loop isolator itself
Some cheap ground loop isolators can fail or have very poor signal pass-through.

## Quick Tests

### Test 1: Check DROK amp volume
With current setup:
- Turn DROK amp volume knob all the way UP (clockwise)
- Run: aplay -D plughw:3,0 cough.wav
- Listen carefully - might be VERY quiet

### Test 2: Bypass ground loop isolator
- Unplug isolator from DROK amp
- Get a regular 3.5mm male-to-male cable
- Connect ReSpeaker directly to DROK amp INPUT
- Run: aplay -D plughw:3,0 cough.wav

If Test 2 works:
→ Ground loop isolator is broken/faulty

If Test 2 also gives only pops:
→ DROK amp issue (wrong jack, no power, or broken)

