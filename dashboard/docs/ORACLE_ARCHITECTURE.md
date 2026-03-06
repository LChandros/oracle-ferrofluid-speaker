# Oracle Ferrofluid Speaker - Complete System Architecture

**Project:** Moneo Voice Interface (Oracle Project)  
**Status:** Architecture Complete - Ready for Implementation  
**Date:** 2026-01-21

---

## Executive Summary

Oracle is a voice-activated ferrofluid speaker that provides a direct interface to Moneo (Claude AI assistant) with:
- **Push-to-talk activation** via physical button
- **Full Moneo context** (calendar, tasks, projects, emails)
- **Hybrid tool execution** (local file ops + cloud services)
- **Multi-sensory feedback** (voice + LED visualization + ferrofluid patterns)
- **Spotify integration** for music playback

---

## System Components

### 1. Raspberry Pi (development-hub) - Edge Device
**Tailscale IP:** 100.82.131.122

**Hardware:**
- ReSpeaker 2-Mic HAT (audio I/O)
- 10 LED WS2812B strip (GPIO 12, Pin 32)
- Electromagnet (GPIO 23, Pin 16 ⚠️ CRITICAL: NOT GPIO 18!)
- Push button (GPIO 17, Pin 11)

**Software Stack:**
- Python 3.9+
- websockets library
- pyaudio (audio capture/playback)
- rpi_ws281x (LED control)
- RPi.GPIO (button + electromagnet)

**Role:**
- Button detection
- Audio capture/playback
- LED visualization
- Electromagnet control
- Local tool execution

---

### 2. DO Server (moneo.agency) - Processing Brain
**IP:** 159.65.245.152

**Software Stack:**
- Node.js (existing Moneo infrastructure)
- ws (WebSocket server)
- OpenAI Realtime API SDK (speech-to-text)
- Anthropic SDK (Claude/Moneo)
- ElevenLabs SDK (text-to-speech)
- Spotify Web API (future)

**Role:**
- WebSocket server for Oracle
- Speech-to-text processing
- Moneo/Claude conversation
- Text-to-speech generation
- Tool routing and coordination
- Cloud service integrations

---

### 3. Local Machine (/root) - Tool Execution Target
**This server** where file operations occur

**Role:**
- File system operations
- Git commands
- Local script execution
- Data storage

---

## Data Flow - Complete Conversation

### User Request: "Hey Moneo, check Google Scholar and save to /root"

```
1. USER PRESSES BUTTON
   └─> Pi: GPIO interrupt → Start recording
   └─> LEDs: Pulse blue (listening state)
   └─> WebSocket: Send "recording_started" to DO server

2. USER SPEAKS & RELEASES BUTTON
   └─> Pi: Capture audio from ReSpeaker mic
   └─> WebSocket: Stream audio chunks to DO server
   └─> Message: { type: "audio_chunk", audio: <base64>, final: true }

3. DO SERVER: SPEECH-TO-TEXT
   └─> Receive audio stream
   └─> Forward to OpenAI Realtime API
   └─> Get transcription: "check Google Scholar for papers..."

4. DO SERVER: MONEO PROCESSING
   └─> oracle-integration.js receives text
   └─> Call voice-integration.js (existing Moneo)
   └─> Build system prompt with context:
       - Current projects (Oracle, Valentine Maps, AGV, etc.)
       - Today's calendar events
       - Pending tasks from Obsidian
       - Available tools
   └─> Call Claude API with tools enabled

5. CLAUDE RESPONSE
   └─> Decides to use two tools:
       Tool 1: web_search (Google Scholar)
       Tool 2: write_file (/root/research/...)

6. TOOL ROUTING
   └─> Tool Router examines each tool:
       
       web_search → SERVER_TOOL
       └─> Execute on DO server
       └─> Google Scholar API call
       └─> Returns 12 papers
       
       write_file → LOCAL_TOOL
       └─> Send to Oracle Pi via WebSocket
       └─> Message: { 
             type: "tool_request",
             tool: "write_file",
             params: { path: "/root/research/...", content: "..." }
           }

7. LOCAL TOOL EXECUTION
   └─> Oracle Pi receives tool_request
   └─> Execute: mkdir -p /root/research
   └─> Execute: write file with paper list
   └─> Send result back:
       { type: "tool_result", success: true }

8. FINAL RESPONSE GENERATION
   └─> DO server compiles tool results
   └─> Call Claude again with results
   └─> Claude: "I found 12 papers... saved to /root/research/..."

9. TEXT-TO-SPEECH
   └─> Send text to ElevenLabs API
   └─> Get audio stream (streaming mode)

10. AUDIO PLAYBACK
    └─> DO server streams audio to Pi via WebSocket
    └─> Pi plays through speaker (plughw:3,0)
    └─> LEDs auto-level to audio volume (rainbow pulsing)
    └─> User hears Moneo's voice response

11. COMPLETION
    └─> LEDs fade to idle (dim rainbow glow)
    └─> Ready for next button press
```

---

## WebSocket Protocol

### Connection
```
wss://moneo.agency/oracle
Authorization: Bearer oracle-secret-key-123
```

### Message Types: Pi → Server

**recording_started**
```json
{
  "type": "recording_started",
  "session_id": "oracle-session-123",
  "timestamp": 1737496000000
}
```

**audio_chunk**
```json
{
  "type": "audio_chunk",
  "session_id": "oracle-session-123",
  "audio": "<base64 PCM>",
  "sample_rate": 16000,
  "channels": 1,
  "final": false
}
```

**tool_result**
```json
{
  "type": "tool_result",
  "tool_id": "tool_2",
  "success": true,
  "result": "File written successfully"
}
```

### Message Types: Server → Pi

**audio_response**
```json
{
  "type": "audio_response",
  "session_id": "oracle-session-123",
  "audio": "<base64 audio>",
  "format": "pcm",
  "sample_rate": 48000,
  "final": false
}
```

**tool_request**
```json
{
  "type": "tool_request",
  "tool_id": "tool_2",
  "tool": "write_file",
  "params": {
    "path": "/root/research/papers.md",
    "content": "# Research Papers\n\n..."
  }
}
```

**led_control**
```json
{
  "type": "led_control",
  "mode": "listening" | "thinking" | "speaking" | "idle",
  "color": "#8B00FF"
}
```

---

## Tool Categories

### LOCAL_TOOLS (Execute on Pi/Local Machine)
```javascript
[
  'write_file',       // File operations
  'read_file',
  'list_directory',
  'bash_command',     // Shell commands
  'git_ops',          // Git operations
  'gpio_control',     // Hardware (LED/magnet)
  'system_info'       // Local system info
]
```

### SERVER_TOOLS (Execute on DO Server)
```javascript
[
  'web_search',       // Web searches (Google Scholar, etc.)
  'send_email',       // Gmail operations
  'calendar_ops',     // Google Calendar
  'database_query',   // Database access
  'api_call',         // External APIs
  'shopify_ops',      // Clam store operations
  'quickbooks_ops',   // Invoice automation
  'spotify_ops'       // Spotify control (future)
]
```

---

## File Structure

### Raspberry Pi: /home/tyahn/oracle/
```
oracle/
├── oracle_main.py              # Main orchestrator
├── button_handler.py            # GPIO button detection
├── audio_handler.py             # Mic/speaker control
├── websocket_client.py          # WebSocket to DO server
├── led_controller.py            # LED auto-leveling visualizer
├── magnet_controller.py         # Ferrofluid patterns
├── local_tool_executor.py       # Execute local tools
├── config.yaml                  # Configuration
└── requirements.txt             # Dependencies
```

### DO Server: /root/moneo/
```
moneo/
├── core/
│   ├── moneo-core.js                         # MODIFY: Add Oracle module
│   └── modules/
│       ├── oracle-integration.js             # NEW: WebSocket server
│       ├── voice-integration.js              # EXISTING: Use as-is
│       ├── tool-router.js                    # NEW: Route LOCAL vs SERVER tools
│       └── spotify-manager.js                # NEW: Spotify (Phase 2)
├── package.json                              # Add: ws, openai, elevenlabs
└── .env                                      # Add API keys
```

---

## Configuration

### Pi: ~/oracle/config.yaml
```yaml
oracle:
  name: "Oracle Ferrofluid Speaker"
  server_url: "wss://moneo.agency/oracle"
  api_key: "oracle-secret-key-123"
  
button:
  gpio_pin: 17              # Physical Pin 11
  bounce_time: 300          # Debounce ms
  
audio:
  input_device: 1           # ReSpeaker
  output_device: "plughw:3,0"
  sample_rate: 16000
  chunk_size: 1024
  
led:
  count: 10
  gpio_pin: 12              # Physical Pin 32
  auto_level: true
  idle_brightness: 0.1
  
magnet:
  gpio_pin: 21              # Physical Pin 40
  enabled: false            # Enable in Phase 3
  pwm_frequency: 1000
```

### DO Server: /root/moneo/.env
```bash
# Existing
ANTHROPIC_API_KEY=sk-ant-xxx

# New for Oracle
OPENAI_API_KEY=sk-xxx                    # Realtime API
ELEVENLABS_API_KEY=xxx                   # TTS
ORACLE_WEBSOCKET_PORT=3003
ORACLE_API_KEY=oracle-secret-key-123

# Future (Phase 2)
SPOTIFY_CLIENT_ID=xxx
SPOTIFY_CLIENT_SECRET=xxx
```

---

## Implementation Phases

### Phase 1: Basic Voice Assistant (Week 1) ✅ PRIORITY
**Goal:** "Press button, ask question, get Moneo response"

Tasks:
- [ ] Create button handler on Pi (GPIO 17)
- [ ] Create WebSocket server on DO server (port 3003)
- [ ] Integrate OpenAI Realtime API (STT)
- [ ] Connect to existing voice-integration.js
- [ ] Integrate ElevenLabs TTS
- [ ] Audio playback on Pi
- [ ] LED visualization during speech

**Deliverable:** Full conversation works end-to-end

---

### Phase 2: Spotify Integration (Week 2)
**Goal:** "Hey Moneo, play Spotify"

Tasks:
- [ ] Spotify Web API authentication
- [ ] librespot setup on DO server
- [ ] Audio streaming to Pi
- [ ] Voice commands (play, pause, skip, volume)
- [ ] LED reaction to music (already working!)

**Deliverable:** Music playback through Oracle speaker

---

### Phase 3: Ferrofluid Integration (Week 3) ⚠️ CURRENT FOCUS
**Goal:** Electromagnet dances to audio without breaking speakers

Tasks:
- [ ] Test electromagnet isolation (separate power supply?)
- [ ] Audio-reactive patterns
- [ ] Synchronize LED + magnet + audio
- [ ] Emotion-based states (calm, excited, urgent)

**Deliverable:** Full audio-visual ferrofluid experience

---

### Phase 4: Tool Execution (Week 4)
**Goal:** Moneo can execute complex multi-tool tasks

Tasks:
- [ ] Implement tool-router.js (LOCAL vs SERVER)
- [ ] Local tool executor on Pi
- [ ] File operations (write, read, list)
- [ ] Bash command execution
- [ ] Git operations
- [ ] Web search tools

**Deliverable:** "Check Google Scholar and save to /root" works

---

### Phase 5: Polish & Optimization (Week 5)
Tasks:
- [ ] Reduce latency (<500ms perceived)
- [ ] Error handling and recovery
- [ ] Conversation history persistence
- [ ] Desktop failover setup
- [ ] Wake word option (optional upgrade)

---

## Hardware Wiring

### Current Setup (Working)
```
ReSpeaker 2-Mic HAT:
├─ Microphone input (Device 1)
└─ Speaker output (plughw:3,0)

LED Strip (10 LEDs):
├─ Data → GPIO 12 (Pin 32)
├─ Power → 5V
└─ Ground → GND
```

### To Add
```
Push Button:
├─ One leg → GPIO 17 (Pin 11)
└─ Other leg → GND
   (Use internal pull-up resistor in software)

Electromagnet (⚠️ Needs isolation testing):
├─ Signal → GPIO 21 (Pin 40)
├─ Power → External 12V supply (NOT Pi 5V!)
└─ Ground → Common ground (isolated from audio?)
   (May need transistor/MOSFET driver)
```

---

## Latency Budget

| Component | Time | Notes |
|-----------|------|-------|
| Button press | 0ms | Instant |
| Audio capture (1s) | 1000ms | User speech duration |
| WebSocket transmission | 20ms | Pi → DO server |
| Speech-to-text | 100ms | OpenAI Realtime (streaming) |
| Moneo/Claude processing | 200ms | Claude API |
| Text-to-speech | 300ms | ElevenLabs (streaming) |
| Audio playback start | 50ms | First chunk |
| **Total** | **1670ms** | **Acceptable** |

**Optimization:** Stream TTS as generated → perceived latency ~700ms

---

## API Costs (Estimated)

### Per Conversation (30 seconds)
- OpenAI Realtime STT: $0.03
- Claude API: $0.01
- ElevenLabs TTS: $0.02
- **Total:** ~$0.06/conversation

### Monthly Usage
- Light (30 min/day): ~$3.60/month
- Heavy (2 hrs/day): ~$14.40/month

---

## Security Considerations

1. **WebSocket Authentication**
   - API key required for connection
   - Session-based authentication
   - Rate limiting on DO server

2. **Local Tool Execution**
   - Whitelist allowed paths
   - Sanitize bash commands
   - No sudo/root access via tools

3. **Network**
   - Use WSS (encrypted WebSocket)
   - Tailscale for Pi connectivity
   - Firewall rules on DO server

---

## Known Issues & Solutions

### Issue 1: Audio/Electromagnet Interference
**Problem:** Electromagnet PWM may cause audio noise  
**Solution:** 
- Use separate power supply for electromagnet
- Add ground loop isolator
- Test electromagnet on/off during audio playback
- May need optical isolation

### Issue 2: WebSocket Reconnection
**Problem:** Connection drops  
**Solution:**
- Implement exponential backoff
- Queue messages during disconnect
- Heartbeat/ping mechanism

### Issue 3: Latency Spikes
**Problem:** Slow Claude responses  
**Solution:**
- Cache common responses
- Use Haiku for simple queries
- Stream TTS early

---

## Testing Plan

### Unit Tests
- [ ] Button detection (GPIO)
- [ ] Audio capture/playback
- [ ] LED visualization
- [ ] WebSocket message parsing
- [ ] Tool router logic

### Integration Tests
- [ ] End-to-end conversation
- [ ] Tool execution flow
- [ ] Error recovery
- [ ] Multi-turn conversations

### Stress Tests
- [ ] Long conversations (>5 minutes)
- [ ] Rapid button presses
- [ ] Network interruption
- [ ] Server restart

---

## Next Immediate Steps

1. **Test Electromagnet** (⚠️ CURRENT)
   - Wire electromagnet to GPIO 21
   - Test PWM control
   - Play audio simultaneously
   - Check for interference

2. **Create Button Handler**
   - Wire button to GPIO 17
   - Test press/release detection
   - Add debouncing

3. **Start WebSocket Server**
   - Create oracle-integration.js
   - Basic echo server first
   - Add authentication

---

**Last Updated:** 2026-01-21  
**Next Review:** After Phase 3 (Electromagnet) complete
