#!/usr/bin/env python3
"""Install AI-generated pairs into the website image directory.

Converts the 1216x832 SDXL PNGs into the 3:2 JPEGs the cards expect, plus
480/900 responsive variants. Verifies before/after are genuinely different
files and that both exist for every slot.
"""
import os, subprocess, sys, hashlib

RAW = "/tmp/ai-raw"
OUT = "/Users/llp/mums-cleaning-site/img/ba"
os.makedirs(OUT, exist_ok=True)
W, H = 1600, 1067

SLOTS = ["floors", "bathroom", "bedroom", "oven", "skirting", "hoover"]
only = sys.argv[1:] or SLOTS

def run(a):
    r = subprocess.run(["magick"] + [str(x) for x in a], capture_output=True, text=True)
    if r.returncode:
        print("FAIL:", " ".join(map(str, a))[:200]); print(r.stderr[:300]); sys.exit(1)

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

for slot in only:
    for st in ("before", "after"):
        src = f"{RAW}/{slot}-{st}.png"
        if not os.path.exists(src):
            print(f"MISSING {src}"); sys.exit(1)
        dst = f"{OUT}/{slot}-{st}.jpg"
        run([src, "-resize", f"{W}x{H}^", "-gravity", "center",
             "-extent", f"{W}x{H}", "+repage",
             "-quality", "88", "-strip", dst])
        for w in (480, 900):
            run([dst, "-resize", f"{w}x", "-quality", "85", "-strip",
                 f"{OUT}/{slot}-{st}-{w}.jpg"])
    b, a = sha(f"{OUT}/{slot}-before.jpg"), sha(f"{OUT}/{slot}-after.jpg")
    assert b != a, f"{slot}: before and after identical!"
    print(f"installed {slot}  before={b[:8]} after={a[:8]}")

print("INSTALL OK")
