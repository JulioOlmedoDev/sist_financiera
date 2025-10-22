from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt
from database import session
from gui.change_password_dialog import ChangePasswordDialog
from gui.two_factor_setup import TwoFactorSetupDialog

class FormMiPerfil(QWidget):
    def __init__(self, usuario_actual):
        super().__init__()
        self.usuario = usuario_actual

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        titulo = QLabel("Mi perfil")
        titulo.setObjectName("titulo")
        layout.addWidget(titulo)

        # Datos básicos
        self.lbl_nombre = QLabel(f"Usuario: {self.usuario.nombre}")
        self.lbl_email  = QLabel(f"Email: {self.usuario.email or '—'}")
        rol_txt = getattr(getattr(self.usuario, 'rol', None), 'nombre', '—')
        self.lbl_rol    = QLabel(f"Rol: {rol_txt}")
        layout.addWidget(self.lbl_nombre)
        layout.addWidget(self.lbl_email)
        layout.addWidget(self.lbl_rol)

        # Estado 2FA
        self.lbl_2fa = QLabel()
        layout.addWidget(self.lbl_2fa)

        # Botones de acciones
        h = QHBoxLayout()
        btn_pw = QPushButton("Cambiar contraseña")
        btn_pw.clicked.connect(self._cambiar_contrasena)
        h.addWidget(btn_pw)

        self.btn_2fa = QPushButton()
        self.btn_2fa.clicked.connect(self._toggle_2fa)
        h.addWidget(self.btn_2fa)

        h.addStretch()
        layout.addLayout(h)

        self._refresh()

    def _refresh(self):
        # Texto de estado 2FA y rótulo del botón
        if getattr(self.usuario, "totp_enabled", False):
            self.lbl_2fa.setText("Ingreso con token: ACTIVADO")
            self.btn_2fa.setText("Desactivar ingreso con token")
            self.btn_2fa.setToolTip("Quitar el doble factor en tu cuenta (si el administrador lo permite).")
        else:
            self.lbl_2fa.setText("Ingreso con token: DESACTIVADO")
            self.btn_2fa.setText("Activar ingreso con token")
            self.btn_2fa.setToolTip("Configurar verificación en dos pasos con app de autenticación.")

    def _cambiar_contrasena(self):
        dlg = ChangePasswordDialog(self, self.usuario)
        if dlg.exec():
            QMessageBox.information(self, "Listo", "Contraseña actualizada.")

    def _toggle_2fa(self):
        if getattr(self.usuario, "totp_enabled", False):
            # Desactivar
            ok = QMessageBox.question(self, "Confirmar",
                                      "¿Seguro que querés desactivar el ingreso con token (2FA)?",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ok == QMessageBox.Yes:
                self.usuario.totp_enabled = False
                self.usuario.totp_secret = None
                session.commit()
                self._refresh()
                QMessageBox.information(self, "Actualizado", "Ingreso con token desactivado.")
        else:
            # Activar (abre asistente con QR)
            dlg = TwoFactorSetupDialog(self, self.usuario)
            if dlg.exec():
                # El propio diálogo guarda en DB si se activó
                session.refresh(self.usuario)
                self._refresh()
