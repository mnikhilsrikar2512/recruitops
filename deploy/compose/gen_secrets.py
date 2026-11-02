#!/usr/bin/env python3
"""Fill the empty secrets in deploy/compose/staging.env (local stack only).

    cp deploy/compose/staging.env.example deploy/compose/staging.env
    python3 deploy/compose/gen_secrets.py deploy/compose/staging.env

Only blank values are filled; anything you already set is kept.
Never reuse these values in a real environment.
"""
import base64
import os
import re
import secrets
import sys

db = "Ro-" + secrets.token_urlsafe(18) + "!9a"  # SQL Server policy: upper, lower, digit, symbol
FRESH = {
    "DB_PASSWORD": db,
    "MSSQL_SA_PASSWORD": db,
    "S3_SECRET_ACCESS_KEY": secrets.token_urlsafe(24),
    "JWT_SIGNING_KEY": secrets.token_urlsafe(48),
    "MFA_ENCRYPTION_KEYS": "local1:" + base64.urlsafe_b64encode(os.urandom(32)).decode(),
    "METRICS_TOKEN": secrets.token_urlsafe(32),
}

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "staging.env")
lines = open(path, encoding="utf-8").read().splitlines()
current = dict(line.split("=", 1) for line in lines if "=" in line and not line.lstrip().startswith("#"))
if current.get("DB_PASSWORD") and not current.get("MSSQL_SA_PASSWORD"):
    FRESH["MSSQL_SA_PASSWORD"] = current["DB_PASSWORD"]  # the stack's app login is sa
filled = []
for i, line in enumerate(lines):
    match = re.match(r"^([A-Z0-9_]+)=$", line)
    if match and match.group(1) in FRESH:
        lines[i] = f"{match.group(1)}={FRESH[match.group(1)]}"
        filled.append(match.group(1))
open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("filled:", ", ".join(filled) or "nothing (all set already)")
