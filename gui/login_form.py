from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,QVBoxLayout, QMessageBox, QHBoxLayout, 
    QSpacerItem, QSizePolicy, QDialog, QFormLayout, QInputDialog
)
from PySide6.QtGui import QPixmap, QFont, QIntValidator
from PySide6.QtCore import Qt
from database import get_session
from models import Usuario
from sqlalchemy.orm import joinedload
import os
from datetime import datetime, timedelta
import pyotp
from gui.two_factor_setup import TwoFactorSetupDialog
from models import get_setting
from utils.security import hash_password, verify_password

PASSWORD_MAX_AGE_DAYS = 60
LOCK_THRESHOLD = 5
LOCK_MINUTES = 15


class ChangePasswordDialog(QDialog):
    def __init__(self, parent, usuario: Usuario):
        super().__init__(parent)
        self.setWindowTitle("Cambiar contraseña")
        self._usuario_id = usuario.id
        self._usuario_nombre = usuario.nombre

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
        if self._usuario_nombre.lower() in pwd1.lower():
            QMessageBox.warning(self, "Contraseña insegura", "No utilices el nombre de usuario dentro de la contraseña."); return

        with get_session() as session:
            u = session.get(Usuario, self._usuario_id)
            u.password = hash_password(pwd1)
            u.last_password_change = datetime.utcnow()
            u.must_change_password = False
            u.failed_attempts = 0
            u.lock_until = None
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
        # --- Branding CREDANZA (reversible) ---
        self.setModal(True)
        self.setMinimumWidth(420)

        # Validación y UX
        self.code.setValidator(QIntValidator(0, 999999, self))  # solo 0–999999
        self.code.setMaxLength(6)                               # asegura 6 dígitos
        btn_ok.setDefault(True)                                 # Enter = Verificar

        # IDs para estilos
        btn_ok.setObjectName("brandPrimary")
        btn_cancel.setObjectName("brandGhost")

        # Estilos del modal, inputs y botones (paleta violeta)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border-radius: 10px;
            }
            QLabel {
                font-size: 15px;
                color: #333333;
            }
            QLineEdit {
                padding: 10px;
                font-size: 18px;
                letter-spacing: 3px;
                border: 1px solid #d7c6ef;
                border-radius: 8px;
                background: #faf7ff;
            }
            QLineEdit:focus {
                border: 1px solid #9c27b0;
                background: #f7f2ff;
            }
            QPushButton {
                min-width: 110px;
                padding: 8px 14px;
                border-radius: 8px;
                font-weight: 700;
            }
            QPushButton:hover { opacity: .96; }
            QPushButton:pressed { transform: translateY(1px); }

            /* Colores corporativos */
            QPushButton#brandPrimary {
                background-color: #9c27b0; color: #ffffff;
            }
            QPushButton#brandGhost {
                background-color: #efe6ff; color: #4a148c;
                border: 1px solid #d9c6ef;
            }
        """)

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

        # 1. Cargar usuario con relaciones eager
        with get_session() as session:
            usuario = (
                session.query(Usuario)
                .options(
                    joinedload(Usuario.permisos),
                    joinedload(Usuario.rol),
                    joinedload(Usuario.personal),
                )
                .filter_by(nombre=nombre_usuario)
                .first()
            )

        if (not usuario) or (not usuario.activo):
            QMessageBox.critical(self, "Error", "Usuario o contraseña incorrectos.")
            return

        now = datetime.utcnow()
        if usuario.lock_until and usuario.lock_until > now:
            minutos = int((usuario.lock_until - now).total_seconds() // 60) + 1
            QMessageBox.warning(self, "Cuenta bloqueada", f"Intentá nuevamente en {minutos} min.")
            return

        ok, legacy = verify_password(password, usuario.password)
        if not ok:
            # 2. Registrar intento fallido
            with get_session() as session:
                u = session.get(Usuario, usuario.id)
                u.failed_attempts = (u.failed_attempts or 0) + 1
                if u.failed_attempts >= LOCK_THRESHOLD:
                    u.failed_attempts = 0
                    u.lock_until = now + timedelta(minutes=LOCK_MINUTES)
                    session.commit()
                    QMessageBox.warning(self, "Cuenta bloqueada", f"Demasiados intentos. Bloqueada por {LOCK_MINUTES} min.")
                else:
                    session.commit()
                    QMessageBox.critical(self, "Error", "Usuario o contraseña incorrectos.")
            return

        # 3. Resetear contadores y migrar hash legacy si aplica
        with get_session() as session:
            u = session.get(Usuario, usuario.id)
            u.failed_attempts = 0
            u.lock_until = None
            if legacy:
                u.password = hash_password(password)
                usuario.password = u.password
                if not u.last_password_change:
                    u.last_password_change = now
                    usuario.last_password_change = now
            session.commit()

        # 4. Cambio de contraseña forzado si corresponde
        expired = (not usuario.last_password_change) or ((now - usuario.last_password_change).days >= PASSWORD_MAX_AGE_DAYS)
        if usuario.must_change_password or expired:
            dlg = ChangePasswordDialog(self, usuario)
            if dlg.exec() != QDialog.Accepted:
                QMessageBox.information(self, "Acción requerida", "Debés cambiar tu contraseña para continuar.")
                return

        # 5. Registrar acceso
        with get_session() as session:
            u = session.get(Usuario, usuario.id)
            u.previous_login_at = usuario.last_login_at
            u.last_login_at = now
            session.commit()
        usuario.previous_login_at = usuario.last_login_at
        usuario.last_login_at = now

        # 6. Política 2FA
        with get_session() as session:
            require_global = (get_setting(session, "require_2fa_global", "0") == "1")
        require_user = bool(getattr(usuario, "require_2fa", False))
        is_enabled   = bool(getattr(usuario, "totp_enabled", False) and getattr(usuario, "totp_secret", None))
        need_token   = require_global or require_user or is_enabled

        if need_token:
            if not getattr(usuario, "totp_enabled", False) or not getattr(usuario, "totp_secret", None):
                QMessageBox.information(
                    self, "Token requerido",
                    "Tu cuenta requiere un token de 6 dígitos (2FA). Vamos a configurarlo ahora."
                )
                dlg_setup = TwoFactorSetupDialog(self, usuario)
                if dlg_setup.exec() != QDialog.Accepted:
                    QMessageBox.warning(self, "Acceso cancelado", "No se completó la configuración del token.")
                    return

            td = TokenDialog(self)
            if td.exec() != QDialog.Accepted:
                QMessageBox.information(self, "Acceso cancelado", "No se ingresó el token.")
                return
            code = td.get_code()
            if not code.isdigit() or len(code) != 6:
                QMessageBox.warning(self, "Código inválido", "Ingresá un código de 6 dígitos.")
                return

            totp = pyotp.TOTP(usuario.totp_secret, digits=6, interval=30)
            if not totp.verify(code, valid_window=1):
                QMessageBox.critical(self, "Token incorrecto", "El código ingresado no es válido.")
                return

        QMessageBox.information(self, "Éxito", "Inicio de sesión correcto.")
        self.on_login_success(usuario)
        self.close()

    def _enforce_2fa(self, usuario) -> bool:
        """
        Devuelve True si puede continuar el login (2FA ok o no requerido).
        Devuelve False si falla o si el usuario cancela.
        """
        with get_session() as session:
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

