from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QHeaderView, QLineEdit
)
from PySide6.QtCore import Qt
from database import session
from models import Cliente
from gui.form_cliente import FormCliente

class FormGestionClientes(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Clientes")

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Título
        titulo = QLabel("Listado de Clientes")
        titulo.setObjectName("titulo")
        layout.addWidget(titulo)

        # Buscador
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("Buscar por apellido, nombre o DNI")
        self.buscador.textChanged.connect(self.filtrar_clientes)
        layout.addWidget(self.buscador)

        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels(["ID", "Apellidos", "Nombres", "DNI", "Calificación", "Acciones"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setAlternatingRowColors(True)
        layout.addWidget(self.tabla)

        self.cargar_datos()

        # Estilo
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

    def cargar_datos(self):
        self.todos_los_clientes = session.query(Cliente).all()
        self.mostrar_clientes(self.todos_los_clientes)

    def mostrar_clientes(self, lista):
        self.tabla.setRowCount(0)
        for row_index, cliente in enumerate(lista):
            self.tabla.insertRow(row_index)
            self.tabla.setItem(row_index, 0, QTableWidgetItem(str(cliente.id)))
            self.tabla.setItem(row_index, 1, QTableWidgetItem(cliente.apellidos))
            self.tabla.setItem(row_index, 2, QTableWidgetItem(cliente.nombres))
            self.tabla.setItem(row_index, 3, QTableWidgetItem(cliente.dni))
            self.tabla.setItem(row_index, 4, QTableWidgetItem(cliente.calificacion if cliente.calificacion else ""))


            # Botón de acción
            btn_editar = QPushButton("Editar")
            btn_editar.clicked.connect(self.generar_callback_editar(cliente.id))

            acciones_layout = QHBoxLayout()
            acciones_layout.setContentsMargins(0, 0, 0, 0)
            acciones_layout.setSpacing(5)
            acciones_layout.addWidget(btn_editar)

            acciones_widget = QWidget()
            acciones_widget.setLayout(acciones_layout)
            self.tabla.setCellWidget(row_index, 5, acciones_widget)

    def editar_cliente(self, cliente_id):
        self.form = FormCliente(cliente_id=cliente_id)
        self.form.setWindowModality(Qt.ApplicationModal)
        self.form.setAttribute(Qt.WA_DeleteOnClose)  # importante para limpiar memoria
        self.form.showMaximized()

        # Conectamos el evento close del formulario a la recarga
        self.form.closeEvent = self._refrescar_al_cerrar

    def generar_callback_editar(self, cliente_id):
        return lambda checked=False: self.editar_cliente(cliente_id)

    def filtrar_clientes(self):
        texto = self.buscador.text().lower()
        filtrados = [c for c in self.todos_los_clientes if 
                     texto in c.apellidos.lower() or 
                     texto in c.nombres.lower() or 
                     texto in c.dni.lower()]
        self.mostrar_clientes(filtrados)

    def _refrescar_al_cerrar(self, event):
        self.cargar_datos()
        event.accept()

