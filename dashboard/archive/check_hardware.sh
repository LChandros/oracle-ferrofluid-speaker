#!/bin/bash
# Hardware verification for Moneo Voice Nexus

echo "=== Moneo Voice Nexus - Hardware Check ==="
echo ""

echo "1. Checking audio devices..."
echo "   Available audio devices:"
python3 -c "
import pyaudio
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        print(f'   [{i}] {info[\"name\"]} (inputs: {info[\"maxInputChannels\"]})')
p.terminate()
"

echo ""
echo "2. Checking LED library..."
python3 -c "import rpi_ws281x; print('   rpi_ws281x library: OK')" 2>/dev/null || echo "   rpi_ws281x library: MISSING"

echo ""
echo "3. Checking audio files..."
ls -lh ~/test-music.mp3 2>/dev/null && echo "   test-music.mp3: OK" || echo "   test-music.mp3: MISSING"

echo ""
echo "4. Checking scripts..."
ls ~/music_visualizer.py >/dev/null 2>&1 && echo "   music_visualizer.py: OK" || echo "   music_visualizer.py: MISSING"
ls ~/test_music_sync.sh >/dev/null 2>&1 && echo "   test_music_sync.sh: OK" || echo "   test_music_sync.sh: MISSING"

echo ""
echo "5. GPIO Pin Assignment:"
echo "   LED Strip Signal: GPIO12 (Physical Pin 32)"
echo ""
echo "=== Hardware check complete ==="
