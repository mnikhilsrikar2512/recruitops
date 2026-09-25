#!/usr/bin/env python3
"""Strip prototype fixture content from live HTML pages, leaving templates."""
from __future__ import annotations

import re
from pathlib import Path

PAGES = Path(__file__).resolve().parent.parent / "pages"
SKIP_NAMES = {
    "login.html",
    "landing.html",
    "forgot-password.html",
    "reset-password.html",
    "password-setup.html",
    "not-found.html",
    "access-denied.html",
    "use-cases.html",
}

PROTO_TEXT = re.compile(
    r"Alice Smith|Bob Johnson|Carol Williams|David Brown|Elena Rostova|"
    r"John Doe|Sarah (?:Chen|Lee|Jenkins)|Alex (?:Mercer|Morgan|Kim|M\.)|"
    r"Jamie Garcia|Sam Lee|Robin Davis|David Jones|Kunal Patel|Omar Farooq|"
    r"Emma Croft|Michael Wu|Pallavi Deshmukh|Gautam Iyer|"
    r"Acme Corp|TechCorp(?: Inc\.)?|Innovate LLC|Design Studio|Analytics Pro|"
    r"Google|Stripe|Amazon|Netflix|Meta|Apple|"
    r"alice\.smith@example\.com|b\.johnson@example\.com|cwilliams99@mail\.com|"
    r"REQ-\d+|CAND-\d+|Req #\d+",
    re.I,
)

SHOWING_RE = re.compile(r"Showing\s+\d+\s+to\s+\d+\s+of\s+\d+\s+entries", re.I)
KPI_RE = re.compile(
    r"(<(?:p|div)[^>]*class=\"[^\"]*font-headline-(?:md|lg)[^\"]*\"[^>]*>)\s*\d+\s*(</(?:p|div)>)",
    re.I,
)


def find_matching_close(html: str, open_pos: int, tag: str = "div") -> int:
    open_pat = re.compile(rf"<{tag}\b", re.I)
    close_pat = re.compile(rf"</{tag}>", re.I)
    start = html.find(">", open_pos)
    if start < 0:
        return -1
    pos = start + 1
    depth = 1
    while pos < len(html) and depth:
        nxt_open = open_pat.search(html, pos)
        nxt_close = close_pat.search(html, pos)
        if not nxt_close:
            return -1
        if nxt_open and nxt_open.start() < nxt_close.start():
            depth += 1
            pos = nxt_open.end()
        else:
            depth -= 1
            pos = nxt_close.end()
            if depth == 0:
                return nxt_close.start()
    return -1


def extract_trs(inner: str) -> list[str]:
    rows = []
    pos = 0
    lower = inner.lower()
    while True:
        start = lower.find("<tr", pos)
        if start < 0:
            break
        end = find_matching_close(inner, start, "tr")
        if end < 0:
            break
        close_end = inner.find(">", end)
        rows.append(inner[start : close_end + 1] if close_end > end else inner[start:end])
        # include </tr>
        close = re.search(r"</tr>", inner[end:], re.I)
        if not close:
            break
        abs_end = end + close.end()
        rows[-1] = inner[start:abs_end]
        pos = abs_end
    return rows


def sanitize_row(row: str) -> str:
    row = PROTO_TEXT.sub("—", row)
    row = re.sub(r"[\w.+-]+@[\w.-]+\.\w+", "—", row)
    if "data-row-template" not in row:
        row = re.sub(r"<tr\b", '<tr hidden data-row-template="true"', row, count=1, flags=re.I)
    return row


def strip_tbodies(html: str) -> str:
    out = []
    pos = 0
    lower = html.lower()
    while True:
        start = lower.find("<tbody", pos)
        if start < 0:
            out.append(html[pos:])
            break
        tag_end = html.find(">", start)
        if tag_end < 0:
            out.append(html[pos:])
            break
        close = find_matching_close(html, start, "tbody")
        if close < 0:
            out.append(html[pos:])
            break
        close_end_match = re.search(r"</tbody>", html[close:], re.I)
        abs_close_end = close + (close_end_match.end() if close_end_match else 7)
        open_tag = html[start : tag_end + 1]
        inner = html[tag_end + 1 : close]
        rows = extract_trs(inner)
        if rows:
            template = sanitize_row(rows[0])
            replacement = f"{open_tag}{template}</tbody>"
        else:
            replacement = html[start:abs_close_end]
        out.append(html[pos:start])
        out.append(replacement)
        pos = abs_close_end
        lower = html.lower()
    return "".join(out)


def replace_underlays(html: str) -> str:
    mount = re.search(r'data-overlay-mount-parent="([^"]+)"', html)
    title = mount.group(1) if mount else "Workspace"
    marker = 'class="overlay-underlay"'
    idx = html.find(marker)
    if idx < 0:
        return html
    open_div = html.rfind("<div", 0, idx)
    backdrop = html.find('class="overlay-backdrop"', idx)
    if open_div < 0 or backdrop < 0:
        return html
    backdrop_div = html.rfind("<div", idx, backdrop)
    replacement = (
        '<div class="overlay-underlay">'
        '<div class="pointer-events-none p-8 opacity-40">'
        f'<h2 class="font-headline-lg text-headline-lg text-on-surface">{title}</h2>'
        '<p class="mt-2 font-body-sm text-text-muted">Live records load from the parent workspace.</p>'
        "</div>"
    )
    return html[:open_div] + replacement + html[backdrop_div:]


def remove_elements_with_class(html: str, token: str) -> str:
    pos = 0
    pieces = []
    lower = html.lower()
    token_l = token.lower()
    while True:
        hit = lower.find(token_l, pos)
        if hit < 0:
            pieces.append(html[pos:])
            break
        open_div = html.rfind("<div", pos, hit)
        if open_div < 0 or open_div < pos:
            pieces.append(html[pos:hit + len(token)])
            pos = hit + len(token)
            continue
        class_attr_start = html.rfind("class=", open_div, hit)
        if class_attr_start < open_div:
            pieces.append(html[pos:hit + len(token)])
            pos = hit + len(token)
            continue
        close = find_matching_close(html, open_div, "div")
        if close < 0:
            pieces.append(html[pos:])
            break
        close_match = re.search(r"</div>", html[close:], re.I)
        abs_end = close + (close_match.end() if close_match else 6)
        pieces.append(html[pos:open_div])
        pos = abs_end
        lower = html.lower()
    return "".join(pieces)


def empty_pipeline_counts(html: str) -> str:
    return re.sub(
        r'(<h3 class="font-headline-sm[^"]*">[^<]+</h3>\s*<span class="bg-surface border border-border text-text-muted px-1\.5 py-0\.5 rounded text-\[11px\] font-medium">)\d+(</span>)',
        r"\g<1>0\2",
        html,
    )


def process(html: str, name: str) -> str:
    html = re.sub(r'\sdata-demo-validate="true"', "", html)
    html = replace_underlays(html)
    html = strip_tbodies(html)
    if "cursor-grab" in html:
        html = remove_elements_with_class(html, "cursor-grab")
        html = empty_pipeline_counts(html)
    html = SHOWING_RE.sub("—", html)
    html = KPI_RE.sub(r"\1—\2", html)
    if name == "meetings.html":
        html = re.sub(
            r'(<div class="grid grid-cols-7 min-h-\[400px\]">)(.*?)(</div>\s*</div>\s*<!-- Upcoming)',
            r'\1<div class="col-span-7 p-8 text-center text-text-muted font-body-sm" data-meetings-calendar>Meetings load from the live API.</div>\3',
            html,
            count=1,
            flags=re.S,
        )
        html = re.sub(
            r'(<div class="bg-surface border border-border rounded-lg shadow-sm">)\s*<!-- Meeting 1 -->(.*?)(</div>\s*</div>\s*</div>\s*</section>)',
            r'\1<div data-meetings-list class="divide-y divide-border"><div class="p-6 text-center text-text-muted">Loading meetings…</div></div>\3',
            html,
            count=1,
            flags=re.S,
        )
        html = html.replace("5 MEETINGS", "LIVE")
    if name == "follow-ups.html":
        html = html.replace(
            '<tbody class="font-data-tabular text-data-tabular text-on-surface divide-y divide-border">',
            '<tbody data-follow-up-list class="font-data-tabular text-data-tabular text-on-surface divide-y divide-border">',
            1,
        )
    if "priority alerts" in html:
        html = re.sub(r"\d+ priority alerts", "0 priority alerts", html)
    return html


def main() -> None:
    changed = 0
    for path in sorted(PAGES.glob("*.html")):
        if path.name in SKIP_NAMES or path.name.startswith("product-tour"):
            text = path.read_text()
            new = re.sub(r'\sdata-demo-validate="true"', "", text)
            if new != text:
                path.write_text(new)
                changed += 1
            continue
        original = path.read_text()
        updated = process(original, path.name)
        if updated != original:
            path.write_text(updated)
            changed += 1
            print(f"stripped {path.name}")
    print(f"updated {changed} pages")


if __name__ == "__main__":
    main()
