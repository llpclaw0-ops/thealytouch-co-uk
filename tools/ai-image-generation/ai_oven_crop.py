#!/usr/bin/env python3
"""Oven pair: tight crop on the appliance, cavity dirtied by inpainting.

The oven base is a closed built-in oven set in a wide kitchen, with a pie on the
shelf. Two problems: the card showed more kitchen than oven, and a pie has
nothing to do with oven cleaning.

Approach:
  1. Crop tightly to the appliance so the card reads as "oven", not "kitchen".
  2. AFTER  = that crop with the pie inpainted away -> clean empty cavity.
  3. BEFORE = the SAME after-image with the cavity inpainted filthy.

Because the before is derived from the after, the appliance, door, controls and
surrounding units are identical by construction; only the cavity changes.
"""
import sys, torch, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from diffusers import StableDiffusionXLInpaintPipeline, DPMSolverMultistepScheduler

RAW = "/tmp/ai-raw"
W, H = 1216, 832

# tight crop around the appliance in the 1216x832 base
CROP = (0.11, 0.02, 0.60, 0.98)
# cavity region inside the CROPPED frame (fractions)
CAV = (0.22, 0.32, 0.82, 0.76)

CLEAN = ("empty clean oven cavity interior, bare chrome wire shelf racks, clean "
         "dark enamel interior walls, nothing inside the oven, no food, "
         "realistic photograph, sharp focus")
CLEAN_NEG = ("food, pie, bread, cake, tray, dish, plate, people, hands, text, "
             "letters, numbers, watermark, logo, cartoon, illustration, cgi, "
             "distorted, warped, blurry, low quality")

DIRTY = ("filthy neglected oven interior, thick black baked-on carbon crust on "
         "the cavity walls, heavy burnt grease deposits, charred brown residue, "
         "grimy blackened wire racks, badly soiled oven that needs deep cleaning, "
         "realistic photograph, sharp focus")
DIRTY_NEG = ("clean, spotless, shiny, new, pristine, gleaming, food, pie, bread, "
             "tray, dish, people, hands, text, letters, numbers, watermark, logo, "
             "cartoon, illustration, cgi, distorted, warped, blurry, low quality")

def mask_for(size, box, blur=10):
    w, h = size
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rectangle(
        [int(box[0]*w), int(box[1]*h), int(box[2]*w), int(box[3]*h)], fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur))

if __name__ == "__main__":
    base = Image.open(f"{RAW}/oven-base.png").convert("RGB").resize((W, H), Image.LANCZOS)
    cb = (int(CROP[0]*W), int(CROP[1]*H), int(CROP[2]*W), int(CROP[3]*H))
    crop = base.crop(cb)

    # work at a 3:2 canvas to match the other cards
    tw, th = 1216, 832
    work = crop.resize((tw, th), Image.LANCZOS)

    print("loading inpaint...", flush=True)
    pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
        "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
        torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe = pipe.to("mps"); pipe.set_progress_bar_config(disable=True)

    cav_mask = mask_for((tw, th), CAV)

    # AFTER: clear the pie out of the cavity
    g = torch.Generator(device="cpu").manual_seed(2024)
    after = pipe(prompt=CLEAN, negative_prompt=CLEAN_NEG, image=work,
                 mask_image=cav_mask, width=tw, height=th, strength=0.97,
                 num_inference_steps=40, guidance_scale=8.0, generator=g).images[0]
    after.save(f"{RAW}/oven-after.png")
    print("after: cavity cleared", flush=True)

    # BEFORE: same image, cavity soiled
    after_fixed = Image.open(f"{RAW}/oven-after.png").convert("RGB")
    g2 = torch.Generator(device="cpu").manual_seed(3131)
    raw_dirty = pipe(prompt=DIRTY, negative_prompt=DIRTY_NEG, image=after_fixed,
                     mask_image=cav_mask, width=tw, height=th, strength=0.95,
                     num_inference_steps=40, guidance_scale=9.0, generator=g2).images[0]
    # HARD constraint: outside the cavity mask, keep the after's exact pixels.
    before = Image.composite(raw_dirty, after_fixed, cav_mask)
    before.save(f"{RAW}/oven-before.png")

    a = np.asarray(after_fixed).astype(int); b = np.asarray(before).astype(int)
    m = np.asarray(cav_mask).astype(float)/255.0
    outside = m < 0.02
    print("max diff outside cavity:", int(np.abs(a-b).sum(2)[outside].max()))
    print("OVEN CROP DONE", flush=True)
