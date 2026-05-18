#!/usr/bin/env python3
"""
Oracle Ferrofluid Speaker - Real-Time Tuning Dashboard
Standalone Flask app on port 3004.
Communicates with oracle_master_service via Unix socket at /tmp/oracle_tuning.sock.
"""

import json
import os
import socket
import threading
import time
import logging

from flask import Flask, render_template, jsonify, request

# Try flask-socketio first, fall back to SSE
try:
    from flask_socketio import SocketIO, emit
    HAS_SOCKETIO = True
except ImportError:
    HAS_SOCKETIO = False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'oracle-tuning-2026'

if HAS_SOCKETIO:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
else:
    socketio = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s [TUNING] %(message)s')
log = logging.getLogger(__name__)

SOCK_PATH = '/tmp/oracle_tuning.sock'
PRESETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'presets.json')
CUSTOM_PRESETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom_presets.json')

DEFAULTS = {
    'min_duty': 35,
    'max_duty': 100,
    'listening_min': 40,
    'listening_max': 85,
    'thinking_min': 70,
    'thinking_max': 95,
    'speaking_min': 80,
    'speaking_max': 95,
    'pwm_frequency': 1000,
    'sub_bass_low': 20,
    'sub_bass_high': 80,
    'mid_bass_low': 80,
    'mid_bass_high': 250,
    'low_mid_low': 250,
    'low_mid_high': 500,
    'sub_bass_weight': 1.0,
    'mid_bass_weight': 1.0,
    'smoothing_normal': 0.15,
    'smoothing_beat': 0.05,
    'beat_threshold': 1.4,
    'beat_boost': 1.3,
}

# Keys that must be sent to the master as ints (vs floats)
INT_KEYS = {
    'min_duty', 'max_duty',
    'listening_min', 'listening_max',
    'thinking_min', 'thinking_max',
    'speaking_min', 'speaking_max',
    'pwm_frequency',
    'sub_bass_low', 'sub_bass_high',
    'mid_bass_low', 'mid_bass_high',
    'low_mid_low', 'low_mid_high',
}


def send_to_master(cmd_dict):
    """Send a JSON command to the master service via Unix socket."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(SOCK_PATH)
        sock.sendall(json.dumps(cmd_dict).encode('utf-8') + b'\n')
        # Read response
        data = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b'\n' in data:
                break
        sock.close()
        if data:
            return json.loads(data.decode('utf-8').strip())
        return {'status': 'ok'}
    except Exception as e:
        log.error(f"Socket error: {e}")
        return {'status': 'error', 'error': str(e)}


def audio_polling_thread():
    """Poll master service for audio data at ~10Hz and push to clients."""
    while True:
        try:
            result = send_to_master({'cmd': 'get_audio'})
            if result.get('status') != 'error' and HAS_SOCKETIO:
                socketio.emit('audio_data', result)
        except Exception:
            pass
        time.sleep(0.1)


# --- Routes ---

@app.route('/')
def index():
    return render_template('tuning.html', has_socketio=HAS_SOCKETIO)


@app.route('/api/params', methods=['GET'])
def get_params():
    result = send_to_master({'cmd': 'get_params'})
    return jsonify(result)


@app.route('/api/param', methods=['POST'])
def set_param():
    data = request.get_json()
    key = data.get('key')
    value = data.get('value')
    if key is None or value is None:
        return jsonify({'status': 'error', 'error': 'missing key or value'}), 400
    # Convert to appropriate type
    try:
        if isinstance(value, str):
            value = float(value)
        if key in INT_KEYS:
            value = int(value)
        else:
            value = float(value)
    except (ValueError, TypeError):
        pass
    result = send_to_master({'cmd': 'set_param', 'key': key, 'value': value})
    return jsonify(result)


@app.route('/api/params/bulk', methods=['POST'])
def set_params_bulk():
    """Set multiple parameters at once (for preset loading)."""
    data = request.get_json()
    params = data.get('params', {})
    results = []
    for key, value in params.items():
        try:
            if key in INT_KEYS:
                value = int(value)
            else:
                value = float(value)
        except (ValueError, TypeError):
            pass
        r = send_to_master({'cmd': 'set_param', 'key': key, 'value': value})
        results.append(r)
    return jsonify({'status': 'ok', 'results': results})


@app.route('/api/defaults', methods=['GET'])
def get_defaults():
    return jsonify(DEFAULTS)


@app.route('/api/presets', methods=['GET'])
def get_presets():
    presets = {}
    # Load built-in presets
    if os.path.exists(PRESETS_FILE):
        with open(PRESETS_FILE) as f:
            presets.update(json.load(f))
    # Load custom presets
    if os.path.exists(CUSTOM_PRESETS_FILE):
        with open(CUSTOM_PRESETS_FILE) as f:
            presets.update(json.load(f))
    return jsonify(presets)


@app.route('/api/presets/save', methods=['POST'])
def save_preset():
    data = request.get_json()
    name = data.get('name')
    params = data.get('params')
    if not name or not params:
        return jsonify({'status': 'error', 'error': 'missing name or params'}), 400
    custom = {}
    if os.path.exists(CUSTOM_PRESETS_FILE):
        with open(CUSTOM_PRESETS_FILE) as f:
            custom = json.load(f)
    custom[name] = params
    with open(CUSTOM_PRESETS_FILE, 'w') as f:
        json.dump(custom, f, indent=2)
    return jsonify({'status': 'ok'})


@app.route('/api/presets/delete', methods=['POST'])
def delete_preset():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({'status': 'error', 'error': 'missing name'}), 400
    if os.path.exists(CUSTOM_PRESETS_FILE):
        with open(CUSTOM_PRESETS_FILE) as f:
            custom = json.load(f)
        if name in custom:
            del custom[name]
            with open(CUSTOM_PRESETS_FILE, 'w') as f:
                json.dump(custom, f, indent=2)
    return jsonify({'status': 'ok'})


# --- Hardware control routes ---

@app.route('/api/magnet/on', methods=['POST'])
def magnet_on():
    data = request.get_json() or {}
    duty = data.get('duty', 100)
    return jsonify(send_to_master({'cmd': 'magnet_on', 'duty': duty}))

@app.route('/api/magnet/off', methods=['POST'])
def magnet_off():
    return jsonify(send_to_master({'cmd': 'magnet_off'}))

@app.route('/api/magnet/pulse', methods=['POST'])
def magnet_pulse():
    data = request.get_json() or {}
    pattern = data.get('pattern', 'pulse')
    return jsonify(send_to_master({'cmd': 'magnet_pulse', 'pattern': pattern}))

@app.route('/api/leds/set', methods=['POST'])
def leds_set():
    data = request.get_json() or {}
    return jsonify(send_to_master({'cmd': 'leds_set', 'r': data.get('r', 0), 'g': data.get('g', 0), 'b': data.get('b', 0)}))

@app.route('/api/leds/off', methods=['POST'])
def leds_off():
    return jsonify(send_to_master({'cmd': 'leds_off'}))

@app.route('/api/state', methods=['POST'])
def set_state():
    data = request.get_json() or {}
    return jsonify(send_to_master({'cmd': 'set_state', 'state': data.get('state', 'IDLE')}))

@app.route('/api/state', methods=['GET'])
def get_state():
    return jsonify(send_to_master({'cmd': 'get_state'}))

@app.route('/api/save', methods=['POST'])
def save_to_disk():
    return jsonify(send_to_master({'cmd': 'save_params'}))


# --- SocketIO events ---

if HAS_SOCKETIO:
    @socketio.on('set_param')
    def handle_set_param(data):
        key = data.get('key')
        value = data.get('value')
        if key is not None and value is not None:
            try:
                if key in INT_KEYS:
                    value = int(value)
                else:
                    value = float(value)
            except (ValueError, TypeError):
                pass
            result = send_to_master({'cmd': 'set_param', 'key': key, 'value': value})
            emit('param_ack', result)

    @socketio.on('get_params')
    def handle_get_params():
        result = send_to_master({'cmd': 'get_params'})
        emit('params', result)

    @socketio.on('connect')
    def handle_connect():
        log.info("Client connected")
        result = send_to_master({'cmd': 'get_params'})
        emit('params', result)


# --- SSE fallback ---

if not HAS_SOCKETIO:
    import queue

    sse_clients = []
    sse_lock = threading.Lock()

    def sse_audio_thread():
        """Poll and push to SSE clients."""
        while True:
            try:
                result = send_to_master({'cmd': 'get_audio'})
                if result.get('status') != 'error':
                    msg = f"data: {json.dumps(result)}\n\n"
                    with sse_lock:
                        dead = []
                        for q in sse_clients:
                            try:
                                q.put_nowait(msg)
                            except queue.Full:
                                dead.append(q)
                        for q in dead:
                            sse_clients.remove(q)
            except Exception:
                pass
            time.sleep(0.1)

    @app.route('/api/stream')
    def stream():
        def event_stream(q):
            try:
                while True:
                    msg = q.get(timeout=30)
                    yield msg
            except Exception:
                with sse_lock:
                    if q in sse_clients:
                        sse_clients.remove(q)

        q = queue.Queue(maxsize=50)
        with sse_lock:
            sse_clients.append(q)
        return app.response_class(event_stream(q), mimetype='text/event-stream')


if __name__ == '__main__':
    log.info(f"Flask-SocketIO available: {HAS_SOCKETIO}")
    log.info(f"Starting tuning dashboard on port 3004")

    if HAS_SOCKETIO:
        # Start audio polling in background
        t = threading.Thread(target=audio_polling_thread, daemon=True)
        t.start()
        socketio.run(app, host='0.0.0.0', port=3004, debug=False, allow_unsafe_werkzeug=True)
    else:
        # SSE fallback
        t = threading.Thread(target=sse_audio_thread, daemon=True)
        t.start()
        app.run(host='0.0.0.0', port=3004, debug=False)
