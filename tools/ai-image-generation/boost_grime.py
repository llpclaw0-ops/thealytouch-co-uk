#!/usr/bin/env python3
"""Make the BEFORE frames read as dirty at card size, without touching geometry.

The problem: at card size five of the six pairs looked almost identical. The
generated dirt was real but gentle - 3-5% of the band - and simply did not read
as filth in a 470px card.

The obvious fix, raising img2img strength, does not work. At 0.72 the skirting
floor's tile layout is redrawn: new seams, different marble. That breaks the
one hard requirement, that the two frames be the same image.

So keep the generation gentle and amplify what it produced, in a way that
cannot invent anything:

  dark  = how much DARKER the generated dirt is than the clean plate, per pixel
  before = after * (1 - k*dark - uniform) * warm_tint

Only darkening is used, because dirt absorbs light - it never adds a highlight.
Amplifying the raw signed difference instead turns colour shifts into lurid
teal patches and blown highlights, which is what a first attempt did. Working
in luminance and multiplying the clean pixel keeps hue and texture intact, so
the surface underneath stays exactly the surface.

`dark` is already zero everywhere the dirt was not painted, so the amplified
grime cannot leak outside the crop. The uniform dulling can, so it is masked to
the same feathered crop the dirt used.
"""
import sys, numpy as np
from PIL import Image, ImageFilter
sys.path.insert(0, "/Users/llp/mums-cleaning-site/tools/ai-image-generation")
from ai_tiled_dirt import JOBS, W, H, feather_mask

RAW = "/tmp/ai-raw"
SRC = "assets-source/ai-raw"


def resolve(name):
    """Prefer the working copy in /tmp, fall back to the copy kept in the repo.

    /tmp does not survive a reboot, and these inputs are diffusion output that
    will not regenerate byte-for-byte, so the repo copies are the artefacts of
    record.
    """
    import os
    for path in (f"{RAW}/{name}", f"{SRC}/{name}"):
        if os.path.exists(path):
            return path
    raise SystemExit(f"missing input {name}: looked in {RAW} and {SRC}")

# k = how hard to amplify the generated grime
# u = flat dulling across the cleaned surface, so it reads as "not cleaned"
BOOST = {
    "floors":   dict(k=13.0, u=0.07),
    # bathroom is NOT boosted - it is built by crevice_grime.py instead.
    # Amplifying its generated dirt produced soft airbrushed charcoal clouds
    # smeared across the toilet: the "AI slop" look. See crevice_grime.py.
    "bedroom":  dict(k=3.0, u=0.02),   # already reads clearly; barely touched
    "oven":     dict(k=15.0, u=0.13),
    "skirting": dict(k=9.0, u=0.05),
    "hoover":   dict(k=6.0, u=0.04),
}

WARM = np.array([1.0, 0.985, 0.94], np.float32)   # grime is warm, not neutral grey

def lum(x):
    return x[..., 0]*0.299 + x[..., 1]*0.587 + x[..., 2]*0.114

def boost(card):
    cfg = BOOST[card]
    # Always derive from the pristine generated dirt, never from a previous
    # boost - otherwise re-running compounds the effect.
    import os, shutil
    os.makedirs(RAW, exist_ok=True)
    raw = f"{RAW}/{card}-before-raw.png"
    if not os.path.exists(raw):
        shutil.copy(resolve(f"{card}-before-raw.png")
                    if os.path.exists(f"{SRC}/{card}-before-raw.png")
                    else resolve(f"{card}-before.png"), raw)

    after  = Image.open(resolve(f"{card}-after.png")).convert("RGB").resize((W, H), Image.LANCZOS)
    before = Image.open(raw).convert("RGB").resize((W, H), Image.LANCZOS)
    A = np.asarray(after).astype(np.float32)
    B = np.asarray(before).astype(np.float32)

    dark = np.clip(lum(A) - lum(B), 0, None) / 255.0

    x0, y0, x1, y1 = JOBS[card]["crop"]
    bx = (int(x0*W), int(y0*H), int(x1*W), int(y1*H))
    sw, sh = bx[2]-bx[0], bx[3]-bx[1]
    m = Image.new("L", (W, H), 0)
    m.paste(feather_mask(sw, sh, max(10, int(sh*0.16))), bx)
    region = np.asarray(m).astype(np.float32) / 255.0

    amount = np.clip(cfg["k"]*dark + cfg["u"]*region, 0, 0.78)
    out = A * (1.0 - amount)[..., None]
    out = out * (1.0 - (1.0 - WARM) * np.clip(amount*2.0, 0, 1)[..., None])
    out = np.clip(out, 0, 255).astype(np.uint8)

    Image.fromarray(out).save(f"{RAW}/{card}-before.png")

    d = np.abs(out.astype(int) - A.astype(int)).max(2)
    outside = region < 0.001
    print(f"{card:9} visible dirt {(d>26).mean()*100:5.1f}% of frame | "
          f"max change outside crop = {int(d[outside].max()) if outside.any() else 0}", flush=True)

if __name__ == "__main__":
    for c in (sys.argv[1:] or list(BOOST)):
        boost(c)
