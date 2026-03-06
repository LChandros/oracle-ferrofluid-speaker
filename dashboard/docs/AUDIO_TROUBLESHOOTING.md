# Audio Troubleshooting Notes - 2026-01-21

## Current Status: ❌ NO AUDIO (Only pops)

### What Was Working:
- Audio played perfectly before electromagnet testing
- LED visualizer syncing to audio
- cough.wav, voice-test.wav all working

### What Changed:
- Added 470μF + 104 ceramic capacitors to electromagnet circuit
- Ran electromagnet pulse test with audio
- After test: only hearing pops, no actual sound

### MOSFET State:
- Currently UNPLUGGED from breadboard
- Issue persists even without MOSFET connected
- → Rules out electromagnet as cause

### Diagnostics Run:
1. ✅ Audio commands execute successfully (aplay runs)
2. ✅ Volume settings confirmed at correct levels:
   - Playback: 255 (100%)
   - Speaker: 96 (76%)
   - PCM switches: ON
3. ❌ Only hearing pops/clicks, no actual audio
4. ❌ speaker-test also just pops

### Most Likely Causes:

1. **Ground Loop Isolator Disconnected/Reversed**
   - Check both 3.5mm cables fully inserted
   - Try swapping input/output (some are directional)
   - Look for INPUT/OUTPUT labels on isolator

2. **DROK Amp Input Cable Loose**
   - 3.5mm from isolator to amp input
   - Should be in INPUT jack (not SPEAKER terminals)

3. **Speaker Wire Loose**
   - Check both speaker wires on DROK amp output terminals
   - Red = positive, Black = negative

4. **Power to DROK Amp**
   - Check amp has power LED
   - Verify 5V to amp VIN

### Tomorrow's Debugging Steps:

1. **Visual inspection:**
   - Ground loop isolator connections
   - All 3.5mm cables seated properly
   - Speaker wires tight in terminals
   - DROK amp power LED on

2. **Test chain step by step:**
   - ReSpeaker → isolator (cable 1)
   - Isolator → DROK amp (cable 2)
   - DROK amp → speakers

3. **Try bypassing ground loop isolator:**
   - Direct cable: ReSpeaker → DROK amp
   - If audio works, isolator is problem
   - If still pops, amp or speaker issue

4. **Check DROK amp:**
   - Volume knob turned up?
   - Input selected correctly?
   - Output terminals have speaker wires?

### Working Audio Settings (To Restore):
```bash
amixer -c 3 set Playback 255
amixer -c 3 set Speaker 96
amixer -c 3 set 'Left Output Mixer PCM' on
amixer -c 3 set 'Right Output Mixer PCM' on
```

### Next Steps After Audio Fixed:
1. Reconnect MOSFET module
2. Test electromagnet pulse with capacitors
3. Verify no interference with audio
4. Move to Phase 1 of Oracle implementation

---
Last Updated: 2026-01-21 Evening
Status: Audio broken, needs physical connection debugging
