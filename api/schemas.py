"""Schemas Pydantic (contratos de entrada/salida) de la API."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Autenticación ---

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
      - "password_change_required"  → usar temp_token en POST /auth/change-password
                                      y volver a iniciar sesión.
      - "2fa_setup_required"        → usar temp_token en /auth/2fa/setup/init y
                                      /auth/2fa/setup/confirm, y volver a iniciar sesión.
      - "2fa_required"              → usar temp_token en POST /auth/verify-2fa.
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


class StatusResponse(BaseModel):
    status: str = "ok"
    detail: Optional[str] = None


# --- Cambio de contraseña ---

class ChangePasswordRequest(BaseModel):
    # La confirmación por doble entrada es responsabilidad del cliente (UI),
    # igual que en ChangePasswordDialog; la API valida las reglas de fondo.
    new_password: str = Field(min_length=1, max_length=255)


# --- Configuración de 2FA ---

class Setup2FAInitResponse(BaseModel):
    """El cliente genera el QR a partir de otpauth_uri (o muestra el secret
    como clave manual, igual que el diálogo de escritorio)."""

    secret: str
    otpauth_uri: str
    setup_token: str
    ya_activo: bool  # True si el usuario ya tenía 2FA (reconfiguración)


class Setup2FAConfirmRequest(BaseModel):
    setup_token: str
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


# --- Clientes ---

class ClienteBase(BaseModel):
    apellidos: Optional[str] = Field(default=None, max_length=100)
    nombres: Optional[str] = Field(default=None, max_length=100)
    tipo_documento: Optional[str] = Field(default=None, max_length=20)
    nro_documento: Optional[str] = Field(default=None, max_length=50)
    fecha_nacimiento: Optional[date] = None
    ocupacion: Optional[str] = Field(default=None, max_length=100)
    domicilio_personal: Optional[str] = Field(default=None, max_length=255)
    localidad: Optional[str] = Field(default=None, max_length=100)
    provincia: Optional[str] = Field(default=None, max_length=100)
    lugar_trabajo_nombre: Optional[str] = Field(default=None, max_length=100)
    domicilio_laboral: Optional[str] = Field(default=None, max_length=255)
    sexo: Optional[str] = Field(default=None, max_length=20)
    estado_civil: Optional[str] = Field(default=None, max_length=50)
    celular_personal: Optional[str] = Field(default=None, max_length=50)
    celular_trabajo: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)
    calificacion: Optional[str] = Field(default=None, max_length=20)
    descripcion: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(ClienteBase):
    """Actualización parcial: solo se aplican los campos enviados."""
    pass


class ClienteOut(ClienteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ClienteListResponse(BaseModel):
    items: List[ClienteOut]
    total: int
    pagina: int
    tamanio: int
