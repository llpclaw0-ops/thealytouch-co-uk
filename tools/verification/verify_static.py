#!/usr/bin/env python3
"""Static verification sweep for the Aly Touch site (gates 11-15, 18)."""
import os, re, glob, hashlib, subprocess, sys

SITE = "/Users/llp/mums-cleaning-site"
os.chdir(SITE)
fails, warns = [], []

pages = sorted(p for p in glob.glob("*.html"))
print(f"pages: {len(pages)} -> {', '.join(pages)}\n")

# --- gate 11: JS syntax
for js in glob.glob("js/*.js"):
    r = subprocess.run(["node", "--check", js], capture_output=True, text=True)
    print(f"[{'OK ' if r.returncode==0 else 'FAIL'}] node --check {js}")
    if r.returncode: fails.append(f"JS syntax {js}: {r.stderr[:200]}")

# --- gate 14: logo hash
def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()
src = "/Users/llp/Desktop/exec-88c0660e-3f28-49ac-bf56-4fc14c683e57.png"
a, b = sha(src), sha("img/the-aly-touch-logo.png")
print(f"[{'OK ' if a==b else 'FAIL'}] logo sha256 {b}")
if a != b: fails.append("logo hash mismatch")

# --- gate 18: phone
BAD_PHONE = re.compile(r"01481|000\s*000")
GOOD_DISPLAY, GOOD_HREF = "07781 446239", "tel:07781446239"
for p in pages:
    s = open(p).read()
    if BAD_PHONE.search(s):
        fails.append(f"{p}: old phone number present")
    for m in re.findall(r'href="tel:([^"]*)"', s):
        if m != "07781446239":
            fails.append(f"{p}: bad tel href tel:{m}")
    for m in re.findall(r'data-site="phone"[^>]*>([^<]*)<', s):
        if m.strip() and m.strip() != GOOD_DISPLAY:
            fails.append(f"{p}: bad phone text {m!r}")
print(f"[{'OK ' if not any('phone' in f for f in fails) else 'FAIL'}] phone number consistency")

# --- gate 15: unsupported services / claims
BANNED = {
    "window clean": r"window[- ]clean", "carpet clean": r"carpet[- ]clean",
    "upholstery": r"upholstery", "office clean": r"office[- ]clean",
    "commercial": r"commercial clean", "holiday let": r"holiday[- ]let",
    "end of tenancy": r"end[- ]of[- ]tenancy", "tenancy": r"\btenancy\b",
    "builders clean": r"builders?[- ]clean", "insured/insurance": r"\binsur",
    "DBS": r"\bDBS\b", "guarantee": r"guarantee", "free quote": r"free\s+quote",
    "no obligation": r"no[- ]obligation", "same day": r"same[- ]day",
    "fully vetted": r"vetted", "years experience": r"years?\s+(of\s+)?experience",
    "5 star/reviews": r"\b5[- ]star\b|(?<!not )(?<!no )testimonials?(?! ,| and not)|\breviews?\b(?! sites)",
    "price": r"£\s?\d", "hours": r"Mon\W*(–|-|to)\W*(Sat|Fri)",
}
for p in pages:
    s = open(p).read()
    for label, rx in BANNED.items():
        for m in re.finditer(rx, s, re.I):
            ctx = s[max(0, m.start()-120):m.end()+80].replace("\n", " ")
            # a denial ("not testimonials", "no guarantee") is not a claim
            if re.search(r"\bnot\b[^.]{0,80}$", ctx[:120+ (m.end()-m.start())], re.I):
                continue
            fails.append(f"{p}: banned '{label}' -> ...{ctx[:150]}...")
print(f"[{'OK ' if not any('banned' in f for f in fails) else 'FAIL'}] no unsupported services/claims")

# --- gate 13: local hrefs exist
for p in pages:
    s = open(p).read()
    for h in re.findall(r'href="([^"#?:]+\.html)[^"]*"', s):
        if not os.path.exists(h):
            fails.append(f"{p}: dead link -> {h}")
print(f"[{'OK ' if not any('dead link' in f for f in fails) else 'FAIL'}] local href targets exist")

# --- gate 12: images exist
imgs = set()
for p in pages:
    s = open(p).read()
    imgs |= set(re.findall(r'src="([^"]+\.(?:jpg|png|svg|webp)(?:\?v=[a-f0-9]+)?)"', s))
    for ss in re.findall(r'srcset="([^"]+)"', s):
        for part in ss.split(","):
            u = part.strip().split()[0]
            if u: imgs.add(u)
# Strip the ?v= cache-bust stamp: what must exist is the file, not the URL.
imgs = {i.split("?", 1)[0] for i in imgs}
missing = [i for i in sorted(imgs) if not os.path.exists(i)]
print(f"[{'OK ' if not missing else 'FAIL'}] {len(imgs)} referenced images, {len(missing)} missing")
for m in missing: fails.append(f"missing image {m}")

# --- gate 16: no misleading fallback (JS must not inject service content)
js = open("js/site.js").read()
if re.search(r"innerHTML\s*=\s*`", js):
    fails.append("site.js injects HTML via innerHTML template — possible fallback divergence")
# Injecting a static icon glyph is fine; injecting page/service CONTENT is not.
_bad = [m.group(0) for m in re.finditer(r'innerHTML\s*=\s*(`[^`]*`|"[^"]*"|\'[^\']*\')', js)
        if len(m.group(0)) > 60 or "<" in m.group(0)]
_inj = bool(_bad)
print(f"[{'OK ' if not _inj else 'FAIL'}] no JS-injected page content")
if _inj: fails.append(f"JS injects content: {_bad[:1]}")

# --- six cards, static, distinct before/after
idx = open("index.html").read()
n_ba = len(re.findall(r"<div class=\"ba\"", idx))
n_handle = len(re.findall(r"ba__handle", idx))
print(f"[{'OK ' if n_ba==6 else 'FAIL'}] homepage comparison cards: {n_ba}")
print(f"[{'OK ' if n_handle==6 else 'FAIL'}] homepage handles: {n_handle}")
if n_ba != 6: fails.append(f"expected 6 cards, found {n_ba}")
if n_handle != 6: fails.append(f"expected 6 handles, found {n_handle}")

for slot in ["floors", "bathroom", "bedroom", "oven", "skirting", "hoover"]:
    bf, af = f"img/ba/{slot}-before.jpg", f"img/ba/{slot}-after.jpg"
    if not (os.path.exists(bf) and os.path.exists(af)):
        fails.append(f"{slot}: missing pair"); continue
    if sha(bf) == sha(af):
        fails.append(f"{slot}: before and after are the SAME file")
print(f"[{'OK ' if not any('SAME file' in f for f in fails) else 'FAIL'}] all six pairs have distinct before/after")

# --- contrast (WCAG AA)
def lum(hexs):
    c = [int(hexs[i:i+2], 16)/255 for i in (1, 3, 5)]
    c = [x/12.92 if x <= .03928 else ((x+.055)/1.055)**2.4 for x in c]
    return .2126*c[0] + .7152*c[1] + .0722*c[2]
def ratio(f, b):
    l1, l2 = sorted([lum(f), lum(b)], reverse=True)
    return (l1+.05)/(l2+.05)
CHECKS = [("ink on ivory", "#17202b", "#fffaf2"), ("ink on beige", "#17202b", "#f4eadf"),
          ("ink on white", "#17202b", "#ffffff"), ("navy heading on ivory", "#0b2341", "#fffaf2"),
          ("copper-dk link on ivory", "#8f5326", "#fffaf2"),
          ("copper-dk link on white", "#8f5326", "#ffffff"),
          ("white on navy btn", "#ffffff", "#0b2341"),
          ("white on deep navy footer", "#ffffff", "#07182d"),
          ("ink-soft on ivory", "#4a5563", "#fffaf2")]
print("\ncontrast:")
for label, f, b in CHECKS:
    r = ratio(f, b)
    ok = r >= 4.5
    print(f"  [{'OK ' if ok else 'FAIL'}] {label}: {r:.2f}:1")
    if not ok: fails.append(f"contrast {label} {r:.2f}")

print("\n" + "="*60)
if fails:
    print(f"FAILURES ({len(fails)}):")
    for f in fails[:40]: print("  -", f)
else:
    print("ALL STATIC GATES PASS")
sys.exit(1 if fails else 0)
