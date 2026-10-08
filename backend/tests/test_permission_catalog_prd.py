"""Plan 2.7: no code ships without a PRD row (PRD §3.2 product rows + §3.3
implementation codes). Every permission code a route checks, a page gate
uses (navigation.config.js) or the Admin template grants must be listed."""
import re
from pathlib import Path

from app.core.rbac import ADMIN_PERMISSION_CODES

REPO = Path(__file__).resolve().parents[2]
CODE = re.compile(r'"([a-z_]+\.[a-z_.]+)"')


def _prd_codes() -> set[str]:
    text = (REPO / "docs" / "PRODUCT_REQUIREMENTS_DOCUMENT.md").read_text(encoding="utf-8")
    body = text.split("### 3.2", 1)[1].split("\n## 4.", 1)[0]
    codes: set[str] = set()
    for line in body.splitlines():
        if not line.startswith("| `"):
            continue
        base = None
        for part in re.findall(r"`([^`]+)`", line.split("|")[1]):
            if part.startswith(".") and base:
                codes.add(base + part)
            else:
                codes.add(part)
                base = part.rsplit(".", 1)[0]
    return codes


def _used_codes() -> dict[str, str]:
    used: dict[str, str] = {}
    for path in (REPO / "backend" / "app" / "api").rglob("*.py"):
        for call in re.findall(r"require_(?:any_)?permissions?\(([^)]*)\)", path.read_text(encoding="utf-8")):
            for code in CODE.findall(call):
                used.setdefault(code, f"route in {path.name}")
    nav = (REPO / "frontend" / "shared" / "navigation.config.js").read_text(encoding="utf-8")
    for code in CODE.findall(nav):
        if not code.endswith(".html"):
            used.setdefault(code, "navigation.config.js")
    for code in ADMIN_PERMISSION_CODES:
        used.setdefault(code, "Admin template")
    return used


def test_every_code_in_use_has_a_prd_row() -> None:
    prd = _prd_codes()
    missing = {code: where for code, where in _used_codes().items() if code not in prd}
    assert not missing, f"add PRD §3.2/§3.3 rows for: {missing}"


def test_scope_company_is_documented_and_admin_only_by_default() -> None:
    text = (REPO / "docs" / "PRODUCT_REQUIREMENTS_DOCUMENT.md").read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| `scope.company`"))
    assert row.rstrip().endswith("| ● | ○ | ○ |")
