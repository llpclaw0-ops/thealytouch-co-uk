# How the oven card is built

The oven is the only card that needs more than one step, because it is the only
one where the thing being cleaned contains hardware.

The generation steps read and write `/tmp/ai-raw`, which does not survive a
reboot. Seed it from the repo first if it is empty:

```bash
mkdir -p /tmp/ai-raw && cp assets-source/ai-raw/*.png /tmp/ai-raw/
```

`oven_restore_fans.py` falls back to `assets-source/ai-raw` on its own, so
steps 3-4 alone rebuild the shipped image without step 1 or 2.

```bash
# 1. base: an open-door oven, empty clean cavity (AI, composition-referenced)
python3 tools/ai-image-generation/ai_oven_open_base.py      # writes candidates
#    pick one by eye -> /tmp/ai-raw/oven-openbase.png

# 2. dirty layer: grime on the cavity, strength 0.65
python3 tools/ai-image-generation/ai_tiled_dirt.py oven
cp /tmp/ai-raw/oven-before.png /tmp/ai-raw/oven-dirty-layer.png

# 3. put the two fan discs back, soiled  -> final before/after
python3 tools/ai-image-generation/oven_restore_fans.py

# 4. install + verify
python3 tools/ai-image-generation/install_ai.py oven
python3 tools/verification/verify_pairs.py
```

## Why step 3 exists

Strength 0.65 is the only setting at which the cavity reads as genuinely
filthy. Below it there is no visible dirt; at 0.75 and above the model starts
inventing hardware. But even at 0.65 it rewrites the two fan discs on the back
wall into pipework. Step 3 takes those discs back from the clean base and
darkens them by the grime's own local tone, deterministically, so they cannot
move or change shape.

## Approaches that did not work

Moved to `tools/ai-image-generation/rejected/` - kept, not deleted, so nobody
spends the compute again. None of them runs in the pipeline:

| Script | Result |
|---|---|
| `rejected/oven_grime_transfer.py` | Low-frequency tone transfer. Keeps every rack and fan exactly in place, but a blurred multiply IS a grey film - it reads as haze over the photo, not dirt on a surface. Adding the source's texture back ghosts, because its geometry differs. |
| `rejected/oven_cavity_inpaint.py` | Inpaint the walls with hardware masked out. The rack is a fine grid, so the mask comes out speckled and the model fills the tiny islands with blocky digital-mosaic noise. |
| `rejected/oven_small_tiles.py` | Small 2D tiles so each tile is pure surface. Upscaling a 160px tile to 768 and back softens it; the result looks out of focus and the fans still vanish. |

## Known limits of the shipped image

- Inside the cavity the BEFORE contains a couple of small invented details -
  a rod-like streak on the lower shelf and some pipework at the top of the back
  wall. They are inside the cavity and read as grime at card size, but they are
  not dirt. Everything outside the cavity is pixel-identical.
- The oven is a French-door range, not the single drop-down door typical of a
  UK domestic kitchen. That came from the composition reference.

## What verify_pairs.py can and cannot catch

It compares the pair pixel by pixel and fails on change **outside** the allowed
band. It cannot see anything wrong **inside** the band.

The previous oven card passed this check while containing an invented second
control panel - four extra knobs and a red indicator in the BEFORE only -
because the old band was `(0.10, 0.95)`, nearly the whole frame, and the panel
sat inside it. Two things were changed:

1. The band is now `(0.30, 0.78)`, the cavity only, so the control panel (rows
   0.11-0.26, measured) is outside it.
2. A `MAX_OUTSIDE_PX = 200` cap was added. `LEAK_FRAC` alone was not enough:
   injecting a single fake knob into the panel changed 1732 px, which is only
   **0.2%** of the ~888k px outside the band and passed the 1% fraction test.
   The absolute cap catches it. This was verified by injecting the defect and
   confirming the check fails, then restoring.

A correct pair changes **exactly 0** pixels outside the band, and all six do.

### Still not caught

Anything wrong *inside* the band is invisible to this check - that includes the
cavity's own hardware. Nothing automated will tell you the fans turned into
pipes. **Look at the montage as well as running the check:**

```bash
cd /tmp/ai-raw && magick oven-before.png -resize 470x oven-after.png -resize 470x +append /tmp/oven_check.png
```

`magick montage` fails on this machine ("unable to read font") - use `+append`.
