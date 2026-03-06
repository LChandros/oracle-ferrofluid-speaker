#!/usr/bin/env python3
"""
Oracle Audio Manager Service
Unified audio routing for the Oracle ferrofluid speaker system.

This service bridges all audio through the ALSA loopback device:
- Captures from loopback (hw:2,1)
- Plays to WM8960 speakers (hw:4,0)
- Sets WM8960 volumes on startup to prevent mute issue
- Allows oracle_led_states_music.py to visualize all audio sources

Audio Flow:
  Spotify/Qwen/ElevenLabs -> Loopback (hw:2,0) -> This Service -> Speakers (hw:4,0)
                                                         |
                                                         +-> oracle_led_states_music.py (hw:2,1)
"""

import subprocess
import time
import signal
import sys
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OracleAudioManager:
    def __init__(self):
        self.loopback_capture = 'plughw:2,1'
        self.speaker_device = 'plughw:4,0'
        self.audio_bridge = None
        self.running = True

        # Register signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        self.cleanup()
        sys.exit(0)

    def set_wm8960_volumes(self):
        """Set WM8960 volumes to prevent mute-on-boot issue"""
        logger.info("Setting WM8960 volumes...")

        commands = [
            ['amixer', '-c', '4', 'sset', 'Headphone', '127'],
            ['amixer', '-c', '4', 'sset', 'Speaker', '127'],
            ['amixer', '-c', '4', 'sset', 'Playback', '255'],
        ]

        for cmd in commands:
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                logger.info(f"Successfully executed: {' '.join(cmd)}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to execute {' '.join(cmd)}: {e}")

        # Save settings
        try:
            subprocess.run(['alsactl', 'store'], check=True, capture_output=True)
            logger.info("ALSA settings saved")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to save ALSA settings: {e}")

    def start_audio_bridge(self):
        """Start the audio bridge from loopback to speakers"""
        logger.info(f"Starting audio bridge: {self.loopback_capture} -> {self.speaker_device}")

        # Using arecord | aplay pipeline with optimal buffer settings
        arecord_cmd = [
            'arecord',
            '-D', self.loopback_capture,
            '-f', 'S16_LE',
            '-c', '2',
            '-r', '44100',
            '--buffer-size', '2048'
        ]

        aplay_cmd = [
            'aplay',
            '-D', self.speaker_device,
            '-f', 'S16_LE',
            '-c', '2',
            '-r', '44100',
            '--buffer-size', '2048'
        ]

        try:
            # Create the pipeline: arecord | aplay
            arecord_proc = subprocess.Popen(
                arecord_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            aplay_proc = subprocess.Popen(
                aplay_cmd,
                stdin=arecord_proc.stdout,
                stderr=subprocess.PIPE
            )

            # Allow arecord to receive SIGPIPE if aplay exits
            arecord_proc.stdout.close()

            self.audio_bridge = (arecord_proc, aplay_proc)
            logger.info("Audio bridge started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start audio bridge: {e}")
            return False

    def monitor_audio_bridge(self):
        """Monitor the audio bridge and restart if needed"""
        if not self.audio_bridge:
            return False

        arecord_proc, aplay_proc = self.audio_bridge

        # Check if processes are still running
        arecord_alive = arecord_proc.poll() is None
        aplay_alive = aplay_proc.poll() is None

        if not arecord_alive or not aplay_alive:
            logger.warning("Audio bridge died, attempting restart...")
            self.cleanup()
            time.sleep(1)
            return self.start_audio_bridge()

        return True

    def cleanup(self):
        """Clean up audio bridge processes"""
        if self.audio_bridge:
            arecord_proc, aplay_proc = self.audio_bridge

            logger.info("Stopping audio bridge...")
            for proc in [aplay_proc, arecord_proc]:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                except Exception as e:
                    logger.error(f"Error cleaning up process: {e}")

            self.audio_bridge = None

    def run(self):
        """Main service loop"""
        logger.info("Oracle Audio Manager starting...")

        # Set volumes on startup
        self.set_wm8960_volumes()

        # Start audio bridge
        if not self.start_audio_bridge():
            logger.error("Failed to start audio bridge on startup")
            return 1

        logger.info("Oracle Audio Manager running. Press Ctrl+C to stop.")

        # Monitor loop
        while self.running:
            try:
                if not self.monitor_audio_bridge():
                    logger.error("Failed to maintain audio bridge")
                    time.sleep(5)  # Wait before retry
                else:
                    time.sleep(2)  # Check every 2 seconds
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Unexpected error in monitor loop: {e}")
                time.sleep(5)

        self.cleanup()
        logger.info("Oracle Audio Manager stopped")
        return 0

if __name__ == '__main__':
    manager = OracleAudioManager()
    sys.exit(manager.run())
