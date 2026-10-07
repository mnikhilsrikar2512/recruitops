"""Phase 4.2: what a file really is, from its first bytes (not its name).

An `.exe` renamed `.pdf` starts with `MZ`, not `%PDF-`, so it is refused.
The declared extension must also agree with the sniffed type.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

MB = 1024 * 1024


@dataclass(frozen=True)
class FileKind:
    name: str
    content_type: str
    extensions: frozenset[str]


PDF = FileKind("pdf", "application/pdf", frozenset({".pdf"}))
DOC = FileKind("doc", "application/msword", frozenset({".doc"}))
DOCX = FileKind("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", frozenset({".docx"}))
PNG = FileKind("png", "image/png", frozenset({".png"}))
JPEG = FileKind("jpeg", "image/jpeg", frozenset({".jpg", ".jpeg"}))

# purpose -> (allowed kinds, size cap)
PURPOSES: dict[str, tuple[frozenset[FileKind], int]] = {
    "resume": (frozenset({PDF, DOC, DOCX}), 10 * MB),
    "document": (frozenset({PDF, DOC, DOCX, PNG, JPEG}), 10 * MB),
    "logo": (frozenset({PNG, JPEG}), 5 * MB),
}


def sniff(content: bytes) -> FileKind | None:
    head = content[:8]
    if content.startswith(b"%PDF-"):
        return PDF
    if head == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return DOC
    if content.startswith(b"PK\x03\x04") and b"word/" in content and b"[Content_Types].xml" in content:
        return DOCX
    if head == b"\x89PNG\r\n\x1a\n":
        return PNG
    if content.startswith(b"\xff\xd8\xff"):
        return JPEG
    return None


class FileRejected(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def check_file(file_name: str, content: bytes, purpose: str) -> FileKind:
    """Return the sniffed kind, or raise FileRejected (size, type, mismatch)."""
    allowed, cap = PURPOSES[purpose]
    if not content:
        raise FileRejected("EMPTY_FILE", "The file is empty")
    if len(content) > cap:
        raise FileRejected("FILE_TOO_LARGE", f"The file is larger than {cap // MB} MB")
    kind = sniff(content)
    allowed_names = ", ".join(sorted(k.name.upper() for k in allowed))
    if kind is None or kind not in allowed:
        raise FileRejected("UNSUPPORTED_FILE_TYPE", f"Only {allowed_names} files are accepted here")
    extension = PurePath(file_name or "").suffix.lower()
    if extension not in kind.extensions:
        raise FileRejected(
            "FILE_TYPE_MISMATCH",
            f"The file's name says '{extension or 'no extension'}' but its content is {kind.name.upper()}",
        )
    return kind
