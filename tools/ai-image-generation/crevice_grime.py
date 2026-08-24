#!/usr/bin/env python3
"""Bathroom grime built from the room's own geometry, not painted on top.

The generated-and-amplified approach produced exactly the look people mean by
"AI slop": soft airbrushed charcoal clouds with feathered edges, smeared in
streaks across the toilet cistern and floating on the wooden wall. Amplifying
the darkening of a low-strength img2img can only ever yield amorphous blobs -
they ignore the form of whatever they sit on, and sooty black on porcelain is
not how a toilet gets dirty anyway.

Real bathroom grime follows geometry. Mould grows in grout lines, silicone
seams and corners, because that is where water sits. Limescale is pale, not
black, and collects where water runs and dries. So derive the dirt from the
clean plate's own structure:

  crevice  where a pixel is darker than its surroundings - grout lines, seams,
           the gaps between mosaic tiles, the join at the floor
  settled  a downward bias, because grime collects low and in corners
  speckle  fixed-seed noise so it breaks up instead of reading as a wash

Grime is then multiplied in, tinted, and deliberately held back on large smooth
bright areas so the porcelain gets a dull film rather than soot. Nothing is
generated, so nothing can be invented, and because the grime is keyed to the
tile grid it cannot float free of the surface.
"""
import sys, numpy as np
from PIL import Image, ImageFilter
sys.path.insert(0, "/Users/llp/mums-cleaning-site/tools/ai-image-generation")
from ai_tiled_dirt import JOBS, W, H, feather_mask

RAW = "/tmp/ai-raw"
SRC = "assets-source/ai-raw"

CFG = {
    "skirting": dict(
        # Marble checkerboard. The grout grid is the whole story: ingrained
        # dirt in the lines, dulling across the tile faces.
        crevice=1.35, settled=0.55, film=0.10, porcelain=0.55,
        mottle=0.50, lime=0.0, streak=0.0,
        tint=(1.0, 0.955, 0.90),
    ),
    "hoover": dict(
        # Cream carpet. No grout to work with, so mottling does the work -
        # trodden dirt patches - with speckle reading as crumbs and lint.
        crevice=0.55, settled=0.35, film=0.09, porcelain=0.75,
        mottle=0.70, lime=0.0, streak=0.0,
        tint=(1.0, 0.945, 0.875),
    ),
    "floors": dict(
        # Wooden worktop. Grease smears and spills, heavier toward the join
        # with the splashback where wiping misses.
        crevice=0.90, settled=0.60, film=0.10, porcelain=0.60,
        mottle=0.62, lime=0.0, streak=0.0,
        tint=(1.0, 0.935, 0.855),
    ),
    "bathroom": dict(
        # Tuned for a LIGHT room. The old plate was dim with black mosaic, so
        # darkening was invisible and pale limescale had to carry everything.
        # On cream tiles and a white tray it is the other way round: dark grime
        # in the grout and around the tray edge reads instantly, and pale
        # deposits barely show. So the dark terms lead and lime is kept small,
        # just enough for dried water streaks on the glass.
        crevice=0.95,
        settled=0.45,
        film=0.13,
        porcelain=0.45,
        tint=(1.0, 0.935, 0.855),
        lime=0.12,
        streak=0.20,
        mottle=0.42,   # scum spread over the tray and floor, not just in lines
    ),
}

def resolve(name):
    import os
    for p in (f"{RAW}/{name}", f"{SRC}/{name}"):
        if os.path.exists(p):
            return p
    raise SystemExit(f"missing {name}")

def run(card):
    c = CFG[card]
    after = Image.open(resolve(f"{card}-after.png")).convert("RGB").resize((W, H), Image.LANCZOS)
    A = np.asarray(after).astype(np.float32)
    L = A[..., 0]*0.299 + A[..., 1]*0.587 + A[..., 2]*0.114

    blur = np.asarray(Image.fromarray(L.astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(4))).astype(np.float32)
    crevice = np.clip((blur - L) / 26.0, 0, 1)          # darker than neighbours
    crevice = np.asarray(Image.fromarray((crevice*255).astype(np.uint8))
                         .filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32)/255.0

    x0, y0, x1, y1 = JOBS[card]["crop"]
    bx = (int(x0*W), int(y0*H), int(x1*W), int(y1*H))
    sw, sh = bx[2]-bx[0], bx[3]-bx[1]
    m = Image.new("L", (W, H), 0)
    m.paste(feather_mask(sw, sh, max(10, int(sh*0.16))), bx)
    region = np.asarray(m).astype(np.float32)/255.0

    ys = np.linspace(0, 1, H)[:, None] * np.ones((1, W), np.float32)
    low = np.clip((ys - y0) / max(y1 - y0, 1e-6), 0, 1) ** 1.5      # heavier toward the floor

    rng = np.random.RandomState(20260822)
    speck = rng.rand(H, W).astype(np.float32)
    speck = np.asarray(Image.fromarray((speck*255).astype(np.uint8))
                       .filter(ImageFilter.GaussianBlur(1.1))).astype(np.float32)/255.0
    speck = 0.55 + 0.9*speck

    # porcelain and other big bright smooth areas take only a fraction
    smooth = 1.0 - np.clip(crevice*3.0, 0, 1)
    bright = np.clip((L - 120.0)/80.0, 0, 1)
    shield = 1.0 - (bright*smooth)*(1.0 - c["porcelain"])

    # Soiling spread ACROSS surfaces, not only along lines. The crevice term
    # alone traced dark outlines around the bath and vanity, because a strong
    # object silhouette is "darker than its surroundings" too - it read as an
    # edge-detect effect. Mottling is low-frequency noise laid on the flat
    # areas between edges, which is what scum on a tray or floor looks like.
    mot = np.asarray(Image.fromarray((rng.rand(H, W)*255).astype(np.uint8))
                     .filter(ImageFilter.GaussianBlur(26))).astype(np.float32)/255.0
    mot = np.clip((mot - 0.42) * 2.6, 0, 1)
    mottle = c.get("mottle", 0.0) * mot * smooth * (0.35 + 0.65*low)

    amount = (c["crevice"]*crevice*speck
              + c["settled"]*low*crevice*2.0
              + mottle
              + c["film"]*low) * region * shield
    amount = np.clip(amount, 0, 0.80)

    out = A * (1.0 - amount)[..., None]
    tint = np.array(c["tint"], np.float32)
    out = out * (1.0 - (1.0 - tint)*np.clip(amount*2.2, 0, 1)[..., None])

    # Pale deposits. Limescale collects in the same grout and seams the mould
    # does, so it is keyed to the same crevice map; the streaks run vertically
    # because that is the way water dries. Added toward white, and only where
    # the surface is dark enough for a chalky deposit to show.
    runs = rng.rand(1, W).astype(np.float32).repeat(H, 0)
    runs = np.asarray(Image.fromarray((runs*255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(2.2))).astype(np.float32)/255.0
    runs = np.clip((runs - 0.45) * 3.0, 0, 1)
    vary = np.asarray(Image.fromarray((rng.rand(H, W)*255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(9))).astype(np.float32)/255.0

    dark_enough = np.clip((150.0 - L) / 110.0, 0, 1)
    lime = (c["lime"]*crevice*speck + c["streak"]*runs*vary*low) * region * dark_enough
    lime = np.clip(lime, 0, 0.55)
    chalk = np.array([232, 234, 231], np.float32)
    out = out + (chalk - out) * lime[..., None]
    out = np.clip(out, 0, 255).astype(np.uint8)

    Image.fromarray(out).save(f"{RAW}/{card}-before.png")
    d = np.abs(out.astype(int) - A.astype(int)).max(2)
    outside = region < 0.001
    print(f"{card}: dirt {(d>26).mean()*100:.1f}% of frame | "
          f"outside crop max = {int(d[outside].max()) if outside.any() else 0}", flush=True)

if __name__ == "__main__":
    import os
    os.makedirs(RAW, exist_ok=True)
    for card in (sys.argv[1:] or list(CFG)):
        run(card)
