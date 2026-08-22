#!/usr/bin/env python3
"""Build an AI open-door oven base, guided by a real photo's COMPOSITION.

Why this exists: text2img could not produce an open oven door (many seeds tried
- it kept returning closed doors and wide kitchen shots). A CC-licensed photo
supplies the geometry SDXL could not invent; img2img at moderate strength then
repaints it into an AI illustration consistent with the other five cards, so no
real person's kitchen is published.

The output is a disposable candidate: pick one by eye, and it becomes the
locked base for the tiled-dirt step (which is what guarantees the pair is the
same image).
"""
import torch
from PIL import Image
from diffusers import StableDiffusionXLImg2ImgPipeline, DPMSolverMultistepScheduler

RAW = "/tmp/ai-raw"
W, H = 1216, 832

PROMPT = ("a modern stainless steel built-in kitchen oven with the door open, "
          "empty clean oven cavity visible inside, bare chrome wire shelf racks, "
          "spotless enamel interior, fitted white kitchen units either side, "
          "bright soft daylight, straight-on interior photograph, sharp focus")

NEG = ("food, pie, bread, cake, tray, dish, plate, pan, roast, "
       "closed door, missing door, second oven, dishwasher, microwave, "
       "people, person, hands, legs, reflection of person, face, "
       "text, letters, numbers, words, labels, watermark, logo, signage, "
       "cartoon, cgi, 3d render, abstract, distorted, warped, melted, "
       "blurry, out of focus, low quality, cluttered, messy")

pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16, variant="fp16", use_safetensors=True).to("mps")
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)

ref = Image.open(f"{RAW}/oven-ref.png").convert("RGB").resize((W, H), Image.LANCZOS)

n = 0
for strength in (0.42, 0.52, 0.62):
    for seed in (11, 27, 43):
        g = torch.Generator(device="cpu").manual_seed(seed)
        img = pipe(prompt=PROMPT, negative_prompt=NEG, image=ref,
                   strength=strength, num_inference_steps=40,
                   guidance_scale=7.5, generator=g).images[0]
        fn = f"{RAW}/oven-cand-s{int(strength*100)}-{seed}.png"
        img.save(fn)
        n += 1
        print("wrote", fn, flush=True)
print("done", n, flush=True)
