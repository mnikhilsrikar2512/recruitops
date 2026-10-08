"""Phase 4.1/4.2 unit tests: type sniffing, malware scanners, storage keys,
signed links."""
from __future__ import annotations

import socket
import struct
import threading

import jwt
import pytest

from app.core.file_storage import LocalStorage, decode_file_token, issue_file_token
from app.core.file_types import FileRejected, check_file
from app.core.malware import EICAR, BuiltinScanner, ClamAVScanner, ScanUnavailable

PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
EXE = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
DOCX = b"PK\x03\x04" + b"\x00" * 26 + b"[Content_Types].xml" + b"word/document.xml"


def test_renamed_exe_is_rejected():
    with pytest.raises(FileRejected) as exc:
        check_file("resume.pdf", EXE, "resume")
    assert exc.value.code == "UNSUPPORTED_FILE_TYPE"


def test_extension_must_match_content():
    with pytest.raises(FileRejected) as exc:
        check_file("resume.docx", PDF, "resume")
    assert exc.value.code == "FILE_TYPE_MISMATCH"


def test_allowlist_per_purpose_and_size_caps():
    assert check_file("cv.pdf", PDF, "resume").name == "pdf"
    assert check_file("cv.docx", DOCX, "resume").name == "docx"
    assert check_file("logo.png", PNG, "logo").name == "png"
    with pytest.raises(FileRejected) as not_a_resume:
        check_file("photo.png", PNG, "resume")
    assert not_a_resume.value.code == "UNSUPPORTED_FILE_TYPE"
    with pytest.raises(FileRejected) as too_big:
        check_file("logo.png", PNG + b"\x00" * (5 * 1024 * 1024), "logo")
    assert too_big.value.code == "FILE_TOO_LARGE"
    with pytest.raises(FileRejected):
        check_file("svg.png", b"<svg onload=alert(1)>", "logo")


def test_builtin_scanner_finds_eicar_only():
    assert BuiltinScanner().scan(PDF).clean is True
    result = BuiltinScanner().scan(PDF + EICAR)
    assert result.clean is False and "Eicar" in result.signature


def _fake_clamd(reply: bytes):
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    received = {}

    def serve():
        conn, _ = server.accept()
        data = b""
        while not data.endswith(struct.pack("!L", 0)):
            chunk = conn.recv(65536)
            if not chunk:
                break
            data += chunk
        received["data"] = data
        conn.sendall(reply)
        conn.close()
        server.close()

    threading.Thread(target=serve, daemon=True).start()
    return server.getsockname()[1], received


def test_clamav_protocol_clean_and_found():
    port, received = _fake_clamd(b"stream: OK\0")
    assert ClamAVScanner("127.0.0.1", port, 5).scan(PDF).clean is True
    assert received["data"].startswith(b"zINSTREAM\0")
    port, _ = _fake_clamd(b"stream: Win.Test.EICAR_HDB-1 FOUND\0")
    result = ClamAVScanner("127.0.0.1", port, 5).scan(EICAR)
    assert result.clean is False and result.signature == "Win.Test.EICAR_HDB-1"


def test_clamav_unreachable_fails_closed():
    with pytest.raises(ScanUnavailable):
        ClamAVScanner("127.0.0.1", 1, 1).scan(PDF)


def test_local_storage_refuses_path_escape(tmp_path):
    storage = LocalStorage(str(tmp_path))
    storage.put("tenant_1/candidates/2/a.pdf", PDF, "application/pdf")
    assert storage.get("tenant_1/candidates/2/a.pdf") == PDF
    with pytest.raises(ValueError):
        storage.put("../escape.pdf", PDF, "application/pdf")


def test_signed_link_roundtrip_tamper_and_expiry():
    token = issue_file_token("tenant_1/candidates/2/a.pdf", "cv.pdf", "application/pdf", 60)
    assert decode_file_token(token)["k"] == "tenant_1/candidates/2/a.pdf"
    with pytest.raises(jwt.InvalidTokenError):
        decode_file_token(token[:-2] + ("AA" if token[-2:] != "AA" else "BB"))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_file_token(issue_file_token("tenant_1/x.pdf", "x.pdf", "application/pdf", -5))
    with pytest.raises(jwt.InvalidTokenError):
        decode_file_token(issue_file_token("quarantine/tenant_1/x.pdf", "x.pdf", "application/pdf", 60))


def test_access_token_decoder_rejects_file_links():
    from app.core.tokens import decode_access_token

    token = issue_file_token("tenant_1/x.pdf", "x.pdf", "application/pdf", 60)
    with pytest.raises(Exception):
        decode_access_token(token)
