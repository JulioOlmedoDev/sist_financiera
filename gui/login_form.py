from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QMessageBox, QHBoxLayout, QSpacerItem, QSizePolicy, QDialog, QFormLayout, QInputDialog
)
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt
from database import session
from models import Usuario
import hashlib
import os
from datetime import datetime, timedelta
import pyotp
from gui.two_factor_setup import TwoFactorSetupDialog
from models import get_setting


# === Seguridad: Argon2id ===
from passlib.hash import argon2

# (opcional) PEPPER por env var
PEPPER = os.environ.get("APP_PEPPER", "")

PASSWORD_MAX_AGE_DAYS = 60
LOCK_THRESHOLD = 5
LOCK_MINUTES = 15

def _hash_new(pwd: str) -> str:
    return argon2.hash(pwd + PEPPER)

def _verify_any(pwd: str, stored: str) -> tuple[bool, bool]:
    """
    Verifica contra Argon2; si no matchea, prueba contra SHA-256 legacy.
    Devuelve (ok, es_legacy).
    """
    # hash Argon2/bcrypt tienen prefijo $argon2.../$2b$..., los sha256 legacy son hex plain
    try:
        if stored.startswith("$argon2"):
            return (argon2.verify(pwd + PEPPER, stored), False)
    except Exception:
        pass
    # Legacy sha256 (lo que tenías)
    legacy = hashlib.sha256(pwd.encode()).hexdigest()
    return (legacy == stored, True if legacy == stored else False)


class ChangePasswordDialog(QDialog):
    def __init__(self, parent, usuario: Usuario):
        super().__init__(parent)
        self.setWindowTitle("Cambiar contraseña")
        self.usuario = usuario

        form = QFormLayout(self)
        self.new1 = QLineEdit(); self.new1.setEchoMode(QLineEdit.Password)
        self.new2 = QLineEdit(); self.new2.setEchoMode(QLineEdit.Password)
        self.new1.setPlaceholderText("Nueva contraseña")
        self.new2.setPlaceholderText("Repetir contraseña")
        form.addRow("Nueva contraseña:", self.new1)
        form.addRow("Repetir contraseña:", self.new2)

        btns = QHBoxLayout()
        btn_ok = QPushButton("Guardar"); btn_cancel = QPushButton("Cancelar")
        btn_ok.clicked.connect(self._save); btn_cancel.clicked.connect(self.reject)
        btns.addStretch(); btns.addWidget(btn_cancel); btns.addWidget(btn_ok)
        form.addRow(btns)

        self.setMinimumWidth(380)

    def _save(self):
        pwd1 = (self.new1.text() or "").strip()
        pwd2 = (self.new2.text() or "").strip()

        # Reglas mínimas (ajustá a gusto)
        if len(pwd1) < 10:
            QMessageBox.warning(self, "Contraseña insegura", "Usá al menos 10 caracteres."); return
        if pwd1 != pwd2:
            QMessageBox.warning(self, "No coincide", "Las contraseñas no coinciden."); return
        if self.usuario.nombre.lower() in pwd1.lower():
            QMessageBox.warning(self, "Contraseña insegura", "No utilices el nombre de usuario dentro de la contraseña."); return

        # Guardar
        self.usuario.password = _hash_new(pwd1)
        self.usuario.last_password_change = datetime.utcnow()
        self.usuario.must_change_password = False
        self.usuario.failed_attempts = 0
        self.usuario.lock_until = None
        session.commit()
        QMessageBox.information(self, "Listo", "Contraseña actualizada.")
        self.accept()

class TokenDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Código de verificación")
        lay = QFormLayout(self)
        self.code = QLineEdit()
        self.code.setMaxLength(6)
        self.code.setPlaceholderText("Código de 6 dígitos")
        self.code.setEchoMode(QLineEdit.Normal)
        lay.addRow("Token:", self.code)
        btns = QHBoxLayout()
        btn_ok = QPushButton("Verificar")
        btn_cancel = QPushButton("Cancelar")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btns.addStretch(); btns.addWidget(btn_cancel); btns.addWidget(btn_ok)
        lay.addRow(btns)

    def get_code(self) -> str:
        return (self.code.text() or "").strip()


class LoginForm(QWidget):
    def __init__(self, on_login_success):
        super().__init__()
        self.setWindowTitle("Iniciar Sesión")
        self.setMinimumSize(500, 400)
        self.on_login_success = on_login_success

        # Logo
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "..", "static", "logo.jpg")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            logo_label.setPixmap(pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignCenter)

        # Campos
        self.user_input = QLineEdit(); self.user_input.setPlaceholderText("Nombre de usuario")
        self.password_input = QLineEdit(); self.password_input.setPlaceholderText("Contraseña")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.btn_login = QPushButton("Ingresar")
        self.btn_login.setFixedHeight(40)
        self.btn_login.clicked.connect(self.verificar_credenciales)

        form_layout = QVBoxLayout(); form_layout.setSpacing(12)
        form_layout.addWidget(QLabel("Usuario:")); form_layout.addWidget(self.user_input)
        form_layout.addWidget(QLabel("Contraseña:")); form_layout.addWidget(self.password_input)
        form_layout.addSpacing(10); form_layout.addWidget(self.btn_login)

        main_layout = QVBoxLayout(); main_layout.setContentsMargins(60, 40, 60, 40); main_layout.setSpacing(30)
        if not logo_label.pixmap().isNull():
            main_layout.addWidget(logo_label)

        titulo = QLabel("Acceso al Sistema"); titulo.setAlignment(Qt.AlignCenter)
        titulo.setFont(QFont("Segoe UI", 18, QFont.Bold)); titulo.setStyleSheet("color: #6a1b9a;")
        main_layout.addWidget(titulo); main_layout.addLayout(form_layout); main_layout.addStretch()
        self.setLayout(main_layout)

        self.setStyleSheet("""
            QWidget { background-color: #fafafa; font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; }
            QLineEdit { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
            QPushButton { background-color: #9c27b0; color: white; font-weight: bold; border: none; border-radius: 4px; }
            QPushButton:hover { background-color: #7b1fa2; }
        """)

    def verificar_credenciales(self):
        nombre_usuario = (self.user_input.text() or "").strip()
        password = (self.password_input.text() or "").strip()

        usuario = session.query(Usuario).filter_by(nombre=nombre_usuario).first()

        # 🔄 asegurar que no usamos un objeto cacheado
        if usuario:
            try:
                session.refresh(usuario)   # fuerza round-trip a la BD
            except Exception:
                pass

        if (not usuario) or (not usuario.activo):
            QMessageBox.critical(self, "Error", "Usuario o contraseña incorrectos.")
            return

        # ¿Cuenta bloqueada?
        now = datetime.utcnow()
        if usuario.lock_until and usuario.lock_until > now:
            minutos = int((usuario.lock_until - now).total_seconds() // 60) + 1
            QMessageBox.warning(self, "Cuenta bloqueada", f"Intentá nuevamente en {minutos} min."); return

        ok, legacy = _verify_any(password, usuario.password)
        if not ok:
            usuario.failed_attempts = (usuario.failed_attempts or 0) + 1
            if usuario.failed_attempts >= LOCK_THRESHOLD:
                usuario.failed_attempts = 0
                usuario.lock_until = now + timedelta(minutes=LOCK_MINUTES)
                session.commit()
                QMessageBox.warning(self, "Cuenta bloqueada", f"Demasiados intentos. Bloqueada por {LOCK_MINUTES} min.")
            else:
                session.commit()
                QMessageBox.critical(self, "Error", "Usuario o contraseña incorrectos.")
            return

        # Login correcto: resetear contadores (AÚN sin commit)
        usuario.failed_attempts = 0
        usuario.lock_until = None

        # Si venía con sha256 legacy, rehash a Argon2 automáticamente
        if legacy:
            usuario.password = _hash_new(password)
            if not usuario.last_password_change:
                usuario.last_password_change = now

        # --- Segundo factor (si está habilitado) ---
        if getattr(usuario, "totp_enabled", False) and getattr(usuario, "totp_secret", None):
            from PySide6.QtWidgets import QInputDialog, QLineEdit
            import pyotp

            code, ok = QInputDialog.getText(
                self,
                "Código 2FA",
                "Ingresá el código de 6 dígitos:",
                QLineEdit.Normal
            )
            if not ok:
                QMessageBox.information(self, "Acción requerida", "Ingresá el código 2FA para continuar.")
                return

            code = (code or "").strip()
            totp = pyotp.TOTP(usuario.totp_secret, digits=6, interval=30)

            # Permitimos ligera tolerancia por desfasaje de reloj
            if not (code.isdigit() and len(code) == 6 and totp.verify(code, valid_window=1)):
                QMessageBox.critical(self, "Código incorrecto", "El código 2FA no es válido.")
                return

        # ¿Debe cambiar contraseña? (primer login o vencida)
        expired = (not usuario.last_password_change) or ((now - usuario.last_password_change).days >= PASSWORD_MAX_AGE_DAYS)
        if usuario.must_change_password or expired:
            dlg = ChangePasswordDialog(self, usuario)
            if dlg.exec() != QDialog.Accepted:
                # Forzamos el cambio: no ingresa si cancela
                QMessageBox.information(self, "Acción requerida", "Debés cambiar tu contraseña para continuar.")
                return

        # Registrar acceso anterior y el actual (recién ahora que pasó todo)
        usuario.previous_login_at = usuario.last_login_at
        usuario.last_login_at = now
        session.commit()

        # --- Política 2FA: global o por usuario ---
        require_global = (get_setting(session, "require_2fa_global", "0") == "1")
        require_user = bool(getattr(usuario, "require_2fa", False))
        need_token = require_global or require_user

        if need_token:
            # Si es requerido pero no está configurado: guiar a configurar
            if not getattr(usuario, "totp_enabled", False) or not getattr(usuario, "totp_secret", None):
                QMessageBox.information(
                    self, "Token requerido",
                    "Tu cuenta requiere un token de 6 dígitos (2FA). Vamos a configurarlo ahora."
                )
                dlg_setup = TwoFactorSetupDialog(self, usuario)
                if dlg_setup.exec() != QDialog.Accepted:
                    QMessageBox.warning(self, "Acceso cancelado", "No se completó la configuración del token.")
                    return
                # Se guardó totp_secret y totp_enabled=True dentro del diálogo

            # Pedir el token
            td = TokenDialog(self)
            if td.exec() != QDialog.Accepted:
                QMessageBox.information(self, "Acceso cancelado", "No se ingresó el token.")
                return
            code = td.get_code()
            if not code.isdigit() or len(code) != 6:
                QMessageBox.warning(self, "Código inválido", "Ingresá un código de 6 dígitos.")
                return

            totp = pyotp.TOTP(usuario.totp_secret, digits=6, interval=30)
            if not totp.verify(code, valid_window=1):  # tolera leve desfase de reloj
                QMessageBox.critical(self, "Token incorrecto", "El código ingresado no es válido.")
                return

        # 2FA: aplicar política (global o por usuario)
        if not self._enforce_2fa(usuario):
            return

        QMessageBox.information(self, "Éxito", "Inicio de sesión correcto.")
        self.on_login_success(usuario)
        self.close()

    def _enforce_2fa(self, usuario) -> bool:
        """
        Devuelve True si puede continuar el login (2FA ok o no requerido).
        Devuelve False si falla o si el usuario cancela.
        """
        # Lee política global (string "1" o "0")
        require_global = (get_setting(session, "require_2fa_global", "0") == "1")
        # Requerido si es global o este usuario lo exige
        required = bool(getattr(usuario, "require_2fa", False)) or require_global

        # Si no es requerido y el usuario no tiene 2FA activo, continuar sin pedir token
        if not required and not getattr(usuario, "totp_enabled", False):
            return True

        # Si es requerido pero el usuario no tiene 2FA configurado, bloquear
        if required and not getattr(usuario, "totp_enabled", False):
            QMessageBox.warning(
                self, "2FA requerido",
                "Tu cuenta requiere ingreso con token, pero aún no está configurado.\n"
                "Pedile al administrador que lo habilite o configurá tu 2FA."
            )
            return False

        # Está habilitado (o requerido y habilitado): pedir código
        code, ok = QInputDialog.getText(
            self, "Verificación con token",
            "Ingresá el código de 6 dígitos de tu app:",
        )
        if not ok:
            return False

        code = (code or "").strip()
        if not code.isdigit() or len(code) != 6:
            QMessageBox.critical(self, "Código inválido", "El token debe tener 6 dígitos.")
            return False

        try:
            totp = pyotp.TOTP(usuario.totp_secret, digits=6, interval=30)
            if totp.verify(code, valid_window=1):
                return True
        except Exception:
            pass

        QMessageBox.critical(self, "Código incorrecto", "El token no es válido. Probá con el código actual.")
        return False

