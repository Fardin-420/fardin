#!/usr/bin/env bash
# build.sh — full pipeline: timeline -> narration -> timing solve -> music/SFX -> mix -> frames -> encode
#
#   npm run build            full 1080x1920 master + preview + srt + contact sheet + QC report
#   npm run preview          fast 540x960 render of every frame (+ audio) -> out/preview_540x960.mp4
#   npm run audio            audio only (narration, music, sfx, mix)
#
# Requirements: Node 20+, Python 3 (numpy scipy soundfile edge-tts pyloudnorm), ffmpeg/ffprobe.
set -euo pipefail
cd "$(dirname "$0")/.."

MODE="full"
for a in "$@"; do
  case "$a" in
    --preview) MODE="preview" ;;
    --audio-only) MODE="audio" ;;
  esac
done

# edge-tts (aiohttp) needs the proxy CA bundle in sandboxed/cloud environments; harmless elsewhere.
if [[ -z "${SSL_CERT_FILE:-}" && -f /root/.ccr/ca-bundle.crt ]]; then export SSL_CERT_FILE=/root/.ccr/ca-bundle.crt; fi

step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
mkdir -p build out

step "1/7 timeline (nominal)"
node src/timeline.js --dump

step "2/7 narration (edge-tts or ./narration.wav)"
python3 audio/tts.py

step "3/7 resolve frame-accurate timeline from narration timing"
node src/timeline.js --resolve

step "4/7 procedural music + SFX"
python3 audio/synth.py

step "5/7 mix (ducking, -14 LUFS, true-peak limiter)"
python3 audio/mix.py

node scripts/export_srt.js

if [[ "$MODE" == "audio" ]]; then echo "audio done: build/audio/mix.wav"; exit 0; fi

mux() { # $1 video-only in, $2 out, extra args...
  local vin="$1" out="$2"; shift 2
  ffmpeg -y -v error -i "$vin" -i build/audio/mix.wav -map 0:v:0 -map 1:a:0 "$@" \
    -c:a aac -b:a 192k -ar 48000 -ac 2 -movflags +faststart -shortest "$out"
}

if [[ "$MODE" == "preview" ]]; then
  step "6/7 render preview frames (540x960, every frame)"
  node src/render.js --out build/video_540.mp4 --scale 0.5
  step "7/7 mux preview"
  mux build/video_540.mp4 out/preview_540x960.mp4 -c:v copy
  echo "preview: out/preview_540x960.mp4"
  exit 0
fi

step "6/7 render 1800 frames (1080x1920) + encode H.264 CRF 18"
node src/render.js --out build/video.mp4 --scale 1

step "7/7 mux master, preview, contact sheet"
mux build/video.mp4 out/ww2_germany_60s.mp4 -c:v copy
ffmpeg -y -v error -i out/ww2_germany_60s.mp4 -vf "scale=540:960:flags=lanczos,format=yuv420p" \
  -c:v libx264 -preset veryfast -crf 20 -c:a copy -movflags +faststart out/preview_540x960.mp4
node scripts/contact_sheet.js

step "QC"
node scripts/qc.js
