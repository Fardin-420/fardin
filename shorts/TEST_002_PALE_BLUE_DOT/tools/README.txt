Rebuild FINAL_SHORT.mp4 (needs: pip install kokoro-onnx soundfile scipy numpy pillow; ffmpeg; Kokoro model files
kokoro-v1.0.onnx + voices-v1.0.bin from github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0;
tts2.py expects them in the parent directory of the working folder, so edit the path T at its top)
1. python3 tts2.py      -> L0..L4.wav (trimmed narration lines)
2. python3 align.py     -> T*.wav + timing.json (1.05x tempo, line placement, word timing)
3. python3 short2.py    -> mix.wav + video.mp4   (python3 short2.py preview for still frames)
4. master: acompressor (-18 dB, 3:1) + alimiter, then two-pass loudnorm to -14 LUFS / -1.5 dBTP target with a final
   alimiter at 0.76; H.264 CRF 20 capped at 12 Mb/s; AAC 192k -> FINAL_SHORT.mp4
