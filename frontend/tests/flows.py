#!/usr/bin/env python3
"""End-to-end UI flows against the contract mock API (tests/mock-api-server.js).

Each flow drives the real pages in Chromium and asserts that the expected API
call went out with a body the backend schema accepts (the mock returns 422 and
records a violation otherwise), with no uncaught errors on the page.

Usage (mock server must be running):
  python tests/flows.py --base http://127.0.0.1:4180
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request

from playwright.sync_api import Page, sync_playwright

TAILWIND_STUB = "window.tailwind = window.tailwind || { config: {} };"


def mock(base, path):
    with urllib.request.urlopen(base + path) as r:
        return json.loads(r.read() or b"{}")


def session(persona="full"):
    return {"token": f"mock-{persona}-token", "user_id": 1, "email": "asha@example.test", "user_name": "Asha Rao",
            "role": persona, "role_name": persona.title(), "role_code": persona, "location_id": 1,
            "location_name": "Bengaluru", "offers_enabled": True, "permissions": []}


# Chromium rejects the cross-document View Transition promise ("Transition
# was aborted because of invalid state") when a navigation starts while the
# page is mid-transition — e.g. logout redirecting at once. It is the
# browser's own internal promise, not app code, and the navigation still
# completes; newer Chromium in CI surfaces it as a pageerror.
_BENIGN_ERRORS = ("Transition was aborted because of invalid state",)


def _benign(message: str) -> bool:
    return any(marker in message for marker in _BENIGN_ERRORS)


class Flow:
    def __init__(self, browser, base, signed_in=True):
        self.base = base
        self.context = browser.new_context()
        if signed_in:
            self.context.add_init_script(
                f"try {{ if (!sessionStorage.getItem('flow-seeded')) {{ sessionStorage.setItem('flow-seeded', '1'); localStorage.setItem('recruitops-session', {json.dumps(json.dumps(session()))}); }}"
                " localStorage.setItem('recruitops-onboarding-complete', 'true'); } catch (e) {}")
        self.context.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base) else r.fulfill(
            status=200, content_type="application/javascript", body=TAILWIND_STUB if "tailwind" in r.request.url else ""))
        self.page: Page = self.context.new_page()
        self.errors: list[str] = []
        self.page.on("pageerror", lambda e: None if _benign(str(e)) else self.errors.append(f"uncaught: {e}"))
        mock(base, "/__mock/reset?persona=full")

    def open(self, name):
        self.page.goto(f"{self.base}/pages/{name}", wait_until="networkidle")
        self.page.wait_for_timeout(300)

    def calls(self, method, path_part):
        return [c for c in mock(self.base, "/__mock/log")["calls"] if c["method"] == method and path_part in c["url"]]

    def violations(self):
        return mock(self.base, "/__mock/log")["violations"]

    def close(self):
        self.context.close()


def flow_login(browser, base):
    f = Flow(browser, base, signed_in=False)
    f.open("login.html")
    f.page.fill("#email", "asha@example.test")
    f.page.fill("#password", "wrong")
    f.page.click("#submit-btn")
    f.page.wait_for_timeout(600)
    assert "login.html" in f.page.url, f"bad credentials should stay on login, got {f.page.url}"
    assert "Authentication Failed" in f.page.inner_text("body"), "bad credentials should show an error"
    f.page.fill("#password", "admin123")
    f.page.click("#submit-btn")
    f.page.wait_for_url("**/home.html", timeout=8000)
    stored = f.page.evaluate("JSON.parse(localStorage.getItem('recruitops-session'))")
    assert stored and stored.get("token"), "session token not stored"
    assert stored.get("permissions"), "permissions not synced after login"
    assert f.calls("GET", "/permissions/me"), "login did not sync /permissions/me"
    return f


def flow_create_client(browser, base):
    f = Flow(browser, base)
    f.open("client-directory.html")
    f.page.evaluate("openClientDialog(null, () => {})")
    f.page.wait_for_selector("#client-dialog-overlay #client_name")
    f.page.fill("#client-dialog-overlay #client_name", "Northwind Traders")
    f.page.fill("#client-dialog-overlay #placement_fee_pct", "8.33")
    # requestSubmit(): layout-independent (the sweep stubs the Tailwind CDN)
    f.page.locator("#client-dialog-overlay form").evaluate("form => form.requestSubmit()")
    f.page.wait_for_timeout(600)
    posts = f.calls("POST", "/api/v1/clients/")
    assert posts, "Create Client did not POST /clients/"
    assert posts[-1]["body"]["client_name"] == "Northwind Traders"
    return f


def flow_create_requisition(browser, base):
    f = Flow(browser, base)
    f.open("requisition-intake.html")
    f.page.fill("#job-title", "Senior Data Engineer")
    f.page.select_option("#client_id", index=1)
    f.page.select_option("#location_id", index=1)
    f.page.select_option("#priority", "medium")
    f.page.fill("#openings", "2")
    f.page.evaluate("RecruitOpsLive.handleFormSubmit(document.querySelector('#requisition-form') || document.body)")
    f.page.wait_for_timeout(800)
    posts = f.calls("POST", "/api/v1/requisitions/")
    assert posts, "requisition intake did not POST /requisitions/"
    body = posts[-1]["body"]
    assert body["client_id"] and body["location_id"] and body["priority"] == "medium", body
    return f


def flow_approve(browser, base):
    f = Flow(browser, base)
    f.open("approvals-inbox.html")
    button = f.page.locator(".approve-btn").first
    assert button.count(), "no pending approval rendered"
    button.click()
    f.page.wait_for_timeout(800)
    assert f.calls("PATCH", "/decide"), "Approve did not PATCH /approvals/{id}/decide"
    return f


def flow_stage_move(browser, base):
    f = Flow(browser, base)
    f.open("stage-move-dialog.html?application_id=1")
    surface = "[data-overlay-surface='true']"
    selects = f.page.locator(f"{surface} select")
    # target stage + rationale selects: pick the first real option in each
    for i in range(selects.count()):
        sel = selects.nth(i)
        if not sel.is_visible():  # e.g. the withdrawal-reason field, shown only for a withdrawn target (4.11)
            continue
        values = sel.evaluate("s => Array.from(s.options).map(o => o.value).filter(Boolean)")
        if values:
            sel.select_option(values[-1] if "rejected" not in values[-1] else values[0])
    f.page.fill(f"{surface} textarea", "Strong technical round; moving forward to the next stage.")
    f.page.locator(f"{surface} button", has_text="Confirm").first.dispatch_event("click")
    f.page.wait_for_timeout(800)
    moves = f.calls("PATCH", "/stage")
    assert moves, "Confirm Transition did not PATCH /pipeline/applications/{id}/stage"
    assert moves[-1]["body"]["to_stage"], "stage move sent no to_stage"
    return f


def flow_notification_read(browser, base):
    f = Flow(browser, base)
    f.open("notifications-center.html")
    f.page.evaluate("markNotificationSeen(1)")
    f.page.wait_for_timeout(300)
    assert f.calls("PATCH", "/notifications/1/read"), "mark-read did not PATCH /notifications/{id}/read"
    return f


def flow_logout(browser, base):
    f = Flow(browser, base)
    f.open("home.html")
    f.page.locator("[data-logout-link]").first.dispatch_event("click")
    f.page.wait_for_url("**/login.html*", timeout=8000)
    assert f.calls("POST", "/auth/logout"), "logout did not POST /auth/logout"
    stored = f.page.evaluate("localStorage.getItem('recruitops-session')")
    assert not stored, "session survived logout"
    return f


FLOWS = [flow_login, flow_create_client, flow_create_requisition, flow_approve, flow_stage_move,
         flow_notification_read, flow_logout]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:4180")
    opts = ap.parse_args()
    failures = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for flow in FLOWS:
            f = None
            try:
                f = flow(browser, opts.base)
                problems = f.errors + [f"contract {v['kind']}: {v['method']} {v['url']} — {v['detail']}" for v in f.violations()]
                if problems:
                    raise AssertionError("; ".join(problems[:5]))
                print(f"ok   {flow.__name__}")
                for c in mock(opts.base, "/__mock/log")["calls"]:
                    if c["method"] != "GET":
                        print(f"       {c['method']} {c['url']} {json.dumps(c.get('body'))[:160]}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"FAIL {flow.__name__}: {exc}")
            finally:
                if f:
                    f.close()
        browser.close()
    print(f"\n{len(FLOWS) - failures}/{len(FLOWS)} flows passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
