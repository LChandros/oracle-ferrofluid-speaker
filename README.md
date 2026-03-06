# Oracle Ferrofluid Speaker System

**A unified voice assistant and music visualization system featuring ferrofluid electromagnet and LED animations.**

---

## System Overview

The Oracle is a Raspberry Pi-based ferrofluid speaker that combines:
- **Voice Assistant** - Wake word activation with Moneo AI integration
- **Music Playback** - Spotify Connect via Raspotify
- **Visual Effects** - 19-LED WS281x strip and electromagnet with audio-reactive animations
- **Scheduling** - Automated announcements and time-based triggers
- **Web Dashboard** - Status monitoring and control interface

### Hardware Components
- Raspberry Pi (running on devhub via Tailscale)
- WM8960 Audio HAT (Card 4) - Physical speakers
- ALSA Loopback Device (Card 2) - Audio routing and capture
- WS281x LED Strip (19 LEDs) - Visual effects via GPIO
- Electromagnet + MOSFET - Ferrofluid animation via PWM
- Microphone - Wake word detection

---

## Architecture

### Audio Flow (NEW - March 2026)

```
┌─────────────┐
│   Spotify   │ (via Raspotify/librespot)
└──────┬──────┘
       │ outputs to hw:2,0
       ▼
┌─────────────────────┐
│  ALSA Loopback      │
│  hw:2,0 (playback)  │
│  hw:2,1 (capture)   │
└──────┬──────┬───────┘
       │      │
       │      └────────────────┐
       │                       ▼
       │              ┌────────────────────┐
       │              │ LED/Magnet Driver  │
       │              │ (visualization)    │
       │              └────────────────────┘
       ▼
┌──────────────────────┐
│ Oracle Audio Manager │ (Python service)
│  - Captures hw:2,1   │
│  - Plays to hw:4,0   │
│  - Sets WM8960 vols  │
└──────┬───────────────┘
       │
       ▼
┌─────────────┐
│  Speakers   │ (WM8960 hw:4,0)
└─────────────┘
```

**Key Design:**
- All audio sources route through the loopback device
- Audio Manager bridges loopback → speakers
- LED/magnet visualization captures same audio stream
- WM8960 volumes are set automatically on startup

---

## System Components

### 1. Oracle Audio Manager (`oracle_audio_manager.py`)
**Purpose:** Unified audio routing service that solves the WM8960 mute-on-boot issue and enables visualization

**What it does:**
- Sets WM8960 volumes (Headphone, Speaker, Playback) on startup
- Bridges audio from loopback (hw:2,1) to physical speakers (hw:4,0)
- Monitors and auto-restarts the audio bridge if it fails
- Allows all audio sources to be visualized via loopback capture

**Systemd Service:** `oracle-audio-manager.service`
- Auto-starts on boot
- Runs before `oracle-master` and `raspotify`
- Restarts on failure

### 2. Oracle Master Service (`oracle_master_service.py`)
**Purpose:** Main coordinator for voice assistant and music detection

**Features:**
- Wake word detection ("jarvis" via Porcupine)
- Voice transcription and Moneo API integration
- Spotify music detection (monitors librespot process)
- State management (IDLE, LISTENING, THINKING, SPEAKING, MUSIC)
- LED controller integration

**Systemd Service:** `oracle-master.service`

### 3. LED & Magnet Controller (`oracle_led_states_music.py`)
**Purpose:** Audio-reactive visualization controller

**Features:**
- 19-LED WS281x strip animations
- Electromagnet PWM control
- Bass-reactive (20-250Hz) with beat detection
- Real-time FFT audio analysis from loopback capture (hw:2,1)

**Note:** Integrated with oracle_master_service, not a standalone service

### 4. Oracle Scheduler (`oracle_scheduler.py`)
**Purpose:** Time-based announcements and automated triggers

**Systemd Service:** `oracle-scheduler.service`

### 5. Web Dashboard (`oracle/dashboard/app.py`)
**Purpose:** Web-based status monitoring and control

**Access:** http://100.125.234.114:3003 (when running)

**Systemd Service:** `oracle-dashboard.service`

---

## Quick Start Guide

### Check System Status
```bash
ssh devhub "systemctl status oracle-master oracle-audio-manager raspotify"
```

### Start/Stop Services
```bash
# Start all Oracle services
ssh devhub "sudo systemctl start oracle-audio-manager oracle-master oracle-scheduler"

# Stop all Oracle services
ssh devhub "sudo systemctl stop oracle-master oracle-scheduler oracle-audio-manager"

# Restart Spotify
ssh devhub "sudo systemctl restart raspotify"
```

### View Logs
```bash
# Audio manager logs
ssh devhub "sudo journalctl -u oracle-audio-manager -f"

# Master service logs
ssh devhub "sudo journalctl -u oracle-master -f"

# Raspotify logs
ssh devhub "sudo journalctl -u raspotify -f"
```

---

## Troubleshooting

### No Audio from Speakers

**Symptom:** Spotify connects but no sound plays

**Solution 1 - Quick Fix:**
```bash
ssh devhub "/home/tyahn/oracle-fix-audio.sh"
```

**Solution 2 - Check Audio Manager:**
```bash
# Verify audio manager is running
ssh devhub "systemctl status oracle-audio-manager"

# Check audio bridge processes
ssh devhub "ps aux | grep -E 'arecord|aplay' | grep -v grep"

# Restart audio manager
ssh devhub "sudo systemctl restart oracle-audio-manager"
```

**Solution 3 - Manual Volume Fix:**
```bash
ssh devhub "amixer -c 4 sset 'Headphone' 127"
ssh devhub "amixer -c 4 sset 'Speaker' 127"
ssh devhub "amixer -c 4 sset 'Playback' 255"
```

### Spotify Won't Connect

**Symptom:** Spotify device not appearing or connection fails

**Check Raspotify:**
```bash
ssh devhub "systemctl status raspotify"
ssh devhub "sudo journalctl -u raspotify -n 50"
```

**Verify Device Configuration:**
```bash
ssh devhub "ps aux | grep librespot"
# Should show: /usr/bin/librespot --device hw:2,0
```

**Restart Raspotify:**
```bash
ssh devhub "sudo systemctl restart raspotify"
```

### LEDs/Magnet Not Animating

**Symptom:** Music plays but no visual effects

**Check Audio Flow:**
```bash
# Verify loopback has audio
ssh devhub "timeout 3 arecord -D hw:2,1 -f S16_LE -c 2 -r 44100 /tmp/test.wav && ls -lh /tmp/test.wav"
# File should be > 0 bytes if audio is flowing
```

**Check Master Service:**
```bash
ssh devhub "systemctl status oracle-master"
ssh devhub "sudo journalctl -u oracle-master -n 100"
```

### Service Won't Start

**Check Dependencies:**
```bash
ssh devhub "systemctl list-dependencies oracle-master"
```

**Reset Services:**
```bash
ssh devhub "sudo systemctl daemon-reload"
ssh devhub "sudo systemctl restart oracle-audio-manager"
ssh devhub "sudo systemctl restart oracle-master"
```

---

## Configuration Files

### Systemd Services
- `/etc/systemd/system/oracle-audio-manager.service` - Audio routing service
- `/etc/systemd/system/oracle-master.service` - Main voice assistant
- `/etc/systemd/system/oracle-scheduler.service` - Announcement scheduler
- `/etc/systemd/system/oracle-dashboard.service` - Web dashboard
- `/etc/systemd/system/raspotify.service.d/audio-device.conf` - Spotify device override
- `/etc/systemd/system/raspotify.service.d/override.conf` - Security settings

### Scripts
- `/home/tyahn/oracle-fix-audio.sh` - Quick audio volume fix
- `/home/tyahn/oracle-restart.sh` - Service restart utility
- `/home/tyahn/ORACLE_AUDIO_FIX.md` - Audio troubleshooting documentation

### Archives
- `/home/tyahn/oracle-archive/old-versions/` - Deprecated Python files
- `/home/tyahn/oracle-archive/test-scripts/` - Old test scripts

---

## Audio Devices Reference

### Sound Cards
```bash
# List all audio devices
ssh devhub "aplay -l"
```

**Card 2: Loopback**
- `hw:2,0` / `plughw:2,0` - Playback (write audio here)
- `hw:2,1` / `plughw:2,1` - Capture (read audio from here)

**Card 4: WM8960**
- `hw:4,0` / `plughw:4,0` - Physical speakers
- Requires volume settings: Headphone, Speaker, Playback

### ALSA Mixer Commands
```bash
# View all WM8960 controls
ssh devhub "amixer -c 4"

# Set specific volume
ssh devhub "amixer -c 4 sset 'Headphone' 127"

# Save settings (requires sudo)
ssh devhub "sudo alsactl store"
```

---

## Development Notes

### Adding New Audio Sources

To add a new audio source (e.g., Qwen TTS, ElevenLabs):

1. **Configure audio output to loopback:**
   ```python
   # In your audio playback code, use:
   device = 'plughw:2,0'  # Loopback playback
   ```

2. **Audio will automatically:**
   - Play through speakers (via audio manager)
   - Trigger LED/magnet visualization
   - Be available for recording/analysis

### Service Dependencies

The startup order is critical:
```
1. sound.target, alsa-restore.service
2. oracle-audio-manager.service  (sets volumes, starts bridge)
3. raspotify.service, oracle-master.service  (use audio system)
4. oracle-scheduler.service, oracle-dashboard.service
```

### Debugging Audio Issues

**Check loopback status:**
```bash
ssh devhub "cat /proc/asound/Loopback/pcm0p/sub0/hw_params"
ssh devhub "cat /proc/asound/Loopback/pcm0c/sub0/hw_params"
```

**Monitor audio bridge:**
```bash
ssh devhub "ps aux | grep -E 'python3.*oracle_audio_manager'"
# Should show parent Python process and child arecord/aplay processes
```

**Test audio path manually:**
```bash
# Generate tone to loopback
ssh devhub "speaker-test -t sine -f 440 -c 2 -r 44100 -D hw:2,0" &
# Should hear 440Hz tone from speakers
```

---

## Changelog

### March 6, 2026 - Audio Architecture Refactor
- **Created:** `oracle_audio_manager.py` - Unified audio routing service
- **Fixed:** WM8960 volume reset issue (now automatically set on boot)
- **Improved:** Audio flow - all sources now route through loopback for visualization
- **Configured:** Raspotify to output to loopback device (hw:2,0)
- **Archived:** 15+ deprecated scripts and old versions
- **Added:** This comprehensive documentation

### Previous Architecture Issues (Resolved)
- ❌ Audio volumes reset to 0 on reboot → ✅ Fixed by audio manager
- ❌ Spotify played directly to speakers (no visualization) → ✅ Fixed by loopback routing
- ❌ Fragmented codebase with 20+ oracle*.py files → ✅ Cleaned up and archived
- ❌ No unified audio management → ✅ Created oracle_audio_manager service

---

## Contact & Support

**System Owner:** Trevor Yahn
**Location:** Pittsburgh, PA (EST/EDT)
**Access:** SSH via Tailscale - `ssh devhub` or `ssh tyahn@100.125.234.114`

For issues or questions, check the troubleshooting section first, then review logs with `journalctl`.
