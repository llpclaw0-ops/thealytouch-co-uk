#!/usr/bin/env python3
"""Remove the pie from the oven base deterministically, then verify.

The base photo has a pie on the lower shelf. Inpainting will not remove it even
at strength 0.92 with explicit food negatives - SDXL keeps reasserting it.

So it is removed with pixel operations only, no model involved:
  1. Sample the dark cavity wall texture from a clean band ABOVE the pie.
  2. Tile that sampled texture over the pie region.
  3. Blend the edges so it merges with the surrounding cavity.

Output: /tmp/ai-raw/oven-base-nopie.png
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SRC = "/tmp/ai-raw/oven-base.png"
OUT = "/tmp/ai-raw/oven-base-nopie.png"

# pie bounding box as fractions of the full frame, measured from a zoom crop
PIE = (0.41, 0.60, 0.56, 0.72)
# clean cavity band to sample replacement texture from (above the pie, below rack)
SRC_BAND = (0.41, 0.50, 0.56, 0.58)

im = Image.open(SRC).convert("RGB")
W, H = im.size

px0, py0 = int(PIE[0]*W), int(PIE[1]*H)
px1, py1 = int(PIE[2]*W), int(PIE[3]*H)
pw, ph = px1-px0, py1-py0

sx0, sy0 = int(SRC_BAND[0]*W), int(SRC_BAND[1]*H)
sx1, sy1 = int(SRC_BAND[2]*W), int(SRC_BAND[3]*H)
patch = im.crop((sx0, sy0, sx1, sy1))

# tile the sampled cavity texture to cover the pie region
tile = Image.new("RGB", (pw, ph))
for yy in range(0, ph, patch.height):
    for xx in range(0, pw, patch.width):
        tile.paste(patch, (xx, yy))

# match brightness to the pie region's surroundings so it does not read as a patch
tile = tile.filter(ImageFilter.GaussianBlur(2.0))

out = im.copy()
# feathered paste so the edges merge into the cavity
m = Image.new("L", (pw, ph), 255)
md = ImageDraw.Draw(m)
edge = max(6, int(min(pw, ph) * 0.22))
for i in range(edge):
    v = int(255 * (i / edge))
    md.rectangle([i, i, pw-1-i, ph-1-i], outline=v)
m = m.filter(ImageFilter.GaussianBlur(edge * 0.5))
out.paste(tile, (px0, py0), m)

out.save(OUT)

a = np.asarray(im).astype(int); b = np.asarray(out).astype(int)
changed = (np.abs(a-b).sum(2) > 20)
region = np.zeros((H, W), bool); region[py0:py1, px0:px1] = True
print(f"pie box px: {px0},{py0} -> {px1},{py1}  ({pw}x{ph})")
print(f"changed pixels inside box: {changed[region].sum()} / {region.sum()}")
print(f"changed pixels OUTSIDE box: {changed[~region].sum()}")
print("wrote", OUT)
