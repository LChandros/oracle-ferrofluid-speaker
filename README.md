# Oracle Ferrofluid Speaker

A voice-controlled AI assistant with audio-reactive ferrofluid visualization, built on Raspberry Pi 4B.

## What It Does

- **Voice assistant** via OpenAI Realtime API — say "Jarvis" to start a natural conversation
- **Audio-reactive ferrofluid** — electromagnet pulses to bass frequencies from music and voice
- **Spotify Connect** — plays music as "development-hub" speaker device
- **LED visualization** — 19-LED WS2812B strip reacts to audio frequencies
- **Tool integration** — calendar, email, system diagnostics, reminders via voice

## Architecture

```
             "Jarvis" wake word (Porcupine)
                       │
                       ▼
              OpenAI Realtime API (WebSocket)
                    │
        ┌───────────┼──────────────┐
        ▼           ▼              ▼
   Spotify     Moneo API       Local Tools
   Control     (Claude)        (debug, remind,
                               run_command)
        │           │              │
        ▼           ▼              ▼
        All audio → ALSA Loopback → Speakers
                         │
                    FFT Analysis
                     /        \
              Electromagnet   LED Strip
              (PWM bass)     (freq colors)
```

## Hardware

- Raspberry Pi 4B (Tailscale: 100.82.131.122)
- WM8960 Audio HAT (Card 4) — speakers + mic
- ALSA Loopback (Card 2) — audio routing
- WS2812B LED Strip — 19 LEDs on GPIO12
- Electromagnet + MOSFET — GPIO23, 1kHz PWM
- DROK 5W×2 amplifier → 78mm speakers

## Key Files

| File | Purpose |
|------|---------|
| `oracle_master_service.py` | Main service — wake word, Realtime API, tools, state machine |
| `oracle_realtime.py` | OpenAI Realtime API WebSocket client with echo suppression |
| `oracle_led_states_music.py` | LED + electromagnet controller with FFT visualization |
| `oracle_scheduler.py` | Time-based announcement scheduler |
| `oracle_audio_manager.py` | Audio routing (legacy, replaced by bridge) |
| `oracle-audio-bridge-simple.sh` | Loopback → speaker bridge (arecord \| aplay) |
| `dashboard_app.py` | Web dashboard (Flask, port 3003) |

## Services

```bash
# Core services (auto-start on boot)
oracle-master.service          # Voice + visualization + tools
oracle-audio-bridge.service    # Loopback → speaker bridge
raspotify.service              # Spotify Connect
oracle-scheduler.service       # Announcements
oracle-dashboard.service       # Web UI
oracle-audio-restore.service   # Volume fix on boot
```

## Voice Tools

| Tool | Description |
|------|-------------|
| `moneo_query` | Ask Moneo (Claude) about tasks, calendar, emails, business |
| `create_calendar_event` | Add events to Google Calendar (tyahn96@gmail.com) |
| `send_email` | Send email via Gmail |
| `debug_system` | Check services, audio, logs, disk, network |
| `run_command` | Execute shell commands on the Pi |
| `set_reminder` | Schedule spoken reminders |
| `spotify_play` | Start Spotify (search/play via API coming soon) |
| `spotify_control` | Pause/resume Spotify |

## Echo Suppression

The speaker and mic are on the same board (WM8960 HAT). Echo is handled by:

1. Killing the mic arecord subprocess when Oracle starts speaking
2. Flushing the audio send queue
3. Sending `input_audio_buffer.clear` to the Realtime API
4. Waiting 2s for speaker buffer to drain
5. Restarting mic arecord after drain
6. Only draining after audio responses (not tool-call-only responses)

## Audio-Reactive Visualization

- FFT analysis on all audio through the loopback
- Sub-bass (20-80Hz) primary driver, mid-bass (80-250Hz) accent
- Adaptive peak normalization (auto-adjusts to volume)
- Beat detection (40% above average = beat trigger)
- 35% baseline PWM hold keeps ferrofluid elevated
- LED colors mapped to frequency bands (bass=red, mid=green, high=blue)

## Setup

Requires: Raspberry Pi OS, Python 3, WM8960 HAT driver, Raspotify, ALSA loopback module.

```bash
# Install on Pi
sudo modprobe snd-aloop  # ALSA loopback
pip3 install pvporcupine openai piper-tts alsaaudio rpi_ws281x RPi.GPIO numpy websockets requests

# Copy files to /home/tyahn/
# Copy systemd services to /etc/systemd/system/
# Copy asound.conf to /etc/asound.conf
sudo systemctl daemon-reload
sudo systemctl enable oracle-master oracle-audio-bridge oracle-scheduler oracle-dashboard oracle-audio-restore raspotify
sudo systemctl start oracle-master oracle-audio-bridge raspotify
```

## Dependencies

- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime) — voice conversation
- [Porcupine](https://picovoice.ai/platform/porcupine/) — wake word detection
- [Raspotify](https://github.com/dtcooper/raspotify) — Spotify Connect
- [Moneo](https://github.com/tyahn/moneo) — personal AI assistant (tasks, calendar, email)
- [Piper TTS](https://github.com/rhasspy/piper) — local text-to-speech (legacy, replaced by Realtime API)

## Built By

Trevor Yahn — Pittsburgh, PA — March 2026
