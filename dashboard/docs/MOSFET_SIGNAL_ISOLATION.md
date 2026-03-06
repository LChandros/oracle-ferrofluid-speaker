# MOSFET Signal Isolation Problem

## Current Behavior
- Audio perfect: MOSFET completely disconnected
- Audio perfect: MOSFET V+/V- connected, SIG + GND disconnected  
- **Audio BREAKS (pops only): As soon as SIG wire connects**

## Key Finding
The interference is NOT coming through power rails or ground loops.
The interference is coming through the **GPIO signal wire itself**.

## Possible Solutions to Try

### 1. Optocoupler Isolation
Use an optocoupler (like PC817) to electrically isolate the Pi GPIO from the MOSFET:
- Pi GPIO → Optocoupler LED side
- Optocoupler transistor side → MOSFET gate
- Complete electrical isolation between Pi and MOSFET

### 2. Different GPIO Pin
Try a different GPIO pin that might be on a different power domain:
- Current: GPIO 18 (PWM0)
- Try: GPIO 23 or GPIO 24 (regular digital pins, not PWM)

### 3. Pull-down Resistor
Add 10kΩ resistor from MOSFET gate to ground:
- May help stabilize the gate voltage
- Prevents floating gate when GPIO is transitioning

### 4. RC Low-Pass Filter on Signal
Add resistor + capacitor between GPIO and MOSFET gate:
- 1kΩ resistor in series with signal
- 100nF capacitor from MOSFET gate to ground
- Filters high-frequency noise

### 5. FerroWave Research
Check matoslav/FerroWave project for their exact wiring:
- Arduino vs Pi differences
- MOSFET module differences
- Signal isolation techniques

## Next Steps
1. Try optocoupler isolation (most likely to work)
2. Research FerroWave schematic
3. Try different GPIO pin
