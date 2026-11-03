import sys
from PIL import ImageDraw
import sp
sp.warm()
arr = sp.plunge_view(1.3, 0.55, "A")
img = sp.finish(arr, 0.6); d = ImageDraw.Draw(img, "RGBA")
d.text((540, 420), "A STAR ATE", font=sp.font(sp.F_CAP, 138), fill=sp.WHITE, anchor="mm", stroke_width=13, stroke_fill=sp.BLACK)
d.text((540, 565), "A PLANET?!", font=sp.font(sp.F_CAP, 146), fill=sp.YELLOW, anchor="mm", stroke_width=13, stroke_fill=sp.BLACK)
img.save(sys.argv[1]); img.resize((540, 960)).save("cover_small.jpg", quality=88)
