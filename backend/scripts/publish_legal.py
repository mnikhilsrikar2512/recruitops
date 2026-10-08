"""Publish a new version of a legal document (Phase 5.1, platform ops).

The new version becomes the one in force; the previous one is kept as
"superseded". Every user (Terms, Privacy) or company (DPA) is asked to
accept the new version at their next sign-in.

    cd backend
    .venv/bin/python scripts/publish_legal.py --type tos --title "Terms of Service" --file ~/legal/terms-v2.md --by "you@company"
    .venv/bin/python scripts/publish_legal.py --list

Counsel's final text must be published without --placeholder; production
refuses to start while any document in force is still a placeholder.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", choices=["tos", "privacy", "dpa"])
    ap.add_argument("--title")
    ap.add_argument("--file", type=Path, help="Markdown file with the full text")
    ap.add_argument("--by", default="ops", help="who published it (kept on the record)")
    ap.add_argument("--placeholder", action="store_true", help="mark as placeholder (not legal text)")
    ap.add_argument("--list", action="store_true", help="show the documents in force and exit")
    opts = ap.parse_args()

    from app.db.session import create_db_engine
    from app.repositories.legal import list_active_documents, publish_document

    engine = create_db_engine()
    if opts.list:
        for doc in list_active_documents(engine):
            flag = "  PLACEHOLDER" if doc["is_placeholder"] else ""
            print(f"{doc['doc_type']:8} v{doc['version']}  {doc['title']}  (since {doc['effective_at']:%Y-%m-%d}){flag}")
        return
    if not (opts.type and opts.title and opts.file):
        ap.error("--type, --title and --file are required to publish")
    body = opts.file.expanduser().read_text(encoding="utf-8").strip()
    if len(body) < 200 and not opts.placeholder:
        raise SystemExit("refusing: the text is shorter than 200 characters; is this the right file?")
    new_id = publish_document(engine, doc_type=opts.type, title=opts.title, body=body,
                              is_placeholder=opts.placeholder, published_by=opts.by)
    print(f"✓ published {opts.type} as document {new_id}; users will be asked to accept it at next sign-in")


if __name__ == "__main__":
    main()
