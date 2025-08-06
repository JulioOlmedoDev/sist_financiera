from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QComboBox, QMessageBox
from database import session
from models import Producto, Categoria

class FormProducto(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crear Producto")
        self.setGeometry(350, 250, 400, 200)

        self.nombre_input = QLineEdit()
        self.categoria_combo = QComboBox()
        self.cargar_categorias()

        self.btn_guardar = QPushButton("Guardar Producto")
        self.btn_guardar.clicked.connect(self.guardar_producto)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Nombre del producto:"))
        layout.addWidget(self.nombre_input)
        layout.addWidget(QLabel("Categoría:"))
        layout.addWidget(self.categoria_combo)
        layout.addWidget(self.btn_guardar)

        self.setLayout(layout)

    def cargar_categorias(self):
        self.categoria_combo.clear()
        categorias = session.query(Categoria).all()
        for c in categorias:
            self.categoria_combo.addItem(c.nombre, userData=c.id)

    def guardar_producto(self):
        nombre = self.nombre_input.text().strip()
        categoria_id = self.categoria_combo.currentData()

        if not nombre or categoria_id is None:
            QMessageBox.warning(self, "Error", "Debe completar todos los campos.")
            return

        producto = Producto(nombre=nombre, categoria_id=categoria_id)
        session.add(producto)
        session.commit()
        QMessageBox.information(self, "Éxito", "Producto guardado correctamente.")
        self.close()
