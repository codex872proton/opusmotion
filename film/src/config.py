import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1080, 1920
FPS = 30
FONTS = os.path.join(ROOT, "assets", "fonts")
DATA = os.path.join(ROOT, "data")
BUILD = os.path.join(ROOT, "build")

def hexc(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)

# palette (display-referred sRGB)
INK = hexc("06080B")
SLATE = hexc("10161D")
BONE = hexc("ECE6D8")
SIGNAL = hexc("FF4A2B")
AMBER = hexc("F2B33D")
ICE = hexc("A9D3EE")
