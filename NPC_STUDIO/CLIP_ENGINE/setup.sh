#!/usr/bin/env bash
# One-time setup: Python env + models (all fetched from GitHub releases / PyPI).
set -euo pipefail
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || { echo "ffmpeg (with libass) is required"; exit 1; }
command -v uv >/dev/null || pip3 install --user uv
uv venv --python 3.13 .venv -q 2>/dev/null || uv venv .venv -q
uv pip install --python .venv/bin/python -q -r requirements.txt
mkdir -p models && cd models
B=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models
M=sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8
[ -f "$M/encoder.int8.onnx" ] || { curl -fsSL -O "$B/$M.tar.bz2" && tar xjf "$M.tar.bz2" && rm "$M.tar.bz2"; }
[ -f silero_vad.onnx ] || curl -fsSL -O "$B/silero_vad.onnx"
[ -s face_detection_yunet_2023mar.onnx ] && [ "$(stat -c%s face_detection_yunet_2023mar.onnx)" -gt 100000 ] || \
  curl -fsSL -o face_detection_yunet_2023mar.onnx \
  https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
echo "npc-clip setup complete"
