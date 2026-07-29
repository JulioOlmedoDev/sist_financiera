"""Dependencias compartidas de FastAPI (autenticación por Bearer token)."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api import tokens
from api.services import auth_service
from api.services.auth_service import UsuarioActual

_esquema_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credenciales: HTTPAuthorizationCredentials = Depends(_esquema_bearer),
) -> UsuarioActual:
    """Valida el token de sesión y devuelve los datos del usuario.

    Rechaza tokens de scope preauth (los intermedios de 2FA no dan acceso).
    """
    if credenciales is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        usuario_id = tokens.decodificar_token(
            credenciales.credentials, tokens.SCOPE_SESSION
        )
    except tokens.TokenInvalido as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    usuario = auth_service.obtener_usuario_actual(usuario_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inexistente o inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario
