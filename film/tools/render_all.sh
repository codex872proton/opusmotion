#!/bin/bash
# Render all shot segments with two parallel workers, then report.
cd "$(dirname "$0")/../src"
FPS=${FPS:-60}
mkdir -p ../build/seg ../build/logs
run() { python3 render.py $1 $2 ../build/seg/$3.mp4 $FPS > ../build/logs/$3.log 2>&1; }
( run 0 14.6 s0; run 45.0 57.4 s5; run 66.2 69.2 s8 ) &
( run 14.6 21.4 s1; run 21.4 27.8 s2; run 27.8 35.2 s3; run 35.2 45.0 s4; run 57.4 61.5 s6; run 61.5 66.2 s7 ) &
wait
echo ALLDONE
