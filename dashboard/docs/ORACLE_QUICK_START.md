# 🎤 ORACLE QUICK START GUIDE

## Hardware Setup (FINAL WORKING CONFIG)

### Power Connections


### GPIO Connections


### MOSFET Wiring (IRF520 Module)


### Electromagnet


## ⚠️ CRITICAL WARNINGS

### DO NOT USE THESE GPIO PINS (Used by ReSpeaker HAT):
- ❌ GPIO 18 (PCM_CLK - audio clock)
- ❌ GPIO 19 (PCM_FS - audio frame sync)
- ❌ GPIO 20 (PCM_DIN - audio data in)
- ❌ GPIO 21 (PCM_DOUT - audio data out)
- ❌ GPIO 2, 3 (I2C)
- ❌ GPIO 10, 11 (SPI for onboard LEDs)
- ❌ GPIO 17 (user button)

### SAFE GPIO PINS (Available for use):
- ✅ GPIO 23, 24, 25
- ✅ GPIO 4, 5, 6
- ✅ GPIO 22, 27
- ⚠️ GPIO 12, 13 (Grove connector - OK if not using Grove)

## Quick Test Commands

### Test Audio Only
```bash
aplay -D plughw:3,0 /home/tyahn/cough.wav
```

### Test Electromagnet Only
```bash
python3 /home/tyahn/test_magnet_gpio23.py
```

### Test Audio + Electromagnet Together
```bash
bash /home/tyahn/test_final.sh
```

### Test LEDs
```bash
sudo python3 /home/tyahn/led_test_simple.py
```

## Audio Troubleshooting

If audio breaks (only pops):

```bash
# Restore mixer settings
amixer -c 3 set Playback 255
amixer -c 3 set Speaker 127
amixer -c 3 set Headphone 127
amixer -c 3 cset numid=16 5  # Speaker AC Volume
amixer -c 3 cset numid=15 5  # Speaker DC Volume
amixer -c 3 cset numid=52 on # Left Output Mixer PCM
amixer -c 3 cset numid=55 on # Right Output Mixer PCM
```

If that doesn't work:
```bash
sudo reboot
```

## Code Template

```python
#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

# GPIO Configuration
MAGNET_PIN = 23  # Physical Pin 16 - CRITICAL: Do not use GPIO 18!
LED_PIN = 12     # Physical Pin 32

GPIO.setmode(GPIO.BCM)
GPIO.setup(MAGNET_PIN, GPIO.OUT)

# Control electromagnet
GPIO.output(MAGNET_PIN, GPIO.HIGH)  # ON
time.sleep(1)
GPIO.output(MAGNET_PIN, GPIO.LOW)   # OFF

GPIO.cleanup()
```

## Next Development Steps

1. ✅ Audio + Electromagnet working
2. ⬜ Audio-reactive electromagnet patterns
3. ⬜ Integrate LED strip synchronization
4. ⬜ Add wake word detection
5. ⬜ Connect to Moneo API
6. ⬜ Build physical enclosure

---
**Last Updated:** 2026-01-22
**Status:** FULLY OPERATIONAL ✅
