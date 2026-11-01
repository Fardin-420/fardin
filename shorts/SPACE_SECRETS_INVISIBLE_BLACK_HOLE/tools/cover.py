import math, numpy as np
from PIL import Image, ImageDraw
import bhfx as B, earth
from bh import font, F_CAP, F_MONO, WHITE, YELLOW, BLACK, SUN_DIR, bh_lens
earth.TEX = "tex/"
arr = B.lens_view(B.plate("bulge"), [bh_lens(560, 820, 300)], off=(40, -80)) * 1.15
arr = earth.render(B.W, B.H, 250, 1700, 210, 15, -20, -28, sun=SUN_DIR, stars=arr)
img = B.finish(arr, 0.5); d = ImageDraw.Draw(img, "RGBA")
d.text((540, 250), "INVISIBLE", font=font(F_CAP, 150), fill=WHITE, anchor="mm", stroke_width=13, stroke_fill=BLACK)
d.text((540, 400), "BLACK HOLE?!", font=font(F_CAP, 132), fill=YELLOW, anchor="mm", stroke_width=13, stroke_fill=BLACK)
d.text((540, 1880), "visualization · lensing exaggerated · Earth not to scale", font=font(F_MONO, 24), fill=(220, 220, 225), anchor="mm", stroke_width=3, stroke_fill=BLACK)
img.save("/home/user/fardin/shorts/SPACE_SECRETS_INVISIBLE_BLACK_HOLE/BLACK_HOLE_COVER.png")
img.resize((540, 960)).save("cover_small.jpg", quality=88)
