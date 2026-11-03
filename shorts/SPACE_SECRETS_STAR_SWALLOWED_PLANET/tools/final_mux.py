# final_mux.py <video_final_v.mp4> <mix.wav> <out.mp4>: loudness-matched AAC 48 kHz 320 kb/s; video stream copied (no re-encode)
import re, subprocess, sys
vid, wav, out = sys.argv[1:4]
def meas(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", f, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]), float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-af", "acompressor=threshold=-18dB:ratio=3:attack=5:release=120:makeup=3dB", "-c:a", "pcm_f32le", "mix_c.wav"], check=True)
g = -14.0 - meas("mix_c.wav")[0]
for it in range(3):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "mix_c.wav", "-af", f"volume={g:.2f}dB,alimiter=limit=0.80:level=false:attack=3:release=60", "-ar", "48000", "-c:a", "pcm_f32le", "mix_m.wav"], check=True)
    I, P = meas("mix_m.wav"); print(f"pass {it}: {g:+.2f} dB -> {I} LUFS, {P} dBTP")
    if abs(I + 14) <= 0.3: break
    g += -14.0 - I
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", vid, "-i", "mix_m.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart", "-shortest", out], check=True)
print("muxed", out)
