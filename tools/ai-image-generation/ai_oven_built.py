#!/usr/bin/env python3
"""Oven pair built from a CONSTRUCTED open-oven scene.

SDXL will not reliably render an oven with its door open: across many attempts
it returned closed doors, dishwashers, wide kitchens and gibberish control
panels. Free stock had no usable straight-on open-oven photo either.

So the appliance is drawn deterministically with PIL - a simple, clean built-in
oven with the door lowered flat and two wire racks - and AI is used only for
what it is good at here: generating the CAVITY TEXTURE (clean enamel vs thick
baked-on carbon). The drawn geometry is byte-identical between the two frames,
so the before/after can never drift.

AFTER  = constructed oven + clean cavity texture
BEFORE = same constructed oven + filthy cavity texture
"""
import sys, torch, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

RAW = "/tmp/ai-raw"
W, H = 1216, 832

# ---- cavity textures, generated once ---------------------------------------
TEX = {
  "oven-cav-clean": ("the inside back wall of a spotlessly clean empty oven, smooth "
                     "pale grey enamel surface, evenly lit, no dirt no grease, "
                     "flat straight-on view of a plain enamel panel, photograph"),
  "oven-cav-dirty": ("the inside back wall of a filthy neglected oven, thick black "
                     "baked-on carbon crust, burnt grease deposits, charred brown "
                     "residue, flat straight-on view of a plain panel, photograph"),
}
NEG = ("door, handle, kitchen, room, people, hands, text, letters, numbers, "
       "watermark, logo, cartoon, illustration, cgi, render, 3d, distorted, "
       "warped, blurry, low quality")

def make_tex():
    import os
    need = [k for k in TEX if not os.path.exists(f"{RAW}/{k}.png")]
    if not need:
        print("textures present"); return
    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe = pipe.to("mps"); pipe.set_progress_bar_config(disable=True)
    for i, k in enumerate(need):
        g = torch.Generator(device="cpu").manual_seed(770 + i)
        img = pipe(prompt=TEX[k], negative_prompt=NEG, width=1024, height=1024,
                   num_inference_steps=34, guidance_scale=7.0, generator=g).images[0]
        img.save(f"{RAW}/{k}.png"); print("wrote", k, flush=True)

# ---- constructed oven -------------------------------------------------------
# geometry (identical for both frames)
CAV = (250, 150, 966, 560)          # cavity opening
DOOR_TOP = 566
DOOR_BOT = 762

def build(state):
    tex = Image.open(f"{RAW}/oven-cav-{state}.png").convert("RGB")
    img = Image.new("RGB", (W, H), (232, 232, 234))
    d = ImageDraw.Draw(img)

    # surrounding cabinetry
    d.rectangle([0, 0, W, H], fill=(238, 238, 240))
    d.rectangle([120, 40, 1096, 800], fill=(215, 216, 219))       # appliance body
    d.rectangle([132, 52, 1084, 788], fill=(198, 200, 204))

    # stainless frame around the opening
    d.rectangle([CAV[0]-34, CAV[1]-40, CAV[2]+34, CAV[3]+30], fill=(176, 179, 184))
    d.rectangle([CAV[0]-24, CAV[1]-30, CAV[2]+24, CAV[3]+20], fill=(150, 153, 158))

    # cavity: paste texture, darken toward the back for depth
    cw, ch = CAV[2]-CAV[0], CAV[3]-CAV[1]
    cav = tex.resize((cw, ch), Image.LANCZOS)
    shade = Image.new("L", (cw, ch), 0)
    sd = ImageDraw.Draw(shade)
    for i in range(ch):
        sd.line([(0, i), (cw, i)], fill=int(70 * (1 - i/ch)))
    cav = Image.composite(Image.new("RGB", (cw, ch), (0, 0, 0)), cav,
                          shade.point(lambda v: int(v*0.9)))
    img.paste(cav, (CAV[0], CAV[1]))

    # side walls converging for perspective
    d.polygon([CAV[0], CAV[1], CAV[0]+46, CAV[1]+34, CAV[0]+46, CAV[3]-34, CAV[0], CAV[3]],
              fill=(0, 0, 0, 0) if False else None)

    # two wire racks
    for ry in (CAV[1] + int(ch*0.34), CAV[1] + int(ch*0.66)):
        d.rectangle([CAV[0]+40, ry, CAV[2]-40, ry+7], fill=(168, 170, 176))
        for x in range(CAV[0]+56, CAV[2]-46, 42):
            d.rectangle([x, ry-3, x+4, ry+10], fill=(150, 152, 158))

    # lowered door: dark glass panel with a steel handle
    d.rectangle([150, DOOR_TOP, 1066, DOOR_BOT], fill=(170, 173, 178))
    d.rectangle([166, DOOR_TOP+12, 1050, DOOR_BOT-14], fill=(44, 46, 50))
    d.rectangle([196, DOOR_TOP+26, 1020, DOOR_BOT-28], fill=(28, 30, 34))
    d.rectangle([150, DOOR_BOT-8, 1066, DOOR_BOT], fill=(140, 143, 148))
    d.rounded_rectangle([210, DOOR_TOP-16, 1006, DOOR_TOP+4], 10, fill=(198, 201, 206))

    # soften so it reads photographic rather than vector-flat
    img = img.filter(ImageFilter.GaussianBlur(0.8))
    arr = np.asarray(img).astype(np.float32)
    rng = np.random.default_rng(4)
    arr += rng.normal(0, 3.2, arr.shape)                    # film grain
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return img

if __name__ == "__main__":
    make_tex()
    build("clean").save(f"{RAW}/oven-after.png")
    build("dirty").save(f"{RAW}/oven-before.png")
    a = np.asarray(Image.open(f"{RAW}/oven-after.png")).astype(int)
    b = np.asarray(Image.open(f"{RAW}/oven-before.png")).astype(int)
    outside = np.ones((H, W), bool)
    outside[CAV[1]:CAV[3], CAV[0]:CAV[2]] = False
    print("max diff outside cavity:", int(np.abs(a-b).sum(2)[outside].max()))
    print("CONSTRUCTED OVEN DONE")
