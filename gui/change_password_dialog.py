from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt
from database import session
from models import Usuario
from datetime import datetime
import os

# Hash seguro
from passlib.hash import argon2
PEPPER = os.environ.get("APP_PEPPER", "")

class ChangePasswordDialog(QDialog):
    """
    Diálogo reutilizable para cambiar la contraseña del usuario actual.
    Uso:
        dlg = ChangePasswordDialog(parent, usuario_actual)
        dlg.exec()
    """
    def __init__(self, parent, usuario: Usuario):
        super().__init__(parent)
        self.setWindowTitle("Cambiar contraseña")
        self.usuario = usuario

        form = QFormLayout(self)
        self.new1 = QLineEdit(); self.new1.setEchoMode(QLineEdit.Password)
        self.new2 = QLineEdit(); self.new2.setEchoMode(QLineEdit.Password)
        self.new1.setPlaceholderText("Nueva contraseña (>= 10 caracteres)")
        self.new2.setPlaceholderText("Repetir contraseña")
        form.addRow("Nueva contraseña:", self.new1)
        form.addRow("Repetir contraseña:", self.new2)

        btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_ok = QPushButton("Guardar")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._save)
        btns.addStretch(); btns.addWidget(btn_cancel); btns.addWidget(btn_ok)
        form.addRow(btns)

        self.setMinimumWidth(380)
        self.setModal(True)

    def _save(self):
        pwd1 = (self.new1.text() or "").strip()
        pwd2 = (self.new2.text() or "").strip()

        # Reglas mínimas
        if len(pwd1) < 10:
            QMessageBox.warning(self, "Contraseña insegura", "Usá al menos 10 caracteres.")
            return
        if pwd1 != pwd2:
            QMessageBox.warning(self, "No coincide", "Las contraseñas no coinciden.")
            return
        if self.usuario and self.usuario.nombre and self.usuario.nombre.lower() in pwd1.lower():
            QMessageBox.warning(self, "Contraseña insegura", "No incluyas el nombre de usuario en la contraseña.")
            return

        # Guardar hash
        self.usuario.password = argon2.hash(pwd1 + PEPPER)
        self.usuario.last_password_change = datetime.utcnow()
        self.usuario.must_change_password = False
        self.usuario.failed_attempts = 0
        self.usuario.lock_until = None

        session.commit()
        QMessageBox.information(self, "Listo", "Contraseña actualizada.")
        self.accept()
