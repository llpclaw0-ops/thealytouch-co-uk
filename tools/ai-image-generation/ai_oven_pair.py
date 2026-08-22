#!/usr/bin/env python3
"""Oven pair from a purpose-generated open-oven base.

The stock oven base was a CLOSED oven containing a pie, so every cavity mask
landed on the door glass and nothing could be dirtied. There is no open-oven
source photo in the project.

Fix: generate the clean open oven once with text2img, keep it as the AFTER
untouched, then inpaint ONLY its cavity to produce the BEFORE. Because the
after is never regenerated, the appliance geometry cannot drift.
"""
import sys, torch, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from diffusers import (StableDiffusionXLPipeline,
                       StableDiffusionXLInpaintPipeline,
                       DPMSolverMultistepScheduler)

RAW = "/tmp/ai-raw"
W, H = 1216, 832
step = sys.argv[1] if len(sys.argv) > 1 else "both"

BASE_PROMPT = (
    "extreme close up product photograph of a single open oven, the oven door "
    "hangs fully open and lowered flat toward the viewer, the empty clean oven "
    "cavity fills the entire frame, two chrome wire shelf racks inside, pale "
    "clean enamel interior walls, stainless steel door front, tightly cropped "
    "so only the oven is visible, no kitchen, no room, no cabinets, straight-on "
    "eye level, studio lighting, photorealistic, sharp focus, high detail")
BASE_NEG = (
    "kitchen, room, cabinets, worktop, counter, wide shot, distant view, sink, window, closed door, shut door, food, bread, pie, loaf, tray, dish, people, hands, "
    "text, letters, numbers, digits, display, watermark, logo, brand, cartoon, "
    "illustration, cgi, render, 3d, anime, distorted, warped, deformed, blurry, "
    "low quality, jpeg artifacts")

if step in ("both", "base"):
    print("generating open-oven base...", flush=True)
    t2i = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
    t2i.scheduler = DPMSolverMultistepScheduler.from_config(t2i.scheduler.config)
    t2i = t2i.to("mps"); t2i.set_progress_bar_config(disable=True)
    g = torch.Generator(device="cpu").manual_seed(9090)
    img = t2i(prompt=BASE_PROMPT, negative_prompt=BASE_NEG, width=W, height=H,
              num_inference_steps=40, guidance_scale=7.5, generator=g).images[0]
    img.save(f"{RAW}/oven-open-base.png")
    img.save(f"{RAW}/oven-after.png")          # AFTER = this, untouched
    print("wrote open base; after = untouched base", flush=True)
    del t2i

if step in ("both", "dirty"):
    base = Image.open(f"{RAW}/oven-open-base.png").convert("RGB")

    # Locate the cavity: the darkest connected region in the middle of the frame.
    a = np.asarray(base.convert("L")).astype(np.float32)
    inner = a[int(H*0.15):int(H*0.75), int(W*0.20):int(W*0.80)]
    thr = float(np.percentile(inner, 35))
    dark = a < thr
    dark[:int(H*0.12), :] = False; dark[int(H*0.80):, :] = False
    dark[:, :int(W*0.18)] = False; dark[:, int(W*0.82):] = False
    cols, rows = dark.sum(0), dark.sum(1)
    xs = np.where(cols > max(cols.max()*0.35, 20))[0]
    ys = np.where(rows > max(rows.max()*0.35, 20))[0]
    x0, x1 = (int(xs.min()), int(xs.max())) if len(xs) else (int(W*0.30), int(W*0.70))
    y0, y1 = (int(ys.min()), int(ys.max())) if len(ys) else (int(H*0.22), int(H*0.62))
    print("dirty mask box:", x0, y0, x1, y1, "thr", round(thr, 1))

    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rectangle([x0, y0, x1, y1], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(12))
    mask.save(f"{RAW}/oven-dirty-mask.png")

    DIRTY = ("the inside of a filthy neglected oven, thick black baked-on carbon "
             "crust coating the interior walls, heavy burnt grease splatter, "
             "charred blackened residue, grimy dirty wire shelf racks, brown "
             "burnt-on stains, badly neglected and never cleaned, photorealistic "
             "photograph, sharp focus, high detail")
    DNEG = ("clean, spotless, shiny, new, pristine, gleaming, people, hands, text, "
            "letters, numbers, digits, display, control panel, watermark, logo, "
            "food, bread, pie, loaf, tray, dish, cartoon, illustration, cgi, "
            "render, distorted, warped, blurry, low quality")

    print("loading inpaint...", flush=True)
    ip = StableDiffusionXLInpaintPipeline.from_pretrained(
        "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
        torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
    ip.scheduler = DPMSolverMultistepScheduler.from_config(ip.scheduler.config)
    ip = ip.to("mps"); ip.set_progress_bar_config(disable=True)
    g = torch.Generator(device="cpu").manual_seed(4242)
    out = ip(prompt=DIRTY, negative_prompt=DNEG, image=base, mask_image=mask,
             width=W, height=H, strength=0.93, num_inference_steps=40,
             guidance_scale=8.0, generator=g).images[0]
    out.save(f"{RAW}/oven-before.png")
    print("OVEN PAIR DONE", flush=True)
