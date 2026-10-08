"""Phase 2 exit gate: the Admin's default sidebar == PRD §3.1, exactly.

The sidebar shows an entry when it is in ADMIN_SIDEBAR_BASE (navigation.js)
AND the Admin template (app/core/rbac.py) holds one of its gate codes
(navigation.config.js), or it has no gate (account chrome)."""
import re
from pathlib import Path

from app.core.rbac import ADMIN_PERMISSION_CODES

REPO = Path(__file__).resolve().parents[2]

# PRD §3.1, mapped to page ids. Pages the PRD lists that are not built yet
# (AI usage & policy) join this set
# when their pages ship. My Work appears only with an execution grant.
PRD_ADMIN_SIDEBAR = {
    # Work / home
    "role-dashboard", "company-dashboard", "location-dashboard",
    # Inbox
    "notifications-center", "approvals-inbox",
    # Admin
    "user-management", "location-management", "role-management", "role-permissions-editor",
    "business-titles", "visibility-rules", "work-assignment", "portal-accounts",
    # Stage Bucket Map: pipeline spec §1.3 control-plane page (Phase 4.5)
    "stage-bucket-map",
    # Audit Log (Phase 5.4)
    "audit-log-viewer",
    # Data Export/Delete Requests (Phase 5.3)
    "data-export-delete-request",
    # Reports (library + oversight views)
    "analytics-dashboard", "reports", "custom-report-builder", "time-to-fill-report",
    "source-effectiveness", "sla-tracker", "user-performance-reports", "team-workload",
    # Account
    "my-profile", "support-workspace", "tenant-setup",
}


def _admin_visible() -> set[str]:
    config = (REPO / "frontend" / "shared" / "navigation.config.js").read_text(encoding="utf-8")
    entries = {
        m.group(1): re.findall(r'"([^"]+)"', m.group(2))
        for m in re.finditer(r'id: "([^"]+)",[\s\S]*?permissions: \[([^\]]*)\]', config)
    }
    nav = (REPO / "frontend" / "shared" / "navigation.js").read_text(encoding="utf-8")
    base = set(re.findall(r'"([a-z-]+)"', nav.split("const ADMIN_SIDEBAR_BASE = new Set([")[1].split("]);")[0]))
    granted = set(ADMIN_PERMISSION_CODES)
    return {page for page in base if page in entries and (not entries[page] or set(entries[page]) & granted)}


def test_admin_sidebar_matches_prd_exactly() -> None:
    visible = _admin_visible()
    assert visible == PRD_ADMIN_SIDEBAR, {
        "extra": sorted(visible - PRD_ADMIN_SIDEBAR),
        "missing": sorted(PRD_ADMIN_SIDEBAR - visible),
    }
