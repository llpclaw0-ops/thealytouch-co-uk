#!/usr/bin/env python3
"""Dirt generated on the real surface, TILE BY TILE at native aspect ratio.

Why the previous surface-crop attempt melted:
A surface strip is very wide and short (e.g. 1216x232). Resizing that to ~1024
square-ish handed SDXL a badly distorted aspect ratio, so it hallucinated
glassy abstract shapes instead of dirt on tiles.

Fix: slide a SQUARE window along the strip, process each tile at 768x768 (no
aspect distortion at all), then reassemble with overlapping feathered blends.
Each tile still contains only surface, so there are no fixtures to redraw, and
each is geometrically undistorted so the model keeps the tile/grain structure.
"""
import sys, zlib, torch, numpy as np
from PIL import Image, ImageFilter
from diffusers import StableDiffusionXLImg2ImgPipeline, DPMSolverMultistepScheduler

RAW = "/tmp/ai-raw"
W, H = 1216, 832
TILE = 768

JOBS = {
    "floors": dict(
        # Was (0.00, 0.52, 1.00, 0.68), which sat mostly on the WHITE CABINET
        # DOORS below the worktop - the grime came out as black scribbles on
        # the cupboards with a hard horizontal cut-off. This lands on the
        # wooden worktop run itself.
        crop=(0.00, 0.46, 1.00, 0.56),
        prompt=("greasy dirty kitchen worktop, crumbs and spilled food, sticky "
                "coffee ring stains, sauce splashes, smeared grease on the "
                "counter top, unwiped work surface, realistic photograph"),
        strength=0.45),
    "bathroom": dict(
        # The bathroom no longer uses this img2img step at all - its BEFORE is
        # built deterministically by crevice_grime.py. The crop is kept here
        # because that tool and verify_pairs both read it from this table.
        # Covers the shower tray, the lower wall tiles and the floor.
        crop=(0.00, 0.55, 1.00, 1.00),
        prompt=("unused - see crevice_grime.py"),
        strength=0.45),
    "oven": dict(
        # Cavity interior ONLY. The previous crop started at y=0.34 (282px) and
        # so contained the control panel at ~290-310px; at strength 0.92 SDXL
        # duly invented a second row of knobs in the BEFORE frame only. A tile
        # must contain no fixtures, which is the whole point of this tool.
        crop=(0.30, 0.33, 0.70, 0.74),
        prompt=("filthy empty oven interior, thick black baked-on carbon crust on the "
                "walls, heavy burnt grease, charred residue, blackened grimy wire "
                "racks, no food inside, badly soiled oven, realistic photograph"),
        # Rewrites the two fan discs on the back wall into pipework at any
        # strength that dirties the cavity, so the oven card needs
        # oven_restore_fans.py afterwards - see docs/OVEN-PIPELINE.md.
        # Do not ship the output of this step alone.
        strength=0.55),
    "skirting": dict(
        crop=(0.00, 0.60, 1.00, 1.00),
        prompt=("dusty dirty tiled floor, grey dust and fluff along the edges, "
                "scuff marks, footprint smudges, dull unpolished dirty surface, "
                "realistic photograph"),
        # 0.60 redrew the tile layout itself - new seams, different marble, a
        # visibly different floor between the two frames. Kept low so the tiles
        # survive; boost_grime.py makes the grime read at card size.
        strength=0.38),
    "bedroom": dict(
        crop=(0.00, 0.52, 0.74, 1.00),
        prompt=("messy unmade bed with rumpled crumpled bedding and twisted "
                "sheets pulled loose, squashed pillows, clothes and clutter "
                "dropped on the floor beside the bed, realistic photograph"),
        strength=0.62),
    "hoover": dict(
        crop=(0.00, 0.68, 1.00, 1.00),
        prompt=("cream carpet that needs vacuuming, scattered crumbs and small "
                "bits of debris, fluff and lint caught in the pile, faint "
                "trodden dirt marks, realistic photograph"),
        # produced a heap that read as spilled plant soil, not a rug needing a hoover
        neg=", soil, earth, mud, compost, dirt pile, spill, heap, black mass",
        strength=0.45),
}

# CLIP truncates at 77 tokens. The full list ran to 99, so everything after
# "damaged cabinets" was silently dropped and never had any effect. Trimmed
# to the 75 tokens that were actually applied - same behaviour, no pretence.
NEG = ("food, pie, bread, cake, tray, dish, plate, clean, spotless, shiny, "
       "people, hands, feet, furniture, wall, window, reflection, "
       "text, letters, numbers, watermark, logo, cartoon, illustration, cgi, "
       "render, 3d, abstract, pattern, distorted, warped, melted, smeared, "
       "damaged cabinets")

def feather_mask(w, h, edge):
    m = Image.new("L", (w, h), 0)
    a = np.zeros((h, w), np.float32)
    ys = np.minimum(np.arange(h), h - 1 - np.arange(h)) / max(edge, 1)
    xs = np.minimum(np.arange(w), w - 1 - np.arange(w)) / max(edge, 1)
    a[:] = np.clip(np.minimum.outer(ys, np.ones(w)), 0, 1)
    a *= np.clip(np.minimum.outer(np.ones(h), xs), 0, 1)
    m = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "L")
    return m.filter(ImageFilter.GaussianBlur(edge * 0.35))

BASE_OVERRIDE = {"oven": "oven-openbase"}

def run(name, cfg, pipe):
    src = BASE_OVERRIDE.get(name, f"{name}-base")
    base = Image.open(f"{RAW}/{src}.png").convert("RGB").resize((W, H), Image.LANCZOS)
    base.save(f"{RAW}/{name}-after.png")

    x0, y0, x1, y1 = cfg["crop"]
    bx = (int(x0*W), int(y0*H), int(x1*W), int(y1*H))
    strip = base.crop(bx)
    sw, sh = strip.size
    result = strip.copy()

    # square windows sliding across the strip, 45% overlap
    win = min(sh, TILE // 2) if sh < TILE else sh
    win = max(win, 192)
    step = int(win * 0.55)
    xs = list(range(0, max(sw - win, 0) + 1, step))
    if xs[-1] != sw - win: xs.append(max(sw - win, 0))

    for i, sx in enumerate(xs):
        tile = strip.crop((sx, 0, min(sx + win, sw), sh))
        tw, th = tile.size
        work = tile.resize((TILE, TILE), Image.LANCZOS)   # square in, square out
        # zlib.crc32, not hash(): Python randomises string hashing per
        # process, so the old seed differed on every run and no card could
        # be regenerated identically.
        seed = (zlib.crc32(name.encode()) + i * 17) % 90000
        g = torch.Generator(device="cpu").manual_seed(seed)
        neg = NEG + cfg.get("neg", "")
        out = pipe(prompt=cfg["prompt"], negative_prompt=neg, image=work,
                   strength=cfg["strength"], num_inference_steps=36,
                   guidance_scale=7.0, generator=g).images[0]
        out = out.resize((tw, th), Image.LANCZOS)
        result.paste(out, (sx, 0), feather_mask(tw, th, max(10, int(min(tw, th) * 0.16))))

    dirty = base.copy()
    edge = max(10, int(sh * 0.16))
    dirty.paste(result, bx, feather_mask(sw, sh, edge))
    dirty.save(f"{RAW}/{name}-before.png")

    a = np.asarray(dirty).astype(int); b = np.asarray(base).astype(int)
    outside = np.ones((H, W), bool); outside[bx[1]:bx[3], bx[0]:bx[2]] = False
    print(f"{name}: {len(xs)} tiles of {win}px | max diff outside = "
          f"{int(np.abs(a-b).sum(2)[outside].max())}", flush=True)

if __name__ == "__main__":
    names = sys.argv[1:] or list(JOBS)
    print("loading img2img...", flush=True)
    pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe = pipe.to("mps"); pipe.set_progress_bar_config(disable=True)
    for n in names:
        run(n, JOBS[n], pipe)
    print("TILED DIRT DONE", flush=True)
