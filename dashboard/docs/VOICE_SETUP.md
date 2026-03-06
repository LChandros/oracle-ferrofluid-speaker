# Oracle Voice Assistant - Setup Guide

## What's New

The Oracle dashboard now has **voice conversation** capability! Talk to Moneo (Claude AI) using the "Talk to Moneo" button.

### Flow:
1. **Click button** → Start recording from browser microphone
2. **Speak** your question
3. **Click again** → Stop recording
4. **Whisper STT** → Transcribes your speech to text
5. **Claude AI** → Generates intelligent response via Moneo Core
6. **ElevenLabs TTS** → Converts response to speech
7. **Visualization** → LEDs + electromagnet pulse to syllables

---

## Setup Required

### 1. Get OpenAI API Key (for Whisper STT)

1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

**Cost:** Whisper is very cheap (~$0.006 per minute of audio)

### 2. Add API Key to Oracle Config

SSH to the Pi and edit the config file:

```bash
ssh tyahn@100.82.131.122
nano /home/tyahn/oracle/dashboard/config.txt
```

Add this line (replace with your actual key):
```
OPENAI_API_KEY=sk-your-key-here
```

Save (Ctrl+O, Enter, Ctrl+X)

### 3. Restart Dashboard

```bash
sudo systemctl restart oracle-dashboard
```

---

## Usage

### Voice Conversation

1. Open dashboard: http://100.82.131.122:5000
2. Scroll to **"Talk to Moneo"** section
3. Select a voice for responses (dropdown)
4. Click **"🎤 Hold to Talk"**
5. Speak your question (e.g., "What's the weather?")
6. Click button again to stop recording
7. Wait for:
   - Transcription (Whisper)
   - Claude thinking (Moneo Core)
   - Response generation (ElevenLabs TTS)
   - Playback with ferrofluid visualization!

### Text-to-Speech (Original)

Still works as before - just type text and click "Speak"

---

## Example Questions

**Calendar/Tasks:**
- "What's on my calendar today?"
- "What are my urgent tasks?"
- "Add a task to buy groceries"

**General:**
- "Tell me a joke"
- "What's the meaning of life?"
- "Explain ferrofluid in simple terms"

**Projects:**
- "What project am I working on?"
- "Tell me about the Oracle project"

---

## Troubleshooting

### "Microphone access denied"

Browser needs permission to access microphone:
- Chrome: Click the 🔒 or 🎥 icon in address bar → Allow microphone
- Firefox: Click the 🎥 icon → Allow
- Safari: Safari → Preferences → Websites → Microphone → Allow

### "OpenAI API key not configured"

Make sure you:
1. Added `OPENAI_API_KEY=...` to `/home/tyahn/oracle/dashboard/config.txt`
2. Restarted the service: `sudo systemctl restart oracle-dashboard`

### "Moneo API error"

Check that Moneo Core is running:
```bash
pm2 status
curl http://localhost:3002/api/voice/status
```

Should show: `{"status":"ready","model":"claude-3-haiku-20240307"}`

### Audio not playing after response

Check headphone volume (this is the known issue):
```bash
sudo amixer -c 3 sset Headphone 127
```

---

## Architecture

```
Browser (Microphone)
   ↓
Oracle Dashboard (Flask)
   ↓
OpenAI Whisper (Speech-to-Text)
   ↓
Moneo Core API (Claude AI)
   ↓
ElevenLabs (Text-to-Speech)
   ↓
Raspberry Pi (LEDs + Electromagnet + Speakers)
```

---

## API Keys Needed

| Service | Purpose | Cost | Link |
|---------|---------|------|------|
| OpenAI | Whisper STT | ~$0.006/min | https://platform.openai.com/api-keys |
| ElevenLabs | TTS voices | Free tier OK | Already configured |
| Anthropic Claude | AI responses | Via Moneo Core | Already configured |

---

## Next Steps

1. **Add OpenAI API key** (see Setup step 2 above)
2. **Test voice conversation** - try asking Moneo a question!
3. **Wait for new electromagnet** - current one is weak, upgrade coming
4. **Future:** Wake word detection ("Hey Moneo") instead of button

---

## Status

- ✅ Voice recording in browser
- ✅ Whisper STT integration
- ✅ Moneo Core (Claude) integration
- ✅ ElevenLabs TTS
- ✅ Syllable-synced visualization
- ✅ Conversation history display
- ⏸️ Stronger electromagnet (ordered, pending)
- ⏸️ Wake word detection (future feature)

**Current Dashboard:** http://100.82.131.122:5000
