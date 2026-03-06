#!/usr/bin/env python3
"""
Interactive TTS with Voice Selection and Visualization
Usage: python3 speak.py [--visualize]
"""
import subprocess
import sys
import os
import argparse
from datetime import datetime

PIPER_PATH = os.path.expanduser("~/.local/bin/piper")
VOICES_DIR = os.path.expanduser("~/piper-voices")
OUTPUT_DIR = os.path.expanduser("~/tts-output")

VOICES = {
    "1": ("US Male (Lessac)", "en_US-lessac-medium.onnx"),
    "2": ("US Female (Amy)", "en_US-amy-medium.onnx"),
    "3": ("British Male (Alan)", "en_GB-alan-medium.onnx"),
}

# Try to import visualizer (requires sudo and hardware)
VISUALIZER_AVAILABLE = False
try:
    # Check if running as root (required for LED control)
    if os.geteuid() == 0:
        sys.path.insert(0, os.path.expanduser("~"))
        from tts_visualizer import TTSVisualizer
        VISUALIZER_AVAILABLE = True
except Exception as e:
    pass

def list_voices():
    """Show available voices"""
    print("\n🎤 Available Voices:")
    for key, (name, _) in VOICES.items():
        print(f"  {key}. {name}")
    print()

def speak(text, voice_file, play=True, visualize=False):
    """Generate and optionally play TTS audio with visualization"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"speech_{timestamp}.wav")
    
    model_path = os.path.join(VOICES_DIR, voice_file)
    
    # Generate audio
    print(f"🔊 Generating audio...")
    process = subprocess.Popen(
        [PIPER_PATH, "--model", model_path, "--output_file", output_file],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    stdout, stderr = process.communicate(input=text.encode())
    
    if process.returncode != 0:
        print(f"❌ Error: {stderr.decode()}")
        return None
    
    file_size = os.path.getsize(output_file)
    print(f"✅ Generated: {output_file} ({file_size/1024:.1f} KB)")
    
    # Play audio (with or without visualization)
    if play:
        if visualize and VISUALIZER_AVAILABLE:
            print("🎨 Playing with visualization...")
            try:
                visualizer = TTSVisualizer()
                visualizer.run(output_file)
            except Exception as e:
                print(f"⚠️  Visualization error: {e}")
                print("▶️  Falling back to simple playback...")
                subprocess.run(["aplay", "-q", "-D", "plughw:3,0", output_file])
        else:
            print("▶️  Playing...")
            subprocess.run(["aplay", "-q", "-D", "plughw:3,0", output_file])
    
    return output_file

def main():
    """Interactive TTS loop"""
    # Parse arguments
    parser = argparse.ArgumentParser(description="TTS with optional visualization")
    parser.add_argument("--visualize", action="store_true", 
                       help="Enable LED + electromagnet visualization (requires sudo)")
    args = parser.parse_args()
    
    # Check visualization availability
    visualize_enabled = args.visualize
    if visualize_enabled and not VISUALIZER_AVAILABLE:
        print("⚠️  Visualization not available. Run with sudo for LED/magnet control:")
        print("    sudo python3 ~/speak.py --visualize")
        print()
        visualize_enabled = False
    
    # Header
    print("=" * 60)
    if visualize_enabled:
        print("🎙️  DYNAMIC TTS - With Visualization! 🧲💡")
    else:
        print("🎙️  DYNAMIC TTS - Fuck ElevenLabs Edition")
    print("=" * 60)
    
    if visualize_enabled:
        print("✨ Visualization ENABLED - LEDs + Electromagnet active!")
    
    # Select voice
    list_voices()
    while True:
        choice = input("Select voice (1-3, or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            print("👋 Goodbye!")
            sys.exit(0)
        if choice in VOICES:
            voice_name, voice_file = VOICES[choice]
            print(f"✓ Selected: {voice_name}\n")
            break
        print("❌ Invalid choice, try again\n")
    
    # TTS loop
    while True:
        print("-" * 60)
        
        # Build prompt
        prompt = "\n📝 Enter text to speak"
        if not visualize_enabled and VISUALIZER_AVAILABLE:
            prompt += " (or 'z' to enable visualization)"
        prompt += " (or 'q' to quit, 'v' to change voice): "
        
        text = input(prompt).strip()
        
        if text.lower() == 'q':
            print("👋 Goodbye!")
            break
        elif text.lower() == 'v':
            list_voices()
            while True:
                choice = input("Select voice (1-3): ").strip()
                if choice in VOICES:
                    voice_name, voice_file = VOICES[choice]
                    print(f"✓ Selected: {voice_name}\n")
                    break
                print("❌ Invalid choice, try again\n")
            continue
        elif text.lower() == 'z' and VISUALIZER_AVAILABLE and not visualize_enabled:
            visualize_enabled = True
            print("✨ Visualization ENABLED!")
            continue
        elif not text:
            print("⚠️  No text entered, try again")
            continue
        
        speak(text, voice_file, play=True, visualize=visualize_enabled)
        print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted, goodbye!")
        sys.exit(0)
