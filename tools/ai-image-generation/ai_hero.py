#!/usr/bin/env python3
"""Generate a warm, bright hero image for the site.

The old hero was a stock photo buried under a dark navy overlay. The brief
wants beige/ivory/white dominant, so generate a genuinely light, warm,
inviting interior that needs no dark scrim to be readable.
"""
import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

OUT = "/tmp/ai-raw"
W, H = 1344, 896

PROMPT = ("bright airy immaculately clean living room interior, warm cream and ivory "
          "walls, soft beige linen sofa, pale oak wooden floor gleaming clean, large "
          "window with sheer curtains and abundant natural sunlight, fresh white "
          "flowers in a vase, neatly arranged cushions, uncluttered and freshly "
          "cleaned, calm and welcoming home, professional interior photograph, "
          "photorealistic, natural daylight, sharp focus, high detail, 35mm")

NEG = ("people, person, hands, text, letters, words, watermark, logo, signage, "
       "dark, gloomy, dim, moody, blue tint, cold colours, clutter, mess, dirt, "
       "cartoon, illustration, painting, cgi, render, 3d, anime, distorted, "
       "warped, deformed, low quality, jpeg artifacts")

print("loading SDXL...", flush=True)
pipe = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("mps"); pipe.set_progress_bar_config(disable=True)

for i, seed in enumerate([4242, 8888, 1357]):
    g = torch.Generator(device="cpu").manual_seed(seed)
    img = pipe(prompt=PROMPT, negative_prompt=NEG, width=W, height=H,
               num_inference_steps=36, guidance_scale=7.0, generator=g).images[0]
    img.save(f"{OUT}/hero-opt{i}.png")
    print("wrote", f"{OUT}/hero-opt{i}.png", flush=True)
print("HERO DONE", flush=True)
