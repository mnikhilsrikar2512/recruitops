#!/usr/bin/env python3
"""Every local <script src>, <link href> and page link in frontend/ must exist.

    python tools/ci/static_assets_check.py
"""
import re
import sys
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
REF = re.compile(r'(?:src|href)="([^"#]+)"')
missing = []
for html in sorted(FRONTEND.rglob("*.html")):
    if "tests" in html.parts:
        continue
    for ref in REF.findall(html.read_text(encoding="utf-8")):
        if re.match(r"^(https?:|mailto:|tel:|data:|javascript:|//)", ref) or "${" in ref:
            continue
        clean = ref.split("?")[0]
        base = FRONTEND if clean.startswith("/") else html.parent  # server.js serves frontend/ at /
        target = (base / clean.lstrip("/")).resolve()
        if not target.exists():
            missing.append(f"{html.relative_to(FRONTEND)} → {ref}")
for item in missing:
    print("MISSING", item)
print(f"{len(missing)} missing local references")
sys.exit(1 if missing else 0)
