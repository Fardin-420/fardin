Rebuild SPACE_SECRETS_EP02.mp4
Needs: ffmpeg; pip install numpy scipy pillow soundfile kokoro-onnx; Kokoro model files (kokoro-v1.0.onnx, voices-v1.0.bin
from github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0); edit path T in tts_ep02.py.
Textures (Solar System Scope, CC BY 4.0) into tex/:
  https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_day_4096.jpg
  https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_night_4096.jpg
  https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_bump_roughness_clouds_4096.jpg
1. python3 tts_ep02.py 1.1        -> L0..L6.wav
2. python3 align_ep02.py          -> T*.wav + timing.json (designed pauses, word timing)
3. python3 ep02.py                -> mix.wav + video.mp4 (4 workers, ~13 min); python3 ep02.py preview [t ...] for stills
4. Master: acompressor(-18 dB, 3:1, +3 dB) + alimiter(0.7) -> two-pass loudnorm I=-14 TP=-1.5 + alimiter(0.76);
   H.264 High -b:v 9500k -maxrate 13M; AAC 256k 48 kHz; +faststart
