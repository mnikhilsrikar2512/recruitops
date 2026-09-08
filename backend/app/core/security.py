from __future__ import annotations

import hashlib
import hmac
import secrets
from hashlib import pbkdf2_hmac

DEFAULT_PBKDF2_ITERATIONS = 600_000


def random_secret(size: int = 16) -> str:
    return secrets.token_hex(size)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_sha256_password_hash(password: str) -> str:
    return f"sha256:{sha256_hex(password)}"


def create_pbkdf2_password_hash(password: str, iterations: int = DEFAULT_PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_hex(32)
    derived = pbkdf2_hmac("sha512", password.encode("utf-8"), salt.encode("utf-8"), iterations, 64).hex()
    return f"pbkdf2${iterations}${salt}${derived}"


def create_bcrypt_password_hash(password: str) -> str:
    try:
        import bcrypt
    except ModuleNotFoundError:
        raise RuntimeError("bcrypt is required for bcrypt password hashing. Install with: pip install bcrypt")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def generate_session_token() -> str:
    return secrets.token_hex(48)


def hash_session_token(token: str) -> str:
    return sha256_hex(token)


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False

    if stored_hash.startswith("$2"):
        try:
            import bcrypt
        except ModuleNotFoundError:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        except ValueError:
            return False

    if stored_hash.startswith("sha256:"):
        return hmac.compare_digest(sha256_hex(password), stored_hash[7:])

    if stored_hash.startswith("pbkdf2$"):
        _, iterations_text, salt, expected_hash = stored_hash.split("$", 3)
        try:
            iterations = int(iterations_text)
        except ValueError:
            return False
        if iterations <= 0 or not salt or not expected_hash:
            return False
        derived_hash = pbkdf2_hmac("sha512", password.encode("utf-8"), salt.encode("utf-8"), iterations, 64).hex()
        return hmac.compare_digest(derived_hash, expected_hash)

    return False
