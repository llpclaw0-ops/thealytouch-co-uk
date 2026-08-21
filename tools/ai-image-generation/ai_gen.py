#!/usr/bin/env python3
"""AI-generated before/after pairs using SDXL img2img on Apple Silicon (MPS).

WHY img2img FROM ONE BASE PHOTO:
Both states are denoised from the SAME source image, so room layout, camera
angle, fixtures and window positions are shared by construction. Only the
surface condition differs. That gives a genuinely matched pair, which a pair
of independent text2img generations could never guarantee.

The dirt is REAL generated texture — actual mould on grout, baked-on carbon
in the oven, crumbs on carpet — not a colour filter.
"""
import os, sys, gc, time
import torch
from PIL import Image
from diffusers import StableDiffusionXLImg2ImgPipeline, DPMSolverMultistepScheduler

OUT = "/Users/llp/mums-cleaning-site/img/ba"
RAW = "/tmp/ai-raw"
os.makedirs(OUT, exist_ok=True); os.makedirs(RAW, exist_ok=True)

GEN_W, GEN_H = 1216, 832          # SDXL-friendly, ~3:2

QUALITY = ("professional interior photograph, real photo, photorealistic, "
           "natural daylight, sharp focus, high detail, 35mm")
NEG = ("people, person, hands, text, letters, words, watermark, logo, signage, "
       "cartoon, illustration, painting, drawing, cgi, render, 3d, anime, "
       "distorted, warped, deformed, extra objects, duplicated furniture, "
       "oversaturated, low quality, jpeg artifacts")

# slot -> (source, crop(px) or None, dirty prompt, clean prompt)
JOBS = {
    "floors": (
        "/tmp/cand/floors-1.jpg", None,
        "filthy neglected kitchen, greasy stained worktop, sticky spills and food "
        "crumbs on the counter, smeared grease marks, grimy dirty tiled floor with "
        "dark stains and scattered debris, dull dirty surfaces, needs deep cleaning",
        "immaculate spotless kitchen, gleaming polished worktop, clean shining tiled "
        "floor, streak-free surfaces, freshly deep cleaned, hygienic and bright"),
    "bathroom": (
        "/tmp/cand/bathroom-2.jpg", None,
        "filthy neglected bathroom, black mould and mildew growing on the grout and "
        "silicone sealant, heavy white limescale crusted on tiles and glass, soap scum, "
        "brown water stains, grimy discoloured surfaces, needs deep cleaning",
        "immaculate spotless bathroom, gleaming white tiles, crystal clear glass, "
        "bright clean grout, no limescale, freshly deep cleaned, hygienic and sparkling"),
    "bedroom": (
        "/tmp/cand/bedroom-0.jpg", None,
        "messy untidy bedroom, unmade bed with badly crumpled rumpled duvet and "
        "twisted bedsheets thrown back, pillows dented and out of place, dusty "
        "cluttered floor, neglected and disordered room",
        "immaculate tidy bedroom, bed perfectly made with crisp smooth fresh linen, "
        "plump neatly arranged pillows, hotel quality bed making, spotless clean floor"),
    "oven": (
        "/tmp/cand5/ovenA-4.jpg", None,
        "filthy neglected oven, thick baked-on burnt grease, blackened carbonised "
        "crusty residue and charred grime coating the door glass and metal, "
        "spattered fat deposits, heavily soiled, needs deep cleaning",
        "immaculate spotless oven, gleaming clean glass door, bright polished stainless "
        "steel, no grease or residue at all, professionally deep cleaned, like new"),
    "skirting": (
        "/tmp/cand2/skirting-2.jpg", (0, 1348, 1536, 2048),
        "dirty neglected floor and skirting board, thick grey dust build-up along the "
        "skirting edge, grimy scuffed dull baseboard, dusty streaked unpolished floor "
        "with marks and smears, needs cleaning and polishing",
        "immaculate floor and skirting board, brilliantly polished glossy floor with "
        "mirror shine, spotless bright white clean skirting, freshly cleaned and buffed"),
    "hoover": (
        "/tmp/cand2/hoover-6.jpg", None,
        "dirty neglected living room floor, crumbs biscuit pieces and dry debris "
        "scattered across the rug, dust lint and fluff, hair and dirt trodden into the "
        "carpet pile, stained grubby rug, needs vacuuming",
        "immaculate living room floor, freshly vacuumed clean rug with visible neat "
        "hoover lines in the pile, spotless carpet, no crumbs or dust, professionally cleaned"),
}

def load_base(src, crop):
    im = Image.open(src).convert("RGB")
    if crop:
        im = im.crop(crop)
    # cover-fit to the generation size
    tw, th = GEN_W, GEN_H
    sr, tr = im.width / im.height, tw / th
    if sr > tr:
        nh = th; nw = int(round(th * sr))
    else:
        nw = tw; nh = int(round(tw / sr))
    im = im.resize((nw, nh), Image.LANCZOS)
    return im.crop(((nw - tw)//2, (nh - th)//2, (nw - tw)//2 + tw, (nh - th)//2 + th))

print("loading SDXL img2img (first run downloads ~7GB)...", flush=True)
pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("mps")
pipe.set_progress_bar_config(disable=True)
print("pipeline ready on MPS", flush=True)

def gen(base, prompt, strength, seed, steps=34, cfg=7.0):
    g = torch.Generator(device="cpu").manual_seed(seed)
    return pipe(prompt=prompt + ", " + QUALITY, negative_prompt=NEG,
                image=base, strength=strength, num_inference_steps=steps,
                guidance_scale=cfg, generator=g).images[0]

# strength: how far from the source. Dirty needs more freedom to grow mould /
# carbon; clean needs less because the source is already tidy.
STRENGTH = {"floors":(0.52,0.34), "bathroom":(0.58,0.36), "bedroom":(0.55,0.35),
            "oven":(0.60,0.38), "skirting":(0.50,0.34), "hoover":(0.52,0.34)}

t0 = time.time()
for slot, (src, crop, dirty, clean) in JOBS.items():
    if not os.path.exists(src):
        print("MISSING", src); continue
    base = load_base(src, crop)
    base.save(f"{RAW}/{slot}-base.png")
    ds, cs = STRENGTH[slot]

    t = time.time()
    img_b = gen(base, dirty, ds, seed=1000 + hash(slot) % 5000)
    img_b.save(f"{RAW}/{slot}-before.png")
    img_a = gen(base, clean, cs, seed=2000 + hash(slot) % 5000)
    img_a.save(f"{RAW}/{slot}-after.png")
    print(f"{slot}: {time.time()-t:.0f}s  (total {time.time()-t0:.0f}s)", flush=True)
    gc.collect()

print("GENERATION DONE", flush=True)
