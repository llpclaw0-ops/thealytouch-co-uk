# Approaches that did not work

Kept, not deleted, so the compute is not spent again. None of these runs in the
pipeline — see `docs/OVEN-PIPELINE.md` for what actually ships. Each script's
docstring says why it failed.

- `oven_grime_transfer.py` — low-frequency tone transfer. Keeps every rack and
  fan exactly in place, but a blurred multiply *is* a film: it reads as haze
  over the photo rather than dirt on a surface.
- `oven_cavity_inpaint.py` — inpaint the walls with hardware masked out. The
  rack is a fine grid, so the mask comes out speckled and the model fills the
  tiny islands with blocky mosaic noise.
- `oven_small_tiles.py` — small 2D tiles so each tile is pure surface. A 160px
  tile upscaled to 768 and back is soft, and the fans still vanish.
