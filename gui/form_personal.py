from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QVBoxLayout, QPushButton, QComboBox,
    QDateEdit, QMessageBox, QScrollArea, QGridLayout, QSizePolicy, QHBoxLayout
)
from PySide6.QtCore import QDate, Qt, QRegularExpression, Signal
from PySide6.QtGui import QRegularExpressionValidator

from database import session
from models import Personal

class FormPersonal(QWidget):
    personal_guardado = Signal()

    def __init__(self, personal_id=None):
        super().__init__()
        self.personal_id = personal_id
        self.editando = personal_id is not None

        self.setWindowTitle("Gestión de Personal")
        self.showMaximized()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenido = QWidget()
        scroll.setWidget(contenido)

        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        self.campos = {}
        self.labels = {}

        campos = [
            ("Apellidos", "apellidos", True),
            ("Nombres", "nombres", True),
            ("DNI", "dni", True),
            ("Fecha de nacimiento", "fecha_nacimiento", True, "date"),
            ("Domicilio personal", "domicilio_personal", True),
            ("Localidad", "localidad", True),
            ("Provincia", "provincia", True),
            ("Sexo", "sexo", True, "combo", ["Masculino", "Femenino", "Otro"]),
            ("Estado civil", "estado_civil", True, "combo", ["Soltero", "Casado", "Divorciado", "Viudo"]),
            ("Celular personal", "celular_personal", True),
            ("Celular alternativo", "celular_alternativo", False),
            ("Email", "email", False),
            ("CUIL", "cuil", True),
            ("Fecha de ingreso", "fecha_ingreso", True, "date"),
            ("Tipo", "tipo", True, "combo", ["Coordinador", "Vendedor", "Cobrador"]),
        ]

        grid = QGridLayout()
        grid.setSpacing(12)

        for i, (label_text, key, requerido, *tipo) in enumerate(campos):
            row, col = divmod(i, 2)
            label = QLabel(f"{label_text}{' *' if requerido else ''}")
            label.setStyleSheet("color: #7b1fa2;" if requerido else "color: #333;")
            self.labels[key] = label

            if tipo and tipo[0] == "combo":
                input_widget = QComboBox()
                input_widget.addItems(tipo[1])
                input_widget.setFocusPolicy(Qt.StrongFocus)
                input_widget.wheelEvent = lambda e: None

            elif tipo and tipo[0] == "date":
                input_widget = QDateEdit()
                input_widget.setCalendarPopup(True)
                input_widget.setDate(QDate.currentDate())
                input_widget.setFocusPolicy(Qt.StrongFocus)
                input_widget.wheelEvent = lambda e: None

            else:
                input_widget = QLineEdit()
                if key == "dni":
                    input_widget.setValidator(QRegularExpressionValidator(QRegularExpression("^[0-9]+$")))
                elif key.startswith("celular"):
                    input_widget.setValidator(QRegularExpressionValidator(QRegularExpression("^[0-9+\\-\\s]+$")))
                elif key == "cuil":
                    regex_cuil = QRegularExpression("^[0-9]{2}-[0-9]{7,8}-[0-9]{1}$")
                    input_widget.setValidator(QRegularExpressionValidator(regex_cuil))
                    input_widget.setPlaceholderText("Ej: 20-12345678-3")

            input_widget.setMinimumHeight(30)
            input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            grid.addWidget(label, row, col * 2)
            grid.addWidget(input_widget, row, col * 2 + 1)
            self.campos[key] = input_widget


        layout.addLayout(grid)

        leyenda = QLabel("Los campos marcados con (*) son obligatorios")
        leyenda.setStyleSheet("color: black; font-size: 12px; margin-top: -8px;")
        layout.addWidget(leyenda)

        botones_principales = QHBoxLayout()
        botones_principales.setContentsMargins(0, 20, 0, 0)
        botones_principales.setSpacing(40)

        if self.editando:
            eliminar_layout = QHBoxLayout()
            eliminar_layout.addWidget(QLabel())
            self.btn_eliminar = QPushButton("Eliminar Personal")
            self.btn_eliminar.setStyleSheet("""
                QPushButton {
                    background-color: #e53935;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c62828;
                }
            """)
            self.btn_eliminar.clicked.connect(self.eliminar_personal)
            eliminar_layout.addWidget(self.btn_eliminar)
            eliminar_layout.addStretch()
            botones_principales.addLayout(eliminar_layout)
        else:
            botones_principales.addStretch()

        acciones_layout = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_guardar = QPushButton("Actualizar Personal" if self.editando else "Guardar Personal")
        acciones_layout.addWidget(self.btn_cancelar)
        acciones_layout.addWidget(self.btn_guardar)

        botones_principales.addLayout(acciones_layout)
        layout.addLayout(botones_principales)

        self.btn_guardar.clicked.connect(self.guardar_personal)
        self.btn_cancelar.clicked.connect(self.close)

        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
                background-color: #fdfdfd;
            }
            QLabel {
                font-weight: bold;
            }
            QLineEdit, QComboBox, QDateEdit {
                padding: 6px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #fff;
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
        """)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        if self.editando:
            self.cargar_datos()

    def cargar_datos(self):
        personal = session.query(Personal).get(self.personal_id)
        if not personal:
            QMessageBox.warning(self, "Error", "Personal no encontrado")
            return
        for key, widget in self.campos.items():
            value = getattr(personal, key, "")
            if isinstance(widget, QLineEdit):
                widget.setText(value or "")
            elif isinstance(widget, QComboBox):
                widget.setCurrentText(value or "")
            elif isinstance(widget, QDateEdit):
                widget.setDate(value or QDate.currentDate())

    def guardar_personal(self):
        campos_requeridos = [
            "apellidos", "nombres", "dni", "fecha_nacimiento",
            "domicilio_personal", "localidad", "provincia",
            "sexo", "estado_civil", "celular_personal",
            "cuil", "fecha_ingreso", "tipo"
        ]

        for campo in campos_requeridos:
            widget = self.campos.get(campo)
            widget.setStyleSheet("")
            if isinstance(widget, QLineEdit) and not widget.text().strip():
                widget.setStyleSheet("border: 2px solid red;")
                return self.mostrar_alerta(campo)
            elif isinstance(widget, QComboBox) and not widget.currentText().strip():
                widget.setStyleSheet("border: 2px solid red;")
                return self.mostrar_alerta(campo)
            elif isinstance(widget, QDateEdit) and not widget.date().isValid():
                widget.setStyleSheet("border: 2px solid red;")
                return self.mostrar_alerta(campo)

        try:
            personal = session.query(Personal).get(self.personal_id) if self.editando else Personal()
            for key, widget in self.campos.items():
                if isinstance(widget, QLineEdit):
                    setattr(personal, key, widget.text())
                elif isinstance(widget, QComboBox):
                    setattr(personal, key, widget.currentText())
                elif isinstance(widget, QDateEdit):
                    setattr(personal, key, widget.date().toPython())

            if not self.editando:
                session.add(personal)

            session.commit()
            QMessageBox.information(self, "Éxito", f"Personal {'actualizado' if self.editando else 'guardado'} correctamente")
            self.personal_guardado.emit()
            self.close()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo guardar el personal:\n{e}")

    def eliminar_personal(self):
        confirmacion = QMessageBox.question(self, "Eliminar", "¿Estás seguro de eliminar este personal?", QMessageBox.Yes | QMessageBox.No)
        if confirmacion == QMessageBox.Yes:
            try:
                personal = session.query(Personal).get(self.personal_id)
                session.delete(personal)
                session.commit()
                QMessageBox.information(self, "Eliminado", "Personal eliminado correctamente")
                self.close()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el personal:\n{e}")

    def mostrar_alerta(self, campo):
        nombre_legible = campo.replace("_", " ").capitalize()
        QMessageBox.warning(self, "Campo requerido", f"Por favor completá el campo: {nombre_legible}")
        self.campos[campo].setFocus()
