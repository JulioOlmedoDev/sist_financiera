"""Endpoints de autenticación."""

from fastapi import APIRouter, Depends, HTTPException, status

from api import config, tokens
from api.deps import get_current_user
from api.schemas import (
    LoginRequest,
    LoginResponse,
    TokenResponse,
    UsuarioMeResponse,
    Verify2FARequest,
)
from api.services import auth_service
from api.services.auth_service import UsuarioActual

router = APIRouter(prefix="/auth", tags=["auth"])

MENSAJE_CREDENCIALES = "Usuario o contraseña incorrectos"


@router.post("/login", response_model=LoginResponse, response_model_exclude_none=True)
def login(datos: LoginRequest) -> LoginResponse:
    resultado = auth_service.login(datos.usuario, datos.password)

    if resultado.status == auth_service.STATUS_INVALID:
        # Mensaje genérico: no revelar si falló el usuario o la contraseña
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=MENSAJE_CREDENCIALES
        )

    if resultado.status == auth_service.STATUS_LOCKED:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=(
                "Cuenta bloqueada por intentos fallidos. "
                f"Intente nuevamente en {resultado.minutos_restantes} minutos."
            ),
        )

    if resultado.status == auth_service.STATUS_PASSWORD_CHANGE:
        return LoginResponse(
            status=resultado.status,
            detail="Debe cambiar su contraseña antes de continuar.",
        )

    if resultado.status == auth_service.STATUS_2FA_SETUP:
        return LoginResponse(
            status=resultado.status,
            detail=(
                "La política de seguridad exige segundo factor (2FA), "
                "pero aún no está configurado para este usuario."
            ),
        )

    if resultado.status == auth_service.STATUS_2FA_REQUIRED:
        return LoginResponse(
            status=resultado.status,
            detail="Ingrese el código de 6 dígitos de su aplicación de autenticación.",
            temp_token=tokens.crear_token_preauth_2fa(resultado.usuario_id),
        )

    # STATUS_OK → emitir token de sesión
    return LoginResponse(
        status="ok",
        access_token=tokens.crear_token_sesion(resultado.usuario_id),
        token_type="bearer",
        expires_in_minutes=config.ACCESS_TOKEN_MINUTES,
    )


@router.post("/verify-2fa", response_model=TokenResponse)
def verify_2fa(datos: Verify2FARequest) -> TokenResponse:
    try:
        usuario_id = tokens.decodificar_token(
            datos.temp_token, tokens.SCOPE_PREAUTH_2FA
        )
    except tokens.TokenInvalido as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión de verificación vencida. Vuelva a iniciar sesión.",
        ) from exc

    if not auth_service.verificar_codigo_2fa(usuario_id, datos.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código de verificación incorrecto.",
        )

    return TokenResponse(
        access_token=tokens.crear_token_sesion(usuario_id),
        expires_in_minutes=config.ACCESS_TOKEN_MINUTES,
    )


@router.get("/me", response_model=UsuarioMeResponse)
def me(usuario: UsuarioActual = Depends(get_current_user)) -> UsuarioMeResponse:
    return UsuarioMeResponse(
        id=usuario.id,
        nombre=usuario.nombre,
        email=usuario.email,
        rol_id=usuario.rol_id,
        activo=usuario.activo,
    )
