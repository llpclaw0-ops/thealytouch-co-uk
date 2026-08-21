# Site tooling

Everything needed to regenerate and verify this site's imagery.

## Why these exist

The before/after cards need images showing real dirt — mould on grout, baked-on
carbon in an oven, crumbs in a carpet. Three earlier attempts using ImageMagick
filters (noise, plasma blotches, darkening) all failed: filters can only change
colour and contrast, so "dirty" came out as black soot splatter or salt-and-pepper
speckle. Real grime is *generated content*, not a filter.

These images are produced locally with **SDXL on Apple Silicon (MPS)**. No API
key and no per-image cost. This machine (M3 Ultra, 96GB) runs a 1216x832 img2img
pass in roughly 35-40 seconds.

## Setup

```bash
python3 -m pip install --break-system-packages diffusers transformers accelerate safetensors
```

First run downloads ~7GB (base) and ~7GB (inpainting) into `~/.cache/huggingface`.

## Scripts

| Script | Purpose |
|---|---|
| `ai-image-generation/ai_gen.py` | Generates all six before/after pairs via img2img from real base photos. |
| `ai-image-generation/ai_oven_inpaint.py` | Oven *dirty* frame via cavity-masked inpainting. |
| `ai-image-generation/ai_oven_clean.py` | Oven *clean* frame, derived from the dirty frame so the door matches. |
| `ai-image-generation/ai_hero.py` | Optional alternative hero backgrounds. |
| `ai-image-generation/install_ai.py` | Converts raw PNGs to site JPEGs + 480/900 variants. |
| `verification/verify_static.py` | Full static gate sweep — run before claiming anything works. |

## The key technique: one base, two states

Both frames are denoised from the **same source image**, so room layout, camera
angle, windows and fixtures are shared by construction. Two independent
text2img generations could never guarantee that, and a mismatched pair
immediately reads as fake.

`strength` controls how far each frame drifts from the base:
- dirty: 0.50-0.60 (needs freedom to grow mould and carbon)
- clean: 0.30-0.38 (source is already tidy, so stay close)

## Pitfalls learned the hard way

1. **Never regenerate the clean frame from a pristine base.** It re-invents the
   appliance — the oven came back with a closed door (twice, once containing a
   loaf of bread, once lemons) while the dirty frame had it open. Derive the
   clean frame from the *dirty* one so geometry is inherited.
2. **Raising global img2img strength does not make something dirtier.** Past
   ~0.7 it changes the whole scene instead of soiling the target surface. Use
   masked inpainting to force dirt into one region.
3. **Negative-prompt text aggressively** (`text, letters, numbers, display`).
   SDXL will otherwise write gibberish on oven displays and appliance panels.
4. **Avoid shallow depth-of-field source photos.** They produce blurry output.
5. `magick montage` fails on this box with `unable to read font`. Use
   `magick a.png -resize 560x b.png -resize 560x +append out.png` instead.

## Regenerating everything

```bash
python3 tools/ai-image-generation/ai_gen.py          # ~4 min, all six pairs
python3 tools/ai-image-generation/ai_oven_inpaint.py before
python3 tools/ai-image-generation/ai_oven_clean.py
python3 tools/ai-image-generation/install_ai.py      # install into img/ba/
python3 tools/verification/verify_static.py          # must print ALL STATIC GATES PASS
```

Raw 1216x832 PNGs are kept in `assets-source/ai-raw/` so images can be
re-cropped or re-exported without paying the generation cost again.

## Honesty requirement

These images are AI-generated illustrations. Every card carries an
"AI-generated image" note and the section intro says so explicitly. They must
never be presented as photographs of customer jobs, testimonials, or proof of
completed work.
