#!/usr/bin/env python3
"""Give every page one cache-busting version for the shared assets.

The version is a hash of everything under shared/, so it changes exactly
when an asset changes. Rewrites `?v=…` on links to shared/ files in
index.html and pages/*.html.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
digest = hashlib.sha256()
for path in sorted((ROOT / "shared").rglob("*")):
    if path.is_file():
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
version = digest.hexdigest()[:10]

PATTERN = re.compile(r'((?:\.\./)?shared/[\w./-]+\.(?:css|js))(?:\?v=[\w]+)?')
changed = 0
for page in [ROOT / "index.html", *sorted((ROOT / "pages").glob("*.html"))]:
    text = page.read_text(encoding="utf-8")
    new = PATTERN.sub(lambda m: f"{m.group(1)}?v={version}", text)
    if new != text:
        page.write_text(new, encoding="utf-8")
        changed += 1
print(f"assets version {version} ({changed} pages updated)")
