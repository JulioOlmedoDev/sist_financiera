from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QComboBox,
    QMessageBox, QHBoxLayout, QScrollArea, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from database import session
from models import Usuario, Personal, Rol
import hashlib

class FormUsuario(QWidget):
    usuario_guardado = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Usuario")
        self.setMinimumSize(800, 400)
        self.usuario_existente = None
        self._roles = []  # cache de roles para buscar id/nombre

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

        label_usuario = QLabel("Nombre de usuario *")
        label_usuario.setStyleSheet("color: #7b1fa2;")
        self.nombre_input = QLineEdit()
        self.nombre_input.setMinimumHeight(30)

        label_password = QLabel("Contraseña")
        label_password.setStyleSheet("color: #7b1fa2;")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(30)

        # ---- NUEVO: Rol
        label_rol = QLabel("Rol del usuario")
        label_rol.setStyleSheet("color: #7b1fa2;")
        self.rol_combo = QComboBox()
        self.rol_combo.setMinimumHeight(30)
        self.rol_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Cargas iniciales
        self.cargar_personal()
        self.cargar_roles()

        # Eventos
        self.personal_combo.currentIndexChanged.connect(self.cargar_datos_usuario)

        # Grid
        grid.addWidget(label_personal, 0, 0)
        grid.addWidget(self.personal_combo, 0, 1)

        grid.addWidget(label_usuario, 1, 0)
        grid.addWidget(self.nombre_input, 1, 1)

        grid.addWidget(label_password, 2, 0)
        grid.addWidget(self.password_input, 2, 1)

        grid.addWidget(label_rol, 3, 0)
        grid.addWidget(self.rol_combo, 3, 1)

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

        # Seleccionar primero y disparar precarga
        if self.personal_combo.count() > 0:
            self.personal_combo.setCurrentIndex(0)
            self.cargar_datos_usuario()

    # -------------------- Helpers de carga --------------------

    def cargar_personal(self):
        self.personal_combo.clear()
        personales = session.query(Personal).all()
        for p in personales:
            texto = f"{(p.apellidos or '').strip()}, {(p.nombres or '').strip()} (DNI {p.dni or ''})"
            self.personal_combo.addItem(texto.strip(), userData=p.id)

    def cargar_roles(self):
        """Llena el combo con: (Sin rol), Administrador, Gerente, Coordinador, Administrativo."""
        self._roles = session.query(Rol).all()
        self.rol_combo.clear()
        self.rol_combo.addItem("— Sin rol —", userData=None)
        for r in self._roles:
            self.rol_combo.addItem(r.nombre, userData=r.id)

    def _set_rol_combo_by_id(self, rol_id):
        """Selecciona en combo el rol por id (o 'Sin rol' si None)."""
        if rol_id is None:
            self.rol_combo.setCurrentIndex(0)
            return
        idx = self.rol_combo.findData(rol_id)
        if idx != -1:
            self.rol_combo.setCurrentIndex(idx)
        else:
            # si no está, dejar "Sin rol"
            self.rol_combo.setCurrentIndex(0)

    def _rol_id_from_nombre(self, nombre: str):
        for r in self._roles:
            if (r.nombre or "").strip().lower() == (nombre or "").strip().lower():
                return r.id
        return None

    # -------------------- Precarga según selección --------------------

    def cargar_datos_usuario(self):
        personal_id = self.personal_combo.currentData()
        if not personal_id:
            return

        usuario = session.query(Usuario).filter_by(personal_id=personal_id).first()
        self.usuario_existente = usuario

        if usuario:
            # Usuario existente: precargar datos
            self.nombre_input.setText(usuario.nombre or "")
            self.password_input.clear()
            self.password_input.setPlaceholderText("Dejar vacío para mantener la contraseña actual")
            # Rol actual
            rol_id = getattr(usuario, "rol_id", None)
            self._set_rol_combo_by_id(rol_id)
        else:
            # Usuario nuevo: limpiar y proponer rol según Personal.tipo
            self.nombre_input.clear()
            self.password_input.clear()
            self.password_input.setPlaceholderText("Contraseña para nuevo usuario")
            self._set_rol_combo_by_id(None)

            per = session.query(Personal).get(personal_id)
            tipo = (per.tipo or "").strip().lower() if per else ""

            # Mapeo de tipo de Personal -> Rol sugerido
            sugerido = None
            if tipo == "gerente":
                sugerido = "Gerente"
            elif tipo == "coordinador":
                sugerido = "Coordinador"
            elif tipo == "administrativo":
                sugerido = "Administrativo"
            else:
                sugerido = None  # Vendedor/Cobrador/u otros: sin rol por defecto

            rol_id = self._rol_id_from_nombre(sugerido) if sugerido else None
            self._set_rol_combo_by_id(rol_id)

    # -------------------- Guardar --------------------

    def guardar_usuario(self):
        nombre = (self.nombre_input.text() or "").strip()
        password = (self.password_input.text() or "").strip()
        personal_id = self.personal_combo.currentData()
        rol_id = self.rol_combo.currentData()  # puede ser None

        if not nombre:
            self.mostrar_alerta("nombre de usuario")
            return
        if not personal_id:
            QMessageBox.warning(self, "Campo requerido", "Debés seleccionar un personal.")
            return

        personal = session.query(Personal).get(personal_id)
        email = personal.email if personal else None

        try:
            if self.usuario_existente:
                # Update
                self.usuario_existente.nombre = nombre
                self.usuario_existente.rol_id = rol_id  # asignar / quitar rol
                if password:
                    self.usuario_existente.password = hashlib.sha256(password.encode()).hexdigest()
                session.commit()
                QMessageBox.information(self, "Éxito", "Usuario actualizado correctamente.")
            else:
                # Create
                if not password:
                    self.mostrar_alerta("contraseña")
                    return

                if email and session.query(Usuario).filter_by(email=email).first():
                    QMessageBox.warning(self, "Error", f"Ya existe un usuario con el email {email}.")
                    return

                nuevo = Usuario(
                    nombre=nombre,
                    email=email,
                    password=hashlib.sha256(password.encode()).hexdigest(),
                    rol_id=rol_id,                # puede ser None
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

