from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QScrollArea, QSizePolicy, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt
from database import session
from models import Usuario, Personal
from gui.form_usuario import FormUsuario

class FormListadoUsuarios(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Listado de Usuarios")
        self.setMinimumSize(900, 500)

        self.setStyleSheet("""
            QWidget {
                background-color: #fdfdfd;
                font-size: 14px;
            }
            QLabel {
                font-weight: bold;
                font-size: 18px;
                color: #333;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #ccc;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)

        self.setContentsMargins(20, 20, 20, 20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenido = QWidget()
        scroll.setWidget(contenido)

        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        titulo = QLabel("Listado de Usuarios")
        titulo.setStyleSheet("color: #6a1b9a;")  # violeta
        layout.addWidget(titulo)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(5)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre", "Email", "Personal", "Activo"])
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.itemSelectionChanged.connect(self.actualizar_estado_boton)
        layout.addWidget(self.tabla)

        botones = QHBoxLayout()
        botones.addStretch()

        self.btn_editar = QPushButton("Editar Usuario")
        self.btn_editar.setStyleSheet("background-color: #7b1fa2; color: white;")  # violeta

        self.btn_estado = QPushButton("Activar/Desactivar")
        self.btn_estado.setStyleSheet("background-color: #b0bec5; color: black;")  # gris claro

        self.btn_editar.clicked.connect(self.editar_usuario)
        self.btn_estado.clicked.connect(self.cambiar_estado_usuario)

        botones.addWidget(self.btn_editar)
        botones.addWidget(self.btn_estado)

        layout.addLayout(botones)

        principal = QVBoxLayout(self)
        principal.addWidget(scroll)

        self.cargar_datos()
        self.actualizar_estado_boton()

    def cargar_datos(self):
        self.tabla.setRowCount(0)
        self.usuarios = session.query(Usuario).all()

        for i, u in enumerate(self.usuarios):
            self.tabla.insertRow(i)
            self.tabla.setItem(i, 0, QTableWidgetItem(str(u.id)))
            self.tabla.setItem(i, 1, QTableWidgetItem(u.nombre or ""))
            self.tabla.setItem(i, 2, QTableWidgetItem(u.email or ""))

            personal = session.query(Personal).get(u.personal_id)
            nombre_personal = f"{personal.apellidos}, {personal.nombres}" if personal else ""
            self.tabla.setItem(i, 3, QTableWidgetItem(nombre_personal))

            estado = "Sí" if u.activo else "No"
            self.tabla.setItem(i, 4, QTableWidgetItem(estado))

    def usuario_seleccionado(self):
        fila = self.tabla.currentRow()
        if fila == -1:
            return None
        usuario_id = int(self.tabla.item(fila, 0).text())
        return session.query(Usuario).get(usuario_id)

    def editar_usuario(self):
        usuario = self.usuario_seleccionado()
        if not usuario:
            QMessageBox.warning(self, "Error", "Seleccioná un usuario.")
            return
        self.abrir_form_usuario(usuario.personal_id)

    def cambiar_estado_usuario(self):
        usuario = self.usuario_seleccionado()
        if not usuario:
            QMessageBox.warning(self, "Error", "Seleccioná un usuario.")
            return

        if usuario.activo:
            confirmar = QMessageBox.question(
                self, "Desactivar", "¿Desactivar este usuario?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirmar == QMessageBox.Yes:
                usuario.activo = False
        else:
            confirmar = QMessageBox.question(
                self, "Reactivar", "¿Reactivar este usuario?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirmar == QMessageBox.Yes:
                usuario.activo = True

        session.commit()
        self.cargar_datos()
        self.actualizar_estado_boton()

    def actualizar_estado_boton(self):
        usuario = self.usuario_seleccionado()
        if usuario:
            if usuario.activo:
                self.btn_estado.setText("Desactivar")
            else:
                self.btn_estado.setText("Reactivar")
        else:
            self.btn_estado.setText("Activar/Desactivar")

    def abrir_form_usuario(self, personal_id=None):
        self.form = FormUsuario()
        if personal_id:
            index = self.form.personal_combo.findData(personal_id)
            if index != -1:
                self.form.personal_combo.setCurrentIndex(index)
        self.form.usuario_guardado.connect(self.cargar_datos)
        self.form.showMaximized()
