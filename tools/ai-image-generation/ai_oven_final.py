#!/usr/bin/env python3
"""Oven pair, final: deterministic cavity blackout + AI carbon texture.

Inpainting alone kept failing on this base because the cavity is brightly
backlit with food on the shelf: SDXL keeps reasserting that bright interior and
re-drawing the food, no matter the strength.

So the cavity content is removed DETERMINISTICALLY first:
  1. Crop tight to the appliance.
  2. Paint the cavity interior with a dark oven-interior gradient (kills the
     food and the glare in one step, with no model involved).
  3. AFTER  = inpaint that dark cavity into clean racks + clean enamel.
  4. BEFORE = take the AFTER and inpaint ONLY the cavity into baked-on carbon,
     then composite through the mask so nothing outside can move.

Everything outside the cavity mask is bit-locked to the after frame.
"""
import torch, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from diffusers import StableDiffusionXLInpaintPipeline, DPMSolverMultistepScheduler

RAW = "/tmp/ai-raw"
W, H = 1216, 832
CROP = (0.11, 0.02, 0.60, 0.98)
CAV  = (0.22, 0.33, 0.82, 0.75)      # cavity interior within the cropped frame

CLEAN = ("clean empty oven interior, bare chrome wire shelf racks, clean dark "
         "enamel oven walls, completely empty with no food, realistic "
         "photograph of an oven cavity, sharp focus")
CNEG  = ("food, pie, bread, cake, pizza, tray, dish, plate, meat, people, hands, "
         "text, letters, numbers, watermark, logo, cartoon, cgi, distorted, "
         "warped, blurry, low quality")

DIRTY = ("filthy neglected oven interior, thick black baked-on carbon crust "
         "covering the walls, heavy burnt grease deposits, charred brown burnt "
         "residue, blackened grimy wire racks, badly soiled oven needing a deep "
         "clean, realistic photograph, sharp focus")
DNEG  = ("clean, spotless, shiny, new, pristine, gleaming, bright, glowing, lit, "
         "food, pie, bread, tray, dish, people, hands, text, letters, numbers, "
         "watermark, logo, cartoon, cgi, distorted, warped, blurry, low quality")

def cav_mask(size, blur=9):
    w, h = size
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rectangle(
        [int(CAV[0]*w), int(CAV[1]*h), int(CAV[2]*w), int(CAV[3]*h)], fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur))

if __name__ == "__main__":
    base = Image.open(f"{RAW}/oven-base.png").convert("RGB").resize((W, H), Image.LANCZOS)
    cb = (int(CROP[0]*W), int(CROP[1]*H), int(CROP[2]*W), int(CROP[3]*H))
    work = base.crop(cb).resize((1216, 832), Image.LANCZOS)
    tw, th = work.size
    mask = cav_mask((tw, th))

    # --- step 1: deterministically blank the cavity to a dark interior --------
    x0, y0 = int(CAV[0]*tw), int(CAV[1]*th)
    x1, y1 = int(CAV[2]*tw), int(CAV[3]*th)
    cw, ch = x1-x0, y1-y0
    dark = Image.new("RGB", (cw, ch), (26, 24, 22))
    d = ImageDraw.Draw(dark)
    for i in range(ch):                       # subtle top-down falloff
        v = int(38 - 16 * (i/ch))
        d.line([(0, i), (cw, i)], fill=(v, v-2, v-4))
    blanked = work.copy()
    blanked.paste(dark, (x0, y0))
    blanked = blanked.filter(ImageFilter.GaussianBlur(0.4))

    print("loading inpaint...", flush=True)
    pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
        "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
        torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe = pipe.to("mps"); pipe.set_progress_bar_config(disable=True)

    # --- step 2: AFTER = clean racks in the blanked cavity --------------------
    g = torch.Generator(device="cpu").manual_seed(6161)
    a_raw = pipe(prompt=CLEAN, negative_prompt=CNEG, image=blanked,
                 mask_image=mask, width=tw, height=th, strength=0.99,
                 num_inference_steps=44, guidance_scale=8.5, generator=g).images[0]
    after = Image.composite(a_raw, work, mask)      # lock everything outside
    after.save(f"{RAW}/oven-after.png")
    print("after written", flush=True)

    # --- step 3: BEFORE = same frame, cavity soiled ---------------------------
    after_fixed = Image.open(f"{RAW}/oven-after.png").convert("RGB")
    # pre-darken so the model starts from grime, not from bright clean enamel
    pre = after_fixed.copy()
    dk = Image.new("RGB", (cw, ch), (18, 14, 11))
    pre.paste(Image.blend(after_fixed.crop((x0, y0, x1, y1)), dk, 0.55), (x0, y0))

    g2 = torch.Generator(device="cpu").manual_seed(8484)
    b_raw = pipe(prompt=DIRTY, negative_prompt=DNEG, image=pre,
                 mask_image=mask, width=tw, height=th, strength=0.92,
                 num_inference_steps=44, guidance_scale=9.0, generator=g2).images[0]
    before = Image.composite(b_raw, after_fixed, mask)
    before.save(f"{RAW}/oven-before.png")

    a = np.asarray(after_fixed).astype(int); b = np.asarray(before).astype(int)
    outside = np.asarray(mask).astype(float)/255.0 < 0.02
    print("max diff outside cavity:", int(np.abs(a-b).sum(2)[outside].max()))
    print("OVEN FINAL DONE", flush=True)
