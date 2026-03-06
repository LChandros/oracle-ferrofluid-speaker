# Oracle Audio Fix - CRITICAL

## Problem
WM8960 soundcard Headphone volume gets reset to 0 (muted) on reboot, causing no audio output even though Spotify is playing.

## Root Cause
The WM8960 chip has separate Headphone and Speaker volume controls. Both need to be set to maximum for audio output.

## Solution Applied (2026-03-06)

### 1. Set volumes to maximum:
```bash
amixer -c 4 sset 'Headphone' 127
amixer -c 4 sset 'Speaker' 127
sudo alsactl store
```

### 2. Removed broken ALSA config:
- Deleted /etc/asound.conf (was trying to use tee plugin incorrectly)
- System now uses direct hardware access

### 3. Verified volume settings:
```bash
amixer -c 4 sget Headphone
amixer -c 4 sget Speaker
# Both should show: Playback 127 [100%] [6.00dB]
```

## Auto-Fix Script
Created: /home/tyahn/oracle-fix-audio.sh
Run this if audio stops working after reboot.

## Verification
Check that audio is flowing:
```bash
cat /proc/asound/card4/pcm0p/sub0/status
# Should show: state: RUNNING (when Spotify is playing)
```

## Date Fixed
2026-03-06 - Trevor's request after multiple support sessions

## Update 2026-03-06 (LED/Magnet Visualization Fix)

### Audio Routing for Visualization:
1. Spotify → Loopback (hw:2,0) via PipeWire
2. Bridge reads from Loopback (hw:2,1) → Plays to Speakers (hw:4,0)
3. Oracle visualization ALSO reads from Loopback (hw:2,1)

### Issue: Multiple readers conflict
The bridge and oracle both read from hw:2,1, causing conflicts.

### Startup Script Created:
-  - Bridges loopback to speakers
- Auto-starts on boot (needs systemd service)

### Manual Start Command:
```bash
# Kill any existing bridge
killall arecord aplay 2>/dev/null

# Start the bridge
arecord -D plughw:2,1 -f S16_LE -c 2 -r 44100 -t raw 2>/dev/null | aplay -D hw:4,0 -f S16_LE -c 2 -r 44100 -t raw 2>/dev/null &
```

### Check if Working:
```bash
# Check speaker audio stream
cat /proc/asound/card4/pcm0p/sub0/status
# Should show: state: RUNNING

# Check oracle visualization
tail -f /tmp/oracle_master.log | grep -E 'MUSIC|bass'
```
