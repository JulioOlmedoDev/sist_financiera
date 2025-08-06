from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QHeaderView, QLineEdit
)
from PySide6.QtCore import Qt
from database import session
from models import Personal
from gui.form_personal import FormPersonal


class FormGestionPersonal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Personal")

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Título
        titulo = QLabel("Listado de Personal")
        titulo.setObjectName("titulo")
        layout.addWidget(titulo)

        # Buscador
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("Buscar por apellido, nombre o DNI")
        self.buscador.textChanged.connect(self.filtrar)
        layout.addWidget(self.buscador)

        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels(["ID", "Apellidos", "Nombres", "DNI", "Tipo", "Acciones"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        layout.addWidget(self.tabla)

        # Estilo visual
        self.setStyleSheet("""
            QLabel#titulo {
                font-size: 22px;
                font-weight: bold;
                color: #6a1b9a;
            }
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #dddddd;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #9c27b0;
                color: white;
                padding: 4px 12px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7b1fa2;
            }
        """)

        self.cargar_datos()

    def cargar_datos(self):
        self.todos = session.query(Personal).all()
        self.mostrar(self.todos)

    def mostrar(self, lista):
        self.tabla.setRowCount(0)
        for row_index, persona in enumerate(lista):
            self.tabla.insertRow(row_index)
            self.tabla.setItem(row_index, 0, QTableWidgetItem(str(persona.id)))
            self.tabla.setItem(row_index, 1, QTableWidgetItem(persona.apellidos or ""))
            self.tabla.setItem(row_index, 2, QTableWidgetItem(persona.nombres or ""))
            self.tabla.setItem(row_index, 3, QTableWidgetItem(persona.dni or ""))
            self.tabla.setItem(row_index, 4, QTableWidgetItem(persona.tipo or ""))

            # Botón editar
            btn_editar = QPushButton("Editar")
            btn_editar.clicked.connect(self.generar_callback_editar(persona.id))

            acciones_layout = QHBoxLayout()
            acciones_layout.setContentsMargins(0, 0, 0, 0)
            acciones_layout.setSpacing(5)
            acciones_layout.addWidget(btn_editar)

            acciones_widget = QWidget()
            acciones_widget.setLayout(acciones_layout)
            self.tabla.setCellWidget(row_index, 5, acciones_widget)

    def editar(self, personal_id):
        self.form = FormPersonal(personal_id=personal_id)
        self.form.setWindowModality(Qt.ApplicationModal)
        self.form.setAttribute(Qt.WA_DeleteOnClose)
        self.form.showMaximized()
        self.form.closeEvent = self._refrescar_al_cerrar

    def generar_callback_editar(self, personal_id):
        return lambda checked=False: self.editar(personal_id)

    def filtrar(self):
        texto = self.buscador.text().lower()
        filtrados = [p for p in self.todos if
                     texto in (p.apellidos or "").lower() or
                     texto in (p.nombres or "").lower() or
                     texto in (p.dni or "")]
        self.mostrar(filtrados)

    def _refrescar_al_cerrar(self, event):
        self.cargar_datos()
        event.accept()
