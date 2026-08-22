#!/usr/bin/env python3
"""Photographic dirt COMPOSITED onto the original photo.

WHY INPAINTING WAS THE WRONG TOOL
Inpainting regenerates the masked pixels. At low strength the dirt is invisible;
at any strength where dirt actually shows, SDXL also redraws the geometry - the
kitchen island edge changed shape, the hob and sink swapped, an extra chair grew
in the living room. There is no strength value that gives visible dirt AND fixed
geometry, because both come from the same knob.

THE RIGHT TOOL
Generate dirt as a separate TEXTURE (crumbs, dust, mould, stains on a plain
background), then composite that texture onto the untouched photo using blend
modes, masked to the surface being soiled. The photo's own pixels are never
regenerated - only darkened and tinted where dirt sits - so geometry is
mathematically guaranteed identical while the dirt is real generated imagery.

AFTER  = original photo, untouched.
BEFORE = original photo + composited dirt texture inside the surface mask.
"""
import sys, torch, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageEnhance
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

RAW = "/tmp/ai-raw"
TEX = "/tmp/ai-tex"
W, H = 1216, 832

import os
os.makedirs(TEX, exist_ok=True)

# Dirt textures to generate once, then reuse. Plain flat-lay so they composite
# cleanly without importing perspective from a different scene.
TEXTURES = {
    "crumbs": ("scattered bread crumbs, biscuit crumbs, small food debris and "
               "specks of dirt spread across a plain flat white surface, "
               "overhead flat lay photograph, sharp focus, even lighting"),
    "grease": ("sticky spilled brown sauce stains, greasy smears and dried food "
               "splashes on a plain flat white surface, overhead flat lay "
               "photograph, sharp focus, even lighting"),
    "mould":  ("black mould spots and grey limescale scale marks on plain white "
               "tile grout, close up macro photograph, sharp focus"),
    "dust":   ("grey dust, fluff, lint and hair gathered on a plain flat pale "
               "surface, overhead flat lay photograph, sharp focus"),
}

NEG = ("people, hands, text, letters, numbers, watermark, logo, brand, cartoon, "
       "illustration, cgi, render, 3d, anime, furniture, room, wall, window, "
       "distorted, warped, blurry, low quality")

def make_textures():
    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe = pipe.to("mps"); pipe.set_progress_bar_config(disable=True)
    for i, (name, prompt) in enumerate(TEXTURES.items()):
        p = f"{TEX}/{name}.png"
        if os.path.exists(p):
            print("have", name); continue
        g = torch.Generator(device="cpu").manual_seed(1000 + i)
        img = pipe(prompt=prompt, negative_prompt=NEG, width=1024, height=1024,
                   num_inference_steps=34, guidance_scale=7.5, generator=g).images[0]
        img.save(p); print("wrote", p, flush=True)

# per-scene: which textures, the surface mask, and how strongly to apply
JOBS = {
    "floors":   dict(mask=(0.00, 0.44, 1.00, 0.80), tex=["crumbs", "grease"],
                     amount=0.62, darken=0.10),
    "bathroom": dict(mask=(0.00, 0.58, 1.00, 1.00), tex=["mould", "dust"],
                     amount=0.58, darken=0.12),
    "skirting": dict(mask=(0.00, 0.52, 1.00, 1.00), tex=["dust", "crumbs"],
                     amount=0.58, darken=0.12),
    "hoover":   dict(mask=(0.00, 0.60, 1.00, 1.00), tex=["crumbs", "dust"],
                     amount=0.66, darken=0.10),
}

def surface_mask(box, feather=40):
    x0, y0, x1, y1 = box
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rectangle([int(x0*W), int(y0*H), int(x1*W), int(y1*H)], fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather))

def apply_dirt(name, cfg):
    base = Image.open(f"{RAW}/{name}-base.png").convert("RGB").resize((W, H), Image.LANCZOS)
    base.save(f"{RAW}/{name}-after.png")            # AFTER: untouched

    mask = surface_mask(cfg["mask"])
    dirty = base.copy()

    for tname in cfg["tex"]:
        t = Image.open(f"{TEX}/{tname}.png").convert("RGB").resize((W, H), Image.LANCZOS)

        # Use only the texture's DARK SPECKS, not its background. Multiplying the
        # whole texture laid a grey translucent film over everything, which read
        # as a filter rather than dirt. Build an alpha from how dark each texel
        # is relative to the texture's own background, so pale background pixels
        # contribute nothing and only crumbs/mould/dust marks land on the photo.
        g = np.asarray(t.convert("L")).astype(np.float32)
        bg = float(np.percentile(g, 80))              # the texture's paper/base tone
        alpha = np.clip((bg - g) / max(bg * 0.55, 1.0), 0.0, 1.0)
        alpha = alpha ** 1.25                          # keep only the real marks
        alpha *= cfg["amount"] / len(cfg["tex"])
        amask = Image.fromarray((alpha * 255).astype(np.uint8), "L")

        # Where a speck sits, darken the photo's own pixels rather than replacing
        # them, so wood grain, grout and tile edges still read through the dirt.
        darkened = ImageChops.multiply(dirty, t)
        dirty = Image.composite(darkened, dirty, amask)

    # Slight overall dulling of the soiled area: real dirt lowers contrast.
    dull = ImageEnhance.Color(dirty).enhance(0.96)
    dull = ImageEnhance.Brightness(dull).enhance(1.0 - cfg["darken"] * 0.35)
    dirty = dull

    # Only inside the mask; everything else stays pixel-identical to the base.
    out = Image.composite(dirty, base, mask)
    out.save(f"{RAW}/{name}-before.png")

    # prove the untouched region really is identical
    a = np.asarray(out).astype(int); b = np.asarray(base).astype(int)
    mk = np.asarray(mask).astype(float) / 255.0
    outside = (mk < 0.02)
    diff = np.abs(a - b).sum(2)
    maxdiff = int(diff[outside].max()) if outside.any() else 0
    print(f"{name}: dirt applied; max pixel diff outside mask = {maxdiff}", flush=True)

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "tex":
        make_textures()
        args = [a for a in args if a != "tex"]
    for name in (args or JOBS):
        apply_dirt(name, JOBS[name])
    print("COMPOSITE DIRT DONE", flush=True)
