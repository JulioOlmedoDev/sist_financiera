from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QMessageBox, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt
from database import session
from models import Usuario
import hashlib
import os

class LoginForm(QWidget):
    def __init__(self, on_login_success):
        super().__init__()
        self.setWindowTitle("Iniciar Sesión")
        self.setMinimumSize(500, 400)
        self.on_login_success = on_login_success

        # Logo (ajustá la ruta según tu estructura)
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "..", "static", "logo.jpg")

        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            logo_label.setPixmap(pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignCenter)

        # Campos de entrada
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Nombre de usuario")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Contraseña")
        self.password_input.setEchoMode(QLineEdit.Password)

        # Botón
        self.btn_login = QPushButton("Ingresar")
        self.btn_login.setFixedHeight(40)
        self.btn_login.clicked.connect(self.verificar_credenciales)

        # Layout central
        form_layout = QVBoxLayout()
        form_layout.setSpacing(12)
        form_layout.addWidget(QLabel("Usuario:"))
        form_layout.addWidget(self.user_input)
        form_layout.addWidget(QLabel("Contraseña:"))
        form_layout.addWidget(self.password_input)
        form_layout.addSpacing(10)
        form_layout.addWidget(self.btn_login)

        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(60, 40, 60, 40)
        main_layout.setSpacing(30)

        if not logo_label.pixmap().isNull():
            main_layout.addWidget(logo_label)

        titulo = QLabel("Acceso al Sistema")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setFont(QFont("Segoe UI", 18, QFont.Bold))
        titulo.setStyleSheet("color: #6a1b9a;")
        main_layout.addWidget(titulo)

        main_layout.addLayout(form_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

        # Estilo general
        self.setStyleSheet("""
            QWidget {
                background-color: #fafafa;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #9c27b0;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7b1fa2;
            }
        """)

    def verificar_credenciales(self):
        nombre_usuario = self.user_input.text().strip()
        password = self.password_input.text().strip()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        usuario = session.query(Usuario).filter_by(nombre=nombre_usuario, password=hashed_password).first()

        if usuario:
            QMessageBox.information(self, "Éxito", "Inicio de sesión correcto.")
            self.on_login_success(usuario)
            self.close()
        else:
            QMessageBox.critical(self, "Error", "Usuario o contraseña incorrectos.")
