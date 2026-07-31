"""Dependencias compartidas de FastAPI (autenticación por Bearer token)."""

from typing import Iterable, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api import tokens
from api.services import auth_service
from api.services.auth_service import UsuarioActual

_esquema_bearer = HTTPBearer(auto_error=False)


def _extraer_usuario_id(
    credenciales: "HTTPAuthorizationCredentials",
    scopes: Union[str, Iterable[str]],
) -> int:
    if credenciales is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return tokens.decodificar_token(credenciales.credentials, scopes)
    except tokens.TokenInvalido as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(
    credenciales: HTTPAuthorizationCredentials = Depends(_esquema_bearer),
) -> UsuarioActual:
    """Valida el token de sesión y devuelve los datos del usuario.
    Rechaza todos los tokens preauth (los intermedios no dan acceso)."""
    usuario_id = _extraer_usuario_id(credenciales, tokens.SCOPE_SESSION)
    usuario = auth_service.obtener_usuario_actual(usuario_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inexistente o inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def get_usuario_id_cambio_password(
    credenciales: HTTPAuthorizationCredentials = Depends(_esquema_bearer),
) -> int:
    """Para POST /auth/change-password. Acepta:
      - token de sesión (usuario logueado cambiando su clave desde el perfil), o
      - token preauth:pwchange (emitido por login cuando la clave venció o
        must_change_password=True)."""
    return _extraer_usuario_id(
        credenciales, {tokens.SCOPE_SESSION, tokens.SCOPE_PREAUTH_PWCHANGE}
    )


def get_usuario_id_setup_2fa(
    credenciales: HTTPAuthorizationCredentials = Depends(_esquema_bearer),
) -> int:
    """Para /auth/2fa/setup/*. Acepta:
      - token de sesión (usuario autoactivando 2FA desde su perfil), o
      - token preauth:2fa_setup (emitido por login cuando la política exige
        2FA y el usuario aún no lo configuró)."""
    return _extraer_usuario_id(
        credenciales, {tokens.SCOPE_SESSION, tokens.SCOPE_PREAUTH_2FA_SETUP}
    )
