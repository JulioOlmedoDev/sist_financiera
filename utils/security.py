import hashlib
import os

from passlib.hash import argon2

PEPPER = os.environ.get("APP_PEPPER", "")


def hash_password(pwd: str) -> str:
    return argon2.hash(pwd + PEPPER)


def verify_password(pwd: str, stored: str) -> tuple[bool, bool]:
    """
    Verifica la contraseña contra el hash almacenado.
    Devuelve (es_valida, es_legacy).
    Soporta Argon2id (hashes actuales) y SHA-256 hex plano (hashes legacy).
    """
    try:
        if stored.startswith("$argon2"):
            return (argon2.verify(pwd + PEPPER, stored), False)
    except Exception:
        pass
    legacy = hashlib.sha256(pwd.encode()).hexdigest()
    return (legacy == stored, True if legacy == stored else False)
