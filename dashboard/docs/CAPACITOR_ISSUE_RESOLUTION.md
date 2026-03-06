# Capacitor Issue - 2026-01-22

## Problem Discovered

When capacitors (470μF + 104 ceramic) were added across the electromagnet circuit:
- ❌ Audio broke (only pops/clicks, no actual sound)
- ❌ LEDs got dramatically brighter when MOSFET signal wire connected
- ❌ System became unstable

## Root Cause

The capacitors created **unintended current paths** through the shared ground rail:

```
5V Rail ──┬── LED Strip
          └── Electromagnet (via MOSFET)

GND Rail ──┬── LED Strip ground
           ├── Electromagnet ground
           ├── MOSFET ground
           ├── Audio ground
           └── [CAPACITORS across electromagnet created backfeed!]
```

The 470μF capacitor stored charge and created a **voltage divider effect** that:
1. Backfed current into LED power rail (LEDs brighter)
2. Injected noise into audio ground (audio broken)
3. Created ground loops

## Solution

**Removed capacitors** → Everything works again!

- ✅ Audio plays correctly
- ✅ LEDs normal brightness
- ✅ No interference between systems

## Lessons Learned

1. **Capacitors need proper isolation**
   - Cannot share ground with sensitive circuits (audio, LEDs)
   - Need dedicated power supply for electromagnet

2. **Shared grounds are dangerous**
   - High-current devices (electromagnet) pollute ground
   - Low-current devices (audio, LEDs) are affected

3. **Ground loops are real**
   - Capacitors across shared grounds = instant problems
   - Need separate power domains

## Next Steps

### For Phase 3 (Ferrofluid Integration):

**Option 1: Separate Power Supply (RECOMMENDED)**
```
Electromagnet Circuit (ISOLATED):
  - External 12V supply → MOSFET V+
  - External GND → MOSFET V- and Electromagnet
  - Pi GPIO 21 → MOSFET SIG
  - Pi GND → MOSFET GND (signal reference ONLY, no power)
  
LED/Audio Circuit:
  - Pi 5V → LEDs, Audio
  - Pi GND → LEDs, Audio
  - COMPLETELY SEPARATE from electromagnet
```

**Option 2: Optoisolator (BETTER)**
```
Pi GPIO 21 → Optoisolator IN → [isolated] → MOSFET SIG
                                             ↓
                              External 12V → MOSFET → Electromagnet
                              External GND ↗
```

**Option 3: No Capacitors (CURRENT STATE)**
```
Just run electromagnet without capacitors for now
Test if PWM switching causes audio interference
If no interference → we're good!
If interference → need separate power (Option 1)
```

## Testing Plan

1. ✅ Audio working (verified)
2. ⏳ Test electromagnet pulse WITHOUT capacitors
3. ⏳ Test electromagnet + audio SIMULTANEOUSLY
4. ⏳ Listen for any clicks, pops, or interference
5. If clean → proceed without capacitors
6. If noisy → implement separate power supply

## References

- ORACLE_ARCHITECTURE.md - Phase 3 isolation notes
- MOSFET_WIRING_DIAGRAM.txt - Current wiring
- test_magnet_audio_isolation.py - Test script

---
**Status:** Audio fixed, electromagnet testing pending
**Date:** 2026-01-22
