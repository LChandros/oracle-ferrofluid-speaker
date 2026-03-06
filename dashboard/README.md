# Oracle Ferrofluid Speaker

DIY Alexa-type AI interface with ferrofluid visualization

## Directory Structure

```
/home/tyahn/oracle/
├── scripts/           # Main control scripts
│   └── oracle_synced.py      # Audio-reactive visualizer with syllable pulsing
├── dashboard/         # Web interface for TTS testing
│   ├── app.py                # Flask backend with ElevenLabs integration
│   ├── templates/index.html  # Web dashboard UI
│   ├── config.txt            # API keys and configuration
│   └── audio/                # Generated audio files
├── patterns/          # Pattern test scripts
│   └── ferrofluid_patterns.py  # Manual electromagnet patterns
├── docs/              # Documentation and wiring guides
│   ├── ORACLE_ARCHITECTURE.md
│   ├── ORACLE_QUICK_START.md
│   ├── AUDIO_FIX_PHYSICAL.md
│   └── FINAL_WIRING.md
├── config/            # Configuration files (future)
└── archive/           # Old test scripts (44 files)

## Hardware Configuration

- **Raspberry Pi 4B** - Main controller
- **ReSpeaker 2-Mic Pi HAT v1.0** - Audio I/O
- **DROK 5W×2 Amplifier** - Speaker power
- **Two 78mm 8Ω speakers** - Audio output
- **WS2812B LED strip** - 19 LEDs on GPIO 12 (Physical Pin 32)
- **Electromagnet** - GPIO 23 (Physical Pin 16) with MOSFET driver
- **Ground Loop Isolator** - BESIGN (between ReSpeaker and DROK)

## Current Features

### Dashboard (Port 5000)
- Text-to-Speech via ElevenLabs API
- 30+ voice options dynamically fetched
- Syllable-based electromagnet pulsing
- Audio-reactive LED visualization
- Cyan/blue Oracle color theme

### Syllable Pulsing
- Counts syllables from input text
- Pre-calculates pulse timing based on audio duration
- Each pulse = 120ms (typical syllable duration)
- Pulses evenly spaced across audio playback

## Usage

### Start Dashboard Manually
```bash
cd /home/tyahn/oracle/dashboard
python3 app.py
```
Access at: http://100.82.131.122:5000

### Start Dashboard as Service
```bash
sudo systemctl start oracle-dashboard
sudo systemctl enable oracle-dashboard  # Auto-start on boot
```

### Test Electromagnet Patterns
```bash
sudo python3 /home/tyahn/oracle/patterns/ferrofluid_patterns.py
```

### Direct Visualizer Usage
```bash
sudo python3 /home/tyahn/oracle/scripts/oracle_synced.py <audio_file> <syllable_count>
```

## Next Phase: Voice Assistant Integration

Goal: Replace dashboard with full voice assistant
- Wake word detection ("Hey Moneo")
- Desktop PC handles Claude API conversation
- Pi receives commands via HTTP (listen/think/speak states)
- LED + electromagnet visualization per state:
  - IDLE: Gentle breathing
  - LISTENING: Pulsing
  - THINKING: Chaos pattern
  - SPEAKING: Syllable sync (current implementation!)

## Pin Reference

- GPIO 12 (Pin 32) → WS2812B LED strip
- GPIO 23 (Pin 16) → Electromagnet MOSFET gate
- 3.5mm Jack (ReSpeaker) → Ground Loop Isolator → DROK Amp → Speakers

## Audio Configuration

Headphone volume MUST be at 127 (100%):
```bash
sudo amixer -c 3 sset Headphone 127
```

Audio device: `plughw:3,0`

## Documentation

See `/home/tyahn/oracle/docs/` for:
- Full architecture plans
- Audio troubleshooting steps
- Wiring diagrams
- Ground loop solution details

## Archive

Old test files preserved in `/home/tyahn/oracle/archive/` (44 scripts)
