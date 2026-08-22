#!/usr/bin/env python3
"""Before/after pairs that are GUARANTEED the same scene.

WHY THE PREVIOUS PAIRS DRIFTED
Both frames were generated with img2img at strength 0.50-0.60. At that strength
SDXL redraws the entire frame, so the two sides were invented independently:
the kitchen camera moved, the bathroom mirror changed shape, the bedroom's wall
art turned into a horse painting, sofa cushions and plants moved. No slider can
hide that - it reads as two different photos.

THE FIX
1. AFTER  = the base photo, untouched. Zero generation, so zero drift.
2. BEFORE = the same photo with dirt inpainted ONLY inside a mask covering the
   surfaces that get dirty (floor, worktop, tiles, bedding). Everything outside
   the mask - walls, windows, furniture, art, fixtures - is pixel-identical to
   the after by construction.

This is the same technique that finally worked for the oven cavity: never
regenerate the clean side, and constrain the dirty side to a mask.
"""
import sys, torch
from PIL import Image, ImageDraw, ImageFilter
from diffusers import StableDiffusionXLInpaintPipeline, DPMSolverMultistepScheduler

RAW = "/tmp/ai-raw"
W, H = 1216, 832

# mask = (x0%, y0%, x1%, y1%) of the frame that should receive dirt.
# Chosen per scene to cover the surfaces a cleaner actually cleans.
JOBS = {
    "floors": dict(
        mask=(0.00, 0.56, 1.00, 0.72),          # front worktop lip only; hob and sink excluded
        prompt=("kitchen worktop with spilled food and crumbs scattered on it, "
                "sticky brown sauce stains and grease smears on the surface, "
                "dirty untidy work surface that needs wiping down"),
        strength=0.72, blend=0.90),
    "bathroom": dict(
        mask=(0.00, 0.66, 1.00, 1.00),          # floor + lowest tiles; keep basin, shower, mirror
        prompt=("bathroom floor tiles and grout that are dirty and neglected, "
                "black mould spots along the grout lines, grey limescale marks "
                "and soap scum, dull stained unwashed tiles"),
        strength=0.70, blend=0.90),
    "bedroom": dict(
        mask=(0.00, 0.55, 0.72, 1.00),          # bed + floor only, keep wall art
        prompt=("messy unmade bed, crumpled rumpled creased bedding thrown back "
                "in a heap, sheets pulled loose and twisted, pillows squashed "
                "and dented, clothes and clutter dropped on the floor"),
        strength=0.60, blend=1.00),             # already good - leave exactly as is
    "skirting": dict(
        mask=(0.00, 0.58, 1.00, 1.00),          # floor + skirting run only
        prompt=("dusty dirty floor along the skirting board, grey dust and fluff "
                "gathered in the edge where floor meets wall, scuffed grubby "
                "skirting, dull unpolished floor with dusty smears"),
        strength=0.70, blend=0.90),
    "hoover": dict(
        mask=(0.00, 0.64, 1.00, 1.00),          # rug + floor, keep sofa/plant/window
        prompt=("dirty carpet with crumbs and bits of debris scattered across it, "
                "fluff and dust on the pile, faint dirty marks trodden in, "
                "carpet that badly needs vacuuming"),
        strength=0.72, blend=0.90),
}

NEG = ("clean, spotless, pristine, tidy, new, gleaming, people, person, hands, "
       "text, letters, numbers, watermark, logo, brand, cartoon, illustration, "
       "cgi, render, 3d, anime, distorted, warped, deformed, extra objects, "
       "new furniture, missing furniture, removed rug, removed hob, changed layout, "
       "blurry, out of focus, low quality, jpeg artifacts")

only = sys.argv[1:] or list(JOBS)

print("loading inpaint pipeline...", flush=True)
pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
    "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
    torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("mps"); pipe.set_progress_bar_config(disable=True)

for name in only:
    cfg = JOBS[name]
    base = Image.open(f"{RAW}/{name}-base.png").convert("RGB").resize((W, H), Image.LANCZOS)

    # AFTER is the untouched base: this is what removes all drift.
    base.save(f"{RAW}/{name}-after.png")

    x0, y0, x1, y1 = cfg["mask"]
    box = [int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)]
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(26))   # soft edge, no hard seam

    g = torch.Generator(device="cpu").manual_seed(abs(hash(name)) % 100000)
    out = pipe(prompt=cfg["prompt"], negative_prompt=NEG,
               image=base, mask_image=mask, width=W, height=H,
               strength=cfg["strength"], num_inference_steps=40,
               guidance_scale=8.0, generator=g).images[0]

    # Blend the generated dirt back over the ORIGINAL photo instead of letting it
    # replace those pixels outright. SDXL invents its own surface texture, which
    # is what reads as "AI slop"; blending keeps the real photograph's grain,
    # grout lines, wood grain and tile edges showing through the dirt, so the
    # before looks like the same photo soiled rather than a repainted one.
    b = float(cfg.get("blend", 1.0))
    if b < 1.0:
        out = Image.blend(base, out, b)
        # Outside the mask must stay pixel-identical to the base, so re-composite
        # using the mask as the alpha channel.
        out = Image.composite(out, base, mask)

    out.save(f"{RAW}/{name}-before.png")
    print(f"{name}: after=untouched base, before=dirt in {box} blend={b}", flush=True)

print("MATCHED PAIRS DONE", flush=True)
