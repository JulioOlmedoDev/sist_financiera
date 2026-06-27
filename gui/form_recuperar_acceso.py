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
from utils.security import hash_password


class FormRecuperarAcceso(QWidget):
    def __init__(self, usuario=None):
        super().__init__()

        # ------------------ GUARDA INTERNA ------------------
        if usuario is None:
            QMessageBox.critical(self, "Acceso denegado", "Usuario no autenticado.")
            self.close()
            return

        if not (es_admin(usuario) or tiene_permiso(usuario, "0350 Recuperar acceso (blanqueo contraseña)")):
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

        btns_totp = QHBoxLayout()
        self.btn_imponer_totp    = QPushButton("Imponer token")
        self.btn_desactivar_totp = QPushButton("Desactivar token")
        self.btn_imponer_totp.clicked.connect(self.imponer_totp)
        self.btn_desactivar_totp.clicked.connect(self.desactivar_totp)
        btns_totp.addWidget(self.btn_imponer_totp)
        btns_totp.addWidget(self.btn_desactivar_totp)

        totp_layout.addLayout(btns_totp)
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
            self.lbl_token.setText("Token: —")
            self.lbl_estado.setText("")
            return

        with get_session() as session:
            user = session.query(Usuario).filter_by(personal_id=pid).first()
            if not user:
                self.lbl_username.setText("Nombre de usuario: —")
                self.lbl_token.setText("Token: —")
                self.lbl_estado.setText(
                    "<span style='color:red;'>Este empleado no tiene usuario asignado.</span>"
                )
                return
            nombre        = user.nombre
            totp_enabled  = user.totp_enabled
            set_by_admin  = user.totp_set_by_admin
            require_2fa   = user.require_2fa
            tiene_secreto = bool(user.totp_secret)

        if totp_enabled and set_by_admin:
            estado_token = "Token: ACTIVO (impuesto por admin)"
        elif totp_enabled:
            estado_token = "Token: ACTIVO (activado por el usuario)"
        elif require_2fa:
            estado_token = "Token: INACTIVO — exigido en próximo login"
        elif tiene_secreto:
            estado_token = "Token: INACTIVO (fue configurado antes)"
        else:
            estado_token = "Token: INACTIVO (nunca configurado)"

        self.lbl_estado.setText("")
        self.lbl_username.setText(f"Nombre de usuario:  {nombre}")
        self.lbl_token.setText(estado_token)

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
                user.password = hash_password(nueva)
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
    # Token — Imponer / Desactivar
    # =======================================================
    def imponer_totp(self):
        pid = self._get_personal_id()
        if not pid:
            QMessageBox.warning(self, "Sin usuario", "Este empleado no tiene usuario.")
            return

        with get_session() as session:
            user = session.query(Usuario).filter_by(personal_id=pid).first()
            if not user:
                QMessageBox.warning(self, "Sin usuario", "Este empleado no tiene usuario.")
                return
            nombre_usuario = user.nombre

        ok = QMessageBox.question(
            self, "Confirmar imposición de token",
            f"¿Imponer el token de seguridad a «{nombre_usuario}»?\n\n"
            "Se le exigirá configurar el 2FA en su próximo login si aún no lo tiene.\n"
            "Si ya lo tenía activo, quedará marcado como impuesto por política de la empresa.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if ok != QMessageBox.Yes:
            return

        try:
            with get_session() as session:
                user = session.query(Usuario).filter_by(personal_id=pid).first()
                if not user:
                    QMessageBox.warning(self, "Sin usuario", "Este empleado no tiene usuario.")
                    return
                user.require_2fa       = True
                user.totp_set_by_admin = True
                session.commit()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        QMessageBox.information(
            self, "Token impuesto",
            f"Se exigió el token de seguridad a «{nombre_usuario}».\n"
            "Deberá configurarlo con su app en el próximo login si aún no lo tiene."
        )
        self.cargar_info_usuario()

    def desactivar_totp(self):
        pid = self._get_personal_id()
        if not pid:
            QMessageBox.warning(self, "Sin usuario", "Este empleado no tiene usuario.")
            return

        with get_session() as session:
            user = session.query(Usuario).filter_by(personal_id=pid).first()
            if not user:
                QMessageBox.warning(self, "Sin usuario", "Este empleado no tiene usuario.")
                return
            nombre_usuario = user.nombre

        ok = QMessageBox.question(
            self, "Confirmar desactivación de token",
            f"¿Desactivar el token de seguridad de «{nombre_usuario}»?\n\n"
            "Se eliminarán la configuración del token y la exigencia de 2FA.\n"
            "El secreto del autenticador quedará invalidado (útil ante celular perdido).",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if ok != QMessageBox.Yes:
            return

        try:
            with get_session() as session:
                user = session.query(Usuario).filter_by(personal_id=pid).first()
                if not user:
                    QMessageBox.warning(self, "Sin usuario", "Este empleado no tiene usuario.")
                    return
                user.totp_enabled      = False
                user.require_2fa       = False
                user.totp_set_by_admin = False
                user.totp_secret       = None
                session.commit()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        QMessageBox.information(
            self, "Token desactivado",
            f"El token de seguridad de «{nombre_usuario}» fue desactivado "
            "y su configuración eliminada."
        )
        self.cargar_info_usuario()
