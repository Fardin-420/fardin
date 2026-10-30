#!/bin/bash
# Render each 3D scene of a story to clips/<scene>.mp4 (8fps render -> 30fps motion-interpolated)
# Usage: ./render_story.sh <story> ; scene list comes from stories.py
cd "$(dirname "$0")"
T=${TMPDIR:-/tmp}
mkdir -p ../clips
python3 -c "
import sys; sys.path.insert(0, '..')
from stories import STORIES
for s in STORIES['$1']:
    if s['type'] == 'clip': print(s['p']['clip'], s['dur'])
" | while read name dur; do
  [ -f ../clips/$name.mp4 ] && { echo "skip $name"; continue; }
  rm -rf $T/r3d_$name && mkdir -p $T/r3d_$name
  python3 scenes3d.py $name $T/r3d_$name $dur 8 12 < /dev/null > $T/r3d_$name.log 2>&1 || { echo "FAIL $name"; continue; }
  ffmpeg -nostdin -v error -y -framerate 8 -i $T/r3d_$name/f_%04d.png \
    -vf "minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:vsbmc=1,scale=576:1024:flags=lanczos" \
    -c:v libx264 -crf 16 -pix_fmt yuv420p ../clips/$name.mp4 && echo "done $name"
  rm -rf $T/r3d_$name
done
