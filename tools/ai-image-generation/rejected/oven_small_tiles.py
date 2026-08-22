#!/usr/bin/env python3
"""Cavity dirt in SMALL 2D tiles - the proven technique, applied properly.

ai_tiled_dirt slides ONE row of square tiles the full height of the strip. For
a floor or a carpet that is fine: the strip is shallow, so a tile is pure
surface. The oven cavity is 487x341, so a full-height tile is 341px and
contains the entire cavity - back wall, both fans, both racks. SDXL sees a
SCENE, not a surface, and rewrites it: the fans become pipes, a copper rod
appears on the shelf.

Small tiles restore the original guarantee. At ~160px each tile is a close-up
of wall or of rack, with no room to hold a fan or a shelf, so there is nothing
to re-invent and the model can only deposit crust. Overlapping 2D coverage with
feathered blending keeps the grime continuous across tiles.
"""
import sys, numpy as np, torch
from PIL import Image
from diffusers import StableDiffusionXLImg2ImgPipeline, DPMSolverMultistepScheduler
sys.path.insert(0, "/Users/llp/mums-cleaning-site/tools/ai-image-generation")
from ai_tiled_dirt import feather_mask, JOBS, W, H, NEG

RAW  = "/tmp/ai-raw"
BASE = "oven-openbase"
WIN, WORK = 160, 768
STRENGTH  = float(sys.argv[1]) if len(sys.argv) > 1 else 0.62

PROMPT = ("black baked-on carbon crust and burnt grease caked on the surface, "
          "charred soot deposits, brown grease streaks, filthy soiled oven "
          "interior surface, close-up photograph")

def axis(total, win, overlap=0.45):
    step = max(int(win * (1 - overlap)), 1)
    pts = list(range(0, max(total - win, 0) + 1, step))
    if pts[-1] != total - win:
        pts.append(max(total - win, 0))
    return pts

base = Image.open(f"{RAW}/{BASE}.png").convert("RGB").resize((W, H), Image.LANCZOS)
x0, y0, x1, y1 = JOBS["oven"]["crop"]
bx = (int(x0*W), int(y0*H), int(x1*W), int(y1*H))
strip = base.crop(bx)
sw, sh = strip.size
result = strip.copy()

pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("mps"); pipe.set_progress_bar_config(disable=True)

xs, ys = axis(sw, WIN), axis(sh, WIN)
print(f"{len(xs)}x{len(ys)} = {len(xs)*len(ys)} tiles of {WIN}px, strength {STRENGTH}", flush=True)

n = 0
for iy, sy in enumerate(ys):
    for ix, sx in enumerate(xs):
        tile = result.crop((sx, sy, sx + WIN, sy + WIN))
        work = tile.resize((WORK, WORK), Image.LANCZOS)
        g = torch.Generator(device="cpu").manual_seed(7000 + iy * 97 + ix * 13)
        out = pipe(prompt=PROMPT, negative_prompt=NEG, image=work,
                   strength=STRENGTH, num_inference_steps=32,
                   guidance_scale=7.0, generator=g).images[0]
        out = out.resize((WIN, WIN), Image.LANCZOS)
        result.paste(out, (sx, sy), feather_mask(WIN, WIN, int(WIN * 0.30)))
        n += 1
        if n % 5 == 0:
            print(f"  {n}/{len(xs)*len(ys)}", flush=True)

before = base.copy()
before.paste(result, bx, feather_mask(sw, sh, max(10, int(sh * 0.16))))
base.save(f"{RAW}/oven-after.png")
before.save(f"{RAW}/oven-before.png")

a = np.asarray(before).astype(int); b = np.asarray(base).astype(int)
outside = np.ones((H, W), bool); outside[bx[1]:bx[3], bx[0]:bx[2]] = False
print(f"max diff outside cavity = {int(np.abs(a-b).sum(2)[outside].max())}", flush=True)
print("SMALL TILES DONE", flush=True)
