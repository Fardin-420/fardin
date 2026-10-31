import math, numpy as np
from PIL import Image, ImageDraw, ImageFilter
import moonfx as M
from moonfx import W, H, font, F_CAP, F_MONO, WHITE, YELLOW, BLACK
SUN = (-0.62, 0.42, 0.66)
arr = M.stars(seed=31, n=3000).copy()
arr = M.earth_disc(arr, 600, 760, 700, lon=15, lat0=8, sun=SUN)
arr = M.limb_glow(arr, 600, 760, 700, SUN, 1.3)
arr = M.moon(arr, 540, 3350, 2450, light=SUN, lat0=55, lon_c=-10, hem=0.0)
img = M.finish(arr, 0.5)
mac = M.macro_frame(M.make_macro(), 1.25, zoom=2.4, dof=False)
loupe = M.finish(mac, 0.3).resize((W, H))
cx, cy, r = 560, 1330, 300
mask = Image.new("L", (W, H), 0); ImageDraw.Draw(mask).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).ellipse((cx - r + 20, cy - r + 30, cx + r + 20, cy + r + 30), fill=200)
img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, sh.filter(ImageFilter.GaussianBlur(30)))
src = loupe.crop((540 - r, 960 - r, 540 + r, 960 + r)).resize((2 * r, 2 * r))
img.paste(src, (cx - r, cy - r), mask.crop((cx - r, cy - r, cx + r, cy + r)))
d = ImageDraw.Draw(img, "RGBA")
d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, 235), width=9)
sx, sy = 760, 1010
d.ellipse((sx - 16, sy - 16, sx + 16, sy + 16), outline=(255, 212, 0, 255), width=5)
d.line((sx - 12, sy + 12, cx + r * 0.62, cy - r * 0.78), fill=(255, 255, 255, 200), width=4)
d.text((540, 250), "THE MOON", font=font(F_CAP, 150), fill=WHITE, anchor="mm", stroke_width=13, stroke_fill=BLACK)
d.text((540, 405), "IS RUSTING?!", font=font(F_CAP, 150), fill=YELLOW, anchor="mm", stroke_width=13, stroke_fill=BLACK)
d.text((cx, cy + r + 46), "hematite grains · magnified (CGI)", font=font(F_MONO, 30), fill=(235, 235, 235), anchor="mm", stroke_width=4, stroke_fill=BLACK)
img.save("/home/user/fardin/shorts/SPACE_SECRETS_MOON_RUSTING/MOON_RUSTING_COVER.png")
img.resize((540, 960)).save("cover_small.jpg", quality=88)
