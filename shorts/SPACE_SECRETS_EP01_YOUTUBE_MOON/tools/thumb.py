import numpy as np, gfx, earth, moonr
from PIL import Image, ImageDraw, ImageFilter
from gfx import *
arr = gfx.night_sky(0.0) * 0.6
arr = gfx.globe(1500, 1060, 640, lat0=35, lon=10, sun=(0.8, 0.3, -0.5), base=gfx.starfield() * 0.6, night_gain=3.5, ambient=0.03, half=False)
m = moonr.render(W, H, 620, 330, 300, light=(0.6, 0.15, 0.78), base=np.zeros((H, W, 3), np.float32), halo=0.35)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
fade = np.clip((xx - 330) / 380, 0, 1)
rng = np.random.default_rng(1)
noise = np.asarray(Image.fromarray((rng.random((H // 6, W // 6)) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255
fade = np.clip(fade * 1.3 - (1 - fade) * noise * 0.6, 0, 1) ** 1.3
arr = arr + m * fade[..., None]
img = gfx.to_img(gfx.tone(gfx.bloom(arr, 0.5)))
d = ImageDraw.Draw(img, "RGBA")
f1 = font(F_BLACK, 210); f0 = font(F_BOLD, 70)
d.text((90, 640), "WHAT IF...", font=f0, fill=(230, 235, 245), anchor="lm", stroke_width=4, stroke_fill=(0, 0, 0))
x = 80
for word, col in (("NO ", (255, 255, 255)), ("MORE", (255, 255, 255))):
    d.text((x, 790), word, font=f1, fill=col, anchor="lm", stroke_width=8, stroke_fill=(0, 0, 0)); x += f1.getlength(word)
d.text((80, 960), "MOON?!", font=f1, fill=(255, 212, 0), anchor="lm", stroke_width=8, stroke_fill=(0, 0, 0))
img.resize((1280, 720), Image.LANCZOS).save("/home/user/fardin/shorts/SPACE_SECRETS_EP01_YOUTUBE_MOON/THUMBNAIL_1280x720.jpg", quality=92)
