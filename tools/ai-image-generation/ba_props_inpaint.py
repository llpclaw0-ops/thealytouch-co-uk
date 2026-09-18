#!/usr/bin/env python3
"""Add or change props in an existing before/after image by local inpainting.

Only the masked area is repainted: the crop around it is upscaled to the
model's working size, inpainted, scaled back and feathered into the source,
so every pixel outside the mask stays identical to the image on the site.

Usage: ba_props_inpaint.py jobs.json
jobs.json: [{"name", "src", "box":[x0,y0,x1,y1], "mask":[[x0,y0,x1,y1],...],
             "prompt", "neg"?, "seeds":[...], "strength"?, "steps"?}]
Each job writes <outdir>/<name>-<seed>.png next to jobs.json.
"""
import json, os, sys, torch
from PIL import Image, ImageDraw, ImageFilter
from diffusers import StableDiffusionXLInpaintPipeline, DPMSolverMultistepScheduler

QUALITY = "professional interior photograph, real photo, photorealistic, natural daylight, sharp focus, high detail"
NEG = ("people, person, hands, text, letters, words, watermark, logo, brand name, label text, "
       "cartoon, illustration, cgi, render, anime, distorted, warped, deformed, blurry, low quality")

jobs_path = sys.argv[1]
outdir = os.path.dirname(os.path.abspath(jobs_path))
jobs = json.load(open(jobs_path))
only = set(sys.argv[2:])

pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
    "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
    torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("mps"); pipe.set_progress_bar_config(disable=True)

def snap(v):  # SDXL wants multiples of 8
    return max(512, int(round(v / 8)) * 8)

for job in jobs:
    if only and job["name"] not in only:
        continue
    src = Image.open(job["src"]).convert("RGB")
    x0, y0, x1, y1 = job["box"]
    crop = src.crop((x0, y0, x1, y1))
    cw, ch = crop.size
    scale = 1024 / max(cw, ch)
    W, H = snap(cw * scale), snap(ch * scale)

    mask = Image.new("L", src.size, 0)
    d = ImageDraw.Draw(mask)
    for r in job["mask"]:
        (d.ellipse if job.get("ellipse") else d.rectangle)(r, fill=255)
    mcrop = mask.crop((x0, y0, x1, y1))
    feather = mcrop.filter(ImageFilter.GaussianBlur(job.get("feather", 6)))

    for seed in job["seeds"]:
        g = torch.Generator(device="cpu").manual_seed(seed)
        out = pipe(prompt=job["prompt"] + ", " + QUALITY,
                   negative_prompt=job.get("neg", "") + ", " + NEG,
                   image=crop.resize((W, H), Image.LANCZOS),
                   mask_image=mcrop.resize((W, H), Image.LANCZOS),
                   width=W, height=H, strength=job.get("strength", 0.99),
                   num_inference_steps=job.get("steps", 40),
                   guidance_scale=job.get("cfg", 7.5), generator=g).images[0]
        patch = out.resize((cw, ch), Image.LANCZOS)
        res = src.copy()
        res.paste(Image.composite(patch, crop, feather), (x0, y0))
        p = f"{outdir}/{job['name']}-{seed}.png"
        res.save(p); print("wrote", p, flush=True)
