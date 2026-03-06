#\!/usr/bin/env python3
"""
Dynamic TTS Demo - Generate speech from any text
Usage: python3 tts-demo.py "Your text here"
       echo "Your text" | python3 tts-demo.py
"""
import subprocess
import sys
import os
from datetime import datetime

PIPER_PATH = os.path.expanduser("~/.local/bin/piper")
MODEL_PATH = os.path.expanduser("~/piper-voices/en_US-lessac-medium.onnx")
OUTPUT_DIR = os.path.expanduser("~/tts-output")

def speak(text, output_file=None):
    """Generate TTS audio from text"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"speech_{timestamp}.wav")
    
    # Run piper
    process = subprocess.Popen(
        [PIPER_PATH, "--model", MODEL_PATH, "--output_file", output_file],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    stdout, stderr = process.communicate(input=text.encode())
    
    if process.returncode == 0:
        file_size = os.path.getsize(output_file)
        print(f"✓ Generated: {output_file} ({file_size/1024:.1f} KB)")
        return output_file
    else:
        print(f"✗ Error: {stderr.decode()}")
        return None

if __name__ == "__main__":
    # Get text from args or stdin
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    elif not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    else:
        print("Usage: python3 tts-demo.py \"Your text here\"")
        print("   or: echo \"Your text\" | python3 tts-demo.py")
        sys.exit(1)
    
    if text:
        speak(text)
    else:
        print("Error: No text provided")
        sys.exit(1)
