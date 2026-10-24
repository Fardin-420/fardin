#!/bin/bash
# Render the documentary in resumable 1,800-frame segments, then join them.
cd "$(dirname "$0")"
NF=23310; STEP=1800
for ((a=0; a<NF; a+=STEP)); do
  b=$((a+STEP)); [ $b -gt $NF ] && b=$NF
  f=seg/s_$(printf %05d $a).mp4
  [ -s "$f.done" ] && continue
  python3 doc.py range $a $b $f >> render.log 2>&1 || { echo "FAILED $a" >> render.log; exit 1; }
  echo ok > "$f.done"
done
ls seg/s_*.mp4 | sort | sed "s/^/file '/; s/$/'/" > seg/list.txt
ffmpeg -y -v error -f concat -safe 0 -i seg/list.txt -c copy video.mp4 && echo "ALL DONE" >> render.log
