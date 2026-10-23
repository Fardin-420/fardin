Rebuild FINAL_SHORT.mp4 (needs: pip install kokoro-onnx soundfile scipy numpy pillow; ffmpeg;
kokoro-v1.0.onnx + voices-v1.0.bin from github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0)
1. python3 tts.py am_puck 1.1     -> am_puck_N.wav; trim to L0..L4.wav (see QUALITY_REPORT; L4 uses the revised line)
2. python3 align.py               -> T*.wav + timing.json
3. python3 short.py               -> mix.wav + video.mp4   (python3 short.py preview for still frames)
4. ffmpeg two-pass loudnorm to -14 LUFS / -1 dBTP, H.264 CRF 20 (12 Mb/s cap), AAC 192k -> FINAL_SHORT.mp4
