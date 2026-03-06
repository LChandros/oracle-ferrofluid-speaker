# Audio Physical Troubleshooting - 2026-01-22

## Current Symptom
✅ Software working (aplay commands run successfully)
❌ Only hearing POPS, no actual audio from speaker

## What This Means
The ReSpeaker HAT is outputting audio correctly, but something in the physical chain is broken.

## Physical Audio Chain
```
ReSpeaker 3.5mm jack
    ↓ (3.5mm cable)
Ground Loop Isolator INPUT
    ↓
Ground Loop Isolator OUTPUT
    ↓ (3.5mm cable)
DROK Amp INPUT jack
    ↓
DROK Amp (powered, volume knob)
    ↓ (speaker wires)
Speaker
```

## Most Likely Causes

### 1. Ground Loop Isolator Disconnected/Reversed (70% probability)
**Symptoms:** Only pops, no audio
**Check:**
- Both 3.5mm cables fully inserted?
- Input/Output might be swapped
- Some isolators are directional

**Fix:** Try flipping the isolator (swap the two cables)

### 2. 3.5mm Cable Loose (20% probability)
**Check:**
- Cable from isolator to DROK amp fully inserted?
- Check both ends

### 3. DROK Amp Issues (10% probability)
**Check:**
- Power LED on amp?
- Volume knob turned up?
- Cable in INPUT jack (not speaker terminals)?
- Speaker wires tight in OUTPUT terminals?

## Step-by-Step Fix

### Test 1: Bypass Everything - Use Headphones
1. Find headphones or earbuds
2. Unplug cable from ReSpeaker 3.5mm jack
3. Plug headphones DIRECTLY into ReSpeaker
4. Run: `aplay -D plughw:3,0 cough.wav`
5. **Expected:** Should hear audio clearly in headphones

If you DON'T hear audio in headphones:
- ReSpeaker HAT hardware problem
- HAT not seated properly on GPIO

If you DO hear audio in headphones:
- ReSpeaker working! Problem is downstream.
- Continue to Test 2

### Test 2: Check Ground Loop Isolator
1. Unplug headphones
2. Reconnect cable from ReSpeaker to isolator
3. **Try flipping the isolator:**
   - Swap the two 3.5mm cables
   - INPUT becomes OUTPUT, OUTPUT becomes INPUT
4. Run: `aplay -D plughw:3,0 cough.wav`
5. **Expected:** Audio should work if isolator was backwards

### Test 3: Bypass Ground Loop Isolator
1. Find a 3.5mm cable
2. Connect ReSpeaker jack DIRECTLY to DROK amp INPUT
3. Skip the isolator completely
4. Run: `aplay -D plughw:3,0 cough.wav`
5. **Expected:** Audio should work

If it works:
- Ground loop isolator is faulty or backwards
- Keep it bypassed for now

### Test 4: Check DROK Amp
1. Power LED on DROK amp should be lit
2. Volume knob turned clockwise (up)
3. 3.5mm cable in INPUT jack (small jack, not speaker terminals)
4. Speaker wires in OUTPUT terminals (screw terminals)
   - Red = positive terminal
   - Black = negative terminal
5. Tighten any loose wires

## Quick Commands

```bash
# Test with cough
aplay -D plughw:3,0 cough.wav

# Test with music
mpg123 -a plughw:3,0 test-music.mp3

# Test with sine tone (440Hz for 3 seconds)
timeout 3 speaker-test -D plughw:3,0 -c 2 -t sine -f 440
```

## If Nothing Works
- Check if ReSpeaker HAT is properly seated on GPIO pins
- Power cycle the Raspberry Pi
- Check for bent/broken GPIO pins

---
**Next:** Once audio working, test electromagnet isolation
