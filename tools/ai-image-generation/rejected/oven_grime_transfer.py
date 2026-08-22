#!/usr/bin/env python3
"""BEFORE = the clean base with grime's TONE transferred onto it.

Why: img2img strength high enough to read as baked-on carbon (>=0.65) also
re-invents cavity hardware - the two fan discs vanish and become pipes. Below
that the cavity is not visibly dirty. There is no strength that gives both.

Split the problem. Let SDXL produce the grime at a strength that actually looks
filthy, then take only its LOW-FREQUENCY component (where soot pools, how dark
it goes) and multiply it onto the clean base. Structure - racks, fans, shelf
supports, walls - comes entirely from the base, so nothing can move. Fine grime
texture is added back only where the base is flat, so metal edges stay crisp.

Dirt absorbs light, so the tone transfer is multiplicative, not an overlay -
that is what stops it reading as a grey film pasted on top.
"""
import numpy as np
from PIL import Image, ImageFilter
import sys
sys.path.insert(0, "/Users/llp/mums-cleaning-site/tools/ai-image-generation")
from ai_tiled_dirt import feather_mask, JOBS, W, H

RAW = "/tmp/ai-raw"
BASE, DIRT = "oven-openbase", "dirtsrc-92"
SIGMA = 11.0          # tone scale: below this is structure, above is staining
RATIO_LO, RATIO_HI = 0.20, 1.00   # dirt only ever absorbs light, never adds it
TEX_GAIN = 1.00      # off: the source's high frequencies are different

def lowpass(a, sigma):
    return np.asarray(Image.fromarray(np.clip(a,0,255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(sigma))).astype(np.float32)

base = Image.open(f"{RAW}/{BASE}.png").convert("RGB").resize((W,H), Image.LANCZOS)
dirt = Image.open(f"{RAW}/{DIRT}.png").convert("RGB").resize((W,H), Image.LANCZOS)

x0,y0,x1,y1 = JOBS["oven"]["crop"]
bx = (int(x0*W), int(y0*H), int(x1*W), int(y1*H))

B = np.asarray(base.crop(bx)).astype(np.float32)
D = np.asarray(dirt.crop(bx)).astype(np.float32)

Bl, Dl = lowpass(B, SIGMA), lowpass(D, SIGMA)
ratio  = np.clip((Dl + 4.0) / (Bl + 4.0), RATIO_LO, RATIO_HI)
out    = B * ratio

# Crusty mottling. Taken from the source's LUMINANCE only and applied
# multiplicatively with a ceiling of 1.0, so it can darken but never add a
# highlight - that is what stopped the earlier attempt ghosting bright streaks
# and coloured patches over the racks. Restricted to flat wall areas so metal
# edges keep their own contrast.
Dlum  = np.asarray(Image.fromarray(D.astype(np.uint8)).convert("L")).astype(np.float32)
Dluml = lowpass(Dlum[..., None].repeat(3, 2), SIGMA)[..., 0]
hf    = Dlum - Dluml                                  # soot mottling, signed
g = np.abs(np.asarray(Image.fromarray(B.astype(np.uint8)).convert("L")
                      .filter(ImageFilter.FIND_EDGES)).astype(np.float32))
flat = np.clip(1.0 - g / 18.0, 0.0, 1.0)
tex  = np.clip(1.0 + TEX_GAIN * (hf / 90.0), 0.55, 1.0)
out *= (1.0 - flat * (1.0 - tex))[..., None]

out = np.clip(out, 0, 255).astype(np.uint8)

strip = Image.fromarray(out)
before = base.copy()
sw, sh = strip.size
before.paste(strip, bx, feather_mask(sw, sh, max(10, int(sh*0.16))))

base.save(f"{RAW}/oven-after.png")
before.save(f"{RAW}/oven-before.png")

a = np.asarray(before).astype(int); b = np.asarray(base).astype(int)
outside = np.ones((H,W), bool); outside[bx[1]:bx[3], bx[0]:bx[2]] = False
d = np.abs(a-b).sum(2)
print(f"max diff outside cavity = {int(d[outside].max())}")
print(f"mean abs change inside  = {d[~outside].mean():.1f}")
