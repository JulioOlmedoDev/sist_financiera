from PySide6.QtWidgets import (
    QWidget, QLabel, QComboBox, QVBoxLayout, QHBoxLayout,
    QCheckBox, QPushButton, QMessageBox, QScrollArea,
    QSizePolicy, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt
from collections import defaultdict
from database import session
from models import Usuario, Permiso


class FormPermisos(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Permisos")
        self.setMinimumSize(800, 500)
        self.setStyleSheet(self.estilo_general())
        self.showMaximized()

        self.permisos_checkboxes = defaultdict(list)
        self.checkbox_todos = QCheckBox("Seleccionar todos los permisos")
        self.checkbox_todos.stateChanged.connect(self.toggle_todos)

        # Scroll principal
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenido = QWidget()
        scroll.setWidget(contenido)
        main_layout = QVBoxLayout(contenido)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # Fila superior: Usuario y combo
        usuario_layout = QHBoxLayout()
        label_usuario = QLabel("Seleccionar Usuario *")
        label_usuario.setStyleSheet("color: #7b1fa2; font-weight: bold;")
        self.usuario_combo = QComboBox()
        self.usuario_combo.setMinimumHeight(30)
        self.usuario_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.usuario_combo.currentIndexChanged.connect(self.cargar_permisos_usuario)

        usuario_layout.addWidget(label_usuario)
        usuario_layout.addSpacing(20)
        usuario_layout.addWidget(self.usuario_combo)

        main_layout.addLayout(usuario_layout)
        main_layout.addWidget(self.checkbox_todos)

        # Área de permisos (grid por grupo)
        self.permisos_container = QVBoxLayout()
        main_layout.addLayout(self.permisos_container)

        # Botones
        botones_layout = QHBoxLayout()
        botones_layout.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_guardar = QPushButton("Guardar Permisos")

        botones_layout.addWidget(self.btn_cancelar)
        botones_layout.addWidget(self.btn_guardar)

        main_layout.addLayout(botones_layout)

        # Conexiones
        self.btn_guardar.clicked.connect(self.guardar_permisos)
        self.btn_cancelar.clicked.connect(self.close)

        # Layout final
        layout_principal = QVBoxLayout(self)
        layout_principal.addWidget(scroll)

        # Carga inicial
        self.cargar_usuarios()
        self.cargar_permisos()
        self.cargar_permisos_usuario()

    def estilo_general(self):
        return """
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
            QCheckBox {
                padding: 4px;
            }
            QPushButton {
                background-color: #9c27b0;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7b1fa2;
            }
        """

    def cargar_usuarios(self):
        self.usuario_combo.clear()
        usuarios = session.query(Usuario).all()
        for u in usuarios:
            self.usuario_combo.addItem(u.nombre, userData=u.id)

    def cargar_permisos(self):
        # Limpia anteriores
        while self.permisos_container.count():
            item = self.permisos_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        self.permisos_checkboxes.clear()

        permisos = session.query(Permiso).all()
        permisos_por_grupo = defaultdict(list)

        for permiso in permisos:
            if " - " in permiso.nombre:
                grupo, nombre = permiso.nombre.split(" - ", 1)
            else:
                grupo, nombre = "Otros", permiso.nombre
            permisos_por_grupo[grupo].append((permiso, nombre))

        for grupo, items in permisos_por_grupo.items():
            group_box = QGroupBox(grupo)
            layout = QGridLayout()
            for i, (permiso, nombre) in enumerate(items):
                checkbox = QCheckBox(nombre)
                row, col = divmod(i, 2)
                layout.addWidget(checkbox, row, col)
                self.permisos_checkboxes[grupo].append((permiso, checkbox))
            group_box.setLayout(layout)
            self.permisos_container.addWidget(group_box)

    def cargar_permisos_usuario(self):
        usuario_id = self.usuario_combo.currentData()
        usuario = session.query(Usuario).get(usuario_id)
        if not usuario:
            return

        usuario_permisos_ids = {p.id for p in usuario.permisos}

        for grupo, lista in self.permisos_checkboxes.items():
            for permiso, checkbox in lista:
                checkbox.setChecked(permiso.id in usuario_permisos_ids)

    def toggle_todos(self, state):
        check = state == Qt.Checked
        for grupo, lista in self.permisos_checkboxes.items():
            for _, checkbox in lista:
                checkbox.setChecked(check)

    def guardar_permisos(self):
        usuario_id = self.usuario_combo.currentData()
        usuario = session.query(Usuario).get(usuario_id)
        if not usuario:
            QMessageBox.warning(self, "Error", "Usuario no válido.")
            return

        usuario.permisos.clear()
        for grupo, lista in self.permisos_checkboxes.items():
            for permiso, checkbox in lista:
                if checkbox.isChecked():
                    usuario.permisos.append(permiso)

        session.commit()
        QMessageBox.information(self, "Éxito", "Permisos actualizados correctamente.")
        self.close()
