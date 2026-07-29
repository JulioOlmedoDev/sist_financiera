"""Schemas Pydantic (contratos de entrada/salida) del módulo de autenticación."""

from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    # El login de CREDANZA es por NOMBRE de usuario, no por email
    # (replica verificar_credenciales de gui/login_form.py).
    usuario: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=255)


class Verify2FARequest(BaseModel):
    temp_token: str
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class LoginResponse(BaseModel):
    """
    status posibles:
      - "ok"                        → login completo, viene access_token.
      - "password_change_required"  → el cliente debe ofrecer cambio de contraseña
                                      antes de continuar (no se emite token).
      - "2fa_setup_required"        → política exige 2FA pero el usuario no lo tiene
                                      configurado (endpoint de setup: fase posterior).
      - "2fa_required"              → falta el segundo paso; usar temp_token en
                                      POST /auth/verify-2fa.
    """

    status: str
    detail: Optional[str] = None
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_in_minutes: Optional[int] = None
    temp_token: Optional[str] = None


class TokenResponse(BaseModel):
    status: str = "ok"
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class UsuarioMeResponse(BaseModel):
    id: int
    nombre: str
    email: str
    rol_id: Optional[int] = None
    activo: bool
