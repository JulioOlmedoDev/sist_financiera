"""
Emisión y validación de tokens JWT.

Dos tipos de token, diferenciados por el claim "scope":
  - SCOPE_SESSION      → token de sesión completo (acceso a endpoints protegidos).
  - SCOPE_PREAUTH_2FA  → token intermedio de vida corta, emitido cuando el login
                         pasó la contraseña pero falta el código TOTP. Solo sirve
                         para POST /auth/verify-2fa; nunca da acceso a la API.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from api import config

SCOPE_SESSION = "session"
SCOPE_PREAUTH_2FA = "preauth:2fa"


class TokenInvalido(Exception):
    """Token vencido, malformado o con scope incorrecto."""


def crear_token(usuario_id: int, scope: str, minutos: int) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "scope": scope,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=minutos),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, config.API_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def crear_token_sesion(usuario_id: int) -> str:
    return crear_token(usuario_id, SCOPE_SESSION, config.ACCESS_TOKEN_MINUTES)


def crear_token_preauth_2fa(usuario_id: int) -> str:
    return crear_token(usuario_id, SCOPE_PREAUTH_2FA, config.PREAUTH_TOKEN_MINUTES)


def decodificar_token(token: str, scope_esperado: str) -> int:
    """Valida firma, expiración y scope. Devuelve el id de usuario."""
    try:
        payload = jwt.decode(
            token, config.API_SECRET_KEY, algorithms=[config.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenInvalido("Token vencido") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalido("Token inválido") from exc

    if payload.get("scope") != scope_esperado:
        raise TokenInvalido("Token con alcance incorrecto")

    try:
        return int(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise TokenInvalido("Token sin identificador de usuario") from exc
