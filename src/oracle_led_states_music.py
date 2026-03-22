#!/usr/bin/env python3
"""
Oracle LED States Controller - ENHANCED v2
Research-based ferrofluid control optimizations:
- Narrowed bass range to 20-250Hz (ferrofluid responds best)
- Sub-bass (20-80Hz) primary driver, mid-bass (80-250Hz) accent
- Beat detection with transient boost
- Reduced smoothing for more responsive movement
- Direct proportional PWM mapping
"""

from rpi_ws281x import PixelStrip, Color
import RPi.GPIO as GPIO
import time
import threading
import alsaaudio
import numpy as np
import struct
import math
import random

# LED Hardware config
LED_PIN = 12
LED_COUNT = 19
LED_BRIGHTNESS = 255

# Electromagnet config
MAGNET_PIN = 23
PWM_FREQUENCY = 1000  # 1kHz PWM

# Audio config for music analysis
AUDIO_DEVICE = "/tmp/oracle_audio_fifo"  # dsnoop device for multiple capture
SAMPLE_RATE = 44100  # Match Raspotify actual output
CHUNK_SIZE = 1024

# Electromagnet pattern parameters
MAGNET_PARAMS = {
    'IDLE': {'min_duty': 0, 'max_duty': 0},           # Completely off
    'LISTENING': {'min_duty': 20, 'max_duty': 50},    # Gentle pulse
    'THINKING': {'min_duty': 15, 'max_duty': 70},     # Chaotic movement (increased range)
    'SPEAKING': {'min_duty': 30, 'max_duty': 85},     # Strong rhythmic (increased)
    'MUSIC': {'min_duty': 35, 'max_duty': 100}        # Audio-reactive (35% baseline hold)
}

# Audio analysis parameters (research-optimized)
FREQUENCY_RANGES = {
    'sub_bass': (20, 80),      # Primary driver - deepest frequencies
    'mid_bass': (80, 250),     # Accent - punchy bass
    'low_mid': (250, 500),     # Minimal influence
}

# Beat detection parameters
BEAT_HISTORY_SIZE = 20
BEAT_THRESHOLD_MULTIPLIER = 1.4  # 40% above average = beat
BEAT_BOOST_FACTOR = 1.3          # Boost PWM by 30% on beats

# Smoothing parameters
SMOOTHING_NORMAL = 0.15    # Reduced from 0.3 for faster response
SMOOTHING_BEAT = 0.05      # Minimal smoothing during beats

class OracleLEDController:
    """Controls LED states for Oracle voice assistant and music visualization"""

    def __init__(self):
        self.strip = PixelStrip(LED_COUNT, LED_PIN, 800000, 10, False, LED_BRIGHTNESS, 0)
        self.strip.begin()

        # Initialize electromagnet with PWM
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(MAGNET_PIN, GPIO.OUT)
        self.magnet_pwm = GPIO.PWM(MAGNET_PIN, PWM_FREQUENCY)
        self.magnet_pwm.start(0)  # Start at 0% duty cycle (off)

        self.current_state = 'IDLE'
        self.running = False
        self.animation_thread = None

        # Audio capture for music reactivity
        self.audio_stream = None

        # TTS audio level (for SPEAKING mode)
        self.tts_audio_level = 0.0

        # Beat detection history
        self.bass_history = []

    def set_state(self, state):
        """Set LED state: IDLE, LISTENING, THINKING, SPEAKING, MUSIC"""
        self.current_state = state

        # Stop any running animation
        if self.animation_thread and self.animation_thread.is_alive():
            self.running = False
            self.animation_thread.join(timeout=0.5)

        # Start new state
        if state == 'IDLE':
            self._set_idle()
        elif state == 'LISTENING':
            self._start_animation(self._animate_listening)
        elif state == 'THINKING':
            self._start_animation(self._animate_thinking)
        elif state == 'SPEAKING':
            self._start_animation(self._animate_speaking)
        elif state == 'MUSIC':
            self._start_animation(self._animate_music)

    def set_tts_audio_level(self, level):
        """Update TTS audio level (0.0-1.0) for SPEAKING mode"""
        self.tts_audio_level = max(0.0, min(1.0, level))

    def _start_animation(self, animation_func):
        """Start animation in background thread"""
        self.running = True
        self.animation_thread = threading.Thread(target=animation_func)
        self.animation_thread.daemon = True
        self.animation_thread.start()

    def _set_idle(self):
        """Idle state - all LEDs off, magnet COMPLETELY off with degaussing"""
        # Turn off LEDs
        for i in range(LED_COUNT):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()
        
        # AGGRESSIVE DEGAUSSING to remove residual magnetism
        # 40 rapid pulses decaying from 80% to 0%
        import time
        for cycle in range(40):
            amplitude = 80 - (cycle * 2)
            if amplitude < 0:
                amplitude = 0
            
            self.magnet_pwm.ChangeDutyCycle(amplitude)
            time.sleep(0.02)
            self.magnet_pwm.ChangeDutyCycle(0)
            time.sleep(0.02)
        
        # Final vibration shake (10 rapid pulses @ 5%)
        for i in range(10):
            self.magnet_pwm.ChangeDutyCycle(5)
            time.sleep(0.01)
            self.magnet_pwm.ChangeDutyCycle(0)
            time.sleep(0.01)
        
        # Final OFF
        self.magnet_pwm.ChangeDutyCycle(0)
        GPIO.output(MAGNET_PIN, GPIO.LOW)

    def _animate_listening(self):
        """Listening state - blue pulse with gentle magnet sine wave"""
        t = 0
        params = MAGNET_PARAMS['LISTENING']

        while self.running and self.current_state == 'LISTENING':
            # Smooth sine wave for breathing effect (slower breath)
            brightness = int(127.5 + 127.5 * math.sin(t * 1.5 * math.pi))

            # Update LEDs
            for i in range(LED_COUNT):
                self.strip.setPixelColor(i, Color(0, 0, brightness))
            self.strip.show()

            # Electromagnet gentle sine wave
            duty = params['min_duty'] + (params['max_duty'] - params['min_duty']) * \
                   (0.5 + 0.5 * math.sin(t * 1.5 * math.pi))
            self.magnet_pwm.ChangeDutyCycle(duty)

            t += 0.02
            time.sleep(0.02)

    def _animate_thinking(self):
        """Thinking state - purple rotating with MORE chaotic magnet"""
        pos = 0
        t = 0
        params = MAGNET_PARAMS['THINKING']

        while self.running and self.current_state == 'THINKING':
            for i in range(LED_COUNT):
                # Create rotating purple pattern (faster rotation)
                distance = abs(i - pos)
                if distance > LED_COUNT / 2:
                    distance = LED_COUNT - distance

                brightness = max(0, 255 - (distance * 40))
                self.strip.setPixelColor(i, Color(brightness, 0, brightness))

            self.strip.show()

            # More chaotic electromagnet pattern
            # Multiple overlapping sine waves + random noise
            chaos1 = math.sin(t * 8) * 0.3
            chaos2 = math.sin(t * 13.7) * 0.25
            chaos3 = math.sin(t * 3.2) * 0.2
            random_spike = random.uniform(-0.4, 0.4)
            
            duty_normalized = 0.5 + chaos1 + chaos2 + chaos3 + random_spike
            duty_normalized = max(0, min(1, duty_normalized))
            duty = min(100, params["min_duty"] + duty_normalized * (params["max_duty"] - params["min_duty"]))
            self.magnet_pwm.ChangeDutyCycle(duty)

            pos = (pos + 1) % LED_COUNT
            t += 0.04  # Faster timing
            time.sleep(0.04)

    def _animate_speaking(self):
        """Speaking state - green waves with STRONGER magnet pulses mimicking speech"""
        pos = 0
        t = 0
        params = MAGNET_PARAMS['SPEAKING']

        while self.running and self.current_state == 'SPEAKING':
            for i in range(LED_COUNT):
                # Create wave pattern
                distance = abs(i - pos)
                if distance > LED_COUNT / 2:
                    distance = LED_COUNT - distance

                brightness = max(0, 255 - (distance * 30))
                self.strip.setPixelColor(i, Color(0, brightness, 0))

            self.strip.show()

            # Electromagnet mimics speech patterns (MORE AGGRESSIVE)
            if self.tts_audio_level > 0.01:
                # Real TTS audio level
                duty_normalized = self.tts_audio_level
            else:
                # Simulated speech pattern - faster, more varied
                # Creates syllable-like bursts
                syllable_pulse = (math.sin(t * 18) ** 2) * (math.sin(t * 6) ** 2)
                burst_pattern = 1.0 if (t % 1.2) < 0.8 else 0.15  # Talk/pause pattern
                emphasis = 1.0 + 0.3 * math.sin(t * 2.5)  # Emphasis variation
                duty_normalized = syllable_pulse * burst_pattern * emphasis

            duty = min(100, params["min_duty"] + duty_normalized * (params["max_duty"] - params["min_duty"]))
            self.magnet_pwm.ChangeDutyCycle(duty)

            pos = (pos + 1) % LED_COUNT
            t += 0.025  # Faster speech cadence
            time.sleep(0.025)

    def _animate_music(self):
        """Music state - RESEARCH-OPTIMIZED audio-reactive ferrofluid"""
        print("\n🎵 Starting ENHANCED music visualization...")
        print("   Sub-bass (20-80Hz): Primary driver")
        print("   Mid-bass (80-250Hz): Accent")
        print("   Beat detection: ENABLED")

        # Check if we have an external audio buffer (fed by master service bridge)
        use_buffer = hasattr(self, 'audio_buffer') and self.audio_buffer is not None
        
        if use_buffer:
            print("   ✓ Using shared audio buffer from master service")
        else:
            # Fallback: open direct ALSA capture from loopback
            try:
                self.audio_stream = alsaaudio.PCM(
                    alsaaudio.PCM_CAPTURE,
                    alsaaudio.PCM_NORMAL,
                    device='plughw:2,1',
                    channels=2,
                    rate=SAMPLE_RATE,
                    format=alsaaudio.PCM_FORMAT_S16_LE,
                    periodsize=CHUNK_SIZE
                )
                print("   ✓ Direct ALSA capture from loopback (fallback)")
            except Exception as e:
                print(f"   ✗ Failed to open audio: {e}")
                print("   Falling back to demo mode...")
                self._animate_music_demo()
                return

        hue_offset = 0
        magnet_smoothed = 0.0
        self.bass_history = []
        frame_count = 0

        while self.running and self.current_state == 'MUSIC':
            try:
                # Read audio data
                if use_buffer:
                    if len(self.audio_buffer) > 0:
                        length, data = self.audio_buffer.popleft()
                    else:
                        time.sleep(0.005)
                        continue
                else:
                    length, data = self.audio_stream.read()

                frame_count += 1

                if length > 0:
                    # Convert stereo to mono
                    audio = struct.unpack(f'{length * 2}h', data)
                    mono = np.array([int((audio[i] + audio[i+1]) / 2) for i in range(0, len(audio), 2)])

                    # FFT analysis
                    fft = np.fft.rfft(mono)
                    freqs = np.fft.rfftfreq(len(mono), 1/SAMPLE_RATE)
                    magnitudes = np.abs(fft)

                    # Extract OPTIMIZED frequency bands
                    sub_bass_mask = (freqs >= 20) & (freqs < 80)
                    mid_bass_mask = (freqs >= 80) & (freqs < 250)

                    sub_bass = np.mean(magnitudes[sub_bass_mask]) if np.any(sub_bass_mask) else 0
                    mid_bass = np.mean(magnitudes[mid_bass_mask]) if np.any(mid_bass_mask) else 0

                    # Combine: Sub-bass is primary (70%), mid-bass is accent (30%)
                    combined_bass = (sub_bass * 0.7 + mid_bass * 0.3)

                    # Adaptive normalization using running peak tracker
                    if not hasattr(self, '_bass_peak'):
                        self._bass_peak = combined_bass if combined_bass > 0 else 1.0
                    if combined_bass > self._bass_peak:
                        self._bass_peak = combined_bass
                    # Slow decay so peak adapts to quieter passages
                    self._bass_peak *= 0.999
                    self._bass_peak = max(self._bass_peak, 1.0)
                    
                    # Normalize to 0-100 using adaptive peak
                    bass_level = min(100, (combined_bass / self._bass_peak) * 100)

                    # Beat detection
                    self.bass_history.append(bass_level)
                    if len(self.bass_history) > BEAT_HISTORY_SIZE:
                        self.bass_history.pop(0)

                    is_beat = False
                    if len(self.bass_history) >= 10:
                        recent_avg = sum(self.bass_history[-10:]) / 10
                        if bass_level > recent_avg * BEAT_THRESHOLD_MULTIPLIER and bass_level > 30:
                            is_beat = True

                    # Apply noise floor - ignore very quiet audio
                    if bass_level < 5:
                        bass_level = 0

                    # Map bass level onto baseline hold range
                    # min_duty = baseline that keeps ferrofluid elevated
                    # Dynamic range rides on top of baseline
                    params = MAGNET_PARAMS['MUSIC']
                    baseline = params['min_duty']
                    ceiling = params['max_duty']
                    
                    # Calculate target: baseline + bass_level maps into remaining range
                    if is_beat:
                        dynamic = min(100, bass_level * BEAT_BOOST_FACTOR)
                        smoothing = SMOOTHING_BEAT
                    else:
                        dynamic = bass_level
                        smoothing = SMOOTHING_NORMAL
                    
                    target_duty = baseline + (dynamic / 100.0) * (ceiling - baseline)

                    # Apply smoothing
                    magnet_smoothed = smoothing * magnet_smoothed + (1 - smoothing) * target_duty
                    self.magnet_pwm.ChangeDutyCycle(magnet_smoothed)

                    # Debug logging every 200 frames
                    if frame_count % 200 == 0:
                        beat_mark = " BEAT!" if is_beat else ""
                        print(f"   [AUDIO] Frame {frame_count}: sub={sub_bass:.1f} mid={mid_bass:.1f} bass={bass_level:.1f}% PWM={magnet_smoothed:.1f}%{beat_mark}")

                    # LED visualization
                    mid_mask = (freqs >= 250) & (freqs < 2000)
                    high_mask = (freqs >= 2000) & (freqs < 8000)
                    mid_level = np.mean(magnitudes[mid_mask]) if np.any(mid_mask) else 0
                    high_level = np.mean(magnitudes[high_mask]) if np.any(high_mask) else 0

                    max_mag = max(combined_bass, mid_level, high_level, 1)
                    bass_led = int((combined_bass / max_mag) * 255) if max_mag > 50 else 0
                    mid_led = int((mid_level / max_mag) * 255) if max_mag > 50 else 0
                    high_led = int((high_level / max_mag) * 255) if max_mag > 50 else 0

                    if is_beat:
                        bass_led = min(255, int(bass_led * 1.5))
                        mid_led = min(255, int(mid_led * 1.3))

                    for i in range(LED_COUNT):
                        hue = (hue_offset + i * (360 / LED_COUNT)) % 360

                        r = int(bass_led * 0.8 + high_led * 0.2)
                        g = int(mid_led * 0.9)
                        b = int(high_led * 0.8 + bass_led * 0.2)

                        wave_pos = (hue_offset / 8 + i) % LED_COUNT
                        wave_brightness = abs(math.sin(wave_pos * math.pi / LED_COUNT))

                        r = int(r * wave_brightness)
                        g = int(g * wave_brightness)
                        b = int(b * wave_brightness)

                        self.strip.setPixelColor(i, Color(g, r, b))

                    self.strip.show()
                    hue_offset = (hue_offset + 6) % 360

                else:
                    time.sleep(0.01)

            except alsaaudio.ALSAAudioError:
                time.sleep(0.01)
                continue
            except Exception as e:
                print(f"   [ERROR] Music visualization: {type(e).__name__}: {e}")
                time.sleep(0.1)
                continue

        # Cleanup
        if hasattr(self, 'audio_stream') and self.audio_stream:
            self.audio_stream.close()
            self.audio_stream = None

    def _animate_music_demo(self):
        """Demo music visualization (enhanced)"""
        hue_offset = 0
        t = 0

        while self.running and self.current_state == 'MUSIC':
            # Simulate bass with varied pattern
            bass_sim = 40 + 50 * abs(math.sin(t * 2.5))
            
            # Simulate beats
            if int(t * 2.5) % 4 == 0 and (t * 2.5) % 1 < 0.1:
                bass_sim = min(100, bass_sim * 1.8)

            self.magnet_pwm.ChangeDutyCycle(bass_sim)

            # LED demo
            intensity = int(127 + 128 * abs(math.sin(t * 2)))
            for i in range(LED_COUNT):
                hue = (hue_offset + i * (360 / LED_COUNT)) % 360
                
                if hue < 120:
                    r = intensity
                    g = int(intensity * (1 - hue/120))
                    b = 0
                elif hue < 240:
                    r = 0
                    g = intensity
                    b = int(intensity * ((hue-120)/120))
                else:
                    r = int(intensity * ((hue-240)/120))
                    g = 0
                    b = intensity

                self.strip.setPixelColor(i, Color(g, r, b))

            self.strip.show()
            hue_offset = (hue_offset + 8) % 360
            t += 0.03
            time.sleep(0.03)

    def cleanup(self):
        """Clean up LED strip and GPIO"""
        self.running = False
        if self.animation_thread and self.animation_thread.is_alive():
            self.animation_thread.join(timeout=0.5)
        if self.audio_stream:
            self.audio_stream.close()
        self._set_idle()
        self.magnet_pwm.stop()
        GPIO.cleanup()
