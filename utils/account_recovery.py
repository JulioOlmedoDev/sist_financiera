# utils/account_recovery.py
from datetime import datetime
import os, secrets, string

from passlib.hash import argon2
from sqlalchemy.orm import Session

PEPPER = os.environ.get("APP_PEPPER", "")

# Genera una clave temporal fuerte (sin caracteres confusos)
def _generar_password_temporal(longitud: int = 14) -> str:
    letras_may = "ABCDEFGHJKLMNPQRSTUVWXYZ"   # sin I O
    letras_min = "abcdefghijkmnpqrstuvwxyz"   # sin l o
    digitos    = "23456789"                   # sin 0 1
    simbolos   = "@#$%&*+-_"

    # Garantizar variedad
    base = [
        secrets.choice(letras_may),
        secrets.choice(letras_min),
        secrets.choice(digitos),
        secrets.choice(simbolos),
    ]
    resto_pool = letras_may + letras_min + digitos + simbolos
    base += [secrets.choice(resto_pool) for _ in range(max(0, longitud - len(base)))]

    # Mezclar
    secrets.SystemRandom().shuffle(base)
    return "".join(base)

def resetear_password_usuario(session: Session, usuario, desactivar_2fa: bool = False) -> str:
    """
    - Genera una clave temporal fuerte.
    - Reemplaza la contraseña por su hash Argon2id (con PEPPER).
    - Obliga cambio de contraseña en el próximo login.
    - Limpia bloqueos/contador.
    - (opcional) Desactiva 2FA y quita la exigencia de 2FA por usuario.
    Devuelve la clave temporal en texto plano (para entregarla al usuario).
    """
    clave_temp = _generar_password_temporal()

    # Hash Argon2id con pepper
    usuario.password = argon2.hash(clave_temp + PEPPER)
    usuario.must_change_password = True
    usuario.failed_attempts = 0
    usuario.lock_until = None
    # Por claridad, no modificamos last_password_change todavía (se setea al cambiarla)

    if desactivar_2fa:
        # Desactivar ingreso con token y la exigencia por usuario
        # (el admin podrá reactivarlo luego)
        if hasattr(usuario, "totp_enabled"):
            usuario.totp_enabled = False
        if hasattr(usuario, "require_2fa"):
            usuario.require_2fa = False

    session.commit()
    return clave_temp
