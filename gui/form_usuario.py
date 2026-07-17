from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QComboBox,
    QMessageBox, QHBoxLayout, QScrollArea, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from database import get_session
from models import Usuario, Personal, Rol
from utils.formato import formato_documento
from utils.security import hash_password
from utils.estilos import PALETA
from utils.guards import require_perm_or_close

class FormUsuario(QWidget):
    usuario_guardado = Signal()

    def __init__(self, usuario=None):
        from models import Rol  # evitar import circular
        super().__init__()

        self.usuario = usuario
        # --- GUARDIA DE ACCESO ---
        if not require_perm_or_close(
            self, self.usuario, "0330", "0340", "usuario",
            msg="No tenés permisos para acceder a este módulo."
        ):
            return

        self.setWindowTitle("Gestión de Usuario")
        self.setMinimumSize(800, 400)
        self.usuario_existente_id = None  # ID del usuario existente (si aplica)
        self._roles = []  # cache de roles para buscar id/nombre

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
        a = PALETA["acciones"]

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_guardar = QPushButton("Guardar")

        self.btn_guardar.setStyleSheet(f"""
            QPushButton {{ background-color: {a['guardar']}; color: white; }}
            QPushButton:hover {{ background-color: {a['guardar_hover']}; }}
        """)
        self.btn_cancelar.setStyleSheet(f"""
            QPushButton {{ background-color: {a['cancelar']}; color: white; }}
            QPushButton:hover {{ background-color: {a['cancelar_hover']}; }}
        """)

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
        with get_session() as session:
            personales = session.query(Personal).all()
            for p in personales:
                doc = formato_documento(p)
                texto = f"{(p.apellidos or '').strip()}, {(p.nombres or '').strip()}" + (f" ({doc})" if doc else "")
                self.personal_combo.addItem(texto, userData=p.id)

    def cargar_roles(self):
        """Llena el combo con: (Sin rol), Administrador, Gerente, Coordinador, Administrativo."""
        with get_session() as session:
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

        with get_session() as session:
            usuario = session.query(Usuario).filter_by(personal_id=personal_id).first()
            if usuario:
                self.usuario_existente_id = usuario.id
                nombre_existente = usuario.nombre
                rol_id_existente = usuario.rol_id
            else:
                self.usuario_existente_id = None
                per = session.query(Personal).get(personal_id)
                tipo = (per.tipo or "").strip().lower() if per else ""

        if self.usuario_existente_id:
            self.nombre_input.setText(nombre_existente or "")
            self.password_input.clear()
            self.password_input.setPlaceholderText("Dejar vacío para mantener la contraseña actual")
            self._set_rol_combo_by_id(rol_id_existente)
        else:
            self.nombre_input.clear()
            self.password_input.clear()
            self.password_input.setPlaceholderText("Contraseña para nuevo usuario")

            sugerido = None
            if tipo == "gerente":
                sugerido = "Gerente"
            elif tipo == "coordinador":
                sugerido = "Coordinador"
            elif tipo == "administrativo":
                sugerido = "Administrativo"

            rol_id = self._rol_id_from_nombre(sugerido) if sugerido else None
            self._set_rol_combo_by_id(rol_id)

    # -------------------- Guardar --------------------

    def guardar_usuario(self):
        nombre = (self.nombre_input.text() or "").strip()
        password = (self.password_input.text() or "").strip()
        personal_id = self.personal_combo.currentData()
        rol_id = self.rol_combo.currentData()

        if not nombre:
            self.mostrar_alerta("nombre de usuario")
            return
        if not personal_id:
            QMessageBox.warning(self, "Campo requerido", "Debés seleccionar un personal.")
            return

        try:
            with get_session() as session:
                personal = session.query(Personal).get(personal_id)
                email = personal.email if personal else None

                if self.usuario_existente_id:
                    # Update
                    usuario = session.query(Usuario).get(self.usuario_existente_id)
                    usuario.nombre = nombre
                    usuario.rol_id = rol_id
                    if password:
                        usuario.password = hash_password(password)
                    session.commit()
                    QMessageBox.information(self, "Éxito", "Usuario actualizado correctamente.")
                else:
                    # Create
                    if not password:
                        self.mostrar_alerta("contraseña")
                        return

                    if email and session.query(Usuario).filter_by(email=email).first():
                        QMessageBox.warning(self, "Email en uso",
                                            f"Ya existe un usuario registrado con el email {email}.")
                        return

                    nuevo = Usuario(
                        nombre=nombre,
                        email=email,
                        password=hash_password(password),
                        rol_id=rol_id,
                        personal_id=personal_id,
                        activo=True
                    )
                    session.add(nuevo)
                    session.commit()
                    QMessageBox.information(self, "Éxito", "Usuario creado correctamente.")

        except Exception as e:
            print(f"[ERROR guardar_usuario] {e}")
            QMessageBox.critical(self, "Error",
                                 "No se pudo guardar el usuario. Verificá los datos e intentá nuevamente.")
            return

        self.usuario_guardado.emit()
        self.close()

    def mostrar_alerta(self, campo):
        QMessageBox.warning(self, "Campo requerido", f"Por favor completá el campo: {campo.capitalize()}")
        if campo == "nombre de usuario":
            self.nombre_input.setFocus()
        elif campo == "contraseña":
            self.password_input.setFocus()
