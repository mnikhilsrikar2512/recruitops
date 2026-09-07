import pytest
from fastapi import HTTPException

from app.core.storage import _allowed_extension, get_file_path


def test_allowed_extension_accepts_pdf() -> None:
    assert _allowed_extension("resume.pdf") is True


def test_allowed_extension_accepts_docx() -> None:
    assert _allowed_extension("resume.docx") is True


def test_allowed_extension_accepts_jpg() -> None:
    assert _allowed_extension("photo.jpg") is True


def test_allowed_extension_rejects_exe() -> None:
    assert _allowed_extension("malware.exe") is False


def test_allowed_extension_rejects_no_extension() -> None:
    assert _allowed_extension("noext") is False


def test_get_file_path_rejects_path_traversal() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_file_path("../../etc/passwd")

    assert exc_info.value.status_code == 403


def test_get_file_path_rejects_nonexistent_file() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_file_path("nonexistent/file.pdf")

    assert exc_info.value.status_code == 404
