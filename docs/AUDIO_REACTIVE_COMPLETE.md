# Oracle Audio-Reactive Visualization - WORKING (March 21, 2026)

## Status: FULLY OPERATIONAL

Audio-reactive ferrofluid and LED visualization is working. The electromagnet and LEDs
respond dynamically to bass frequencies in real-time from Spotify playback.

---

## Architecture

```
Spotify (librespot) --> hw:2,0 (Loopback playback)
                              |
                    ALSA Loopback Device
                              |
                        hw:2,1 (Loopback capture)
                              |
                    oracle_master_service.py
                      [Audio Bridge Thread]
                         /            \
                        v              v
              plughw:4,0 (speakers)   shared deque buffer
                                       |
                                       v
                              oracle_led_states_music.py
                                [_animate_music()]
                                   /         \
                                  v           v
                            FFT Analysis    LED Animation
                            (20-250Hz)     (frequency color mapping)
                                  |
                                  v
                          Electromagnet PWM
                          (GPIO23, 1kHz)
```

### Key Design Decision: In-Process Audio Bridge

Previous approach used a shell script with `arecord | tee FIFO | aplay`. This had a
fatal flaw: when the visualization was not in MUSIC state, nobody read the FIFO, tee
blocked, and the entire audio chain stalled.

**Fix:** Moved the audio bridge into the master service Python process. One thread
captures from loopback, writes to speakers via alsaaudio, and feeds a shared
`collections.deque` buffer. The LED controller reads from this buffer for FFT analysis.
No FIFO, no tee, no multi-process coordination.

---

## FFT Analysis

- **Sub-bass (20-80Hz):** Primary driver, 70% weight
- **Mid-bass (80-250Hz):** Accent, 30% weight
- **Normalization:** Adaptive peak tracker (tracks loudest recent bass, decays at 0.999/frame)
- **Noise floor:** Bass levels below 5% are zeroed out
- **Beat detection:** 40% above recent average = beat, triggers 30% PWM boost
- **Smoothing:** 0.15 normal, 0.05 during beats (snappy response)

---

## Services

### Active
- `oracle-master.service` - Main service (voice + visualization + audio bridge)
- `raspotify.service` - Spotify Connect (outputs to loopback hw:2,0)
- `oracle-scheduler.service` - Scheduled announcements
- `oracle-dashboard.service` - Web dashboard
- `oracle-audio-restore.service` - Volume restore on boot

### Disabled (replaced by in-process bridge)
- `oracle-audio-bridge.service` - OLD tee/FIFO bridge (disabled March 21, 2026)
- `oracle-audio-manager.service` - OLD Python bridge attempt (was already disabled)

---

## Files Modified (March 21, 2026)

### oracle_led_states_music.py
- `_animate_music()` rewritten to read from shared `self.audio_buffer` deque
- Falls back to direct ALSA capture if buffer not available
- Adaptive peak normalization replaces fixed divisor (was /50, caused 100% saturation)
- Noise floor at 5% prevents residual magnet engagement on silence
- Beat boost reduced from 1.8x to 1.3x

### oracle_master_service.py
- Added `audio_bridge_loop()` method - captures from plughw:2,1, plays to plughw:4,0
- Shared `deque(maxlen=30)` buffer connects bridge to visualization
- Bridge pauses speaker playback during voice interactions (frees device for TTS)
- Sets WM8960 volumes on startup (Headphone=127, Speaker=127, Playback=255)
- Bridge thread started alongside Spotify monitor, wake word, and FIFO reader threads

---

## Backups

- `oracle_led_states_music.py.backup_20260321`
- `oracle_master_service.py.backup_20260321`

---

## Testing

### Quick verification
```bash
# Check services
ssh devhub "systemctl status oracle-master raspotify"

# Watch bass levels live
ssh devhub "sudo journalctl -u oracle-master -f" | grep AUDIO

# Test with sine wave (no Spotify needed)
ssh devhub "speaker-test -D hw:2,0 -t sine -f 80 -c 2 -r 44100 -l 1"
```

### Expected log output during music
```
[AUDIO] Frame 200: sub=94242.7 mid=241257.5 bass=0.0% PWM=3.3%
[AUDIO] Frame 400: sub=824804.4 mid=105254.1 bass=18.6% PWM=23.6%
[AUDIO] Frame 600: sub=1559192.6 mid=90294.9 bass=39.8% PWM=40.0%
[AUDIO] Frame 800: sub=0.0 mid=0.0 bass=0.0% PWM=0.0%
```

Bass% and PWM% should vary dynamically with the music. If stuck at 100%, the
normalization is broken. If stuck at 0%, check loopback status:
```bash
ssh devhub "cat /proc/asound/Loopback/pcm0p/sub0/status"
# Should show state: RUNNING when Spotify is playing
```

---

## Spotify Connection

- **Device name:** "development-hub" (default hostname)
- **How to connect:** Open Spotify app -> Devices -> select "development-hub"
- **Note:** Restarting oracle-master kills librespot session; reconnect from Spotify app

---

## What Was Broken Before (and Why)

### Problem 1: FIFO Deadlock (pre-March 21)
The tee-based audio bridge (`oracle-audio-bridge.service`) used a named pipe (FIFO)
to split audio between speakers and visualization. When the system wasn't in MUSIC
state, nobody read the FIFO, tee blocked, and the entire audio pipeline froze.

### Problem 2: FFT Saturation (March 21, first attempt)
The original FFT normalization divided combined bass by 50 to get a percentage.
Real music FFT magnitudes are in the hundreds of thousands to millions, so
everything pegged at 100% PWM constantly. Fixed with adaptive peak tracking.

### Solution
1. Replaced multi-process bridge with in-process Python thread
2. Replaced FIFO with thread-safe deque
3. Replaced fixed normalization with adaptive peak tracker
