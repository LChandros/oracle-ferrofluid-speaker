#!/bin/bash
# Simple audio bridge: loopback capture -> speakers
# No FIFO, no tee - just pipe audio through
exec arecord -D plughw:2,1 -f S16_LE -c 2 -r 44100 -t raw 2>/dev/null |      aplay -D plughw:4,0 -f S16_LE -c 2 -r 44100 -t raw 2>/dev/null
