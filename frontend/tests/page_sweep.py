#!/usr/bin/env python3
"""Browser sweep of every frontend page against the contract mock API.

Fails (exit 1) when any page:
  - throws an uncaught exception (ReferenceError, TypeError, …)
  - logs console.error
  - calls an API path/method/body the backend does not accept
    (reported by tests/mock-api-server.js)
and when a core list page does not render rows loaded from the API.

Usage (mock server must be running):
  python tests/page_sweep.py --base http://127.0.0.1:4180 [--persona admin] [--only pipeline-board]

Requires: pip install playwright && playwright install chromium
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGES = Path(__file__).resolve().parent.parent / "pages"
PUBLIC = {"login", "landing", "forgot-password", "reset-password", "password-setup", "use-cases",
          "not-found", "access-denied", "product-tour"}

# Core module pages must show rows that came from the API (Phase 1 exit gate).
# Value: CSS selector whose element count must be ≥ 1 after load.
LIVE_DATA_CHECKS = {
    "client-directory": ".workspace-surface tbody tr:not([hidden]):not([data-generated-empty-state])",
    "requisition-list": ".workspace-surface tbody tr:not([hidden]):not([data-generated-empty-state])",
    "candidate-profiles": "tbody tr:not([hidden]):not([data-generated-empty-state])",
    "approvals-inbox": "tbody tr[data-approval-id]",
    "pipeline-board": "[data-application-id], [data-pipeline-candidate-card]",
    "notifications-center": "[data-notification-id]",
    "user-management": "tbody tr:not([hidden]):not([data-generated-empty-state])",
}

# Pages the Admin (control plane, D-03) must reach by grant. Every other page
# may show Access Denied for the admin persona; the "full" persona (every
# code) must never be denied anything.
ADMIN_PAGES = {
    "location-management", "location-dashboard", "user-management", "user-detail",
    "role-management", "role-permissions-editor", "role-dashboard", "business-titles",
    "visibility-rules", "work-assignment", "portal-accounts", "approvals-inbox",
    "notifications-center", "notification-detail-panel", "analytics-dashboard",
    "company-dashboard", "user-performance-reports", "team-workload", "reports",
    "custom-report-builder", "report-viewer", "time-to-fill-report", "source-effectiveness",
    "sla-tracker",
}

# Third-party assets are stubbed so the sweep is hermetic and fast.
TAILWIND_STUB = "window.tailwind = window.tailwind || { config: {} };"

IGNORED_CONSOLE = (
    "Failed to load resource",  # stubbed fonts/images
    "favicon",
)
# Chrome aborts the cross-document @view-transition (global.css) when a page
# redirects while still loading (e.g. access-denied → login). The browser
# raises it as an uncaught DOMException; it is navigation noise, not app code.
IGNORED_PAGEERRORS = (
    "Transition was aborted because of invalid state",
)


LIVE = {"enabled": False, "session": None}


def mock(base: str, path: str):
    if LIVE["enabled"]:  # real backend: no mock log; contract checks don't apply
        return {"calls": [], "violations": []}
    with urllib.request.urlopen(base + path) as response:
        return json.loads(response.read() or b"{}")


def session_for(persona: str) -> dict:
    return {
        "token": f"mock-{persona}-token",
        "user_id": 1,
        "email": "asha@example.test",
        "user_name": "Asha Rao",
        "role": persona,
        "role_name": persona.title(),
        "role_code": persona,
        "location_id": 1,
        "location_name": "Bengaluru",
        "offers_enabled": True,
        "permissions": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:4180")
    ap.add_argument("--persona", default="admin")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--report", default="")
    ap.add_argument("--live", action="store_true", help="real backend: sign in through login.html first")
    ap.add_argument("--email", default="ci.admin@recruitops-test.com")
    ap.add_argument("--password", default="admin123")
    opts = ap.parse_args()

    names = sorted(p.stem for p in PAGES.glob("*.html"))
    if opts.only:
        names = [n for n in names if n in opts.only]
    LIVE["enabled"] = opts.live
    mock(opts.base, f"/__mock/reset?persona={opts.persona}")

    results: dict[str, dict] = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        if opts.live:
            # Real sign-in through the UI; reuse the resulting session for every page.
            login_ctx = browser.new_context()
            login_page = login_ctx.new_page()
            login_page.goto(f"{opts.base}/pages/login.html", wait_until="networkidle")
            login_page.fill("#email", opts.email)
            login_page.fill("#password", opts.password)
            login_page.click("#submit-btn")
            login_page.wait_for_url("**/home.html", timeout=15000)
            LIVE["session"] = login_page.evaluate("localStorage.getItem('recruitops-session')")
            login_ctx.close()
        for name in names:
            context = browser.new_context()
            if name not in PUBLIC and LIVE["session"]:
                context.add_init_script(
                    f"try {{ localStorage.setItem('recruitops-session', {json.dumps(LIVE['session'])});"
                    " localStorage.setItem('recruitops-onboarding-complete', 'true'); } catch (e) {}"
                )
            elif name not in PUBLIC:
                context.add_init_script(
                    f"try {{ localStorage.setItem('recruitops-session', {json.dumps(json.dumps(session_for(opts.persona)))});"
                    " localStorage.setItem('recruitops-onboarding-complete', 'true'); } catch (e) {}"
                )

            def route_external(route):
                url = route.request.url
                if "cdn.tailwindcss.com" in url:
                    return route.fulfill(status=200, content_type="application/javascript", body=TAILWIND_STUB)
                return route.fulfill(status=200, body="")

            # Third-party assets (Tailwind CDN, fonts) are stubbed in both modes.
            context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(opts.base) else route_external(route))
            page = context.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda exc, errors=errors: errors.append(f"uncaught: {exc}")
                    if not any(s in str(exc) for s in IGNORED_PAGEERRORS) else None)
            page.on("console", lambda msg, errors=errors: errors.append(f"console.error: {msg.text}")
                    if msg.type == "error" and not any(s in msg.text for s in IGNORED_CONSOLE) else None)
            before = len(mock(opts.base, "/__mock/log")["violations"])
            try:
                page.goto(f"{opts.base}/pages/{name}.html", wait_until="networkidle", timeout=20000)
                page.wait_for_timeout(400)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"navigation: {exc}")
            final = page.url.split("/")[-1]
            live = None
            denied = page.locator("text=Access Denied").count() > 0 or final.startswith("access-denied")
            if denied and name not in PUBLIC and (
                opts.persona == "full" or (opts.persona == "admin" and name in ADMIN_PAGES)
            ):
                errors.append(f"{opts.persona} persona was denied this page")
            if name in LIVE_DATA_CHECKS and not errors and not denied:
                live = page.locator(LIVE_DATA_CHECKS[name]).count()
                if live < 1:
                    errors.append(f"no API-loaded rows matched {LIVE_DATA_CHECKS[name]!r}")
            log = mock(opts.base, "/__mock/log")
            contract = [v for v in log["violations"][before:]]
            for v in contract:
                errors.append(f"contract {v['kind']}: {v['method']} {v['url']} — {v['detail']}")
            results[name] = {"errors": errors, "final_url": final, "live_rows": live, "denied": denied}
            context.close()
        browser.close()

    failed = {n: r for n, r in results.items() if r["errors"]}
    for name, r in sorted(results.items()):
        status = "FAIL" if r["errors"] else "ok  "
        extra = f" rows={r['live_rows']}" if r["live_rows"] is not None else ""
        extra += " (denied)" if r.get("denied") else ""
        redirected = "" if r["final_url"].startswith(name) else f" → {r['final_url']}"
        print(f"{status} {name}{extra}{redirected}")
        for e in r["errors"][:8]:
            print(f"       {e}")
    calls = mock(opts.base, "/__mock/log")["calls"]
    print(f"\n{len(results)} pages, {len(failed)} failing, {len(calls)} API calls served (persona={opts.persona})")
    if opts.report:
        Path(opts.report).write_text(json.dumps(results, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
