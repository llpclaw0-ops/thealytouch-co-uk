#!/usr/bin/env python3
"""Regenerate the oven pair only.

Previous attempt failed: the source crop was a shallow-depth-of-field shot of
an oven control panel, so SDXL produced (a) a blurry image and (b) gibberish
lettering on the digital display. Fix: use a text2img-led composition for the
oven interior instead, which is what the card actually needs to show, then
derive both states from that single generated base so they stay matched.
"""
import os, torch, time
from PIL import Image
from diffusers import (StableDiffusionXLPipeline,
                       StableDiffusionXLImg2ImgPipeline,
                       DPMSolverMultistepScheduler)

RAW = "/tmp/ai-raw"
os.makedirs(RAW, exist_ok=True)
W, H = 1216, 832

QUALITY = ("professional interior photograph, real photo, photorealistic, "
           "natural daylight, sharp focus, high detail, 35mm")
NEG = ("people, person, hands, text, letters, words, numbers, digits, display, "
       "screen, watermark, logo, signage, brand name, cartoon, illustration, "
       "painting, cgi, render, 3d, anime, distorted, warped, deformed, blurry, "
       "out of focus, bokeh, shallow depth of field, low quality, jpeg artifacts")

BASE_PROMPT = ("open empty domestic oven with the door lowered, viewed straight on, "
               "clean stainless steel and glass, two wire shelf racks inside the "
               "cavity, plain kitchen behind, whole oven fully in frame and in focus")

print("loading SDXL text2img...", flush=True)
t2i = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
t2i.scheduler = DPMSolverMultistepScheduler.from_config(t2i.scheduler.config)
t2i = t2i.to("mps"); t2i.set_progress_bar_config(disable=True)

g = torch.Generator(device="cpu").manual_seed(7731)
base = t2i(prompt=BASE_PROMPT + ", " + QUALITY, negative_prompt=NEG,
           width=W, height=H, num_inference_steps=38, guidance_scale=7.0,
           generator=g).images[0]
base.save(f"{RAW}/oven-base.png")
print("base oven generated", flush=True)
del t2i
import gc; gc.collect()

print("loading img2img...", flush=True)
i2i = StableDiffusionXLImg2ImgPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
i2i.scheduler = DPMSolverMultistepScheduler.from_config(i2i.scheduler.config)
i2i = i2i.to("mps"); i2i.set_progress_bar_config(disable=True)

DIRTY = ("extremely filthy disgusting oven interior, every surface caked in thick "
         "black baked-on burnt carbon crust, dark brown hardened grease coating the "
         "oven walls and roof, charred food residue and burnt spillage covering the "
         "wire racks, greasy blackened smeared glass door, years of neglect, "
         "heavily soiled encrusted grimy oven cavity")
CLEAN = ("immaculate spotless oven interior, gleaming clean enamel walls, bright "
         "shining wire racks, crystal clear glass door, no grease or residue at all, "
         "professionally deep cleaned, like new")

def run(prompt, strength, seed):
    gg = torch.Generator(device="cpu").manual_seed(seed)
    return i2i(prompt=prompt + ", " + QUALITY, negative_prompt=NEG, image=base,
               strength=strength, num_inference_steps=36, guidance_scale=7.0,
               generator=gg).images[0]

run(DIRTY, 0.74, 4411).save(f"{RAW}/oven-before.png")
run(CLEAN, 0.30, 5522).save(f"{RAW}/oven-after.png")
print("OVEN DONE", flush=True)
