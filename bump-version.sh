#!/bin/bash
# Run this after editing css/style.css, js/site.js, or ANY image, so browsers
# pick the change up. Images previously had no cache-busting at all: their
# filenames never change and the preview server sends no Cache-Control or
# ETag, so a rebuilt before/after JPEG kept showing the old picture.
cd "$(dirname "$0")"
python3 - <<'PY'
import glob, re, hashlib
css_v = hashlib.md5(open("css/style.css","rb").read()).hexdigest()[:8]
js_v  = hashlib.md5(open("js/site.js","rb").read()).hexdigest()[:8]
def img_v(path):
    try:
        return hashlib.md5(open(path, "rb").read()).hexdigest()[:8]
    except OSError:
        return None

IMG = re.compile(r'(img/[A-Za-z0-9_\-./]+\.(?:jpg|png|svg|webp))(\?v=[A-Za-z0-9_.\-]*)?')

def stamp(m):
    v = img_v(m.group(1))
    return m.group(1) + (f"?v={v}" if v else "")

n = 0
for f in glob.glob("*.html"):
    s = open(f).read()
    s = re.sub(r'href="css/style\.css(\?v=[^"]*)?"', f'href="css/style.css?v={css_v}"', s)
    s = re.sub(r'src="js/site\.js(\?v=[^"]*)?"',   f'src="js/site.js?v={js_v}"', s)
    s, k = IMG.subn(stamp, s)
    n += k
    open(f, "w").write(s)
print(f"bumped: css={css_v} js={js_v} images={n}")
PY
