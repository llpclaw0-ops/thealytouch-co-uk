#!/usr/bin/env python3
"""BEFORE = carbon inpainted onto the cavity WALLS, hardware masked out.

The route here, and why the earlier ones failed:

  img2img on the cavity  - at 0.45-0.55 there is no visible dirt; at 0.65+ it
                           looks properly filthy but the two fan discs turn
                           into pipes. No single strength gives both.
  low-frequency tone transfer - keeps every rack and fan exactly in place but
                           reads as a grey film over the photo, because a
                           blurred multiply IS a film. Adding the source's
                           texture back ghosts, since its geometry differs.

So: generate real carbon texture, but only where there is no hardware. The
mask is derived from the base itself - bright metal and high-detail pixels are
protected - so racks, shelf supports and fans cannot be redrawn at any
strength. Those protected pixels instead get a multiplicative darkening, which
soils them without moving them.
"""
import sys, numpy as np, torch
from PIL import Image, ImageFilter
from diffusers import StableDiffusionXLInpaintPipeline, DPMSolverMultistepScheduler
sys.path.insert(0, "/Users/llp/mums-cleaning-site/tools/ai-image-generation")
from ai_tiled_dirt import feather_mask, JOBS, W, H

RAW  = "/tmp/ai-raw"
BASE = "oven-openbase"
TILE = 768

PROMPT = ("thick black baked-on carbon crust caked on the oven cavity wall, "
          "burnt grease, charred soot deposits, brown grease streaks running "
          "down the enamel, filthy neglected oven, close-up photograph")
NEG    = ("food, tray, dish, pan, bread, cake, "
          "rack, shelf, grid, wire, fan, handle, knob, door, appliance, oven, "
          "object, tool, text, letters, numbers, logo, watermark, "
          "clean, shiny, spotless, people, hands, "
          "cartoon, illustration, cgi, 3d render, abstract, pattern, "
          "warped, melted, blurry, low quality")

def hardware_mask(B):
    """White = protect (metal / detailed hardware). Black = free wall."""
    lum = np.asarray(Image.fromarray(B.astype(np.uint8)).convert("L")).astype(np.float32)
    bright = lum > 118
    L = Image.fromarray(lum.astype(np.uint8))
    detail = np.abs(np.asarray(L.filter(ImageFilter.FIND_EDGES)).astype(np.float32))
    m = (bright | (detail > 26)).astype(np.uint8) * 255
    # Dilate by ONE pixel only. The rack is a fine grid: a 7px dilation
    # merged it into a solid mass and protected the whole cavity.
    m = Image.fromarray(m).filter(ImageFilter.MaxFilter(3))
    return m.filter(ImageFilter.GaussianBlur(1.0))

base = Image.open(f"{RAW}/{BASE}.png").convert("RGB").resize((W, H), Image.LANCZOS)
x0, y0, x1, y1 = JOBS["oven"]["crop"]
bx = (int(x0*W), int(y0*H), int(x1*W), int(y1*H))
strip = base.crop(bx)
B = np.asarray(strip).astype(np.float32)

protect = hardware_mask(B)
paint   = Image.fromarray(255 - np.asarray(protect))            # inpaint the walls
protect.save(f"{RAW}/oven-protect-mask.png")

if "--mask-only" in sys.argv:
    print("mask written, protected fraction = %.1f%%" %
          (np.asarray(protect).mean()/255*100)); sys.exit()

pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
    "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
    torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("mps"); pipe.set_progress_bar_config(disable=True)

sw, sh = strip.size
result = strip.copy()
win  = sh
step = int(win * 0.55)
xs   = list(range(0, max(sw - win, 0) + 1, step))
if xs[-1] != sw - win:
    xs.append(max(sw - win, 0))

for i, sx in enumerate(xs):
    box = (sx, 0, min(sx + win, sw), sh)
    t_img = strip.crop(box).resize((TILE, TILE), Image.LANCZOS)
    t_msk = paint.crop(box).resize((TILE, TILE), Image.NEAREST)
    g = torch.Generator(device="cpu").manual_seed(1234 + i * 31)
    out = pipe(prompt=PROMPT, negative_prompt=NEG, image=t_img, mask_image=t_msk,
               strength=0.95, num_inference_steps=38, guidance_scale=7.5,
               generator=g).images[0]
    tw, th = box[2]-box[0], box[3]-box[1]
    out = out.resize((tw, th), Image.LANCZOS)
    result.paste(out, (sx, 0), feather_mask(tw, th, max(10, int(min(tw, th)*0.14))))

# Hardware kept from the base, but soiled: multiplicative darkening only.
R  = np.asarray(result).astype(np.float32)
pm = (np.asarray(protect).astype(np.float32) / 255.0)[..., None]
grimy_metal = B * 0.62
R = R * (1.0 - pm) + grimy_metal * pm
strip_out = Image.fromarray(np.clip(R, 0, 255).astype(np.uint8))

before = base.copy()
before.paste(strip_out, bx, feather_mask(sw, sh, max(10, int(sh*0.16))))
base.save(f"{RAW}/oven-after.png")
before.save(f"{RAW}/oven-before.png")

a = np.asarray(before).astype(int); b = np.asarray(base).astype(int)
outside = np.ones((H, W), bool); outside[bx[1]:bx[3], bx[0]:bx[2]] = False
d = np.abs(a-b).sum(2)
print(f"tiles={len(xs)} | max diff outside cavity = {int(d[outside].max())}", flush=True)
print("INPAINT DONE", flush=True)
