from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLineEdit, QHeaderView
)
from PySide6.QtCore import Qt
from database import session
from models import Garante
from gui.form_garante import FormGarante

class FormGestionGarantes(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Garantes")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Título
        titulo = QLabel("Listado de Garantes")
        titulo.setObjectName("titulo")
        layout.addWidget(titulo)

        # Buscador
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("Buscar por apellido, nombre o DNI")
        self.buscador.textChanged.connect(self.filtrar_garantes)
        layout.addWidget(self.buscador)

        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(5)
        self.tabla.setHorizontalHeaderLabels(["ID", "Apellidos", "Nombres", "DNI", "Acciones"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setAlternatingRowColors(True)
        layout.addWidget(self.tabla)

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
            }
            QPushButton:hover {
                background-color: #7b1fa2;
            }
        """)

        self.cargar_datos()

    def cargar_datos(self):
        self.todos_los_garantes = session.query(Garante).all()
        self.mostrar_garantes(self.todos_los_garantes)

    def mostrar_garantes(self, lista):
        self.tabla.setRowCount(0)
        for row_index, garante in enumerate(lista):
            self.tabla.insertRow(row_index)
            self.tabla.setItem(row_index, 0, QTableWidgetItem(str(garante.id)))
            self.tabla.setItem(row_index, 1, QTableWidgetItem(garante.apellidos))
            self.tabla.setItem(row_index, 2, QTableWidgetItem(garante.nombres))
            self.tabla.setItem(row_index, 3, QTableWidgetItem(garante.dni))

            btn_editar = QPushButton("Editar")
            btn_editar.clicked.connect(self.generar_callback_editar(garante.id))

            acciones_layout = QHBoxLayout()
            acciones_layout.setContentsMargins(0, 0, 0, 0)
            acciones_layout.setSpacing(5)
            acciones_layout.addWidget(btn_editar)

            acciones_widget = QWidget()
            acciones_widget.setLayout(acciones_layout)
            self.tabla.setCellWidget(row_index, 4, acciones_widget)

    def generar_callback_editar(self, garante_id):
        return lambda checked=False: self.editar_garante(garante_id)

    def editar_garante(self, garante_id):
        self.form = FormGarante(garante_id=garante_id)
        self.form.setWindowModality(Qt.ApplicationModal)
        self.form.showMaximized()
        self.form.destroyed.connect(self.cargar_datos)  # Esto recarga el listado

        self.form.closeEvent = self._refrescar_al_cerrar


    def filtrar_garantes(self):
        texto = self.buscador.text().lower()
        filtrados = [g for g in self.todos_los_garantes if
                     texto in g.apellidos.lower() or
                     texto in g.nombres.lower() or
                     texto in g.dni.lower()]
        self.mostrar_garantes(filtrados)


    def _refrescar_al_cerrar(self, event):
        self.cargar_datos()
        event.accept()
