#!/usr/bin/env python3
"""Dirt generated IN PLACE on a tight crop of the real surface.

Why the previous two approaches failed:
- Full-frame inpainting: any strength that made dirt visible also let SDXL
  redraw fixtures (hob/sink swapped, extra chair appeared).
- Composited flat-lay textures: SDXL produced smooth blobs rather than distinct
  crumbs, so they read as smears and greasy film laid over the photo.

This approach: crop ONLY the surface strip (worktop, floor, carpet), run img2img
on that crop alone at high strength, then paste it back with a feathered edge.
Because the crop contains nothing but the surface, there are no fixtures for the
model to redraw - it can only alter the surface it was given. The rest of the
frame is never touched, so geometry outside the strip is bit-identical.
"""
import sys, os, torch, numpy as np
from PIL import Image, ImageFilter
from diffusers import StableDiffusionXLImg2ImgPipeline, DPMSolverMultistepScheduler

RAW = "/tmp/ai-raw"
W, H = 1216, 832

# crop = (x0, y0, x1, y1) as fractions: the surface strip only.
JOBS = {
    "floors": dict(
        crop=(0.00, 0.50, 1.00, 0.78),
        prompt=("close up of a dirty kitchen worktop surface, scattered bread "
                "crumbs and food debris, sticky brown spill stains, greasy "
                "smears and dried splashes, unwiped messy counter, "
                "photograph, sharp focus, natural light"),
        strength=0.42),
    "bathroom": dict(
        crop=(0.00, 0.68, 1.00, 1.00),
        prompt=("close up of a dirty bathroom tiled floor, black mould in the "
                "grout lines, grey limescale marks, soap scum and water stains, "
                "grubby unwashed tiles, photograph, sharp focus"),
        strength=0.42),
    "skirting": dict(
        crop=(0.00, 0.62, 1.00, 1.00),
        prompt=("close up of a dusty dirty floor, grey dust and fluff gathered "
                "in the corners, scuff marks and footprint smudges, dull "
                "unpolished surface, photograph, sharp focus"),
        strength=0.40),
    "hoover": dict(
        crop=(0.00, 0.70, 1.00, 1.00),
        prompt=("close up of a dirty cream carpet, scattered crumbs and small "
                "bits of debris, fluff and lint on the pile, faint dirt marks "
                "trodden in, needs vacuuming, photograph, sharp focus"),
        strength=0.44),
}

NEG = ("people, hands, feet, furniture, wall, window, door, text, letters, "
       "numbers, watermark, logo, cartoon, illustration, cgi, render, 3d, "
       "distorted, warped, melted, smeared, blurry, out of focus, low quality")

def run(name, cfg, pipe):
    base = Image.open(f"{RAW}/{name}-base.png").convert("RGB").resize((W, H), Image.LANCZOS)
    base.save(f"{RAW}/{name}-after.png")                # AFTER: untouched

    x0, y0, x1, y1 = cfg["crop"]
    box = (int(x0*W), int(y0*H), int(x1*W), int(y1*H))
    crop = base.crop(box)
    cw, ch = crop.size

    # SDXL wants dimensions divisible by 8 and works best near 1024 wide.
    tw = 1024
    th = max(256, int(round(ch * (tw / cw) / 8)) * 8)
    work = crop.resize((tw, th), Image.LANCZOS)

    g = torch.Generator(device="cpu").manual_seed(abs(hash(name)) % 90000)
    out = pipe(prompt=cfg["prompt"], negative_prompt=NEG, image=work,
               strength=cfg["strength"], num_inference_steps=40,
               guidance_scale=7.5, generator=g).images[0]
    out = out.resize((cw, ch), Image.LANCZOS)

    # Feathered paste so the strip edge does not show as a hard line.
    m = Image.new("L", (cw, ch), 255)
    feather = max(12, int(ch * 0.18))
    px = m.load()
    for yy in range(ch):
        top = min(1.0, yy / feather)
        bot = min(1.0, (ch - 1 - yy) / feather)
        v = int(255 * min(top, bot) ** 0.8)
        for xx in range(cw):
            px[xx, yy] = v
    m = m.filter(ImageFilter.GaussianBlur(6))

    dirty = base.copy()
    dirty.paste(out, box, m)
    dirty.save(f"{RAW}/{name}-before.png")

    a = np.asarray(dirty).astype(int); b = np.asarray(base).astype(int)
    outside = np.ones((H, W), bool); outside[box[1]:box[3], box[0]:box[2]] = False
    md = int(np.abs(a-b).sum(2)[outside].max())
    print(f"{name}: crop {box} strength {cfg['strength']} | max diff outside = {md}", flush=True)

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
    print("SURFACE DIRT DONE", flush=True)
