from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QComboBox,
    QMessageBox, QHBoxLayout, QScrollArea, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from database import session
from models import Usuario, Personal
import hashlib

class FormUsuario(QWidget):
    usuario_guardado = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Usuario")
        self.setMinimumSize(800, 400)
        self.usuario_existente = None

        self.showMaximized()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenido = QWidget()
        scroll.setWidget(contenido)

        main_layout = QVBoxLayout(contenido)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        grid = QGridLayout()
        grid.setSpacing(12)

        # Campos
        label_personal = QLabel("Seleccionar Personal *")
        label_personal.setStyleSheet("color: #7b1fa2;")
        self.personal_combo = QComboBox()
        self.personal_combo.setMinimumHeight(30)
        self.personal_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.cargar_personal()
        self.personal_combo.currentIndexChanged.connect(self.cargar_datos_usuario)

        label_usuario = QLabel("Nombre de usuario *")
        label_usuario.setStyleSheet("color: #7b1fa2;")
        self.nombre_input = QLineEdit()
        self.nombre_input.setMinimumHeight(30)

        label_password = QLabel("Contraseña")
        label_password.setStyleSheet("color: #7b1fa2;")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(30)

        grid.addWidget(label_personal, 0, 0)
        grid.addWidget(self.personal_combo, 0, 1)
        grid.addWidget(label_usuario, 1, 0)
        grid.addWidget(self.nombre_input, 1, 1)
        grid.addWidget(label_password, 2, 0)
        grid.addWidget(self.password_input, 2, 1)

        main_layout.addLayout(grid)

        leyenda = QLabel("Los campos marcados con (*) son obligatorios.")
        leyenda.setStyleSheet("color: black; font-size: 12px; margin-top: -8px;")
        main_layout.addWidget(leyenda)

        botones = QHBoxLayout()
        botones.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_guardar = QPushButton("Guardar Usuario")

        self.btn_guardar.setStyleSheet("background-color: #4caf50; color: white;")
        self.btn_cancelar.setStyleSheet("background-color: #ef9a9a; color: black;")

        botones.addWidget(self.btn_cancelar)
        botones.addWidget(self.btn_guardar)

        main_layout.addLayout(botones)

        self.btn_guardar.clicked.connect(self.guardar_usuario)
        self.btn_cancelar.clicked.connect(self.close)

        layout_principal = QVBoxLayout(self)
        layout_principal.addWidget(scroll)

        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
                background-color: #fdfdfd;
            }
            QLabel {
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                padding: 6px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #fff;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)

    def cargar_personal(self):
        self.personal_combo.clear()
        personales = session.query(Personal).all()
        for p in personales:
            texto = f"{p.apellidos or ''}, {p.nombres or ''} (DNI {p.dni or ''})"
            self.personal_combo.addItem(texto.strip(), userData=p.id)

    def cargar_datos_usuario(self):
        personal_id = self.personal_combo.currentData()
        if not personal_id:
            return

        usuario = session.query(Usuario).filter_by(personal_id=personal_id).first()
        self.usuario_existente = usuario

        if usuario:
            self.nombre_input.setText(usuario.nombre)
            self.password_input.setPlaceholderText("Dejar vacío para mantener la contraseña actual")
        else:
            self.nombre_input.clear()
            self.password_input.clear()
            self.password_input.setPlaceholderText("Contraseña para nuevo usuario")

    def guardar_usuario(self):
        nombre = self.nombre_input.text().strip()
        password = self.password_input.text().strip()
        personal_id = self.personal_combo.currentData()

        if not nombre:
            self.mostrar_alerta("nombre de usuario")
            return

        personal = session.query(Personal).get(personal_id)
        email = personal.email

        try:
            if self.usuario_existente:
                self.usuario_existente.nombre = nombre
                if password:
                    self.usuario_existente.password = hashlib.sha256(password.encode()).hexdigest()
                session.commit()
                QMessageBox.information(self, "Éxito", "Usuario actualizado correctamente.")
            else:
                if not password:
                    self.mostrar_alerta("contraseña")
                    return

                if session.query(Usuario).filter_by(email=email).first():
                    QMessageBox.warning(self, "Error", f"Ya existe un usuario con el email {email}.")
                    return

                nuevo = Usuario(
                    nombre=nombre,
                    email=email,
                    password=hashlib.sha256(password.encode()).hexdigest(),
                    rol_id=None,
                    personal_id=personal_id,
                    activo=True
                )
                session.add(nuevo)
                session.commit()
                QMessageBox.information(self, "Éxito", "Usuario creado correctamente.")

            self.usuario_guardado.emit()
            self.close()

        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo guardar el usuario:\n{e}")

    def mostrar_alerta(self, campo):
        QMessageBox.warning(self, "Campo requerido", f"Por favor completá el campo: {campo.capitalize()}")
        if campo == "nombre de usuario":
            self.nombre_input.setFocus()
        elif campo == "contraseña":
            self.password_input.setFocus()
