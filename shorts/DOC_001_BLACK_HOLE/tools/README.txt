Rebuild FINAL_DOCUMENTARY.mp4
Needs: ffmpeg; pip install numpy scipy pillow soundfile kokoro-onnx; Kokoro model files kokoro-v1.0.onnx + voices-v1.0.bin
(github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0). Edit the model path T in tts_bh.py.
1. python3 tts_bh.py 1.1                      -> L00..L10.wav (copy to L0..L10.wav)
2. python3 align_bh.py                         -> T*.wav + timing.json (line placement, designed pauses, word timing)
3. python3 -c "import raytrace as r, numpy as n; n.save('sky.npy', r.make_sky().astype(n.uint8))"
4. python3 doc_bh.py                           -> mix.wav + video.mp4 (4 worker processes; ~10 min)
   python3 doc_bh.py preview [t1 t2 ...]       -> stills in pv/
   python3 rerender_ranges.py in.mp4 out.mp4   -> re-render selected scenes into an existing master, frame-exact
5. Master: ffmpeg acompressor(-18 dB, 3:1, +3 dB) + alimiter(0.7) -> two-pass loudnorm I=-14 TP=-1.5 + alimiter(0.76);
   H.264 High -b:v 9500k -maxrate 13M; AAC 256k 48 kHz; +faststart
Physics: Schwarzschild (non-rotating) black hole; per-camera-distance RK4 integration of d2u/dphi2 = 3u^2 - u over 6000
impact parameters; thin disk r = 6M..22M with relativistic Doppler + gravitational redshift (approximate).
