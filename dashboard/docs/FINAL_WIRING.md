# WORKING CONFIGURATION - Oracle Ferrofluid Speaker

## Success! Audio + Electromagnet on Same Breadboard

### The Solution: Isolated Audio Amp Power

**Problem:** Electromagnet switching creates voltage spikes in shared 5V/GND rails → noise in audio

**Solution:** Power audio amp DIRECTLY from Pi, bypass breadboard rails entirely

---

## Final Wiring Diagram

### Raspberry Pi Connections:
```
Pin 2  (5V)      → Audio Amp VIN (DIRECT, isolated)
Pin 4  (5V)      → Breadboard 5V rail (for LEDs + electromagnet)
Pin 6  (GND)     → Breadboard GND rail (for LEDs + electromagnet)
Pin 9  (GND)     → Audio Amp GND (DIRECT, isolated)
Pin 12 (GPIO 18) → MOSFET SIG
Pin 32 (GPIO 12) → LED strip DATA
```

### Audio Amp (Isolated):
```
VIN  ← Pi Pin 2 (5V) - DEDICATED wire
GND  ← Pi Pin 9 (GND) - DEDICATED wire
INPUT ← ReSpeaker 3.5mm headphone jack
OUTPUT → Speaker wires
```

### Breadboard 5V/GND Rails:
```
5V Rail ← Pi Pin 4
  → LED strip power
  → MOSFET V+ power

GND Rail ← Pi Pin 6
  → LED strip ground
  → MOSFET GND reference
```

### MOSFET Module:
```
SIG ← GPIO 18 (Pin 12)
GND ← Breadboard GND rail
V+  ← Breadboard 5V rail
V-  → Electromagnet negative
```

### Electromagnet:
```
Positive → MOSFET output V+
Negative → MOSFET output V-

Flyback Diode (1N400x):
  Cathode (stripe) → Positive wire
  Anode (plain)    → Negative wire
```

### LED Strip (WS2812B):
```
DATA  ← GPIO 12 (Pin 32)
5V    ← Breadboard 5V rail
GND   ← Breadboard GND rail
```

---

## Why This Works

**Audio amp has ISOLATED power path:**
- No shared rails with electromagnet
- Voltage spikes from electromagnet switching dont affect audio
