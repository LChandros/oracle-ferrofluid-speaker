# Oracle Hardware Configuration
**Date: 2026-01-27**
**Current Status: Phase 2 Complete, Ready for Phase 4**

## GPIO Pin Assignments

| Component | GPIO (BCM) | Physical Pin | Notes |
|-----------|------------|--------------|-------|
| WS2812B LED Strip | GPIO 12 | Pin 32 | 19 LEDs, 5V power |
| Electromagnet | GPIO 23 | Pin 16 | Via MOSFET (AOD4184A) |
| ReSpeaker HAT | I2C/I2S | Multiple | Audio I/O |

## Current Electromagnet

- **Type:** 5V electromagnet (weak - awaiting upgrade)
- **Control:** PWM via MOSFET driver
- **Status:** WORKING - pulses synchronized to syllables
- **Next:** 12V electromagnet ordered

## Audio Chain

```
ReSpeaker 2-Mic HAT (3.5mm out)
   ↓
BESIGN Ground Loop Isolator (transformer coupling)
   ↓
DROK 5W×2 Class D Amplifier
   ↓
Two 78mm 8Ω 10W Speakers
```

**Critical Settings:**
- Headphone volume: `amixer -c 3 sset Headphone 127`
- Audio device: `plughw:3,0`
- Ground loop isolator REQUIRED (prevents hum/static)

## Power Configuration

- External 5V power supply
- Shared breadboard power for Pi + DROK
- Electromagnet shares 5V rail
- LED strip: 5V, < 1A draw (19 LEDs × ~50mA max)

## Software Status

**Working Features:**
- [x] Text-to-Speech (ElevenLabs API, 30+ voices)
- [x] Syllable-based electromagnet pulsing
- [x] Audio-reactive LED visualization
- [x] Web dashboard (http://100.82.131.122:5000)
- [x] Systemd service (auto-starts on boot)

**Organized Structure:**
```
/home/tyahn/oracle/
├── scripts/           (12K) - Main visualizer
├── dashboard/         (3.2M) - Flask web interface
├── patterns/          (16K) - Test patterns
├── docs/              (80K) - Documentation
├── config/            (4K)  - Configuration
├── archive/           (276K) - 44 archived test scripts
└── README.md          - Quick reference
```

**Next Steps:**
1. Test with new 12V electromagnet when it arrives
2. Integrate with Moneo voice assistant (/root/moneo/voice-assistant/)
3. Replace dashboard with voice interface (wake word detection)
4. Implement state-based visualization:
   - IDLE → Breathing LEDs
   - LISTENING → Pulsing LEDs
   - THINKING → Chaos pattern
   - SPEAKING → Syllable sync (already working!)

## Testing Commands

**Dashboard:**
```bash
sudo systemctl status oracle-dashboard
sudo systemctl restart oracle-dashboard
```

**Manual Test:**
```bash
sudo python3 /home/tyahn/oracle/patterns/ferrofluid_patterns.py
```

**Direct Visualizer:**
```bash
sudo python3 /home/tyahn/oracle/scripts/oracle_synced.py <audio_file> <syllable_count>
```

## Network Access

- Dashboard: http://100.82.131.122:5000
- Tailscale hostname: development-hub
- SSH: `ssh tyahn@100.82.131.122`
