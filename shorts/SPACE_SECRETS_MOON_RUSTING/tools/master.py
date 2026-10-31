# master.py <video> <mix.wav> <out.mp4>: compress, measured gain to -14 LUFS, peak limiter (-1.5 dBTP), H.264 High 8.3 Mb/s, AAC 256k, faststart
import re, subprocess, sys
vid, wav, out = sys.argv[1:4]
def meas(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", f, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]); P = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1]); return I, P
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-af", "acompressor=threshold=-18dB:ratio=3:attack=5:release=120:makeup=3dB", "-c:a", "pcm_f32le", "mix_c.wav"], check=True)
g = -14.0 - meas("mix_c.wav")[0]
for it in range(3):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "mix_c.wav", "-af", f"volume={g:.2f}dB,alimiter=limit=0.80:level=false:attack=3:release=60", "-ar", "48000", "-c:a", "pcm_f32le", "mix_m.wav"], check=True)
    I, P = meas("mix_m.wav"); print(f"pass {it}: gain {g:+.2f} dB -> {I} LUFS, TP {P} dBFS")
    if abs(I + 14) <= 0.3: break
    g += -14.0 - I
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", vid, "-i", "mix_m.wav", "-map", "0:v", "-map", "1:a",
                "-c:v", "libx264", "-preset", "slow", "-b:v", "8300k", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p", "-profile:v", "high",
                "-r", "30", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", out], check=True)
print("mastered", out)
