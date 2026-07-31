"""
Emisión y validación de tokens JWT.

Tipos de token, diferenciados por el claim "scope":
  - SCOPE_SESSION            → sesión completa (acceso a endpoints protegidos).
  - SCOPE_PREAUTH_2FA        → login pasó la contraseña, falta el código TOTP.
                               Solo sirve para POST /auth/verify-2fa.
  - SCOPE_PREAUTH_PWCHANGE   → login pasó la contraseña pero está vencida o
                               must_change_password=True. Solo sirve para
                               POST /auth/change-password.
  - SCOPE_PREAUTH_2FA_SETUP  → la política exige 2FA y el usuario no lo tiene
                               configurado. Solo sirve para /auth/2fa/setup/*.
  - SCOPE_2FA_SETUP_PENDING  → token interno del asistente de 2FA: transporta
                               el secret TOTP recién generado entre init y
                               confirm, SIN persistirlo en la base (igual que
                               el diálogo de escritorio: nada se guarda hasta
                               que el usuario demuestra un código válido).
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Iterable, Tuple, Union

import jwt

from api import config

SCOPE_SESSION = "session"
SCOPE_PREAUTH_2FA = "preauth:2fa"
SCOPE_PREAUTH_PWCHANGE = "preauth:pwchange"
SCOPE_PREAUTH_2FA_SETUP = "preauth:2fa_setup"
SCOPE_2FA_SETUP_PENDING = "2fa_setup_pending"


class TokenInvalido(Exception):
    """Token vencido, malformado o con scope incorrecto."""


def _crear(payload_extra: dict, scope: str, minutos: int) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "scope": scope,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=minutos),
        "jti": uuid.uuid4().hex,
    }
    payload.update(payload_extra)
    return jwt.encode(payload, config.API_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def crear_token(usuario_id: int, scope: str, minutos: int) -> str:
    return _crear({"sub": str(usuario_id)}, scope, minutos)


def crear_token_sesion(usuario_id: int) -> str:
    return crear_token(usuario_id, SCOPE_SESSION, config.ACCESS_TOKEN_MINUTES)


def crear_token_preauth_2fa(usuario_id: int) -> str:
    return crear_token(usuario_id, SCOPE_PREAUTH_2FA, config.PREAUTH_TOKEN_MINUTES)


def crear_token_preauth_pwchange(usuario_id: int) -> str:
    return crear_token(usuario_id, SCOPE_PREAUTH_PWCHANGE, config.PREAUTH_TOKEN_MINUTES)


def crear_token_preauth_2fa_setup(usuario_id: int) -> str:
    return crear_token(usuario_id, SCOPE_PREAUTH_2FA_SETUP, config.PREAUTH_TOKEN_MINUTES)


def crear_token_setup_2fa(usuario_id: int, totp_secret: str) -> str:
    """Token del asistente de 2FA: lleva el secret adentro (firmado), para que
    el flujo init→confirm sea stateless y no pise el secret vigente en la base."""
    return _crear(
        {"sub": str(usuario_id), "totp_secret": totp_secret},
        SCOPE_2FA_SETUP_PENDING,
        config.SETUP_2FA_TOKEN_MINUTES,
    )


def _decodificar(token: str) -> dict:
    try:
        return jwt.decode(
            token, config.API_SECRET_KEY, algorithms=[config.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenInvalido("Token vencido") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalido("Token inválido") from exc


def decodificar_token(token: str, scopes_esperados: Union[str, Iterable[str]]) -> int:
    """Valida firma, expiración y scope (uno o varios aceptados).
    Devuelve el id de usuario."""
    if isinstance(scopes_esperados, str):
        scopes_esperados = {scopes_esperados}
    else:
        scopes_esperados = set(scopes_esperados)

    payload = _decodificar(token)
    if payload.get("scope") not in scopes_esperados:
        raise TokenInvalido("Token con alcance incorrecto")
    try:
        return int(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise TokenInvalido("Token sin identificador de usuario") from exc


def decodificar_token_setup_2fa(token: str) -> Tuple[int, str]:
    """Devuelve (usuario_id, totp_secret) del token del asistente de 2FA."""
    payload = _decodificar(token)
    if payload.get("scope") != SCOPE_2FA_SETUP_PENDING:
        raise TokenInvalido("Token con alcance incorrecto")
    try:
        return int(payload["sub"]), str(payload["totp_secret"])
    except (KeyError, ValueError) as exc:
        raise TokenInvalido("Token de configuración incompleto") from exc
