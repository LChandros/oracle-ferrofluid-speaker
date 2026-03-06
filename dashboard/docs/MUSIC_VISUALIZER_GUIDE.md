# Moneo Voice Nexus - Music Visualizer Guide

## Hardware Setup

**LED Strip:** 10 addressable LEDs (WS2812B/NeoPixel)
- **Signal Pin:** GPIO12 (Physical Pin 32)
- **Power:** 5V
- **Ground:** GND

**Speaker:** Connected via ReSpeaker audio HAT

## Quick Start

### 1. Test the Visualizer (No Music)
```bash
sudo python3 ~/music_visualizer.py
```
This will show LED reactions to ambient sound from the microphone.

### 2. Play Music with LED Sync
```bash
./test_music_sync.sh
```
This plays `test-music.mp3` through the speaker with LED visualization.

### 3. Different Color Schemes
```bash
sudo python3 ~/music_visualizer.py --scheme rainbow
sudo python3 ~/music_visualizer.py --scheme fire
sudo python3 ~/music_visualizer.py --scheme ocean
sudo python3 ~/music_visualizer.py --scheme moneo    # Default purple theme
```

## How It Works

### Frequency Analysis
The visualizer splits audio into 8-10 frequency bands:
1. **Sub-bass** (20-100 Hz) - LED 0 - Deep bass
2. **Bass** (100-250 Hz) - LED 1 - Kick drum
3. **Low-mid** (250-500 Hz) - LED 2 - Bass guitar
4. **Mid** (500-1000 Hz) - LED 3 - Vocals
5. **High-mid** (1000-2000 Hz) - LED 4 - Vocals/guitar
6. **Presence** (2000-4000 Hz) - LED 5 - Clarity
7. **Brilliance** (4000-8000 Hz) - LED 6 - Cymbals
8. **Air** (8000-16000 Hz) - LED 7 - High harmonics

Each LED responds to its frequency band with:
- **Brightness** - Volume level in that band
- **Color** - Preset color scheme
- **Smoothing** - Prevents flickering

### Audio Source Options

**Option 1: Microphone Input (Current)**
- Uses ReSpeaker microphone
- Picks up played music + ambient sound
- No additional wiring needed

**Option 2: Loopback (Future Enhancement)**
- Monitor speaker output directly
- More accurate sync
- Requires ALSA loopback configuration

## Configuration

Edit `~/music_visualizer.py` to adjust:

```python
LED_COUNT = 10          # Number of LEDs
LED_BRIGHTNESS = 255    # 0-255 brightness
SMOOTHING = 0.7         # 0-1 (higher = smoother)
GAIN = 3.0              # Sensitivity multiplier
```

## Troubleshooting

### LEDs Not Lighting
1. Check wiring (GPIO12, 5V, GND)
2. Run with sudo: `sudo python3 ~/music_visualizer.py`
3. Check LED strip is WS2812B/NeoPixel compatible

### No Audio Detection
1. Verify ReSpeaker is connected: `arecord -l`
2. Test microphone: `arecord -d 5 test.wav && aplay test.wav`
3. Check audio device index: `python3 ~/music_visualizer.py --device 0`

### LEDs Too Dim/Bright
- Adjust `GAIN` in the script (higher = brighter)
- Adjust `LED_BRIGHTNESS` (0-255)

### LEDs Too Flickery
- Increase `SMOOTHING` value (0-1)

## Integration with Ferrofluid

To sync both ferrofluid patterns AND LEDs:

1. Run ferrofluid control script
2. Run LED visualizer in background
3. Play audio through speaker

Both systems will react to the same audio source!

## Audio Settings Reference

Your working audio configuration is in `~/audio_settings_working.txt`.

Key settings:
- **Playback Volume:** 255/255 (max)
- **Speaker Volume:** 96/96
- **Capture Volume:** 63/63 (for microphone)

## Next Steps

1. **Test current setup** - Run visualizer, verify LEDs react to sound
2. **Calibrate sensitivity** - Adjust GAIN for your music volume
3. **Choose color scheme** - Pick your favorite theme
4. **Integrate with ferrofluid** - Sync both visual systems
5. **Build enclosure** - House LEDs around ferrofluid display

---

**Created:** 2026-01-21
**For:** Moneo Voice Nexus (Oracle Project - Ferrofluid Interface)
**Hardware:** Raspberry Pi + ReSpeaker + WS2812B LED Strip
