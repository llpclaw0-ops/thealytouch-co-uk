#!/usr/bin/env python3
"""Oven pair, final approach: DIRTY the clean base, never regenerate the clean.

Six attempts at generating a clean frame failed the same way: any mask large
enough to clean the cavity gives SDXL enough freedom to re-invent the appliance
(door closed, door missing, dishwasher control panel, invented food).

Inverting the problem removes the failure entirely:
  AFTER  = the original base photo, UNTOUCHED. Perfect geometry, guaranteed.
  BEFORE = the same photo with ONLY the cavity interior inpainted dirty.

The door, hinges, kitchen and worktop are then pixel-identical by construction,
because the after is not generated at all.
"""
import torch, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from diffusers import StableDiffusionXLInpaintPipeline, DPMSolverMultistepScheduler

RAW = "/tmp/ai-raw"
W, H = 1216, 832

base = Image.open(f"{RAW}/oven-base.png").convert("RGB").resize((W, H), Image.LANCZOS)

# The AFTER is the untouched base. No generation, no drift.
base.save(f"{RAW}/oven-after.png")
print("after = untouched base")

# Mask only the dark cavity interior of the clean oven.
a = np.asarray(base.convert("L")).astype(np.float32)
dark = a < 70
cols, rows = dark.sum(0), dark.sum(1)
xs = np.where(cols > max(cols.max() * 0.40, 25))[0]
ys = np.where(rows > max(rows.max() * 0.40, 25))[0]
x0, x1 = (int(xs.min()), int(xs.max())) if len(xs) else (int(W * 0.30), int(W * 0.70))
y0, y1 = (int(ys.min()), int(ys.max())) if len(ys) else (int(H * 0.22), int(H * 0.64))
# stay strictly inside the opening so the door frame and kitchen are never touched
x0 = max(x0, int(W * 0.28)); x1 = min(x1, int(W * 0.72))
y0 = max(y0, int(H * 0.20)); y1 = min(y1, int(H * 0.62))
print("dirty mask box:", x0, y0, x1, y1)

mask = Image.new("L", (W, H), 0)
ImageDraw.Draw(mask).rectangle([x0, y0, x1, y1], fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(12))

DIRTY = ("the inside of a filthy neglected oven, thick black baked-on carbon crust "
         "coating the interior walls, heavy burnt grease splatter, charred residue, "
         "grimy blackened wire shelf racks, brown burnt-on stains, badly neglected, "
         "photorealistic interior photograph, sharp focus, high detail")
NEG = ("clean, spotless, shiny, new, pristine, gleaming, white enamel, people, hands, "
       "text, letters, numbers, digits, display, control panel, dials, knobs, screen, "
       "watermark, logo, food, bread, loaf, tray, dish, cartoon, illustration, cgi, "
       "render, distorted, warped, blurry, low quality")

print("loading inpaint...", flush=True)
pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
    "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
    torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("mps"); pipe.set_progress_bar_config(disable=True)

g = torch.Generator(device="cpu").manual_seed(7731)
img = pipe(prompt=DIRTY, negative_prompt=NEG, image=base, mask_image=mask,
           width=W, height=H, strength=0.92, num_inference_steps=40,
           guidance_scale=8.0, generator=g).images[0]
img.save(f"{RAW}/oven-before.png")
print("DIRTY OVEN DONE", flush=True)
