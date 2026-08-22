#!/usr/bin/env python3
"""Objectively verify every before/after pair is the SAME photo plus dirt.

Eyeballing misses things. This measures where the two frames actually differ:

  - Builds a per-pixel difference map between before and after.
  - Reports the vertical band where changes occur (the "dirt zone").
  - FAILS if meaningful change happens OUTSIDE that band, because that means
    furniture, fixtures or handles were regenerated rather than soiled.
  - Renders a visual diff sheet so the changed regions can be inspected.

A correct pair changes ONLY on the surface being cleaned. Anything else - a new
chair, extra cabinet handles, a different table - shows up here as change in a
region it has no business being in.
"""
import re, sys, pathlib
import numpy as np
from PIL import Image, ImageChops

BA = pathlib.Path("/Users/llp/mums-cleaning-site/img/ba")
OUT = pathlib.Path("/tmp/pair-diffs")
OUT.mkdir(exist_ok=True)

CARDS = ["floors", "bathroom", "bedroom", "oven", "skirting", "hoover"]

# Where each card is ALLOWED to change, as fractions of height.
# Everything outside this band must stay essentially identical.
#
# Derived from the crops in ai_tiled_dirt.py rather than kept by hand, because
# the two drifted: after the floors crop moved to the worktop (0.46-0.56) its
# band still ran to 0.85, leaving the cabinet doors below it unchecked - which
# is exactly where a previous defect had appeared. Parsed with a regex instead
# of imported so this stays free of torch/diffusers.
MARGIN = 0.03          # feather bleed at the crop edges

def _bands():
    src = (pathlib.Path(__file__).resolve().parents[1]
           / "ai-image-generation" / "ai_tiled_dirt.py").read_text()
    out = {}
    # Entries can carry comment lines between `dict(` and `crop=`, so scan
    # forward from each card name rather than matching the whole block.
    for m in re.finditer(r'"(\w+)": dict\(', src):
        window = src[m.end():m.end() + 900]
        c = re.search(r"crop=\(\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)\s*\)", window)
        if c:
            y0, y1 = float(c.group(2)), float(c.group(4))
            out[m.group(1)] = (max(0.0, y0 - MARGIN), min(1.0, y1 + MARGIN))
    missing = [c for c in CARDS if c not in out]
    if missing:
        raise SystemExit(f"could not read crops for {missing} from ai_tiled_dirt.py")
    return out

ALLOWED = _bands()

THRESH = 26          # per-channel delta counted as a real change
LEAK_FRAC = 0.010    # >1% of outside pixels changed = fail

# A fraction alone is far too blunt. The dirt is pasted only inside the crop,
# so a correct pair changes EXACTLY 0 pixels outside the band - measured, all
# six sit at 0. Against an outside area of ~900k px, a whole invented control
# knob is only 0.2%, which sails under LEAK_FRAC. So cap the absolute count
# too. 200 leaves room for stray JPEG noise while catching any real object.
MAX_OUTSIDE_PX = 200

def check(name):
    bp, ap = BA / f"{name}-before.jpg", BA / f"{name}-after.jpg"
    if not bp.exists() or not ap.exists():
        return name, False, "missing image", None
    b = Image.open(bp).convert("RGB")
    a = Image.open(ap).convert("RGB")
    if b.size != a.size:
        a = a.resize(b.size, Image.LANCZOS)
    W, H = b.size

    nb, na = np.asarray(b).astype(int), np.asarray(a).astype(int)
    delta = np.abs(nb - na).max(axis=2)
    changed = delta > THRESH

    y0, y1 = ALLOWED[name]
    band = np.zeros((H, W), bool)
    band[int(y0 * H):int(y1 * H), :] = True

    outside = changed & ~band
    inside = changed & band
    out_frac = outside.sum() / max((~band).sum(), 1)
    in_frac = inside.sum() / max(band.sum(), 1)

    # rows where change occurs, to describe the real dirt zone
    rows = np.where(changed.any(axis=1))[0]
    zone = (round(rows.min() / H, 2), round(rows.max() / H, 2)) if len(rows) else (0, 0)

    out_px = int(outside.sum())
    ok = (out_frac <= LEAK_FRAC and out_px <= MAX_OUTSIDE_PX and in_frac >= 0.02)
    why = []
    if out_frac > LEAK_FRAC:
        why.append(f"LEAK {out_frac*100:.1f}% of area outside dirt band changed")
    if out_px > MAX_OUTSIDE_PX:
        why.append(f"LEAK {out_px} px changed outside dirt band (max {MAX_OUTSIDE_PX})")
    if in_frac < 0.02:
        why.append(f"TOO SUBTLE only {in_frac*100:.1f}% of dirt band changed")

    # visual diff: red where changed outside band, green inside
    vis = a.copy().convert("RGB")
    arr = np.asarray(vis).copy()
    arr[inside] = (arr[inside] * 0.35 + np.array([0, 255, 0]) * 0.65).astype(np.uint8)
    arr[outside] = (arr[outside] * 0.25 + np.array([255, 0, 0]) * 0.75).astype(np.uint8)
    Image.fromarray(arr).save(OUT / f"{name}-diff.png")

    return name, ok, ("; ".join(why) if why else
                      f"clean: {in_frac*100:.0f}% dirt in band, {out_px} px leak"), zone

if __name__ == "__main__":
    names = sys.argv[1:] or CARDS
    fails = []
    print(f"{'card':10s} {'result':6s} detail")
    print("-" * 74)
    for n in names:
        name, ok, why, zone = check(n)
        print(f"{name:10s} {'PASS' if ok else 'FAIL':6s} {why}"
              + (f"  [change rows {zone[0]}-{zone[1]}]" if zone else ""))
        if not ok:
            fails.append(name)
    print("-" * 74)
    print("ALL PAIRS CLEAN" if not fails else f"NEEDS WORK: {', '.join(fails)}")
    print(f"diff sheets in {OUT}")
    sys.exit(1 if fails else 0)
