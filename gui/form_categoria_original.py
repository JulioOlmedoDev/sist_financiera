from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox
from database import session
from models import Categoria

class FormCategoria(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crear Categoría")
        self.setGeometry(350, 250, 400, 150)

        self.nombre_input = QLineEdit()
        self.btn_guardar = QPushButton("Guardar Categoría")
        self.btn_guardar.clicked.connect(self.guardar_categoria)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Nombre de la categoría:"))
        layout.addWidget(self.nombre_input)
        layout.addWidget(self.btn_guardar)

        self.setLayout(layout)

    def guardar_categoria(self):
        nombre = self.nombre_input.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Error", "El nombre no puede estar vacío.")
            return

        categoria = Categoria(nombre=nombre)
        session.add(categoria)
        session.commit()
        QMessageBox.information(self, "Éxito", "Categoría guardada correctamente.")
        self.close()
