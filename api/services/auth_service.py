"""
Servicio de autenticación.

Replica EXACTAMENTE la lógica de verificar_credenciales (gui/login_form.py),
en el mismo orden de pasos, incluyendo:
  - error genérico único para usuario inexistente / inactivo / password mala,
  - bloqueo por 5 intentos fallidos durante 15 minutos,
  - migración transparente de hashes legacy SHA-256 → Argon2id,
  - expiración de contraseña a los 60 días / must_change_password,
  - política 2FA: global (SystemSetting) OR por usuario OR TOTP ya configurado.

Fidelidad al flujo original: last_login_at / previous_login_at se actualizan
ANTES de la verificación 2FA (paso 8 antes del 9), igual que la desktop app.

Reusa models.py, database.py y utils/security.py de la raíz del proyecto:
NO duplica lógica de hashing ni de acceso a datos.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import pyotp
from sqlalchemy.orm import joinedload

from database import get_session
from models import Usuario, get_setting
from utils.security import hash_password, verify_password

# Mismas constantes que la desktop app (gui/login_form.py)
PASSWORD_MAX_AGE_DAYS = 60
LOCK_THRESHOLD = 5
LOCK_MINUTES = 15

# Estados posibles del intento de login
STATUS_OK = "ok"
STATUS_INVALID = "invalid"
STATUS_LOCKED = "locked"
STATUS_PASSWORD_CHANGE = "password_change_required"
STATUS_2FA_SETUP = "2fa_setup_required"
STATUS_2FA_REQUIRED = "2fa_required"


@dataclass
class LoginResult:
    status: str
    usuario_id: Optional[int] = None
    minutos_restantes: Optional[int] = None


@dataclass
class UsuarioActual:
    """Datos del usuario autenticado, desacoplados de la sesión SQLAlchemy.

    Se usa un dataclass (y no el objeto Usuario) porque con sesiones por
    operación el objeto quedaría detached al salir del context manager.
    """

    id: int
    nombre: str
    email: str
    rol_id: Optional[int]
    activo: bool


def _require_2fa_global(session) -> bool:
    """Lee la política global de 2FA desde SystemSetting.

    Normaliza valores tipo "1"/"true"/"True" a booleano.
    """
    valor = get_setting(session, "require_2fa_global", "0")
    return str(valor).strip().lower() in ("1", "true", "si", "sí")


def login(nombre_usuario: str, password: str) -> LoginResult:
    ahora = datetime.now()

    with get_session() as session:
        # Paso 1: buscar por NOMBRE (no email), con eager loading
        usuario = (
            session.query(Usuario)
            .options(
                joinedload(Usuario.permisos),
                joinedload(Usuario.rol),
                joinedload(Usuario.personal),
            )
            .filter(Usuario.nombre == nombre_usuario)
            .first()
        )

        # Paso 2: inexistente o inactivo → error genérico (no revelar cuál falló)
        if usuario is None or not usuario.activo:
            return LoginResult(status=STATUS_INVALID)

        # Paso 3: cuenta bloqueada
        if usuario.lock_until and usuario.lock_until > ahora:
            restantes = int((usuario.lock_until - ahora).total_seconds() // 60) + 1
            return LoginResult(status=STATUS_LOCKED, minutos_restantes=restantes)

        # Paso 4: verificar contraseña (Argon2id o legacy SHA-256)
        ok, legacy = verify_password(password, usuario.password)

        # Paso 5: contraseña incorrecta → contar intentos y bloquear si corresponde
        if not ok:
            usuario.failed_attempts = (usuario.failed_attempts or 0) + 1
            if usuario.failed_attempts >= LOCK_THRESHOLD:
                usuario.failed_attempts = 0
                usuario.lock_until = ahora + timedelta(minutes=LOCK_MINUTES)
                session.commit()
                return LoginResult(
                    status=STATUS_LOCKED, minutos_restantes=LOCK_MINUTES
                )
            session.commit()
            return LoginResult(status=STATUS_INVALID)

        # Paso 6: contraseña correcta → resetear contadores y migrar hash legacy
        usuario.failed_attempts = 0
        usuario.lock_until = None
        if legacy:
            usuario.password = hash_password(password)
            if usuario.last_password_change is None:
                usuario.last_password_change = ahora

        # Paso 7: cambio de contraseña obligatorio o vencida (>= 60 días)
        vencida = (
            usuario.last_password_change is not None
            and (ahora - usuario.last_password_change).days >= PASSWORD_MAX_AGE_DAYS
        )
        if usuario.must_change_password or vencida:
            session.commit()  # persistir reset de intentos y migración de hash
            return LoginResult(
                status=STATUS_PASSWORD_CHANGE, usuario_id=usuario.id
            )

        # Paso 8: actualizar marcas de login (antes del 2FA, igual que la desktop app)
        usuario.previous_login_at = usuario.last_login_at
        usuario.last_login_at = ahora

        # Paso 9: política de 2FA
        need_token = (
            _require_2fa_global(session)
            or bool(usuario.require_2fa)
            or (bool(usuario.totp_enabled) and bool(usuario.totp_secret))
        )

        session.commit()

        if need_token:
            # Paso 10: exige 2FA pero no está configurado → setup pendiente
            if not (usuario.totp_enabled and usuario.totp_secret):
                return LoginResult(status=STATUS_2FA_SETUP, usuario_id=usuario.id)
            # Paso 11: exigir código de 6 dígitos (segundo paso vía /auth/verify-2fa)
            return LoginResult(status=STATUS_2FA_REQUIRED, usuario_id=usuario.id)

        # Paso 12: login completo
        return LoginResult(status=STATUS_OK, usuario_id=usuario.id)


def verificar_codigo_2fa(usuario_id: int, code: str) -> bool:
    """Segundo paso del login. Misma verificación que la desktop app:
    pyotp.TOTP(secret, digits=6, interval=30).verify(code, valid_window=1)
    """
    with get_session() as session:
        usuario = session.get(Usuario, usuario_id)
        if (
            usuario is None
            or not usuario.activo
            or not usuario.totp_enabled
            or not usuario.totp_secret
        ):
            return False
        totp = pyotp.TOTP(usuario.totp_secret, digits=6, interval=30)
        return bool(totp.verify(code, valid_window=1))


def obtener_usuario_actual(usuario_id: int) -> Optional[UsuarioActual]:
    """Carga el usuario para endpoints protegidos. Devuelve None si no existe
    o está inactivo (un token válido de un usuario desactivado no debe servir).
    """
    with get_session() as session:
        usuario = session.get(Usuario, usuario_id)
        if usuario is None or not usuario.activo:
            return None
        return UsuarioActual(
            id=usuario.id,
            nombre=usuario.nombre,
            email=usuario.email,
            rol_id=usuario.rol_id,
            activo=usuario.activo,
        )


# ---------------------------------------------------------------------------
# Fase 2 / Sesión 2: cambio de contraseña y configuración de 2FA
# ---------------------------------------------------------------------------

ISSUER_2FA = "CREDANZA"  # mismo issuer que gui/two_factor_setup.py

# Estados de cambio de contraseña
PW_OK = "ok"
PW_CORTA = "corta"
PW_CONTIENE_NOMBRE = "contiene_nombre"
PW_USUARIO_INVALIDO = "usuario_invalido"

# Estados de desactivación de 2FA
DIS_OK = "ok"
DIS_BLOQUEADO_ADMIN = "bloqueado_admin"
DIS_NO_ACTIVO = "no_activo"
DIS_USUARIO_INVALIDO = "usuario_invalido"


def cambiar_password(usuario_id: int, nueva_password: str) -> str:
    """Replica exactamente las reglas y efectos de ChangePasswordDialog._save:
      - mínimo 10 caracteres (tras strip),
      - no puede contener el nombre de usuario (case-insensitive),
      - al guardar: hash Argon2, last_password_change=utcnow(),
        must_change_password=False, failed_attempts=0, lock_until=None.

    Nota de fidelidad: se usa datetime.utcnow() porque es lo que escribe la
    desktop app (aunque el login compara con now() local; desfase de horas,
    irrelevante para el umbral de 60 días — pendiente de unificar).
    """
    pwd = (nueva_password or "").strip()

    if len(pwd) < 10:
        return PW_CORTA

    with get_session() as session:
        usuario = session.get(Usuario, usuario_id)
        if usuario is None or not usuario.activo:
            return PW_USUARIO_INVALIDO

        if usuario.nombre and usuario.nombre.lower() in pwd.lower():
            return PW_CONTIENE_NOMBRE

        usuario.password = hash_password(pwd)
        usuario.last_password_change = datetime.utcnow()
        usuario.must_change_password = False
        usuario.failed_attempts = 0
        usuario.lock_until = None
        session.commit()
        return PW_OK


def iniciar_setup_2fa(usuario_id: int):
    """Genera un secret TOTP nuevo y la URI de aprovisionamiento, igual que
    TwoFactorSetupDialog: pyotp.random_base32(), name="CREDANZA:{email o nombre}",
    issuer_name="CREDANZA". NO persiste nada — el secret viaja en el setup_token
    firmado y solo se guarda en confirmar_setup_2fa tras un código válido.

    Devuelve (secret, otpauth_uri, ya_activo) o None si el usuario no es válido.
    """
    with get_session() as session:
        usuario = session.get(Usuario, usuario_id)
        if usuario is None or not usuario.activo:
            return None

        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret, digits=6, interval=30)
        cuenta = usuario.email or usuario.nombre
        uri = totp.provisioning_uri(
            name="{}:{}".format(ISSUER_2FA, cuenta), issuer_name=ISSUER_2FA
        )
        ya_activo = bool(usuario.totp_enabled)
        return secret, uri, ya_activo


def confirmar_setup_2fa(usuario_id: int, secret: str, code: str) -> bool:
    """Verifica el código contra el secret pendiente (valid_window=1, igual que
    el diálogo) y recién entonces persiste totp_secret + totp_enabled=True.
    Autoservicio: totp_set_by_admin no se modifica."""
    totp = pyotp.TOTP(secret, digits=6, interval=30)
    if not totp.verify(code, valid_window=1):
        return False

    with get_session() as session:
        usuario = session.get(Usuario, usuario_id)
        if usuario is None or not usuario.activo:
            return False
        usuario.totp_secret = secret
        usuario.totp_enabled = True
        session.commit()
        return True


def desactivar_2fa(usuario_id: int) -> str:
    """Replica la política de FormMiPerfil._toggle_2fa:
      - si totp_set_by_admin=True → el usuario NO puede desactivarlo
        (fue impuesto por política de la empresa),
      - si lo activó él mismo → totp_enabled=False, totp_secret=None.
    """
    with get_session() as session:
        usuario = session.get(Usuario, usuario_id)
        if usuario is None or not usuario.activo:
            return DIS_USUARIO_INVALIDO
        if not usuario.totp_enabled:
            return DIS_NO_ACTIVO
        if usuario.totp_set_by_admin:
            return DIS_BLOQUEADO_ADMIN
        usuario.totp_enabled = False
        usuario.totp_secret = None
        session.commit()
        return DIS_OK
