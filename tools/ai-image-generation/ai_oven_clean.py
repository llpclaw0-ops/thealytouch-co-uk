#!/usr/bin/env python3
"""Oven AFTER derived from the BEFORE image's own geometry.

Every attempt that regenerated the clean oven from the pristine base produced
a different door position (closed) because the base has a closed-door bias and
the inpaint model re-invents the appliance.

Fix: take the DIRTY image — which already has the open door, racks and burnt
tray in exactly the right places — and inpaint ONLY the cavity to clean it.
Both frames then share the same door, same racks, same kitchen by construction.
"""
import torch, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from diffusers import StableDiffusionXLInpaintPipeline, DPMSolverMultistepScheduler

RAW = "/tmp/ai-raw"
W, H = 1216, 832

# Start from the DIRTY frame, not the pristine base.
src = Image.open(f"{RAW}/oven-before.png").convert("RGB").resize((W, H), Image.LANCZOS)

# Mask the cavity: the dark interior region. Detect it, then keep it inside the
# oven opening so the door front and kitchen stay untouched.
a = np.asarray(src.convert("L")).astype(np.float32)
dark = a < 60
cols, rows = dark.sum(0), dark.sum(1)
xs = np.where(cols > max(cols.max()*0.35, 25))[0]
ys = np.where(rows > max(rows.max()*0.35, 25))[0]
x0, x1 = (int(xs.min()), int(xs.max())) if len(xs) else (int(W*0.30), int(W*0.70))
y0, y1 = (int(ys.min()), int(ys.max())) if len(ys) else (int(H*0.20), int(H*0.66))
# clamp to the cavity opening (exclude the lowered door apron at the bottom)
x0 = max(x0, int(W*0.26)); x1 = min(x1, int(W*0.74))
y0 = max(y0, int(H*0.16)); y1 = min(y1, int(H*0.62))
print("clean mask box:", x0, y0, x1, y1)

mask = Image.new("L", (W, H), 0)
ImageDraw.Draw(mask).rectangle([x0, y0, x1, y1], fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(10))
mask.save(f"{RAW}/oven-clean-mask.png")

CLEAN = ("the inside of an immaculate spotless clean oven cavity, gleaming pale "
         "enamel interior walls, bright clean empty wire shelf racks, no grease, "
         "no burnt food, no black carbon, freshly deep cleaned, hygienic, like new, "
         "professional interior photograph, photorealistic, sharp focus")
NEG = ("dirt, grease, grime, burnt, carbon, soot, black crust, food, bread, loaf, "
       "tray, dish, baking, people, hands, text, letters, numbers, watermark, logo, "
       "cartoon, illustration, cgi, render, distorted, warped, blurry, low quality")

print("loading inpaint...", flush=True)
pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
    "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
    torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("mps"); pipe.set_progress_bar_config(disable=True)

g = torch.Generator(device="cpu").manual_seed(5150)
img = pipe(prompt=CLEAN, negative_prompt=NEG, image=src, mask_image=mask,
           width=W, height=H, strength=0.97, num_inference_steps=40,
           guidance_scale=8.5, generator=g).images[0]
img.save(f"{RAW}/oven-after.png")
print("CLEAN OVEN DONE", flush=True)
