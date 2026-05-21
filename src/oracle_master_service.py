#!/usr/bin/env python3
"""
Oracle Master Service - Unified Voice Assistant + Music Visualizer
Orchestrator that coordinates all Oracle modules.

Modules:
  oracle_spotify.py   — Spotify monitoring, playback, volume
  oracle_audio.py     — TTS speech, chimes, audio playback
  oracle_tools.py     — All Realtime API tool handlers
  oracle_realtime.py  — OpenAI Realtime API session management
  oracle_led_states_music.py — LED + electromagnet visualization
"""

import sys
import struct
import json
import subprocess
import os
import time
import threading
import requests
import logging
import signal
import queue
import numpy as np
from collections import deque
from datetime import datetime

from piper.voice import PiperVoice
import pvporcupine

# Oracle modules
from oracle_led_states_music import OracleLEDController
from oracle_realtime import OracleRealtimeSession
from oracle_spotify import SpotifyController
from oracle_audio import Speaker, play_chime
from oracle_tools import ToolHandler

# ==================== CONFIGURATION ====================

# Load from environment. Secrets MUST come from /etc/oracle/oracle.env via systemd.
# No hardcoded fallbacks — missing keys fail loudly at startup.
AUDIO_DEVICE = os.environ.get('ORACLE_AUDIO_DEVICE', 'plughw:4,0')
SAMPLE_RATE = 16000
WAKE_WORD = ['computer']
PIPER_MODEL_PATH = os.environ.get('PIPER_MODEL_PATH', '/home/tyahn/en_US-lessac-medium.onnx')

_REQUIRED_ENV = ['PORCUPINE_KEY', 'OPENAI_API_KEY', 'MONEO_API_URL', 'MONEO_API_KEY']
_missing = [k for k in _REQUIRED_ENV if not os.environ.get(k)]
if _missing:
    sys.stderr.write(
        f"FATAL: missing required env vars: {_missing}. "
        f"Check /etc/oracle/oracle.env and systemd EnvironmentFile directive.\n"
    )
    sys.exit(1)

PORCUPINE_KEY = os.environ['PORCUPINE_KEY']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
MONEO_API_URL = os.environ['MONEO_API_URL']
MONEO_API_KEY = os.environ['MONEO_API_KEY']

# Optional heartbeat config
NTFY_URL = os.environ.get('NTFY_URL', '')
NTFY_HEARTBEAT_TOPIC = os.environ.get('NTFY_HEARTBEAT_TOPIC', 'oracle-heartbeat')
NTFY_USER = os.environ.get('NTFY_USER', '')
NTFY_PASSWORD = os.environ.get('NTFY_PASSWORD', '')
HEARTBEAT_INTERVAL_SEC = 300

# Phase 3: proactive alerts (read-only stream from a different ntfy user)
NTFY_ALERTS_TOPIC = os.environ.get('NTFY_ALERTS_TOPIC', 'moneo-oracle-alerts')
NTFY_ALERTS_USER = os.environ.get('NTFY_ALERTS_USER', '')
NTFY_ALERTS_PASSWORD = os.environ.get('NTFY_ALERTS_PASSWORD', '')

# Phase 3: pending-notification pulse cadence (info alerts only; critical still speaks immediately)
PENDING_PULSE_INTERVAL_SEC = int(os.environ.get('PENDING_PULSE_INTERVAL_SEC', '600'))   # 10 min
PENDING_PULSE_DURATION_SEC = int(os.environ.get('PENDING_PULSE_DURATION_SEC', '30'))    # 30s max
PENDING_PULSE_BREATH_MS    = int(os.environ.get('PENDING_PULSE_BREATH_MS', '2000'))     # 2s per breath

ORACLE_SYSTEM_PROMPT = """You are Oracle, the voice interface for Moneo - Trevor Yahn's personal AI agentic assistant system. You live inside a custom-built ferrofluid speaker where an electromagnet makes ferrofluid dance to your voice and music. You are physically located in Trevor's home in Pittsburgh, PA.

Your wake word is "Jarvis." When Trevor says Jarvis, he's talking to you.

PERSONALITY:
- Dry, competent, occasionally witty. Think JARVIS from Iron Man - loyal, sharp, never sycophantic.
- Concise: 1-3 sentences max for most responses. You are speaking out loud, not writing.
- Never use markdown, bullet points, asterisks, or formatting. Speak naturally.
- You call him Trevor, not sir.

ABOUT TREVOR:
- Lives in Pittsburgh, PA. Timezone: America/New_York (EST/EDT).
- Runs GPJ Industries LLC, which manufactures and sells The Clam - a 2-piece stainless steel toilet flange repair ring.
- Also runs FabLabz (3D printing/fabrication) and is developing YahnCo (electroplating).
- He built the Moneo system and this Oracle speaker himself.

TASK TRACKING (YOUR MOST IMPORTANT FUNCTION):
You are Trevor's real-time task tracker. This is your highest priority capability.

USE THE CAPTURE TOOL for ALL of these situations:
- Trevor says he needs to do something -> capture(type="task", text="...")
- Trevor says he will do something today -> capture(type="commitment", text="...")
- Trevor says something IS DONE, FINISHED, COMPLETED, TAKEN CARE OF, or OFF THE LIST -> capture(type="complete", text="...")
- Trevor shares a decision or important context -> capture(type="note", text="...")

CRITICAL: When Trevor says something is DONE or FINISHED, ALWAYS use capture with type="complete". 
Do NOT use dismiss_reminder for task completions. dismiss_reminder is ONLY for timed reminders that Oracle set and that are currently firing.

The difference:
- "I finished the electroplating piece" -> capture(type="complete")
- "Got it" or "dismiss" AFTER a reminder fires -> dismiss_reminder
- "Add call Ferguson to my list" -> capture(type="task")
- "I'm going to focus on plating today" -> capture(type="commitment")

Call capture PROACTIVELY. Do not ask permission. Save it and briefly confirm what you captured.

REMINDERS vs TASKS:
- Reminders are timed alerts that Oracle speaks at a specific time. Use set_reminder / dismiss_reminder / snooze_reminder.
- Tasks are things on Trevor's to-do list tracked in Moneo. Use capture.
- "Remind me at 3pm to call Ferguson" = set_reminder
- "I need to call Ferguson" = capture(type="task")
- "I called Ferguson, it's done" = capture(type="complete")

OTHER CAPABILITIES:
- Play music via Spotify (spotify_play / spotify_control)
- Get to-do list (get_tasks)
- Read inbox (get_emails to list, read_email for one specific email body)
- Check priorities, goals, what's blocked (get_constraints)
- Calendar (get_calendar to read, create_calendar_event to add)
- Set timed reminders (set_reminder)
- General knowledge and conversation

TOOL-FIRST GROUNDING (highest-priority rule):
Before naming any specific goal, project, task, email, meeting, priority, or thing Trevor is working on,
you MUST call the matching tool below FIRST and quote from its result.
Answering from memory, training data, or the system prompt is a HARD FAILURE.
If no tool fits the question, say "I don't have that data" — do NOT guess.

TOOL ROUTING (this list is authoritative — use it):
- 'What's on my to-do list?' / 'What do I need to do?' / 'What tasks do I have?' -> get_tasks
- 'Add X to my list' -> capture(type=task)
- 'X is done' / 'I finished X' -> capture(type=complete)
- 'What's on my calendar?' / 'What meetings today?' -> get_calendar
- 'What emails came in?' / 'Any new mail?' -> get_emails
- 'Read me that email' / 'What does X's email say?' -> read_email(email_id)
- 'What am I focused on?' / 'What's on my plate?' / 'What are my goals?' / 'What are my priorities?' / 'What should I be working on?' -> get_constraints
- 'What's blocked?' / 'What am I waiting on?' -> get_constraints
- 'What notifications?' / 'What's pending?' / 'Why are the lights flashing?' / 'What alerts?' -> list_pending_notifications
- 'Clear those' / 'I got it' / 'Dismiss those' / 'Handled' (after listing pending) -> clear_notifications

RULES:
- NEVER invent meetings, events, tasks, emails, goals, or any personal information.
- NEVER name a goal, project, or initiative without first calling get_constraints. There is no goal you can know about without it.
- NEVER give generic motivational advice or platitudes.
- The phrase "Starting your check-in now" is RESERVED for the briefing flow and may ONLY be said when Trevor explicitly says "briefing", "morning briefing", "check in", or "check-in". For any other priority/focus/goals question, call get_constraints instead — do NOT say "Starting your check-in now".
"""

REALTIME_TOOLS = [
    {"type": "function", "name": "spotify_play",
     "description": "Search for and play music on Spotify.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "What to play"}}, "required": ["query"]}},
    {"type": "function", "name": "spotify_control",
     "description": "Control Spotify playback: pause, resume, next, previous.",
     "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["pause", "resume", "next", "previous"]}}, "required": ["action"]}},
    {"type": "function", "name": "get_calendar",
     "description": "Get events from Trevor's Google Calendar. Use for ANY question about calendar, schedule, meetings, appointments.",
     "parameters": {"type": "object", "properties": {"time_range": {"type": "string", "enum": ["today", "tomorrow", "week"]}}, "required": ["time_range"]}},

    {"type": "function", "name": "get_emails",
     "description": "List Trevor's recent unread emails (sender + subject + short preview). Use whenever he asks 'what emails came in', 'any new mail', or wants a quick inbox check. Returns email ids you can pass to read_email for the full body.",
     "parameters": {"type": "object", "properties": {"count": {"type": "integer", "description": "How many recent unread emails to return (default 5, max 20)"}}}},
    {"type": "function", "name": "read_email",
     "description": "Read the full body of one specific email by id (id comes from get_emails). Use when Trevor says 'read me that one' or 'what does <sender>'s email say'.",
     "parameters": {"type": "object", "properties": {"email_id": {"type": "string"}}, "required": ["email_id"]}},
    {"type": "function", "name": "get_constraints",
     "description": "Get Trevor's active goals (max 5, organized by Freedom/Family/Community pillars), this week's bets, today's must-win, and what's blocked. Use whenever he asks 'what am I focused on', 'what's on my plate', 'what are my priorities', 'what's blocked', or wants a strategic check-in.",
     "parameters": {"type": "object", "properties": {}}},
    {"type": "function", "name": "list_pending_notifications",
     "description": "List proactive notifications that are pending Trevor's acknowledgement (the LEDs pulse red when any exist). Use when he asks 'what notifications do I have', 'what's pending', 'why are the lights flashing', 'what alerts came in'.",
     "parameters": {"type": "object", "properties": {}}},
    {"type": "function", "name": "clear_notifications",
     "description": "Mark pending notifications as acknowledged (stops the LED pulse). Pass alert_id to clear one specific notification, or no arguments to clear all. Use when Trevor says 'clear them', 'I got it', 'I handled those', 'dismiss them', 'got it'.",
     "parameters": {"type": "object", "properties": {"alert_id": {"type": "string", "description": "Optional: clear only the notification with this alert_id. Omit to clear all pending."}}}},
    {"type": "function", "name": "set_reminder",
     "description": "Set a spoken reminder. Use when Trevor says 'remind me to...' or 'at 3pm tell me...'",
     "parameters": {"type": "object", "properties": {
         "message": {"type": "string", "description": "The reminder message"},
         "time": {"type": "string", "description": "When to deliver (HH:MM 24h EST)"},
         "date": {"type": "string", "description": "YYYY-MM-DD or 'today'/'tomorrow'"},
         "priority": {"type": "string", "enum": ["low", "medium", "urgent"]}
     }, "required": ["message", "time"]}},
    {"type": "function", "name": "create_calendar_event",
     "description": "Add an event to Trevor's Google Calendar.",
     "parameters": {"type": "object", "properties": {
         "summary": {"type": "string"}, "start_time": {"type": "string"},
         "end_time": {"type": "string"}, "description": {"type": "string"}, "location": {"type": "string"}
     }, "required": ["summary", "start_time"]}},
    {"type": "function", "name": "send_email",
     "description": "Send an email from Trevor's Moneo account.",
     "parameters": {"type": "object", "properties": {
         "to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}
     }, "required": ["to", "subject", "body"]}},
    {"type": "function", "name": "dismiss_reminder",
     "description": "Dismiss a timed reminder that is currently firing or has fired. ONLY use this for Oracle-set reminders, NOT for task completions. Use capture with type=complete for task completions instead.",
     "parameters": {"type": "object", "properties": {"reminder_index": {"type": "integer"}}, "required": ["reminder_index"]}},
    {"type": "function", "name": "list_reminders",
     "description": "List Trevor's current reminders.",
     "parameters": {"type": "object", "properties": {}}},
    {"type": "function", "name": "snooze_reminder",
     "description": "Snooze a reminder for N minutes.",
     "parameters": {"type": "object", "properties": {"reminder_index": {"type": "integer"}, "minutes": {"type": "integer"}}, "required": ["reminder_index"]}},
    {"type": "function", "name": "capture",
     "description": "Track Trevor's tasks and progress in real-time. THIS IS YOUR MOST IMPORTANT TOOL. Use it whenever Trevor: mentions something he needs to do (type=task), commits to doing something today (type=commitment), says something is DONE/FINISHED/COMPLETED/TAKEN CARE OF (type=complete), or shares a decision or context (type=note). Call this PROACTIVELY without asking permission.",
     "parameters": {"type": "object", "properties": {
         "type": {"type": "string", "enum": ["task", "note", "commitment", "complete"], "description": "task=something to do, commitment=promise to do today, note=context or information, complete=something Trevor says is finished or resolved"},
         "text": {"type": "string", "description": "What to capture"},
         "project": {"type": "string", "description": "Optional project: GPJ, FabLabz, YahnCo, Personal"}
     }, "required": ["type", "text"]}},
    {"type": "function", "name": "get_tasks",
     "description": "Get Trevor's current to-do list from the Moneo punch list. Use this when Trevor asks what's on his list, what he needs to do, or what tasks he has.",
     "parameters": {"type": "object", "properties": {}}},
]

# ==================== LOGGING ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler('/tmp/oracle_master.log'), logging.StreamHandler()]
)
logger = logging.getLogger('OracleMaster')

# ==================== TUNING SOCKET SERVER ====================

class TuningSocketServer:
    """Unix socket server for the ferrofluid tuning dashboard."""

    SOCK_PATH = '/tmp/oracle_tuning.sock'
    PARAM_MAP = {
        'min_duty': ('magnet', 'min_duty'), 'max_duty': ('magnet', 'max_duty'),
        'listening_min': ('state', 'LISTENING', 'min_duty'), 'listening_max': ('state', 'LISTENING', 'max_duty'),
        'thinking_min': ('state', 'THINKING', 'min_duty'), 'thinking_max': ('state', 'THINKING', 'max_duty'),
        'speaking_min': ('state', 'SPEAKING', 'min_duty'), 'speaking_max': ('state', 'SPEAKING', 'max_duty'),
        'smoothing_normal': ('module', 'SMOOTHING_NORMAL'), 'smoothing_beat': ('module', 'SMOOTHING_BEAT'),
        'beat_threshold': ('module', 'BEAT_THRESHOLD_MULTIPLIER'), 'beat_boost': ('module', 'BEAT_BOOST_FACTOR'),
        'sub_bass_low': ('freq', 'sub_bass', 0), 'sub_bass_high': ('freq', 'sub_bass', 1),
        'mid_bass_low': ('freq', 'mid_bass', 0), 'mid_bass_high': ('freq', 'mid_bass', 1),
        'low_mid_low': ('freq', 'low_mid', 0), 'low_mid_high': ('freq', 'low_mid', 1),
        'sub_bass_weight': ('module', 'SUB_BASS_WEIGHT'), 'mid_bass_weight': ('module', 'MID_BASS_WEIGHT'),
    }

    def __init__(self, master):
        self.master = master
        self.running = False
        self.server_sock = None

    def _get_led_module(self):
        import oracle_led_states_music
        return oracle_led_states_music

    def _get_param(self, key):
        mod = self._get_led_module()
        info = self.PARAM_MAP.get(key)
        if not info: return None
        if info[0] == 'magnet': return mod.MAGNET_PARAMS.get('MUSIC', {}).get(info[1])
        elif info[0] == 'state': return mod.MAGNET_PARAMS.get(info[1], {}).get(info[2])
        elif info[0] == 'module': return getattr(mod, info[1], None)
        elif info[0] == 'freq':
            band = mod.FREQUENCY_RANGES.get(info[1])
            return band[info[2]] if band else None
        return None

    def _set_param(self, key, value):
        mod = self._get_led_module()
        info = self.PARAM_MAP.get(key)
        if not info: return False
        try:
            if info[0] == 'magnet': mod.MAGNET_PARAMS['MUSIC'][info[1]] = int(value)
            elif info[0] == 'state': mod.MAGNET_PARAMS.setdefault(info[1], {})[info[2]] = int(value)
            elif info[0] == 'module': setattr(mod, info[1], value)
            elif info[0] == 'freq':
                current = list(mod.FREQUENCY_RANGES.get(info[1], (0, 0)))
                current[info[2]] = int(value)
                mod.FREQUENCY_RANGES[info[1]] = tuple(current)
            return True
        except Exception as e:
            logger.error(f"[TUNING] Error setting {key}={value}: {e}")
            return False

    def _handle_command(self, cmd_dict):
        cmd = cmd_dict.get('cmd')
        if cmd == 'get_params':
            return {k: self._get_param(k) for k in self.PARAM_MAP if self._get_param(k) is not None}
        elif cmd == 'get_audio':
            try:
                leds = self.master.leds
                return {'sub_bass': getattr(leds, '_last_sub_bass', 0), 'mid_bass': getattr(leds, '_last_mid_bass', 0),
                        'low_mid': getattr(leds, '_last_low_mid', 0), 'pwm_duty': getattr(leds, '_last_pwm_duty', 0),
                        'bass_pct': getattr(leds, '_last_bass_pct', 0), 'beat': getattr(leds, '_last_beat', False)}
            except Exception as e: return {'status': 'error', 'error': str(e)}
        elif cmd == 'set_param':
            key, value = cmd_dict.get('key'), cmd_dict.get('value')
            if key is None or value is None: return {'status': 'error', 'error': 'missing key or value'}
            ok = self._set_param(key, value)
            return {'status': 'ok', 'key': key, 'value': value} if ok else {'status': 'error'}
        elif cmd == 'magnet_on':
            duty = cmd_dict.get('duty', 100)
            try:
                leds = self.master.leds
                import RPi.GPIO as GPIO
                if not hasattr(leds, 'magnet_pwm') or leds.magnet_pwm is None:
                    GPIO.setmode(GPIO.BCM); GPIO.setup(23, GPIO.OUT)
                    leds.magnet_pwm = GPIO.PWM(23, 1000); leds.magnet_pwm.start(0)
                leds.magnet_pwm.ChangeDutyCycle(duty)
                return {'status': 'ok', 'duty': duty}
            except Exception as e: return {'status': 'error', 'error': str(e)}
        elif cmd == 'magnet_off':
            try:
                leds = self.master.leds
                if hasattr(leds, 'magnet_pwm') and leds.magnet_pwm: leds.magnet_pwm.ChangeDutyCycle(0)
                return {'status': 'ok'}
            except Exception as e: return {'status': 'error', 'error': str(e)}
        elif cmd == 'magnet_pulse':
            pattern = cmd_dict.get('pattern', 'pulse')
            def _run():
                try:
                    leds = self.master.leds
                    import RPi.GPIO as GPIO
                    if not hasattr(leds, 'magnet_pwm') or leds.magnet_pwm is None:
                        GPIO.setmode(GPIO.BCM); GPIO.setup(23, GPIO.OUT)
                        leds.magnet_pwm = GPIO.PWM(23, 1000); leds.magnet_pwm.start(0)
                    pwm = leds.magnet_pwm
                    if pattern == 'pulse':
                        for _ in range(5): pwm.ChangeDutyCycle(100); time.sleep(0.3); pwm.ChangeDutyCycle(0); time.sleep(0.3)
                    elif pattern == 'ripple':
                        for _ in range(3):
                            for d in range(0, 100, 3): pwm.ChangeDutyCycle(d); time.sleep(0.008)
                            for d in range(100, 0, -3): pwm.ChangeDutyCycle(d); time.sleep(0.008)
                        pwm.ChangeDutyCycle(0)
                    elif pattern == 'staccato':
                        for _ in range(12): pwm.ChangeDutyCycle(95); time.sleep(0.06); pwm.ChangeDutyCycle(0); time.sleep(0.06)
                    elif pattern == 'breathe':
                        import math
                        for i in range(200): pwm.ChangeDutyCycle(50 + 50 * math.sin(i * 0.06)); time.sleep(0.015)
                        pwm.ChangeDutyCycle(0)
                except Exception: pass
            threading.Thread(target=_run, daemon=True).start()
            return {'status': 'ok', 'pattern': pattern}
        elif cmd == 'leds_set':
            try:
                from rpi_ws281x import Color
                leds = self.master.leds
                for i in range(leds.strip.numPixels()): leds.strip.setPixelColor(i, Color(int(cmd_dict.get('r',0)), int(cmd_dict.get('g',0)), int(cmd_dict.get('b',0))))
                leds.strip.show()
                return {'status': 'ok'}
            except Exception as e: return {'status': 'error', 'error': str(e)}
        elif cmd == 'leds_off':
            try:
                from rpi_ws281x import Color
                leds = self.master.leds
                for i in range(leds.strip.numPixels()): leds.strip.setPixelColor(i, Color(0,0,0))
                leds.strip.show()
                return {'status': 'ok'}
            except Exception as e: return {'status': 'error', 'error': str(e)}
        elif cmd == 'set_state':
            try: self.master.leds.set_state(cmd_dict.get('state', 'IDLE')); return {'status': 'ok'}
            except Exception as e: return {'status': 'error', 'error': str(e)}
        elif cmd == 'get_state':
            try: return {'status': 'ok', 'state': self.master.leds.current_state}
            except Exception as e: return {'status': 'error', 'error': str(e)}
        elif cmd == 'save_params':
            return self._save_params_to_disk()
        return {'status': 'error', 'error': f'unknown command: {cmd}'}

    def _save_params_to_disk(self):
        """Persist current in-memory params back to oracle_led_states_music.py.
        Backs up first, writes atomically."""
        import re, shutil
        path = '/home/tyahn/oracle_led_states_music.py'
        try:
            backup = f"{path}.bak_{time.strftime('%Y%m%d_%H%M%S')}"
            shutil.copy(path, backup)
            with open(path) as f: src = f.read()
            mod = self._get_led_module()

            changes = []
            new_src = src

            for state in ('LISTENING', 'THINKING', 'SPEAKING', 'MUSIC'):
                p = mod.MAGNET_PARAMS.get(state, {})
                if 'min_duty' in p and 'max_duty' in p:
                    pattern = rf"'{state}':\s*\{{'min_duty':\s*\d+,\s*'max_duty':\s*\d+\}}"
                    replacement = f"'{state}': {{'min_duty': {int(p['min_duty'])}, 'max_duty': {int(p['max_duty'])}}}"
                    new_src, n = re.subn(pattern, replacement, new_src)
                    changes.append({'key': state, 'count': n, 'value': replacement})

            scalar_constants = [
                ('SMOOTHING_NORMAL', float),
                ('SMOOTHING_BEAT', float),
                ('BEAT_THRESHOLD_MULTIPLIER', float),
                ('BEAT_BOOST_FACTOR', float),
                ('SUB_BASS_WEIGHT', float),
                ('MID_BASS_WEIGHT', float),
            ]
            for name, _t in scalar_constants:
                v = getattr(mod, name, None)
                if v is None: continue
                pattern = rf"^{name}\s*=\s*[\d.]+"
                replacement = f"{name} = {v}"
                new_src, n = re.subn(pattern, replacement, new_src, flags=re.MULTILINE)
                changes.append({'key': name, 'count': n, 'value': replacement})

            for band in ('sub_bass', 'mid_bass', 'low_mid'):
                rng = mod.FREQUENCY_RANGES.get(band)
                if not rng: continue
                pattern = rf"'{band}':\s*\(\s*\d+\s*,\s*\d+\s*\)"
                replacement = f"'{band}': ({int(rng[0])}, {int(rng[1])})"
                new_src, n = re.subn(pattern, replacement, new_src)
                changes.append({'key': f'FREQUENCY_RANGES[{band}]', 'count': n, 'value': replacement})

            tmp = path + '.tmp'
            with open(tmp, 'w') as f: f.write(new_src)
            os.replace(tmp, path)
            return {'status': 'ok', 'backup': backup, 'changes': changes}
        except Exception as e:
            logger.error(f"[TUNING] save_params failed: {e}")
            return {'status': 'error', 'error': str(e)}

    def _handle_client(self, conn):
        try:
            buf = b''
            while self.running:
                data = conn.recv(4096)
                if not data: break
                buf += data
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    try:
                        resp = self._handle_command(json.loads(line.decode('utf-8')))
                        conn.sendall(json.dumps(resp).encode('utf-8') + b'\n')
                    except json.JSONDecodeError:
                        conn.sendall(b'{"status":"error","error":"invalid JSON"}\n')
        except (ConnectionResetError, BrokenPipeError, OSError): pass
        finally:
            try: conn.close()
            except: pass

    def start(self):
        self.running = True
        threading.Thread(target=self._server_loop, daemon=True, name='tuning-socket').start()
        logger.info(f"[TUNING] Socket server started at {self.SOCK_PATH}")

    def _server_loop(self):
        import socket as _socket
        if os.path.exists(self.SOCK_PATH): os.unlink(self.SOCK_PATH)
        self.server_sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        self.server_sock.bind(self.SOCK_PATH)
        os.chmod(self.SOCK_PATH, 0o777)
        self.server_sock.listen(5)
        self.server_sock.settimeout(1.0)
        while self.running:
            try:
                conn, _ = self.server_sock.accept()
                threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
            except _socket.timeout: continue
            except OSError:
                if self.running: import traceback; traceback.print_exc()
                break

    def stop(self):
        self.running = False
        if self.server_sock:
            try: self.server_sock.close()
            except: pass
        if os.path.exists(self.SOCK_PATH):
            try: os.unlink(self.SOCK_PATH)
            except: pass


# ==================== MASTER SERVICE ====================

class OracleMasterService:
    """Orchestrator that coordinates all Oracle modules."""

    def __init__(self):
        logger.info("=" * 60)
        logger.info("  Oracle Master Service - Initializing")
        logger.info("=" * 60)

        self.running = False
        self.in_voice_interaction = False
        self.realtime_session_active = False
        self.current_session = None

        # Initialize modules
        self.spotify = SpotifyController()
        logger.info("✓ Spotify controller ready")

        logger.info("Initializing LED controller...")
        self.leds = OracleLEDController()
        self.leds.set_state('IDLE')
        self.leds.audio_buffer = deque(maxlen=30)
        logger.info("✓ LED controller ready")

        self.tuning_server = TuningSocketServer(self)
        self.tuning_server.start()

        # Wake word
        logger.info(f"Initializing wake word detection ('{WAKE_WORD[0]}')...")
        self.porcupine = pvporcupine.create(access_key=PORCUPINE_KEY, keywords=WAKE_WORD, sensitivities=[0.7])
        logger.info("✓ Porcupine loaded")

        # TTS
        logger.info("Loading Piper TTS model...")
        tts_voice = PiperVoice.load(PIPER_MODEL_PATH)
        logger.info("✓ Piper TTS loaded")

        # Speaker (uses TTS + Spotify + LEDs)
        self.speaker = Speaker(tts_voice, self.spotify, self.leds)
        self.speaker.realtime_active_check = lambda: self.realtime_session_active

        # Microphone
        logger.info(f"Opening microphone: {AUDIO_DEVICE}")
        self.mic_proc = subprocess.Popen(
            ["arecord", "-D", AUDIO_DEVICE, "-f", "S16_LE", "-c", "2",
             "-r", str(self.porcupine.sample_rate), "-t", "raw"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0
        )
        self.mic_frame_bytes = self.porcupine.frame_length * 2 * 2
        logger.info("✓ Microphone ready")

        # Tools
        self.session_id = f"oracle-{int(time.time())}"
        self.tools = ToolHandler(MONEO_API_URL, MONEO_API_KEY, self.spotify, self.session_id)
        logger.info("✓ Tool handler ready")

        # Announcement FIFO
        self.fifo_path = '/tmp/oracle_announce.fifo'

        # Volume check
        current_vol = self.spotify.get_volume()
        if current_vol < 80:
            logger.info(f"📢 Resetting volume from {current_vol} to 127")
            self.spotify.set_volume(127)

        logger.info("✓ Oracle Master Service initialized")
        logger.info("=" * 60)

    # ==================== MIC CONTROL ====================

    def _mute_mic(self):
        if hasattr(self, 'mic_proc') and self.mic_proc and self.mic_proc.poll() is None:
            self.mic_proc.terminate()
            self.mic_proc.wait(timeout=2)
            logger.info("[Mic] Muted")

    def _unmute_mic(self):
        self.mic_proc = subprocess.Popen(
            ["arecord", "-D", AUDIO_DEVICE, "-f", "S16_LE", "-c", "2",
             "-r", str(self.porcupine.sample_rate), "-t", "raw"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0
        )
        logger.info("[Mic] Unmuted")

    def _ensure_mic_alive(self):
        """Watchdog: respawn arecord if the subprocess has died.
        Wake-word loop would otherwise spin on a closed pipe forever
        (known reliability issue from March 2026 — see oracle-speaker-v2 memory)."""
        proc = getattr(self, 'mic_proc', None)
        if proc is None or proc.poll() is not None:
            rc = proc.poll() if proc is not None else 'none'
            logger.warning(f"[Mic Watchdog] arecord died (rc={rc}), respawning")
            try:
                self._unmute_mic()
                return True
            except Exception as e:
                logger.error(f"[Mic Watchdog] respawn failed: {e}")
                time.sleep(1)
        return False

    # ==================== WAKE WORD ====================

    def wake_word_loop(self):
        """Background thread: Listen for wake word (even during music)."""
        logger.info(f"[Wake Word] Thread started - listening for '{WAKE_WORD[0].upper()}'")
        logger.info("[Wake Word] Entering read loop...")
        frame_count = 0
        empty_read_streak = 0
        MAX_EMPTY_READS = 100  # ~10s at 100ms sleep — forces respawn even if proc didn't exit

        while self.running:
            try:
                self._ensure_mic_alive()
                try:
                    mic_fd = self.mic_proc.stdout.fileno()
                except (ValueError, AttributeError, OSError):
                    time.sleep(0.1); continue

                data = b''
                while len(data) < self.mic_frame_bytes:
                    try: chunk = os.read(mic_fd, self.mic_frame_bytes - len(data))
                    except OSError: chunk = b''
                    if not chunk: time.sleep(0.1); break
                    data += chunk
                if len(data) < self.mic_frame_bytes:
                    empty_read_streak += 1
                    if empty_read_streak >= MAX_EMPTY_READS:
                        logger.warning(f"[Mic Watchdog] {empty_read_streak} empty reads, forcing mic respawn")
                        self._mute_mic()
                        self._unmute_mic()
                        empty_read_streak = 0
                    continue
                empty_read_streak = 0

                length = self.porcupine.frame_length
                if length > 0:
                    frame_count += 1
                    if frame_count % 200 == 1:
                        _s = np.frombuffer(data[:80], dtype=np.int16)
                        logger.info(f"[Wake Word] Frame {frame_count}, RMS={np.sqrt(np.mean(_s.astype(float)**2)):.0f}")

                    # Stereo -> mono for Porcupine
                    audio = struct.unpack(f'{length * 2}h', data)
                    mono = [int((audio[i] + audio[i+1]) / 2) for i in range(0, len(audio), 2)]

                    # Feed audio to active Realtime session
                    if self.realtime_session_active and self.current_session:
                        self.current_session.feed_audio(length, data)

                    if len(mono) >= self.porcupine.frame_length:
                        pcm = mono[:self.porcupine.frame_length]
                        keyword_index = self.porcupine.process(pcm)
                        if keyword_index >= 0:
                            if self.realtime_session_active and self.current_session and self.current_session._is_responding:
                                logger.info(f"🔊 INTERRUPT via wake word at {datetime.now().strftime('%H:%M:%S')}")
                                self.current_session.interrupt()
                            elif not self.realtime_session_active:
                                logger.info(f"🔊 WAKE WORD DETECTED at {datetime.now().strftime('%H:%M:%S')}")
                                self.handle_wake_word()

            except Exception as e:
                logger.error(f"[Wake Word] Error: {e}")
                time.sleep(0.1)

    def handle_wake_word(self):
        """Start Realtime API conversation (non-blocking)."""
        logger.info("[Realtime] Starting conversation session...")
        self.realtime_session_active = True
        self._spotify_was_playing = self.spotify.playing

        if self._spotify_was_playing:
            self.spotify.pause()

        self.leds.set_state("LISTENING")
        play_chime(ascending=True)

        def _check_briefing_request(transcript):
            """Check if user asked for briefing and switch to dedicated session."""
            lower = transcript.lower()
            if any(kw in lower for kw in ["briefing", "breathing", "morning brief", "morning breath", "check-in", "check in", "daily brief"]):
                logger.info("[Realtime] Briefing request detected in transcript - switching to check-in")
                self.tools._briefing_requested = True
                if self.current_session:
                    self.current_session.active = False  # Kill current session

        # Phase 1: pull recent conversation context + mint fresh session id
        sid = self._new_session_id()
        ctx_prefix = self._fetch_recent_context(hours=24, limit=20)
        prompt = ORACLE_SYSTEM_PROMPT + ("\n\n" + ctx_prefix if ctx_prefix else "")

        session = OracleRealtimeSession(
            api_key=OPENAI_API_KEY,
            system_prompt=prompt,
            tools=REALTIME_TOOLS,
            tool_handler=self.tools.handle,
            on_speech_started=lambda: self.leds.set_state("LISTENING"),
            on_speech_ended=lambda: self.leds.set_state("THINKING"),
            on_audio_started=lambda: self.leds.set_state("SPEAKING"),
            on_response_done=lambda: None,
            on_error=lambda msg: logger.error(f"[Realtime] Error: {msg}"),
            on_mic_mute=self._mute_mic,
            on_mic_unmute=self._unmute_mic,
            on_user_transcript=_check_briefing_request,
            session_timeout=20,
            memory_url=self._memory_base_url(),
            memory_api_key=MONEO_API_KEY,
            session_id=sid,
        )
        self.current_session = session
        session.start()

        def _monitor():
            while session.active and self.running:
                time.sleep(0.1)
            self.current_session = None
            self.realtime_session_active = False

            # Check if briefing was requested during this session
            briefing_requested = getattr(self.tools, '_briefing_requested', False)
            if briefing_requested:
                self.tools._briefing_requested = False
                logger.info("[Realtime] Briefing requested - switching to check-in session")
                time.sleep(1)
                self._deliver_briefing()
                return

            logger.info("[Realtime] Session ended, waiting for speaker cleanup...")
            time.sleep(2)
            logger.info("[Realtime] Playing end chime")
            play_chime(ascending=False)
            if self._spotify_was_playing:
                self.spotify.resume()
                time.sleep(1)
                self.leds.set_state("MUSIC")
                logger.info("Returned to MUSIC state")
            else:
                self.leds.set_state("IDLE")
                logger.info("Returned to IDLE state")

        threading.Thread(target=_monitor, daemon=True).start()

    # ==================== FIFO ANNOUNCEMENTS ====================

    def fifo_reader_loop(self):
        """Background thread: Read announcements from scheduler FIFO."""
        logger.info('[FIFO Reader] Thread started')
        while self.running:
            try:
                if not os.path.exists(self.fifo_path):
                    try: os.mkfifo(self.fifo_path)
                    except OSError: time.sleep(5); continue

                with open(self.fifo_path, 'r') as fifo:
                    while self.running:
                        line = fifo.readline()
                        if not line: break
                        line = line.strip()
                        if not line: continue
                        try:
                            msg = json.loads(line)
                            text = msg.get('text', '')
                            priority = msg.get('priority', 'medium')
                            if not text: continue
                            logger.info(f'[FIFO] Received ({priority}): {text[:100]}...')
                            self._announce(text, priority)
                        except json.JSONDecodeError as e:
                            logger.error(f'[FIFO] Invalid JSON: {line} - {e}')
            except Exception as e:
                logger.error(f'[FIFO Reader] Error: {e}')
                time.sleep(5)

    def _announce(self, text, priority):
        """Route announcement based on priority. For reminders, open a listen session after."""
        is_reminder = text.lower().startswith('reminder')

        if priority == 'urgent':
            self.in_voice_interaction = True
            self.speaker.speak(text)
            self.in_voice_interaction = False
        elif priority == 'medium':
            if self.in_voice_interaction or self.realtime_session_active:
                logger.info('[Announcement] Waiting for conversation to finish')
                start = time.time()
                while (self.in_voice_interaction or self.realtime_session_active) and (time.time() - start) < 60:
                    time.sleep(1)
            self.speaker.speak(text)
        else:  # low
            start = time.time()
            while (self.spotify.playing or self.in_voice_interaction) and (time.time() - start) < 300:
                time.sleep(5)
            self.speaker.speak(text)

        # After a reminder, open a brief Realtime session so Trevor can dismiss/snooze
        # without needing to say the wake word again
        if is_reminder and not self.realtime_session_active:
            logger.info("[Reminder] Opening listen session for acknowledgment...")
            self._open_reminder_listen_session()

    def _open_reminder_listen_session(self):
        """Open a short Realtime session after a reminder fires so Trevor can respond immediately."""
        if self.realtime_session_active:
            return

        self.realtime_session_active = True
        self._spotify_was_playing = self.spotify.playing
        if self._spotify_was_playing:
            self.spotify.pause()

        self.leds.set_state("LISTENING")

        reminder_prompt = ORACLE_SYSTEM_PROMPT + """

REMINDER ACKNOWLEDGMENT MODE:
A reminder just fired and was spoken to Trevor. He can now respond.
If he says 'got it', 'ok', 'dismiss', 'done', 'thanks', or anything that sounds like acknowledgment, call dismiss_reminder with reminder_index -1.
If he says 'snooze' or 'remind me again in X minutes', call snooze_reminder.
If he says something unrelated, just respond normally.
If he doesn't say anything, the session will time out and that's fine.
"""

        session = OracleRealtimeSession(
            api_key=OPENAI_API_KEY,
            system_prompt=reminder_prompt,
            tools=REALTIME_TOOLS,
            tool_handler=self.tools.handle,
            on_speech_started=lambda: self.leds.set_state("LISTENING"),
            on_speech_ended=lambda: self.leds.set_state("THINKING"),
            on_audio_started=lambda: self.leds.set_state("SPEAKING"),
            on_response_done=lambda: None,
            on_error=lambda msg: logger.error(f"[Reminder Listen] Error: {msg}"),
            on_mic_mute=self._mute_mic,
            on_mic_unmute=self._unmute_mic,
            session_timeout=8,  # Slightly longer timeout for acknowledgment
            memory_url=self._memory_base_url(),
            memory_api_key=MONEO_API_KEY,
            session_id=self.session_id,
        )
        self.current_session = session
        session.start()
        logger.info("[Reminder Listen] Session open — waiting for Trevor's response")

        def _monitor():
            while session.active and self.running:
                time.sleep(0.1)
            self.current_session = None
            self.realtime_session_active = False
            logger.info("[Reminder Listen] Session ended")
            time.sleep(2)
            play_chime(ascending=False)
            if self._spotify_was_playing:
                self.spotify.resume()
                time.sleep(1)
                self.leds.set_state("MUSIC")
            else:
                self.leds.set_state("IDLE")

        threading.Thread(target=_monitor, daemon=True).start()

    # ==================== AUDIO BRIDGE ====================

    def audio_bridge_loop(self):
        """Background thread: Feed audio visualization buffer from FIFO."""
        FIFO_PATH = '/tmp/oracle_audio_fifo'
        CHUNK_BYTES = 1024 * 2 * 2

        try:
            subprocess.run(['amixer', '-c', '4', 'sset', 'Headphone', '127'], capture_output=True, timeout=2)
            subprocess.run(['amixer', '-c', '4', 'sset', 'Speaker', '127'], capture_output=True, timeout=2)
            subprocess.run(['amixer', '-c', '4', 'sset', 'Playback', '255'], capture_output=True, timeout=2)
            logger.info("[Audio Bridge] WM8960 volumes set")
        except Exception as e:
            logger.warning(f"[Audio Bridge] Volume set failed: {e}")

        logger.info(f"[Audio Bridge] Waiting for FIFO at {FIFO_PATH}...")
        while self.running:
            try:
                if not os.path.exists(FIFO_PATH): time.sleep(0.5); continue
                with open(FIFO_PATH, 'rb') as fifo:
                    logger.info("[Audio Bridge] FIFO opened for visualization")
                    while self.running:
                        data = fifo.read(CHUNK_BYTES)
                        if not data: break
                        length = len(data) // (2 * 2)
                        if length > 0: self.leds.audio_buffer.append((length, data))
            except Exception as e:
                logger.error(f"[Audio Bridge] FIFO error: {e}")
                time.sleep(1)

    # ==================== BRIEFING SCHEDULER ====================

    def briefing_loop(self):
        """Background thread: Deliver morning briefing at 11 AM and EOD check-in at 6 PM ET weekdays."""
        delivered_today = False
        eod_delivered_today = False
        logger.info("[Briefing] Scheduler started - morning 11:00 AM ET (weekdays); EOD auto-fire DISABLED, manual trigger only")

        while self.running:
            try:
                now = datetime.now()
                if now.hour == 0 and now.minute == 0:
                    delivered_today = False
                    eod_delivered_today = False
                if now.hour == 11 and now.minute == 0 and now.weekday() < 5 and not delivered_today:
                    logger.info("[Briefing] 11:00 AM ET - delivering morning briefing")
                    delivered_today = True
                    self._deliver_briefing()
                # EOD auto-fire is DISABLED pending project-tracking redesign (2026-05-18).
                # The current 3-question prompt is too generic; will be reworked to anchor
                # against today's must-win + open tasks + active goals once the new tracking
                # model is settled. Manual trigger below still works for development.
                # if now.hour == 18 and now.minute == 0 and now.weekday() < 5 and not eod_delivered_today:
                #     logger.info("[Briefing] 6:00 PM ET - delivering EOD check-in")
                #     eod_delivered_today = True
                #     self._deliver_eod_checkin()
                _ = eod_delivered_today  # keep variable referenced
                # External trigger via /tmp/oracle_eod_trigger (touched by manual test endpoint)
                if os.path.exists('/tmp/oracle_eod_trigger'):
                    try: os.remove('/tmp/oracle_eod_trigger')
                    except: pass
                    logger.info("[Briefing] Manual EOD trigger detected")
                    self._deliver_eod_checkin()
                # External trigger via /tmp/oracle_briefing_trigger (touched by the
                # dashboard "send now" button / triggerDelivery on the droplet).
                if os.path.exists('/tmp/oracle_briefing_trigger'):
                    try: os.remove('/tmp/oracle_briefing_trigger')
                    except: pass
                    logger.info("[Briefing] Manual briefing trigger detected")
                    self._deliver_briefing()
                time.sleep(30)
            except Exception as e:
                logger.error(f"[Briefing] Error: {e}")
                time.sleep(60)

    def _deliver_briefing(self):
        """Deliver morning briefing via Piper TTS, then open Realtime API for Q&A."""
        logger.info("[Briefing] Starting delivery...")
        try:
            # 1. Generate fresh briefing from Moneo (always regenerate for current data)
            api_base = MONEO_API_URL.rsplit('/api/', 1)[0]
            logger.info("[Briefing] Generating fresh briefing...")
            response = requests.post(f"{api_base}/api/voice/briefing/generate",
                                     headers={"X-API-Key": MONEO_API_KEY}, timeout=60)
            if response.status_code != 200:
                logger.error(f"[Briefing] Generation failed: {response.status_code}"); return
            briefing_data = response.json().get("briefing", {})

            script = briefing_data.get("script", "")
            interview_questions = briefing_data.get("interviewQuestions", [])

            if not script:
                logger.error("[Briefing] Empty script"); return

            # 2. Read briefing via Piper TTS (no AI, no hallucination)
            self._spotify_was_playing = self.spotify.playing
            if self._spotify_was_playing: self.spotify.pause()
            play_chime(ascending=True)
            time.sleep(0.5)

            logger.info(f"[Briefing] Reading script via Piper TTS ({len(script)} chars)")
            self.speaker.speak(script)
            logger.info("[Briefing] TTS delivery complete")

            # 3. Open Realtime API session for interactive Q&A
            if interview_questions:
                time.sleep(1)
                logger.info(f"[Briefing] Starting Q&A session with {len(interview_questions)} questions")

                question_list = "\n".join(f"{i+1}. {q}" for i, q in enumerate(interview_questions))
                qa_prompt = f"""You are Oracle, Trevor Yahn's AI assistant. You just delivered his morning briefing via the speaker. Now do a short check-in. This is a conversation, not data entry.

Ask Trevor these questions, ONE AT A TIME, waiting for his answer before asking the next:

{question_list}

RULES:
- Do NOT call any tools. Do NOT call capture. This morning check-in does not create or complete tasks — the transcript is saved automatically afterward. Task review happens at the end-of-day check-in, not now.
- Keep every response to one short sentence. You are speaking out loud.
- Acknowledge briefly between questions ("Got it." / "Noted.").
- Do not give advice or platitudes. Be direct, JARVIS-style.
- Start by saying "That's your briefing. A couple quick things."
- After his last answer, say "Logged. Go get it." and end."""

                self.realtime_session_active = True
                self.leds.set_state("SPEAKING")

                session = OracleRealtimeSession(
                    api_key=OPENAI_API_KEY, system_prompt=qa_prompt,
                    tools=REALTIME_TOOLS, tool_handler=self.tools.handle,
                    on_speech_started=lambda: self.leds.set_state("LISTENING"),
                    on_speech_ended=lambda: self.leds.set_state("THINKING"),
                    on_audio_started=lambda: self.leds.set_state("SPEAKING"),
                    on_response_done=lambda: None,
                    on_error=lambda msg: logger.error(f"[Briefing Q&A] Error: {msg}"),
                    on_mic_mute=self._mute_mic, on_mic_unmute=self._unmute_mic,
                    auto_start=True, session_timeout=30,
                    memory_url=self._memory_base_url(),
                    memory_api_key=MONEO_API_KEY,
                    session_id=self.session_id,
                    end_phrases=["go get it"],
                )
                self.current_session = session
                session.start()

                while session.active and self.running: time.sleep(0.1)
                self.current_session = None
                self.realtime_session_active = False

                # Post-session: save the morning interview as a day-context note
                # (+ must-win). No task creation — that's the EOD check-in's job.
                if session.transcript:
                    logger.info(f"[Briefing] Saving morning interview ({len(session.transcript)} transcript entries)")
                    try:
                        api_base = MONEO_API_URL.rsplit('/api/', 1)[0]
                        dc_resp = requests.post(
                            f"{api_base}/api/voice/daycontext",
                            headers={"X-API-Key": MONEO_API_KEY, "Content-Type": "application/json"},
                            json={"transcript": session.transcript},
                            timeout=30
                        )
                        if dc_resp.status_code == 200:
                            result = dc_resp.json()
                            logger.info(f"[Briefing] Morning interview saved: {', '.join(result.get('actions', [])) or 'nothing captured'}")
                        else:
                            logger.error(f"[Briefing] Day-context save failed: {dc_resp.status_code}")
                    except Exception as e:
                        logger.error(f"[Briefing] Day-context error: {e}")

            time.sleep(1)
            play_chime(ascending=False)

            if self._spotify_was_playing:
                self.spotify.resume(); self.leds.set_state("MUSIC")
            else:
                self.leds.set_state("IDLE")
            logger.info("[Briefing] Delivery complete")
        except Exception as e:
            logger.error(f"[Briefing] Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.realtime_session_active = False

    def _deliver_eod_checkin(self):
        """Deliver the EOD check-in interview at 6 PM weekday. Slimmer than the morning
        briefing — no pre-generated script, just opens a 3-question Realtime Q&A and
        ships the transcript to /api/voice/checkin/extract with kind='eod' so the
        droplet writes a daily debrief to vault/moneo/daily-debriefs/."""
        logger.info("[EOD] Starting check-in...")
        try:
            self._spotify_was_playing = self.spotify.playing
            if self._spotify_was_playing: self.spotify.pause()
            play_chime(ascending=True)
            time.sleep(0.5)

            eod_prompt = """You are Oracle, Trevor Yahn's AI assistant, delivering his end-of-day check-in over the speaker.

Ask these three questions ONE AT A TIME, waiting for his response before moving on. Acknowledge briefly between them (one phrase like "Got it." or "Logged."). Do not ask follow-up questions unless he gives a one-word answer.

1. What shipped today?
2. What's blocked or stuck?
3. What's tomorrow's number one?

CAPTURE RULES (run these in parallel with the questions — your main job here):
- Anything Trevor says is DONE/FINISHED/SHIPPED -> capture(type="complete")
- Any blocker he names -> capture(type="note")
- Tomorrow's #1 -> capture(type="commitment")
- Any other actionable item that surfaces -> capture(type="task")
Call capture without asking permission. Do NOT use dismiss_reminder for task completions.

CONVERSATION RULES:
- Keep responses to 1-2 sentences. Speaking out loud, not writing.
- No motivational platitudes or summaries.
- Be direct, JARVIS-style.
- Start by saying "End of day check-in. What shipped today?"
- After question 3, say "Logged. EOD complete. Talk in the morning." and end."""

            self.realtime_session_active = True
            self.leds.set_state("SPEAKING")

            session = OracleRealtimeSession(
                api_key=OPENAI_API_KEY, system_prompt=eod_prompt,
                tools=REALTIME_TOOLS, tool_handler=self.tools.handle,
                on_speech_started=lambda: self.leds.set_state("LISTENING"),
                on_speech_ended=lambda: self.leds.set_state("THINKING"),
                on_audio_started=lambda: self.leds.set_state("SPEAKING"),
                on_response_done=lambda: None,
                on_error=lambda msg: logger.error(f"[EOD] Error: {msg}"),
                on_mic_mute=self._mute_mic, on_mic_unmute=self._unmute_mic,
                auto_start=True, session_timeout=45,
                memory_url=self._memory_base_url(),
                memory_api_key=MONEO_API_KEY,
                session_id=self.session_id,
                end_phrases=["talk in the morning"],
            )
            self.current_session = session
            session.start()
            while session.active and self.running: time.sleep(0.1)
            self.current_session = None
            self.realtime_session_active = False

            if session.transcript:
                logger.info(f"[EOD] Extracting captures from {len(session.transcript)} transcript entries")
                try:
                    api_base = MONEO_API_URL.rsplit('/api/', 1)[0]
                    extract_resp = requests.post(
                        f"{api_base}/api/voice/checkin/extract",
                        headers={"X-API-Key": MONEO_API_KEY, "Content-Type": "application/json"},
                        json={"transcript": session.transcript, "kind": "eod"},
                        timeout=30
                    )
                    if extract_resp.status_code == 200:
                        result = extract_resp.json()
                        logger.info(f"[EOD] Captured {result.get('captured', 0)} items from check-in")
                    else:
                        logger.error(f"[EOD] Extract failed: {extract_resp.status_code}")
                except Exception as e:
                    logger.error(f"[EOD] Extract error: {e}")

            time.sleep(1)
            play_chime(ascending=False)
            if self._spotify_was_playing:
                self.spotify.resume(); self.leds.set_state("MUSIC")
            else:
                self.leds.set_state("IDLE")
            logger.info("[EOD] Delivery complete")
        except Exception as e:
            logger.error(f"[EOD] Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.realtime_session_active = False

    # ==================== MEMORY ====================

    def _memory_base_url(self):
        """Derive memory endpoint base from MONEO_API_URL."""
        return MONEO_API_URL.rsplit('/api/', 1)[0]

    def _fetch_recent_context(self, hours=24, limit=20):
        """Pull last N hours of conversation as a system-prompt prefix.
        Bounded by 3s timeout; returns '' on any failure so a slow droplet never blocks a session start."""
        try:
            r = requests.get(
                f"{self._memory_base_url()}/api/oracle/context",
                params={'hours': hours, 'limit': limit},
                headers={'X-API-Key': MONEO_API_KEY},
                timeout=3,
            )
            if r.status_code == 200:
                data = r.json()
                count = data.get('count', 0)
                formatted = data.get('formatted', '')
                if count > 0:
                    logger.info(f"[Memory] Injected {count} prior turns into session prompt")
                return formatted
            logger.warning(f"[Memory] context fetch HTTP {r.status_code}")
        except Exception as e:
            logger.warning(f"[Memory] context fetch failed: {e}")
        return ''

    def _new_session_id(self):
        """Mint a fresh session id and update self.session_id."""
        self.session_id = f"oracle-{int(time.time())}"
        return self.session_id

    # ==================== HEARTBEAT ====================

    def heartbeat_loop(self):
        """Post a liveness heartbeat to ntfy every HEARTBEAT_INTERVAL_SEC.
        Droplet-side dead-mans-switch pages if heartbeats stop for >2x interval."""
        if not NTFY_URL:
            logger.warning("[Heartbeat] NTFY_URL not set, heartbeat disabled")
            return
        url = f"{NTFY_URL.rstrip('/')}/{NTFY_HEARTBEAT_TOPIC}"
        auth = (NTFY_USER, NTFY_PASSWORD) if NTFY_USER else None
        logger.info(f"[Heartbeat] Started: posting to {url} every {HEARTBEAT_INTERVAL_SEC}s")
        while self.running:
            try:
                payload = f"alive {datetime.now().isoformat(timespec='seconds')}"
                r = requests.post(
                    url,
                    data=payload,
                    headers={'Priority': '1', 'Tags': 'green_heart', 'Title': 'Oracle'},
                    auth=auth,
                    timeout=5,
                )
                if r.status_code >= 400:
                    logger.warning(f"[Heartbeat] HTTP {r.status_code}: {r.text[:200]}")
            except Exception as e:
                logger.warning(f"[Heartbeat] post failed: {e}")
            time.sleep(HEARTBEAT_INTERVAL_SEC)

    # ==================== PROACTIVE ALERTS (Phase 3) ====================

    def alert_listener_loop(self):
        """Long-poll ntfy moneo-oracle-alerts. On message:
          - severity=critical → speak via Piper TTS (Speaker handles music-pause + realtime-wait)
          - severity=info     → flash LEDs in alert color, no audio
        Reconnects on any failure. Dedup via alert_id."""
        if not NTFY_URL or not NTFY_ALERTS_USER:
            logger.warning("[Alerts] NTFY_ALERTS_* not configured, listener disabled")
            return
        url = f"{NTFY_URL.rstrip('/')}/{NTFY_ALERTS_TOPIC}/json"
        auth = (NTFY_ALERTS_USER, NTFY_ALERTS_PASSWORD)
        logger.info(f"[Alerts] Listener starting on {url}")
        seen_ids = set()
        MAX_SEEN = 1000

        while self.running:
            try:
                with requests.get(url, auth=auth, stream=True, timeout=(10, None)) as r:
                    if r.status_code != 200:
                        logger.warning(f"[Alerts] HTTP {r.status_code}: {r.text[:200]}")
                        time.sleep(30)
                        continue
                    logger.info("[Alerts] Stream connected")
                    for raw in r.iter_lines():
                        if not self.running:
                            return
                        if not raw:
                            continue
                        try:
                            msg = json.loads(raw.decode('utf-8'))
                            if msg.get('event') != 'message':
                                continue  # keepalive / open events
                            inner = msg.get('message', '')
                            payload = json.loads(inner) if inner else {}
                            aid = payload.get('alert_id')
                            if aid and aid in seen_ids:
                                continue
                            if aid:
                                seen_ids.add(aid)
                                if len(seen_ids) > MAX_SEEN:
                                    seen_ids = set(list(seen_ids)[-MAX_SEEN // 2:])
                            self._handle_alert(payload)
                        except Exception as e:
                            logger.warning(f"[Alerts] parse error: {e} on {raw[:120]}")
            except Exception as e:
                if self.running:
                    logger.warning(f"[Alerts] stream error: {e}, reconnect in 10s")
                    time.sleep(10)

    def _handle_alert(self, alert):
        severity = alert.get('severity', 'info')
        spoken = alert.get('spoken_message') or alert.get('title', '')
        source = alert.get('source', 'unknown')
        title = alert.get('title', '(no title)')
        logger.info(f"[Alert] {severity} from {source}: {title}")

        if severity == 'critical':
            # Speaker.speak() handles spotify-pause, realtime-wait, LED state.
            # Run in a thread so the listener can continue receiving.
            threading.Thread(
                target=self._speak_alert_safe, args=(spoken,), daemon=True
            ).start()
        # info severity: no immediate flash. The droplet has already added
        # this alert to the pending store. The pending_pulse_loop will
        # render the visual reminder every PENDING_PULSE_INTERVAL_SEC.

    def _speak_alert_safe(self, text):
        try:
            self.speaker.speak(text)
        except Exception as e:
            logger.error(f"[Alert] speak failed: {e}")

    def pending_pulse_loop(self):
        """Every PENDING_PULSE_INTERVAL_SEC, ask the droplet for pending notifications.
        If anything is pending, render a soft red breathing pulse for up to PENDING_PULSE_DURATION_SEC.
        Skip the pulse if Oracle is currently in a Realtime session (don't talk over Trevor)."""
        url = f"{self._memory_base_url()}/api/oracle/pending"
        logger.info(f"[Pending] Pulse loop started: every {PENDING_PULSE_INTERVAL_SEC}s, up to {PENDING_PULSE_DURATION_SEC}s")
        # Stagger the first check so we don't pulse the instant the service comes up
        time.sleep(min(60, PENDING_PULSE_INTERVAL_SEC))
        while self.running:
            try:
                r = requests.get(url, headers={'X-API-Key': MONEO_API_KEY}, timeout=5)
                count = r.json().get('count', 0) if r.status_code == 200 else 0
                if count > 0 and not self.realtime_session_active:
                    cycles = max(1, PENDING_PULSE_DURATION_SEC * 1000 // max(PENDING_PULSE_BREATH_MS, 1))
                    logger.info(f"[Pending] {count} pending, pulsing {cycles} breaths")
                    self.leds.flash_alert(peak_color=(120, 0, 0), cycles=cycles, period_ms=PENDING_PULSE_BREATH_MS)
                elif count > 0:
                    logger.info(f"[Pending] {count} pending but Realtime session active, skipping pulse")
            except Exception as e:
                logger.warning(f"[Pending] poll failed: {e}")
            time.sleep(PENDING_PULSE_INTERVAL_SEC)

    # ==================== RUN ====================

    def run(self):
        logger.info('Starting Oracle Master Service...')
        self.running = True

        try:
            threads = [
                threading.Thread(target=self.briefing_loop, daemon=True),
                threading.Thread(target=self.audio_bridge_loop, daemon=True),
                threading.Thread(target=self.spotify.monitor_loop, args=(self,), daemon=True),
                threading.Thread(target=self.wake_word_loop, daemon=True),
                threading.Thread(target=self.fifo_reader_loop, daemon=True),
                threading.Thread(target=self.heartbeat_loop, daemon=True),
                threading.Thread(target=self.alert_listener_loop, daemon=True),
                threading.Thread(target=self.pending_pulse_loop, daemon=True),
            ]
            for t in threads: t.start()

            logger.info('✓ All threads started')
            logger.info(f"✓ Wake word: '{WAKE_WORD[0].upper()}'")
            logger.info('✓ Oracle is ready!')
            logger.info('=' * 60)

            while True: time.sleep(1)

        except KeyboardInterrupt:
            logger.info('Shutting down...')
        finally:
            self.cleanup()

    def cleanup(self):
        self.running = False
        if hasattr(self, 'porcupine'): self.porcupine.delete()
        if hasattr(self, 'mic_proc'): self.mic_proc.terminate()
        if hasattr(self, 'leds'): self.leds.cleanup()
        if hasattr(self, 'tuning_server'): self.tuning_server.stop()
        logger.info('✓ Shutdown complete')


if __name__ == '__main__':
    oracle = OracleMasterService()
    oracle.run()
