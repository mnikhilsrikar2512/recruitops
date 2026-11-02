"""Phase 6.3: TOTP seeds encrypted at rest."""
from __future__ import annotations

import base64
import os

import pytest

from app.core import secret_box as box
from app.core.config import settings


def _key() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


@pytest.fixture
def ring(monkeypatch):
    def use(value: str) -> None:
        monkeypatch.setattr(settings, "mfa_encryption_keys", value)
    return use


def test_round_trip_and_format(ring):
    ring(f"k1:{_key()}")
    sealed = box.encrypt("JBSWY3DPEHPK3PXP", box.mfa_context(7))
    assert sealed.startswith("enc:v1:k1:") and "JBSWY3DPEHPK3PXP" not in sealed
    assert len(sealed) <= 512
    assert box.decrypt(sealed, box.mfa_context(7)) == "JBSWY3DPEHPK3PXP"
    assert box.encrypt("x", "c") != box.encrypt("x", "c")  # fresh nonce every time


def test_ciphertext_is_bound_to_its_row(ring):
    ring(f"k1:{_key()}")
    sealed = box.encrypt("SEED", box.mfa_context(7))
    with pytest.raises(box.SecretBoxError):
        box.decrypt(sealed, box.mfa_context(8))


def test_tampering_is_detected(ring):
    ring(f"k1:{_key()}")
    sealed = box.encrypt("SEED", "ctx")
    flipped = sealed[:-2] + ("A" if sealed[-2] != "A" else "B") + sealed[-1]
    with pytest.raises(box.SecretBoxError):
        box.decrypt(flipped, "ctx")


def test_legacy_plaintext_still_reads_and_needs_rewrap(ring):
    ring(f"k1:{_key()}")
    assert box.decrypt("JBSWY3DPEHPK3PXP", "ctx") == "JBSWY3DPEHPK3PXP"
    assert box.needs_rewrap("JBSWY3DPEHPK3PXP")


def test_rotation_old_key_still_decrypts_and_is_flagged(ring):
    old, new = _key(), _key()
    ring(f"old:{old}")
    sealed = box.encrypt("SEED", "ctx")
    ring(f"new:{new},old:{old}")
    assert box.decrypt(sealed, "ctx") == "SEED" and box.needs_rewrap(sealed)
    assert not box.needs_rewrap(box.encrypt("SEED", "ctx"))
    ring(f"new:{new}")  # old key dropped too early
    with pytest.raises(box.SecretBoxError, match="no key 'old'"):
        box.decrypt(sealed, "ctx")


@pytest.mark.parametrize("bad", ["nocolon", "k1:not-base64!!", f"k1:{base64.urlsafe_b64encode(b'short').decode()}",
                                 "k1:{0},k1:{0}".format(base64.urlsafe_b64encode(b'x' * 32).decode())])
def test_bad_key_rings_are_refused(bad):
    with pytest.raises(box.SecretBoxError):
        box.parse_key_ring(bad)


def test_development_falls_back_to_a_dev_key(ring, monkeypatch):
    ring("")
    monkeypatch.setattr(settings, "app_env", "development")
    assert box.current_key_id() == "dev"


def test_production_requires_keys():
    from app.core.config import Settings, validate_settings

    missing = Settings(_env_file=None, APP_ENV="production")
    assert any("MFA_ENCRYPTION_KEYS must be set" in e for e in validate_settings(missing))
    broken = Settings(_env_file=None, APP_ENV="production", MFA_ENCRYPTION_KEYS="k1:short")
    assert any("MFA_ENCRYPTION_KEYS is invalid" in e for e in validate_settings(broken))


def test_repository_stores_ciphertext_and_returns_the_seed(ring):
    from app.repositories import mfa as repo

    ring(f"k1:{_key()}")
    stored = {}

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, statement, params=None):
            if "INSERT INTO dbo.user_mfa" in str(statement):
                stored.update(params)
            class Result:
                def mappings(self_inner):
                    return self_inner

                def first(self_inner):
                    return {"user_id": 5, "totp_secret": stored["s"], "enabled_at": None, "last_used_step": None}
            return Result()

    class Engine:
        def begin(self):
            return Conn()

        def connect(self):
            return Conn()

    repo.start_enrollment(Engine(), 5, "JBSWY3DPEHPK3PXP")
    assert stored["s"].startswith("enc:v1:k1:")
    assert repo.find_mfa(Engine(), 5).totp_secret == "JBSWY3DPEHPK3PXP"


def test_rewrap_script_encrypts_plaintext_and_old_keys(ring):
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "encrypt_mfa_secrets", Path(__file__).resolve().parent.parent / "scripts" / "encrypt_mfa_secrets.py")
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)

    old, new = _key(), _key()
    ring(f"old:{old}")
    rows = {1: "PLAINSEED", 2: box.encrypt("SEED2", box.mfa_context(2))}
    ring(f"new:{new},old:{old}")
    rows[3] = box.encrypt("SEED3", box.mfa_context(3))

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, statement, params=None):
            sql = str(statement)
            if sql.startswith("SELECT"):
                class R:
                    def all(self_inner):
                        return list(rows.items())
                return R()
            ok = rows.get(params["u"]) == params["old"]
            if ok:
                rows[params["u"]] = params["new"]

            class U:
                rowcount = 1 if ok else 0
            return U()

    class Engine:
        def connect(self):
            return Conn()

        def begin(self):
            return Conn()

    assert script.rewrap_all(Engine(), dry_run=True)["encrypted"] == 1
    counts = script.rewrap_all(Engine())
    assert counts == {"checked": 3, "encrypted": 1, "rewrapped": 1, "skipped_changed": 0}
    assert all(v.startswith("enc:v1:new:") for v in rows.values())
    assert box.decrypt(rows[1], box.mfa_context(1)) == "PLAINSEED"
    assert box.decrypt(rows[2], box.mfa_context(2)) == "SEED2"
