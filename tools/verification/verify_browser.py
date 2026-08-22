#!/usr/bin/env python3
"""Browser verification gates for The Aly Touch.

Covers the gates that need a real engine: navigation, slider pointer/keyboard/
touch interaction, viewport overflow, console cleanliness, image loading.

Uses Playwright driving the installed Chrome, so it needs no remote-debugging
approval dialog.
"""
import sys, re, pathlib
from playwright.sync_api import sync_playwright

BASE = "http://localhost:4321"
ROOT = pathlib.Path("/Users/llp/mums-cleaning-site")
PAGES = sorted(p.name for p in ROOT.glob("*.html"))

fails, notes = [], []
def ok(m):   print(f"[OK ] {m}")
def bad(m):  print(f"[FAIL] {m}"); fails.append(m)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")

    # ---------- desktop pass ----------
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    console = []
    page.on("console", lambda m: console.append((m.type, m.text)))
    page.on("pageerror", lambda e: console.append(("pageerror", str(e))))

    # gate 2: every page loads
    for name in PAGES:
        r = page.goto(f"{BASE}/{name}", wait_until="networkidle")
        if not r or r.status != 200:
            bad(f"{name} status {r.status if r else 'none'}")
            continue
        # gate 12: images actually load
        broken = page.evaluate(
            "[...document.querySelectorAll('img')]"
            ".filter(i=>i.complete&&i.naturalWidth===0).map(i=>i.getAttribute('src'))")
        if broken: bad(f"{name} broken images {broken}")
        # gate 9: no horizontal overflow
        if page.evaluate("document.documentElement.scrollWidth>window.innerWidth+1"):
            bad(f"{name} horizontal overflow at 1440px")
    ok(f"all {len(PAGES)} pages load, images resolve, no desktop overflow")

    # gate 3: primary nav works from every primary page
    primaries = ["index.html","services.html","about.html","contact.html","blog.html"]
    for name in primaries:
        page.goto(f"{BASE}/{name}", wait_until="networkidle")
        links = page.evaluate(
            "[...document.querySelectorAll('.site-nav a,nav a')]"
            ".map(a=>a.getAttribute('href')).filter(h=>h&&!h.startsWith('#'))")
        if len(links) < 4: bad(f"{name} nav has only {len(links)} links")
        for h in links:
            t = (ROOT / h.split('#')[0]).resolve()
            if not t.exists(): bad(f"{name} nav -> missing {h}")
    ok("primary navigation resolves from every primary page")

    # gates 4/5/6: comparison cards
    page.goto(f"{BASE}/index.html", wait_until="networkidle")
    cards = page.locator("[data-ba]")
    n = cards.count()
    if n != 6: bad(f"expected 6 comparison cards, found {n}")
    else: ok("6 comparison cards present")

    handles = page.locator("[role='slider']")
    if handles.count() != 6: bad(f"expected 6 handles, found {handles.count()}")
    else: ok("6 draggable handles present")

    # gate 5: real pointer drag
    # NOTE: role="slider" sits on the whole card, not a small grip, so drag from
    # the card centre and stay inside its bounds. Re-query the value after the
    # mouse settles rather than reading a stale handle reference.
    for i in range(n):
        h = handles.nth(i)
        h.scroll_into_view_if_needed(); page.wait_for_timeout(150)
        before = h.get_attribute("aria-valuenow")
        box = h.bounding_box()
        cx, cy = box["x"]+box["width"]/2, box["y"]+box["height"]/2
        page.mouse.move(cx, cy); page.mouse.down(); page.wait_for_timeout(60)
        page.mouse.move(box["x"]+box["width"]*0.15, cy, steps=15)
        page.wait_for_timeout(100); page.mouse.up(); page.wait_for_timeout(200)
        after = h.get_attribute("aria-valuenow")
        if before == after: bad(f"card {i+1}: pointer drag did not move slider ({before})")
    ok("pointer drag moves all 6 sliders")

    # gate 6: keyboard
    for i in range(n):
        h = handles.nth(i)
        h.focus()
        start = h.get_attribute("aria-valuenow")
        page.keyboard.press("ArrowLeft"); page.keyboard.press("ArrowLeft")
        mid = h.get_attribute("aria-valuenow")
        page.keyboard.press("ArrowRight")
        end = h.get_attribute("aria-valuenow")
        if not (start != mid and mid != end):
            bad(f"card {i+1}: arrow keys did not move slider {start}->{mid}->{end}")
        page.keyboard.press("Home");  home = h.get_attribute("aria-valuenow")
        page.keyboard.press("End");   endk = h.get_attribute("aria-valuenow")
        if home != "0" or endk != "100":
            bad(f"card {i+1}: Home/End gave {home}/{endk}, expected 0/100")
    ok("ArrowLeft/Right and Home/End move all 6 sliders")

    # gate 19: Get a Quote route + form
    page.goto(f"{BASE}/index.html", wait_until="networkidle")
    q = page.locator("a:has-text('Get a quote'):visible").first
    if q.count() == 0: bad("no visible Get a Quote link on homepage")
    else:
        q.click(); page.wait_for_load_state("networkidle")
        if "contact" not in page.url: bad(f"Get a Quote went to {page.url}")
        else:
            form = page.locator("form")
            if form.count() == 0: bad("contact page has no form")
            else:
                fields = page.evaluate(
                    "[...document.querySelectorAll('form input,form textarea,form select')].length")
                labelled = page.evaluate("""
                  [...document.querySelectorAll('form input,form textarea,form select')]
                    .filter(el=>{
                      if(el.type==='hidden')return true;
                      if(el.getAttribute('aria-label'))return true;
                      if(el.closest('label'))return true;          // wrapping label is valid
                      const id=el.id; return id && document.querySelector(`label[for="${id}"]`);
                    }).length""")
                if fields != labelled:
                    bad(f"form: {fields-labelled} of {fields} controls unlabelled")
                else:
                    ok(f"Get a Quote reaches contact form; {fields} controls all labelled")

    # gate 20 + heading sanity: no clipping/overflow of headings
    for name in PAGES:
        page.goto(f"{BASE}/{name}", wait_until="networkidle")
        clipped = page.evaluate("""
          [...document.querySelectorAll('h1,h2,h3')].filter(h=>{
            const s=getComputedStyle(h);
            return h.scrollWidth > h.clientWidth + 2 && s.overflow !== 'visible';
          }).map(h=>h.textContent.trim().slice(0,40))""")
        if clipped: bad(f"{name} clipped headings {clipped}")
    ok("no clipped or overflowing headings on any page")

    # ---------- mobile pass ----------
    mctx = browser.new_context(viewport={"width":390,"height":844},
                               is_mobile=True, has_touch=True,
                               user_agent=("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                                           "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile Safari/604.1"))
    m = mctx.new_page()
    mconsole = []
    m.on("console", lambda x: mconsole.append((x.type, x.text)))
    m.on("pageerror", lambda e: mconsole.append(("pageerror", str(e))))

    for name in PAGES:
        m.goto(f"{BASE}/{name}", wait_until="networkidle")
        if m.evaluate("document.documentElement.scrollWidth>window.innerWidth+1"):
            bad(f"{name} horizontal overflow at 390px")
    ok("no horizontal overflow at 390x844 on any page")

    # mobile menu
    m.goto(f"{BASE}/index.html", wait_until="networkidle")
    btn = m.locator("[aria-expanded]").first
    if btn.count() == 0:
        notes.append("no mobile menu toggle found")
    else:
        pre = btn.get_attribute("aria-expanded")
        btn.click(); m.wait_for_timeout(350)
        opened = btn.get_attribute("aria-expanded")
        btn.click(); m.wait_for_timeout(350)
        closed = btn.get_attribute("aria-expanded")
        if not (pre=="false" and opened=="true" and closed=="false"):
            bad(f"mobile menu aria-expanded {pre}->{opened}->{closed}")
        else: ok("mobile menu opens and closes with correct aria-expanded")

    # gate 7: touch drag.
    # The slider uses POINTER events (which cover touch), so synthetic TouchEvent
    # objects never reach it. Dispatch real touch input via CDP instead - this is
    # what an actual finger sends.
    m.goto(f"{BASE}/index.html", wait_until="networkidle")
    mh = m.locator("[role='slider']").first
    mh.scroll_into_view_if_needed(); m.wait_for_timeout(400)
    b4 = mh.get_attribute("aria-valuenow")
    box = mh.bounding_box()
    if box:
        cx, cy = box["x"]+box["width"]/2, box["y"]+box["height"]/2
        cdp = m.context.new_cdp_session(m)
        cdp.send("Input.dispatchTouchEvent", {"type":"touchStart","touchPoints":[{"x":cx,"y":cy}]})
        for step in range(6):
            nx = cx - (box["width"]*0.35)*(step+1)/6
            cdp.send("Input.dispatchTouchEvent", {"type":"touchMove","touchPoints":[{"x":nx,"y":cy}]})
            m.wait_for_timeout(30)
        cdp.send("Input.dispatchTouchEvent", {"type":"touchEnd","touchPoints":[]})
        m.wait_for_timeout(250)
        aft = mh.get_attribute("aria-valuenow")
        if b4 == aft: bad(f"touch drag did not move slider ({b4})")
        else: ok(f"touch drag moves slider {b4} -> {aft}")

    # gate 10: console clean
    noise = [c for c in console+mconsole
             if c[0] in ("error","warning","pageerror")
             and "favicon" not in c[1].lower()]
    if noise:
        for t,msg in noise[:8]: bad(f"console {t}: {msg[:110]}")
    else:
        ok("no console errors or warnings on any page (desktop + mobile)")

    browser.close()

print()
for n in notes: print(f"[note] {n}")
print("="*60)
print("ALL BROWSER GATES PASS" if not fails else f"{len(fails)} BROWSER GATE FAILURE(S)")
sys.exit(1 if fails else 0)
