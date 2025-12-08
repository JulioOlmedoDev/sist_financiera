from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout,
    QMessageBox, QComboBox
)
from PySide6.QtCore import Qt
from database import session
from models import Usuario, Personal
from utils.permisos import tiene_permiso, es_admin
import hashlib
import secrets


class RecoveryDialog(QDialog):
    """
    Pantalla para recuperar acceso de cualquier usuario:
    - Reset password
    - Habilitar/Deshabilitar 2FA
    - Regenerar secret TOTP
    """

    def __init__(self, parent=None, usuario=None):
        super().__init__(parent)

        self.usuario_logueado = usuario  # quien ejecuta la acción
        self.usuario_objetivo = None     # a quién se le va a recuperar acceso

        # --- GUARDIA ---
        if self.usuario_logueado is None:
            QMessageBox.critical(self, "Acceso denegado", "No hay usuario autenticado.")
            self.close()
            return

        if not (es_admin(self.usuario_logueado) or tiene_permiso(self.usuario_logueado, "recuperar_acceso")):
            QMessageBox.critical(self, "Acceso denegado",
                                 "No tenés permisos para recuperar accesos.")
            self.close()
            return
        # ----------------

        self.setWindowTitle("Recuperar Acceso de Usuario")
        self.setMinimumSize(500, 320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        titulo = QLabel("Recuperar Acceso")
        titulo.setStyleSheet("font-size: 22px; font-weight: bold; color: #6a1b9a;")
        layout.addWidget(titulo)

        # --- Selección de usuario ---
        self.combo = QComboBox()
        self.combo.setMinimumHeight(32)
        layout.addWidget(QLabel("Seleccionar usuario"))
        layout.addWidget(self.combo)

        self._cargar_usuarios()
        self.combo.currentIndexChanged.connect(self._actualizar_usuario)

        # --- Campo nueva contraseña ---
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setPlaceholderText("Nueva contraseña (opcional)")
        self.pass_input.setMinimumHeight(32)

        layout.addWidget(QLabel("Resetear contraseña"))
        layout.addWidget(self.pass_input)

        # --- Botones principales ---
        botonera = QHBoxLayout()

        self.btn_reset_pass = QPushButton("Cambiar contraseña")
        self.btn_reset_pass.setStyleSheet("background-color: #7b1fa2; color: white;")
        self.btn_reset_pass.clicked.connect(self._reset_password)

        self.btn_toggle_2fa = QPushButton("")
        self.btn_toggle_2fa.setStyleSheet("background-color: #5c6bc0; color: white;")
        self.btn_toggle_2fa.clicked.connect(self._toggle_2fa)

        self.btn_regenerar_secret = QPushButton("Regenerar token secreto")
        self.btn_regenerar_secret.setStyleSheet("background-color: #9c27b0; color: white;")
        self.btn_regenerar_secret.clicked.connect(self._regenerar_secret)

        botonera.addWidget(self.btn_reset_pass)
        botonera.addWidget(self.btn_toggle_2fa)
        botonera.addWidget(self.btn_regenerar_secret)

        layout.addLayout(botonera)

        self._actualizar_usuario()

        self.setStyleSheet("""
            QWidget { font-size: 14px; }
            QLineEdit, QComboBox {
                border: 1px solid #bbb; border-radius: 5px; padding: 6px;
            }
            QPushButton {
                padding: 6px 14px; border-radius: 6px; font-weight: bold;
            }
        """)

    # ------------------------------------------------------------
    #   CARGA DE USUARIOS
    # ------------------------------------------------------------
    def _cargar_usuarios(self):
        self.combo.clear()
        usuarios = session.query(Usuario).order_by(Usuario.nombre).all()

        for u in usuarios:
            texto = f"{u.nombre} — {u.email}"
            self.combo.addItem(texto, userData=u.id)

    def _actualizar_usuario(self):
        uid = self.combo.currentData()
        if uid:
            self.usuario_objetivo = session.query(Usuario).get(uid)
        else:
            self.usuario_objetivo = None

        if not self.usuario_objetivo:
            return

        # Cambiar texto del botón activar/desactivar 2FA
        if self.usuario_objetivo.totp_enabled:
            self.btn_toggle_2fa.setText("Desactivar 2FA")
        else:
            self.btn_toggle_2fa.setText("Activar 2FA")

    # ------------------------------------------------------------
    #   ACCIONES
    # ------------------------------------------------------------
    def _reset_password(self):
        if not self.usuario_objetivo:
            return

        new_pass = (self.pass_input.text() or "").strip()
        if not new_pass:
            QMessageBox.warning(self, "Campo vacío",
                                "Ingresá una nueva contraseña.")
            return

        self.usuario_objetivo.password = hashlib.sha256(new_pass.encode()).hexdigest()
        self.usuario_objetivo.must_change_password = False
        self.usuario_objetivo.failed_attempts = 0
        self.usuario_objetivo.lock_until = None

        session.commit()
        QMessageBox.information(self, "Éxito", "Contraseña actualizada correctamente.")
        self.pass_input.clear()

    def _toggle_2fa(self):
        if not self.usuario_objetivo:
            return

        self.usuario_objetivo.totp_enabled = not self.usuario_objetivo.totp_enabled
        session.commit()

        estado = "activado" if self.usuario_objetivo.totp_enabled else "desactivado"
        QMessageBox.information(self, "2FA", f"Autenticación en dos pasos {estado}.")
        self._actualizar_usuario()

    def _regenerar_secret(self):
        if not self.usuario_objetivo:
            return

        nuevo_secret = secrets.token_hex(16)
        self.usuario_objetivo.totp_secret = nuevo_secret
        session.commit()

        QMessageBox.information(
            self,
            "Nuevo token",
            f"Se generó un nuevo código secreto.\n\nColocalo en Google Authenticator."
        )
