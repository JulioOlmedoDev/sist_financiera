# gui/dialog_crear_admin.py
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLabel, QLineEdit,
    QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt
from database import session
from models import Usuario, Permiso
import hashlib

class DialogCrearAdmin(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crear Superusuario")
        self.setModal(True)
        self.resize(350, 200)

        layout = QFormLayout(self)

        # Campo de usuario
        self.usuario_input = QLineEdit()
        self.usuario_input.setPlaceholderText("Nombre de usuario")
        layout.addRow(QLabel("Usuario:"), self.usuario_input)

        # Campo de email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("email@dominio.com")
        layout.addRow(QLabel("Email:"), self.email_input)

        # Campo de contraseña
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Contraseña")
        layout.addRow(QLabel("Contraseña:"), self.password_input)

        # Campo de confirmación
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText("Confirmar contraseña")
        layout.addRow(QLabel("Confirmar contraseña:"), self.confirm_input)

        # Botones Aceptar/Cancelar
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        user  = self.usuario_input.text().strip()
        email = self.email_input.text().strip()
        pwd   = self.password_input.text()
        conf  = self.confirm_input.text()

        # Validaciones básicas
        if not user or not email or not pwd:
            QMessageBox.warning(self, "Error", "Todos los campos son obligatorios.")
            return

        # Validar formato básico de email
        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "Error", "Ingresá un email válido.")
            return

        if pwd != conf:
            QMessageBox.warning(self, "Error", "Las contraseñas no coinciden.")
            return

        # Verificar que no exista ya ese usuario o ese email
        if session.query(Usuario).filter_by(nombre=user).first():
            QMessageBox.warning(self, "Error", f"El usuario «{user}» ya existe.")
            return
        if session.query(Usuario).filter_by(email=email).first():
            QMessageBox.warning(self, "Error", f"El email «{email}» ya está en uso.")
            return

        # Hashear la contraseña
        pwd_hash = hashlib.sha256(pwd.encode("utf-8")).hexdigest()

        # Crear superusuario y asignar todos los permisos existentes
        try:
            admin = Usuario(
                nombre=user,
                email=email,
                password=pwd_hash,
                rol_id=None,
                personal_id=None
            )

            # Asignar todos los permisos de la tabla permisos
            todos = session.query(Permiso).all()
            admin.permisos.extend(todos)

            session.add(admin)
            session.commit()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error al crear admin", str(e))
            return

        QMessageBox.information(self, "Éxito", "Superusuario creado correctamente.")
        self.accept()
