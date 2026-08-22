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
import sys, pathlib
import numpy as np
from PIL import Image, ImageChops

BA = pathlib.Path("/Users/llp/mums-cleaning-site/img/ba")
OUT = pathlib.Path("/tmp/pair-diffs")
OUT.mkdir(exist_ok=True)

CARDS = ["floors", "bathroom", "bedroom", "oven", "skirting", "hoover"]

# Where each card is ALLOWED to change, as fractions of height.
# Everything outside this band must stay essentially identical.
ALLOWED = {
    "floors":   (0.45, 0.85),
    "bathroom": (0.60, 1.00),
    "bedroom":  (0.50, 1.00),
    "oven":     (0.10, 0.95),
    "skirting": (0.50, 1.00),
    "hoover":   (0.55, 1.00),
}

THRESH = 26          # per-channel delta counted as a real change
LEAK_FRAC = 0.010    # >1% of outside pixels changed = fail

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

    ok = out_frac <= LEAK_FRAC and in_frac >= 0.02
    why = []
    if out_frac > LEAK_FRAC:
        why.append(f"LEAK {out_frac*100:.1f}% of area outside dirt band changed")
    if in_frac < 0.02:
        why.append(f"TOO SUBTLE only {in_frac*100:.1f}% of dirt band changed")

    # visual diff: red where changed outside band, green inside
    vis = a.copy().convert("RGB")
    arr = np.asarray(vis).copy()
    arr[inside] = (arr[inside] * 0.35 + np.array([0, 255, 0]) * 0.65).astype(np.uint8)
    arr[outside] = (arr[outside] * 0.25 + np.array([255, 0, 0]) * 0.75).astype(np.uint8)
    Image.fromarray(arr).save(OUT / f"{name}-diff.png")

    return name, ok, ("; ".join(why) if why else
                      f"clean: {in_frac*100:.0f}% dirt in band, {out_frac*100:.2f}% leak"), zone

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
