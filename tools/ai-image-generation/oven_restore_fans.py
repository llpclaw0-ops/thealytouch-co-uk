#!/usr/bin/env python3
"""Put the two fan discs back, soiled, into the dirty cavity.

img2img at 0.65 is the only setting that makes the cavity genuinely look
filthy, but it rewrites the two fan discs on the back wall into pipework. The
discs are the single fragile detail in the frame, so rather than weaken the
dirt to protect them, restore them afterwards: take their geometry from the
clean base and darken them by the grime's own local tone, so they sit in the
dirt instead of looking wiped clean.

Deterministic - no model - so the discs cannot move or change shape.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, "/Users/llp/mums-cleaning-site/tools/ai-image-generation")
from ai_tiled_dirt import JOBS, W, H          # one definition of the cavity crop

RAW = "/tmp/ai-raw"
SRC = "assets-source/ai-raw"
# Disc centres are measured on oven-openbase.png specifically. They do not
# transfer to a different base candidate.
DISCS = [(521, 435, 58), (699, 435, 58)]     # cx, cy, r
SIGMA = 14.0

def resolve(name):
    """Prefer the working copy in /tmp, fall back to the copy kept in the repo.

    Both inputs are diffusion output, so they will not regenerate byte-for-byte
    on another machine - the repo copies are the artefacts of record, and /tmp
    does not survive a reboot.
    """
    a, b = f"{RAW}/{name}", f"{SRC}/{name}"
    if os.path.exists(a):
        return a
    if os.path.exists(b):
        return b
    raise SystemExit(f"missing input {name}: looked in {RAW} and {SRC}")

base  = Image.open(resolve("oven-openbase.png")).convert("RGB").resize((W, H), Image.LANCZOS)
# The dirty layer from `ai_tiled_dirt.py oven` (strength 0.65).
dirty = Image.open(resolve("oven-dirty-layer.png")).convert("RGB").resize((W, H), Image.LANCZOS)

B = np.asarray(base).astype(np.float32)
D = np.asarray(dirty).astype(np.float32)

def lowpass(a):
    return np.asarray(Image.fromarray(np.clip(a,0,255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(SIGMA))).astype(np.float32)

# Soil the base discs using the grime's own local tone, so they match.
ratio  = np.clip((lowpass(D) + 4.0) / (lowpass(B) + 4.0), 0.25, 1.0)
soiled = B * ratio          # ratio <= 1 and B <= 255, so already in range

m = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(m)
for cx, cy, r in DISCS:
    d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=255)
m = m.filter(ImageFilter.GaussianBlur(9))
a = (np.asarray(m).astype(np.float32) / 255.0)[..., None]

# Tried and rejected: raising the per-pixel (dirty/clean) ratio to a power >1
# to deepen the grime. It clamps brightened pixels back down and so removes the
# brown sooty highlights that actually read as filth - the result looked
# CLEANER, not dirtier. Left as a plain composite.
out = D * (1 - a) + soiled * a

before = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

os.makedirs(RAW, exist_ok=True)
base.save(f"{RAW}/oven-after.png")
before.save(f"{RAW}/oven-before.png")

nb = np.asarray(before).astype(int); na = np.asarray(base).astype(int)
diff = np.abs(nb - na).sum(2)
x0, y0, x1, y1 = JOBS["oven"]["crop"]
cav = np.zeros((H, W), bool)
cav[int(y0*H):int(y1*H), int(x0*W):int(x1*W)] = True
print("max diff outside cavity =", int(diff[~cav].max()))
print("mean change inside cavity =", round(float(diff[cav].mean()), 1))
