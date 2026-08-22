# Where the before/after imagery comes from

Every before/after image on the site is **AI-generated** (SDXL, run locally).
None is a photograph of a customer's home or of a completed job, and the page
says so next to the cards. Nothing here should ever be presented as a real job.

## The oven card

The oven card needed something the other five did not: an oven with its **door
open** and the cavity visible, so the cavity could be shown dirty and then
clean.

Text-to-image could not produce it. Across many seeds and prompt variants SDXL
returned closed doors, wide kitchen shots, and gibberish lettering on control
panels. The earlier base photo was a closed built-in oven with a pie on the
middle shelf, which survived inpainting even at strength 0.92.

So a Creative Commons photograph was used **as a composition reference only**,
passed through img2img so the published image is AI-generated and is not that
photograph or anyone's real kitchen:

| | |
|---|---|
| Title | "oven" |
| Author | RBerteig |
| Source | https://www.flickr.com/photos/51035786238@N01/8011162515 |
| Licence | CC BY 2.0 — https://creativecommons.org/licenses/by/2.0/ |
| Attribution string | "oven" by RBerteig is licensed under CC BY 2.0. |
| Found via | Openverse API |
| Used as | img2img composition reference, strength 0.42, seed 11 |
| Kept at | `assets-source/ai-raw/oven-composition-ref.png` (cropped to 3:2) |

The reference is **not** published anywhere on the site. It was used because a
real photograph could supply the open-door geometry that the model could not
invent. Publishing the photograph itself was deliberately avoided: adding
filth to a real, identifiable home in order to advertise cleaning would
misrepresent that home, and a CC BY licence grants copyright permission, not
permission to do that.

If you would rather not rely on a CC BY reference at all, the fix is to
commission or shoot one photograph of an open oven; everything downstream
already works from a single base image.

## How a pair is made

The AFTER is the untouched base image. The BEFORE is that same image with dirt
generated only on the surface being cleaned. `tools/verification/verify_pairs.py`
compares the two pixel by pixel and fails if anything meaningful changes
outside the allowed band.
