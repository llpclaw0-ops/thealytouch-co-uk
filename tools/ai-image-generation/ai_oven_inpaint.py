#!/usr/bin/env python3
"""Oven pair via INPAINTING.

img2img kept returning a showroom-clean oven: the base composition (gleaming
stainless built-in oven) dominates the denoise, and raising strength globally
just changes the whole kitchen instead of soiling the cavity.

Inpainting solves it: mask ONLY the oven cavity and force the model to repaint
that region as filthy, leaving the surrounding kitchen pixel-identical. That
also guarantees the before/after are the same scene.
"""
import os, torch, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from diffusers import StableDiffusionXLInpaintPipeline, DPMSolverMultistepScheduler

RAW = "/tmp/ai-raw"
W, H = 1216, 832

base = Image.open(f"{RAW}/oven-base.png").convert("RGB").resize((W, H), Image.LANCZOS)

# Locate the dark oven cavity automatically: the largest dark region near centre.
a = np.asarray(base.convert("L")).astype(np.float32)
dark = a < 70
cols = dark.sum(0); rows = dark.sum(1)
cthr = max(cols.max() * 0.30, 25); rthr = max(rows.max() * 0.30, 25)
xs = np.where(cols > cthr)[0]; ys = np.where(rows > rthr)[0]
x0, x1 = (int(xs.min()), int(xs.max())) if len(xs) else (int(W*0.30), int(W*0.70))
y0, y1 = (int(ys.min()), int(ys.max())) if len(ys) else (int(H*0.25), int(H*0.75))
# keep it to the central cavity, not the whole dark kitchen
x0 = max(x0, int(W*0.24)); x1 = min(x1, int(W*0.76))
y0 = max(y0, int(H*0.18)); y1 = min(y1, int(H*0.80))
print("cavity box:", x0, y0, x1, y1)

mask = Image.new("L", (W, H), 0)
ImageDraw.Draw(mask).rectangle([x0, y0, x1, y1], fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(14))
mask.save(f"{RAW}/oven-mask.png")

QUALITY = ("professional interior photograph, real photo, photorealistic, "
           "sharp focus, high detail")
NEG = ("people, hands, text, letters, numbers, watermark, logo, brand, cartoon, "
       "illustration, cgi, render, anime, distorted, warped, blurry, low quality, "
       "closed oven door, shut door, food, bread, loaf, tray, dish, baking")

DIRTY = ("the inside of a disgustingly filthy neglected oven, thick black baked-on "
         "carbon crust and burnt charcoal deposits caked over the oven cavity walls "
         "and roof, dark brown sticky hardened grease, burnt spilled food debris and "
         "charred crumbs covering the wire shelf racks, filthy blackened greasy "
         "interior, years of burnt-on residue, grimy and encrusted")
CLEAN = ("the inside of an immaculate spotless oven with its door still open and "
         "lowered, gleaming clean pale enamel cavity walls, bright shining clean wire "
         "shelf racks in place, empty cavity, no grease, no burnt residue, "
         "professionally deep cleaned, hygienic and like new")

print("loading SDXL inpaint...", flush=True)
pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
    "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
    torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("mps"); pipe.set_progress_bar_config(disable=True)

def run(prompt, strength, seed, out):
    g = torch.Generator(device="cpu").manual_seed(seed)
    img = pipe(prompt=prompt + ", " + QUALITY, negative_prompt=NEG,
               image=base, mask_image=mask, width=W, height=H,
               strength=strength, num_inference_steps=40, guidance_scale=8.0,
               generator=g).images[0]
    img.save(out); print("wrote", out, flush=True)

import sys
which = sys.argv[1] if len(sys.argv)>1 else "both"
if which in ("both","before"): run(DIRTY, 0.99, 8821, f"{RAW}/oven-before.png")
if which in ("both","after"):  run(CLEAN, 0.42, 2207, f"{RAW}/oven-after.png")
print("OVEN INPAINT DONE", flush=True)
