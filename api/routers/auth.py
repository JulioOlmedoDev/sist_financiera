"""Endpoints de autenticación."""

from fastapi import APIRouter, Depends, HTTPException, status

from api import config, tokens
from api.deps import (
    get_current_user,
    get_usuario_id_cambio_password,
    get_usuario_id_setup_2fa,
)
from api.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    Setup2FAConfirmRequest,
    Setup2FAInitResponse,
    StatusResponse,
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
                "Intente nuevamente en {} minutos.".format(resultado.minutos_restantes)
            ),
        )

    if resultado.status == auth_service.STATUS_PASSWORD_CHANGE:
        return LoginResponse(
            status=resultado.status,
            detail=(
                "Debe cambiar su contraseña antes de continuar. "
                "Use el temp_token en POST /auth/change-password y vuelva a iniciar sesión."
            ),
            temp_token=tokens.crear_token_preauth_pwchange(resultado.usuario_id),
        )

    if resultado.status == auth_service.STATUS_2FA_SETUP:
        return LoginResponse(
            status=resultado.status,
            detail=(
                "La política de seguridad exige segundo factor (2FA). "
                "Use el temp_token en /auth/2fa/setup/init y /auth/2fa/setup/confirm, "
                "y vuelva a iniciar sesión."
            ),
            temp_token=tokens.crear_token_preauth_2fa_setup(resultado.usuario_id),
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


@router.post("/change-password", response_model=StatusResponse)
def change_password(
    datos: ChangePasswordRequest,
    usuario_id: int = Depends(get_usuario_id_cambio_password),
) -> StatusResponse:
    """Cambia la contraseña del usuario autenticado.

    Mismas reglas que ChangePasswordDialog: mínimo 10 caracteres y no puede
    contener el nombre de usuario. Resetea must_change_password, intentos
    fallidos y bloqueo. Si se llegó con temp_token (clave vencida), el cliente
    debe volver a iniciar sesión con la clave nueva.
    """
    resultado = auth_service.cambiar_password(usuario_id, datos.new_password)

    if resultado == auth_service.PW_CORTA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña insegura: usá al menos 10 caracteres.",
        )
    if resultado == auth_service.PW_CONTIENE_NOMBRE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña insegura: no incluyas el nombre de usuario.",
        )
    if resultado == auth_service.PW_USUARIO_INVALIDO:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inexistente o inactivo.",
        )

    return StatusResponse(
        detail="Contraseña actualizada. Vuelva a iniciar sesión con la clave nueva."
    )


@router.post("/2fa/setup/init", response_model=Setup2FAInitResponse)
def setup_2fa_init(
    usuario_id: int = Depends(get_usuario_id_setup_2fa),
) -> Setup2FAInitResponse:
    """Genera un secret TOTP nuevo y la URI para el QR (issuer CREDANZA).

    NADA se persiste todavía: el secret viaja firmado dentro de setup_token
    y solo se guarda en /confirm tras verificar un código válido — misma
    garantía que el asistente de escritorio.
    """
    resultado = auth_service.iniciar_setup_2fa(usuario_id)
    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inexistente o inactivo.",
        )
    secret, uri, ya_activo = resultado
    return Setup2FAInitResponse(
        secret=secret,
        otpauth_uri=uri,
        setup_token=tokens.crear_token_setup_2fa(usuario_id, secret),
        ya_activo=ya_activo,
    )


@router.post("/2fa/setup/confirm", response_model=StatusResponse)
def setup_2fa_confirm(
    datos: Setup2FAConfirmRequest,
    usuario_id: int = Depends(get_usuario_id_setup_2fa),
) -> StatusResponse:
    """Verifica el código contra el secret pendiente y activa el 2FA."""
    try:
        token_usuario_id, secret = tokens.decodificar_token_setup_2fa(
            datos.setup_token
        )
    except tokens.TokenInvalido as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Configuración vencida. Vuelva a iniciar el asistente de 2FA.",
        ) from exc

    if token_usuario_id != usuario_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token de configuración no corresponde a este usuario.",
        )

    if not auth_service.confirmar_setup_2fa(usuario_id, secret, datos.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El código no es válido. Probá con el código actual.",
        )

    return StatusResponse(detail="2FA activado correctamente.")


@router.post("/2fa/disable", response_model=StatusResponse)
def setup_2fa_disable(
    usuario: UsuarioActual = Depends(get_current_user),
) -> StatusResponse:
    """Desactiva el 2FA del usuario logueado (requiere sesión completa).

    Política de FormMiPerfil: si el token fue impuesto por un administrador
    (totp_set_by_admin), el usuario no puede desactivarlo por sí mismo.
    """
    resultado = auth_service.desactivar_2fa(usuario.id)

    if resultado == auth_service.DIS_BLOQUEADO_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Tu token de seguridad fue activado por política de la empresa "
                "y no podés desactivarlo vos mismo. Solicitá a un usuario "
                "autorizado que lo gestione desde Recuperar acceso."
            ),
        )
    if resultado == auth_service.DIS_NO_ACTIVO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El 2FA no está activo en esta cuenta.",
        )
    if resultado == auth_service.DIS_USUARIO_INVALIDO:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inexistente o inactivo.",
        )

    return StatusResponse(detail="Ingreso con token desactivado.")


@router.get("/me", response_model=UsuarioMeResponse)
def me(usuario: UsuarioActual = Depends(get_current_user)) -> UsuarioMeResponse:
    return UsuarioMeResponse(
        id=usuario.id,
        nombre=usuario.nombre,
        email=usuario.email,
        rol_id=usuario.rol_id,
        activo=usuario.activo,
    )
