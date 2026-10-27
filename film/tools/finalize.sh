#!/bin/bash
# Concatenate rendered segments, loudness-normalise the mix (-16 LUFS, -1 dBTP ceiling), mux, verify.
set -e
cd "$(dirname "$0")/../build"
OUT=${1:-senior_bowl_d21.mp4}
: > seg/list.txt
for s in s0 s1 s2 s3 s4 s5 s6 s7 s8; do echo "file '$s.mp4'" >> seg/list.txt; done
ffmpeg -y -loglevel error -f concat -safe 0 -i seg/list.txt -c copy video.mp4
I=$(ffmpeg -hide_banner -i mix.wav -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1 | awk '{print $2}')
G=$(python3 -c "print(round(-16.0 - ($I), 2))")
echo "mix I=$I LUFS, gain $G dB"
ffmpeg -y -loglevel error -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy \
  -af "volume=${G}dB,alimiter=limit=0.89:attack=1:release=40:level=disabled" -c:a aac -b:a 256k -ar 48000 \
  -movflags +faststart -shortest "$OUT"
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,nb_frames,sample_rate,channels -of compact "$OUT"
ffmpeg -hide_banner -i "$OUT" -map 0:a -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):"
