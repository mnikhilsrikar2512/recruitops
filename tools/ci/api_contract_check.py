#!/usr/bin/env python3
"""Static API contract check: every apiRequest() path the frontend calls must
match a route the FastAPI backend declares (method + path template).

Parses backend/app/api/router.py for router prefixes and backend/app/api/v1/*.py
for @router.<method>("...") decorators, then scans frontend/shared/*.js for
apiRequest(<string or template literal>, { method: ... }) calls.
Exit code 1 if any call has no matching route.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
API = ROOT / "backend/app/api"

prefixes = {m.group(1): m.group(2) for m in re.finditer(
    r'include_router\((\w+)\.router(?:,\s*prefix="([^"]*)")?', (API / "router.py").read_text())}
prefixes = {k: (v or "") for k, v in prefixes.items()}

routes: list[tuple[str, re.Pattern, str]] = []
for f in sorted((API / "v1").glob("*.py")):
    mod = f.stem
    if mod not in prefixes:
        continue
    src = f.read_text()
    for m in re.finditer(r'@router\.(get|post|patch|put|delete)\(\s*"([^"]*)"', src):
        method, path = m.group(1).upper(), prefixes[mod] + m.group(2)
        regex = re.sub(r"\{[^}:]+:path\}", ".+", path)
        regex = re.sub(r"\{[^}]+\}", "[^/]+", regex)
        routes.append((method, re.compile("^" + regex.rstrip("/") + "/?$"), path))

CALL = re.compile(r'apiRequest\(\s*([`"\'])(.*?)\1\s*(\+[^,)]*)?(?:,\s*\{(.{0,200}?)\})?', re.S)
# Concrete sample URL for each backend route ({param} → 1, {x:path} → a/b).
samples = []
for method, _rx, path in routes:
    sample = re.sub(r"\{[^}:]+:path\}", "a/b", path)
    samples.append((method, re.sub(r"\{[^}]+\}", "1", sample).rstrip("/") or "/", path))

def frontend_regex(raw: str, concat: bool) -> re.Pattern:
    """Literal parts must match exactly; each ${...} (or a trailing + expr)
    may stand for any run of path characters (an id, a segment, a query)."""
    parts = re.split(r"\$\{[^}]*\}", raw)
    body = "[^?]*".join(re.escape(p) for p in parts)
    if concat:
        body += "[^?]*"
    body = body.split("\\?")[0]  # drop the literal query string
    if body.startswith(re.escape("/api/v1")):
        body = body[len(re.escape("/api/v1")):]
    return re.compile("^" + body.rstrip("/") + "/?(?:\\?.*)?$")

failures, checked = [], 0
for js in sorted((ROOT / "frontend/shared").glob("*.js")):
    text = js.read_text()
    for m in CALL.finditer(text):
        raw, concat, opts = m.group(2), bool(m.group(3)), m.group(4) or ""
        mm = re.search(r'method:\s*["\'](\w+)["\']', opts)
        method = (mm.group(1) if mm else "GET").upper()
        rx = frontend_regex(raw, concat)
        checked += 1
        concrete = re.sub(r"\$\{[^}]*\}", "X", raw.split("?")[0]) + ("X" if concat else "")
        if concrete.startswith("/api/v1"):
            concrete = concrete[len("/api/v1"):]
        concrete = concrete.rstrip("/") or "/"
        by_route = any(meth == method and route_rx.match(concrete) for meth, route_rx, _ in routes)
        by_sample = any(meth == method and (rx.match(sample) or rx.match(sample + "/"))
                        for meth, sample, _ in samples)
        if not (by_route or by_sample):
            line = text.count("\n", 0, m.start()) + 1
            failures.append(f"{js.name}:{line}  {method} {raw}{' + …' if concat else ''}")

print(f"{len(routes)} backend routes, {checked} frontend calls checked")
for f in failures:
    print("  NO MATCHING ROUTE:", f)
sys.exit(1 if failures else 0)
