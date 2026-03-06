# Electromagnet + LEDs + Audio - Shared Power Integration

## Goal
Get electromagnet, LED strip, and audio amp ALL working together on same breadboard with Pi 5V power.

## The Problem We Solved Before

**Issue:** Capacitors across electromagnet created ground loop → broke audio + made LEDs bright
**Why:** Capacitor stored charge and created backfeed current through shared ground

## Solution: Proper Ground Separation WITHOUT Extra Power Supply

### Strategy: Isolated Signal, Shared Power Rails

```
                    Raspberry Pi
                         │
              ┌──────────┼──────────┐
              │          │          │
         GPIO 12    GPIO 18      5V Rail
              │          │          │
              │          │          ├─→ LED Strip 5V
              │          │          ├─→ DROK Amp 5V  
              │          │          └─→ MOSFET V+ (electromagnet power)
              │          │
         LED Strip   MOSFET SIG
         Data         (control)
              │          │
              │          │
         GND Rail ←─────┴──────────┐
              │                     │
              ├─→ LED Strip GND     │
              ├─→ DROK Amp GND      │
              └─→ MOSFET GND        │
                  (signal ref only, │
                   NO power return) │
                                    │
                         Electromagnet GND
                         (through MOSFET V-)
```

### Key Insight: Capacitors Go AFTER The MOSFET

**WRONG (what we did before):**
```
5V → MOSFET → [Capacitor] → Electromagnet → GND rail
                    ↑
              Backfed into main GND!
```

**RIGHT (what we should do):**
```
5V → MOSFET → Electromagnet → [Capacitor to local GND point] → GND rail
                                        ↑
                            Filters at the load only
```

## Wiring Plan

### 1. Power Rails (Breadboard)
```
5V Rail:
  ← Pi Pin 2 (5V)
  → LED strip 5V
  → DROK amp VIN
  → MOSFET V+ terminal

GND Rail:
  ← Pi Pin 6 (GND)
  → LED strip GND
  → DROK amp GND  
  → MOSFET GND (signal reference)
```

### 2. Signal Lines
```
GPIO 12 (Pin 32) → LED strip DATA pin
GPIO 18 (Pin 12) → MOSFET SIG pin
```

### 3. Electromagnet Circuit
```
MOSFET Module:
  SIG ← GPIO 18
  GND ← GND rail (signal reference only)
  V+  ← 5V rail
  V-  → Row X (output negative)
  
Electromagnet:
  Positive → MOSFET output V+ (Row Y)
  Negative → MOSFET output V- (Row X)
  
Capacitor (470μF):
  POSITIVE (+) → Row Y (electromagnet positive)
  NEGATIVE (-) → Row X (electromagnet negative)
  
Capacitor (104 ceramic):
  One leg → Row Y
  Other leg → Row X
```

**CRITICAL:** Capacitors are ONLY across the electromagnet terminals, NOT connected directly to main GND rail!

### 4. Audio Amp (Keep Isolated)
```
DROK Amp:
  VIN ← 5V rail (power only)
  GND ← GND rail (power only)
  INPUT ← ReSpeaker headphone jack (3.5mm cable)
  OUTPUT → Speaker wires
```

**Audio signal path stays completely separate from electromagnet!**

## Why This Works

1. **LEDs:** Direct GPIO control, minimal current on signal line
2. **Audio:** Analog signal on separate cable, powered but signal-isolated
3. **Electromagnet:** 
   - Power from 5V rail (okay, Pi can handle it)
   - Signal from GPIO (okay, MOSFET isolates)
   - **Capacitors ONLY filter the electromagnet itself**
   - **No capacitor current flows back to main GND**

## Testing Procedure

### Step 1: Baseline (Current State)
- ✅ Audio working
- ✅ LEDs working
- ❌ MOSFET unplugged

### Step 2: Add MOSFET (NO Capacitors Yet)
1. Wire MOSFET as shown above
2. Test electromagnet pulse script
3. **Listen for audio interference**
4. **Watch LEDs for flickering**

If Step 2 works clean → electromagnet is compatible!
If Step 2 causes issues → electromagnet PWM creates noise (need filter)

### Step 3: Add Capacitors (ONLY If Needed)
1. Install 470μF across electromagnet terminals ONLY
2. Install 104 ceramic across electromagnet terminals ONLY
3. **Verify capacitors NOT connected to main GND rail**
4. Test full system

## Expected Results

**BEST CASE:** Electromagnet works WITHOUT capacitors, no interference!
- Audio clean
- LEDs clean  
- Electromagnet responds to GPIO

**LIKELY CASE:** Small clicking when electromagnet switches
- Add capacitors ONLY across electromagnet
- Filters the switching noise locally
- Rest of system unaffected

**WORST CASE:** Heavy interference
- Need flyback diode across electromagnet
- Need RC filter on MOSFET signal line
- May need to reduce electromagnet duty cycle

## Next Step

Wire up the MOSFET WITHOUT capacitors first.
Test with: `sudo python3 test_magnet_audio_isolation.py`

This will tell us if we even NEED the capacitors!

