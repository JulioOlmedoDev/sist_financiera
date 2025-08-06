from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox, QLabel, QHeaderView
)
from PySide6.QtCore import Qt
from database import session
from models import Personal
from gui.form_personal import FormPersonal


class FormListadoPersonal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Listado de Personal")
        self.setMinimumSize(1100, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("Buscar por apellido, nombre o DNI")
        self.buscador.setMinimumHeight(36)
        self.buscador.textChanged.connect(self.actualizar_tabla)
        layout.addWidget(self.buscador)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels(["Apellidos", "Nombres", "DNI", "Email", "Tipo", "Acciones"])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setStyleSheet("""
            QTableWidget {
                font-size: 14px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #ccc;
            }
        """)
        header = self.tabla.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.Stretch)

        # Fijamos solo la columna de acciones
        for i in range(self.tabla.columnCount()):
            if i == 5:  # Acciones
                header.setSectionResizeMode(i, QHeaderView.Fixed)
                self.tabla.setColumnWidth(i, 200)


        layout.addWidget(self.tabla)

        self.actualizar_tabla()

    def actualizar_tabla(self):
        texto = self.buscador.text().lower()
        personales = session.query(Personal).all()
        filtrados = [
            p for p in personales if
            texto in (p.apellidos or "").lower()
            or texto in (p.nombres or "").lower()
            or texto in (p.dni or "")
        ]

        self.tabla.setRowCount(len(filtrados))

        for row, persona in enumerate(filtrados):
            self.tabla.setItem(row, 0, QTableWidgetItem(persona.apellidos or ""))
            self.tabla.setItem(row, 1, QTableWidgetItem(persona.nombres or ""))
            self.tabla.setItem(row, 2, QTableWidgetItem(persona.dni or ""))
            self.tabla.setItem(row, 3, QTableWidgetItem(persona.email or ""))
            self.tabla.setItem(row, 4, QTableWidgetItem(persona.tipo or ""))

            # Botones
            btn_editar = QPushButton("✏️ Editar")
            btn_eliminar = QPushButton("🗑 Eliminar")

            for btn in [btn_editar, btn_eliminar]:
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #9c27b0;
                        color: white;
                        padding: 5px 10px;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 13px;
                    }
                    QPushButton:hover {
                        background-color: #7b1fa2;
                    }
                """)

            btn_editar.clicked.connect(lambda _, p=persona: self.abrir_formulario_edicion(p.id))
            btn_eliminar.clicked.connect(lambda _, p=persona: self.eliminar_personal(p.id))

            contenedor = QHBoxLayout()
            contenedor.setContentsMargins(0, 0, 0, 0)
            contenedor.setSpacing(10)
            contenedor.addWidget(btn_editar)
            contenedor.addWidget(btn_eliminar)

            acciones_widget = QWidget()
            acciones_widget.setLayout(contenedor)
            self.tabla.setCellWidget(row, 5, acciones_widget)

    def abrir_formulario_edicion(self, personal_id):
        self.form = FormPersonal(personal_id=personal_id)
        self.form.personal_guardado.connect(self.actualizar_tabla)
        self.form.show()

    def eliminar_personal(self, personal_id):
        confirmacion = QMessageBox.question(self, "Eliminar", "¿Eliminar este personal?", QMessageBox.Yes | QMessageBox.No)
        if confirmacion == QMessageBox.Yes:
            try:
                persona = session.query(Personal).get(personal_id)
                session.delete(persona)
                session.commit()
                self.actualizar_tabla()
                QMessageBox.information(self, "Eliminado", "Personal eliminado correctamente.")
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"No se pudo eliminar:\n{e}")
