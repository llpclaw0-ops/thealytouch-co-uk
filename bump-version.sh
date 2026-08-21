#!/bin/bash
# Run this after editing css/style.css or js/site.js so browsers pick up changes.
cd "$(dirname "$0")"
python3 - <<'PY'
import glob, re, hashlib
css_v = hashlib.md5(open("css/style.css","rb").read()).hexdigest()[:8]
js_v  = hashlib.md5(open("js/site.js","rb").read()).hexdigest()[:8]
for f in glob.glob("*.html"):
    s = open(f).read()
    s = re.sub(r'href="css/style\.css(\?v=[a-f0-9]+)?"', f'href="css/style.css?v={css_v}"', s)
    s = re.sub(r'src="js/site\.js(\?v=[a-f0-9]+)?"',   f'src="js/site.js?v={js_v}"', s)
    open(f,"w").write(s)
print(f"bumped: css={css_v} js={js_v}")
PY
