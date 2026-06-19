# gui/form_recuperar_acceso.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QMessageBox,
    QVBoxLayout, QHBoxLayout, QComboBox, QGroupBox
)
from PySide6.QtCore import Qt
from database import get_session
from models import Usuario, Personal
from utils.permisos import tiene_permiso, es_admin
from datetime import datetime
from gui.login_form import _hash_new


class FormRecuperarAcceso(QWidget):
    def __init__(self, usuario=None):
        super().__init__()

        # ------------------ GUARDA INTERNA ------------------
        if usuario is None:
            QMessageBox.critical(self, "Acceso denegado", "Usuario no autenticado.")
            self.close()
            return

        if not (es_admin(usuario) or tiene_permiso(usuario, "recuperar_acceso")):
            QMessageBox.critical(
                self, "Acceso denegado",
                "No tenés permisos para recuperar acceso de usuarios."
            )
            self.close()
            return
        # -----------------------------------------------------

        self.usuario_actual = usuario

        self.setWindowTitle("Recuperar Acceso de Usuario")
        self.setMinimumSize(650, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # -----------------------------------------------------
        # Caja: Selección de personal
        # -----------------------------------------------------
        box_personal = QGroupBox("Seleccionar empleado (Personal)")
        box_p_layout = QVBoxLayout(box_personal)

        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.lineEdit().setPlaceholderText("Buscar por apellido o nombre...")
        self.combo.setMinimumHeight(32)

        self.cargar_personal()
        self.combo.currentIndexChanged.connect(self.cargar_info_usuario)

        box_p_layout.addWidget(self.combo)
        layout.addWidget(box_personal)

        # -----------------------------------------------------
        # Información del usuario asignado
        # -----------------------------------------------------
        box_info = QGroupBox("Información del usuario")
        info_layout = QVBoxLayout(box_info)

        self.lbl_username = QLabel("Nombre de usuario: —")
        self.lbl_token = QLabel("Token habilitado: —")
        self.lbl_estado = QLabel("")

        info_layout.addWidget(self.lbl_username)
        info_layout.addWidget(self.lbl_token)
        info_layout.addWidget(self.lbl_estado)

        layout.addWidget(box_info)

        # -----------------------------------------------------
        # Reinicio de contraseña
        # -----------------------------------------------------
        box_pass = QGroupBox("Blanquear contraseña")
        pass_layout = QVBoxLayout(box_pass)

        self.txt_nueva_pass = QLineEdit()
        self.txt_nueva_pass.setEchoMode(QLineEdit.Password)
        self.txt_nueva_pass.setPlaceholderText("Ingresar nueva contraseña temporal")
        self.txt_nueva_pass.setMinimumHeight(32)

        self.btn_aplicar_pass = QPushButton("Aplicar nueva contraseña")
        self.btn_aplicar_pass.clicked.connect(self.blanquear_password)

        pass_layout.addWidget(self.txt_nueva_pass)
        pass_layout.addWidget(self.btn_aplicar_pass)

        layout.addWidget(box_pass)

        # -----------------------------------------------------
        # Token (TOTP)
        # -----------------------------------------------------
        box_totp = QGroupBox("Token de seguridad (2FA)")
        totp_layout = QVBoxLayout(box_totp)

        self.btn_toggle_totp = QPushButton("Activar / Desactivar token")
        self.btn_toggle_totp.clicked.connect(self.toggle_totp)

        totp_layout.addWidget(self.btn_toggle_totp)
        layout.addWidget(box_totp)

        layout.addStretch()

    # =======================================================
    # Helpers
    # =======================================================
    def cargar_personal(self):
        self.combo.clear()
        with get_session() as session:
            lista = session.query(Personal).order_by(Personal.apellidos).all()
            for p in lista:
                nombre = f"{p.apellidos}, {p.nombres}"
                self.combo.addItem(nombre, p.id)

    def _get_personal_id(self):
        """Devuelve el ID del Personal seleccionado en el combo."""
        return self.combo.currentData()

    # =======================================================
    # Cargar información
    # =======================================================
    def cargar_info_usuario(self):
        pid = self._get_personal_id()
        if not pid:
            self.lbl_username.setText("Nombre de usuario: —")
            self.lbl_token.setText("Token habilitado: —")
            self.lbl_estado.setText("")
            return

        with get_session() as session:
            user = session.query(Usuario).filter_by(personal_id=pid).first()
            if not user:
                self.lbl_username.setText("Nombre de usuario: —")
                self.lbl_token.setText("Token habilitado: —")
                self.lbl_estado.setText("<span style='color:red;'>Este empleado no tiene usuario asignado.</span>")
                return
            nombre = user.nombre
            totp_enabled = user.totp_enabled

        self.lbl_estado.setText("")
        self.lbl_username.setText(f"Nombre de usuario:  {nombre}")
        self.lbl_token.setText(f"Token habilitado:  {'Sí' if totp_enabled else 'No'}")

    # =======================================================
    # Blanqueo de contraseña
    # =======================================================
    def blanquear_password(self):
        pid = self._get_personal_id()
        if not pid:
            QMessageBox.warning(self, "Sin usuario", "Este empleado no tiene usuario.")
            return

        nueva = self.txt_nueva_pass.text().strip()
        if not nueva:
            QMessageBox.warning(self, "Dato requerido", "Debe ingresar una nueva contraseña temporal.")
            return

        try:
            with get_session() as session:
                user = session.query(Usuario).filter_by(personal_id=pid).first()
                if not user:
                    QMessageBox.warning(self, "Sin usuario", "Este empleado no tiene usuario.")
                    return
                user.password = _hash_new(nueva)
                user.must_change_password = True
                user.last_password_change = datetime.now()
                user.failed_attempts = 0
                user.lock_until = None
                session.commit()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        QMessageBox.information(
            self, "Contraseña actualizada",
            "La nueva contraseña temporal fue aplicada.\n"
            "El usuario deberá cambiarla al ingresar."
        )
        self.txt_nueva_pass.clear()

    # =======================================================
    # Token ON/OFF
    # =======================================================
    def toggle_totp(self):
        pid = self._get_personal_id()
        if not pid:
            QMessageBox.warning(self, "Sin usuario", "Este empleado no tiene usuario.")
            return

        try:
            with get_session() as session:
                user = session.query(Usuario).filter_by(personal_id=pid).first()
                if not user:
                    QMessageBox.warning(self, "Sin usuario", "Este empleado no tiene usuario.")
                    return

                if user.totp_enabled:
                    user.totp_enabled = False
                    session.commit()
                    QMessageBox.information(self, "Token deshabilitado", "El token fue desactivado temporalmente.")
                else:
                    if not user.totp_secret:
                        QMessageBox.warning(
                            self,
                            "No disponible",
                            "Este usuario nunca configuró su token.\nDebe activarlo desde su propio perfil."
                        )
                        return
                    user.totp_enabled = True
                    session.commit()
                    QMessageBox.information(self, "Token habilitado", "El token fue activado nuevamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.cargar_info_usuario()
