#!/usr/bin/env python3
"""Generate a BRIGHT bathroom base, because the old one could not show dirt.

The previous bathroom plate was a dim room with black mosaic tiles. Against
black tiles, grime simply does not read: darkening is invisible, and the pale
limescale treatment that did show had to be pushed so far it started to look
like haze. No amount of tuning fixes a base that has nowhere for dirt to show.

A bright room with pale tiles and white sanitaryware gives dark grime somewhere
to sit, so the before/after difference is obvious at card size.
"""
import torch
from PIL import Image
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

RAW, W, H = "/tmp/ai-raw", 1216, 832

PROMPT = ("a bright clean modern bathroom, large pale cream and white wall "
          "tiles, white basin on a vanity unit, glass shower screen, white "
          "bath, light tiled floor, soft daylight from a window, spacious, "
          "interior photograph, straight on, sharp focus")

NEG = ("people, person, hands, face, text, letters, numbers, watermark, logo, "
       "dark, dim, gloomy, black tiles, mosaic, cluttered, messy, towels "
       "everywhere, cartoon, cgi, 3d render, distorted, warped, blurry, "
       "low quality")

pipe = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16, variant="fp16", use_safetensors=True).to("mps")
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe.set_progress_bar_config(disable=True)

for seed in (3, 11, 19, 27, 41, 53):
    g = torch.Generator(device="cpu").manual_seed(seed)
    img = pipe(prompt=PROMPT, negative_prompt=NEG, width=W, height=H,
               num_inference_steps=40, guidance_scale=7.0, generator=g).images[0]
    img.save(f"{RAW}/bath-cand-{seed}.png")
    print("wrote", seed, flush=True)
print("BATH BASE DONE", flush=True)
