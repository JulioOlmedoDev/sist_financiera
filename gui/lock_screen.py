from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton, QMessageBox
from PySide6.QtCore import Qt
from database import session
from models import Usuario
import os, hashlib
from passlib.hash import argon2

PEPPER = os.environ.get("APP_PEPPER", "")

def _verify_password(plain: str, stored: str) -> bool:
    """
    Verifica la contraseña: primero Argon2id, si no, SHA-256 legacy.
    """
    if stored.startswith("$argon2"):
        try:
            return argon2.verify(plain + PEPPER, stored)
        except Exception:
            return False
    # Legacy SHA-256 (hex)
    return hashlib.sha256(plain.encode()).hexdigest() == stored

class LockScreenDialog(QDialog):
    """
    Diálogo modal de bloqueo: pide la contraseña del usuario actual para desbloquear.
    """
    def __init__(self, parent, usuario: Usuario):
        super().__init__(parent)
        self.setWindowTitle("Pantalla bloqueada")
        self.setModal(True)
        self.usuario = usuario

        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        title = QLabel("🔒 Pantalla bloqueada")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:18px; font-weight:bold; color:#6a1b9a;")
        lay.addWidget(title)

        info = QLabel(f"Usuario: <b>{usuario.nombre}</b>")
        info.setAlignment(Qt.AlignCenter)
        lay.addWidget(info)

        lbl = QLabel("Ingresá tu contraseña para continuar:")
        lay.addWidget(lbl)

        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.Password)
        self.input.setPlaceholderText("Contraseña")
        self.input.returnPressed.connect(self._try_unlock)
        lay.addWidget(self.input)

        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_cancel = QPushButton("Cerrar sesión")
        self.btn_unlock = QPushButton("Desbloquear")
        self.btn_unlock.setDefault(True)

        self.btn_cancel.clicked.connect(self._quit_app)
        self.btn_unlock.clicked.connect(self._try_unlock)

        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_unlock)
        lay.addLayout(btns)

        self.setMinimumWidth(420)
        self.setStyleSheet("""
            QDialog { background: #fafafa; }
            QLineEdit { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
            QPushButton { background:#9c27b0; color:white; border:none; border-radius:4px; padding:8px 12px; }
            QPushButton:hover { background:#7b1fa2; }
        """)

        # Evitá cerrar con ESC o con la X (opcional):
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)

    def _try_unlock(self):
        plain = (self.input.text() or "").strip()
        if not plain:
            QMessageBox.warning(self, "Campos vacíos", "Ingresá tu contraseña."); return

        # Refrescá el usuario por las dudas
        user = session.query(Usuario).get(self.usuario.id)
        if not user or not user.activo:
            QMessageBox.critical(self, "Sesión inválida", "Tu usuario no está disponible. Cerrando sesión.")
            self._quit_app()
            return

        if _verify_password(plain, user.password):
            self.accept()
        else:
            QMessageBox.critical(self, "Contraseña incorrecta", "La contraseña no es válida.")
            self.input.clear()
            self.input.setFocus()

    def _quit_app(self):
        # Cerrar aplicación completa (podemos cambiar a “volver a login” más adelante)
        from PySide6.QtWidgets import QApplication
        QApplication.quit()
