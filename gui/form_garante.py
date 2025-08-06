from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QVBoxLayout, QPushButton, QScrollArea,
    QGridLayout, QSizePolicy, QTextEdit, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import QDate, Qt, QRegularExpression, Signal
from PySide6.QtGui import QRegularExpressionValidator

from utils.widgets_custom import ComboBoxSinScroll, DateEditSinScroll
from database import session
from models import Garante


class FormGarante(QWidget):
    garante_guardado = Signal()

    def __init__(self, garante_id=None):
        super().__init__()
        self.garante_id = garante_id
        self.editando = garante_id is not None

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
            ("Ocupación", "ocupacion", False),
            ("Domicilio personal", "domicilio_personal", True),
            ("Localidad", "localidad", True),
            ("Provincia", "provincia", True),
            ("Lugar de trabajo", "lugar_trabajo_nombre", False),
            ("Domicilio laboral", "domicilio_laboral", False),
            ("Sexo", "sexo", True, "combo", ["Masculino", "Femenino", "Otro"]),
            ("Estado civil", "estado_civil", True, "combo", ["Soltero", "Casado", "Divorciado", "Viudo"]),
            ("Celular personal", "celular_personal", True),
            ("Celular laboral", "celular_trabajo", False),
            ("Email", "email", False),
        ]

        grid = QGridLayout()
        grid.setSpacing(12)

        for i, (label_text, key, requerido, *tipo) in enumerate(campos):
            row, col = divmod(i, 2)
            label = QLabel(f"{label_text}{' *' if requerido else ''}")
            label.setStyleSheet("color: #7b1fa2;" if requerido else "color: #333;")
            self.labels[key] = label

            if tipo and tipo[0] == "combo":
                input_widget = ComboBoxSinScroll()
                input_widget.addItems(tipo[1])
            elif tipo and tipo[0] == "date":
                input_widget = DateEditSinScroll()
                input_widget.setCalendarPopup(True)
                input_widget.setDate(QDate.currentDate())
            else:
                input_widget = QLineEdit()
                if key == "dni":
                    input_widget.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9]+")))
                if key.startswith("celular"):
                    input_widget.setValidator(QRegularExpressionValidator(QRegularExpression("[0-9+\\-\\s]+")))

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
            self.btn_eliminar = QPushButton("Eliminar Garante")
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
            self.btn_eliminar.clicked.connect(self.eliminar_garante)
            eliminar_layout.addWidget(self.btn_eliminar)
            eliminar_layout.addStretch()
            botones_principales.addLayout(eliminar_layout)
        else:
            botones_principales.addStretch()

        acciones_layout = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_guardar = QPushButton("Actualizar Garante" if self.editando else "Guardar Garante")
        acciones_layout.addWidget(self.btn_cancelar)
        acciones_layout.addWidget(self.btn_guardar)

        botones_principales.addLayout(acciones_layout)
        layout.addLayout(botones_principales)

        self.btn_guardar.clicked.connect(self.guardar_garante)
        self.btn_cancelar.clicked.connect(self.close)

        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
                background-color: #fdfdfd;
            }
            QLabel {
                font-weight: bold;
                color: #333;
            }
            QLineEdit, QComboBox, QDateEdit, QTextEdit {
                padding: 6px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #fff;
            }
            QLineEdit.error, QComboBox.error, QDateEdit.error {
                border: 2px solid red;
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
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #bdbdbd;
                selection-background-color: #ffe0b2;
                selection-color: #424242;
                padding: 4px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        if self.editando:
            self.cargar_datos()

    def cargar_datos(self):
        garante = session.query(Garante).get(self.garante_id)
        if not garante:
            QMessageBox.warning(self, "Error", "Garante no encontrado")
            return

        for key, widget in self.campos.items():
            valor = getattr(garante, key, "")
            if isinstance(widget, QLineEdit):
                widget.setText(valor or "")
            elif isinstance(widget, ComboBoxSinScroll):
                widget.setCurrentText(valor or "")
            elif isinstance(widget, DateEditSinScroll):
                widget.setDate(valor if valor else QDate.currentDate())

        self.btn_guardar.setText("Actualizar Garante")

    def guardar_garante(self):
        campos_requeridos = [
            "apellidos", "nombres", "dni", "fecha_nacimiento",
            "domicilio_personal", "localidad", "provincia",
            "sexo", "estado_civil", "celular_personal"
        ]

        for campo in campos_requeridos:
            widget = self.campos[campo]
            widget.setStyleSheet("")
            if isinstance(widget, QLineEdit) and not widget.text().strip():
                widget.setStyleSheet("border: 2px solid red;")
                return self.mostrar_alerta(campo)
            elif isinstance(widget, ComboBoxSinScroll) and (widget.currentIndex() == -1 or not widget.currentText().strip()):
                widget.setStyleSheet("border: 2px solid red;")
                return self.mostrar_alerta(campo)
            elif isinstance(widget, DateEditSinScroll) and not widget.date().isValid():
                widget.setStyleSheet("border: 2px solid red;")
                return self.mostrar_alerta(campo)

        try:
            garante = session.query(Garante).get(self.garante_id) if self.editando else Garante()

            for key, widget in self.campos.items():
                if isinstance(widget, QLineEdit):
                    setattr(garante, key, widget.text())
                elif isinstance(widget, ComboBoxSinScroll):
                    setattr(garante, key, widget.currentText())
                elif isinstance(widget, DateEditSinScroll):
                    setattr(garante, key, widget.date().toPython())

            if not self.editando:
                session.add(garante)

            session.commit()
            QMessageBox.information(self, "Éxito", f"Garante {'actualizado' if self.editando else 'guardado'} correctamente")
            self.garante_guardado.emit()

            if self.editando:
                self.close()
            else:
                self.limpiar_formulario()

        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo guardar el garante:\n{e}")

    def eliminar_garante(self):
        confirmacion = QMessageBox.question(self, "Eliminar", "¿Estás seguro de eliminar este garante?", QMessageBox.Yes | QMessageBox.No)
        if confirmacion == QMessageBox.Yes:
            try:
                garante = session.query(Garante).get(self.garante_id)
                session.delete(garante)
                session.commit()
                QMessageBox.information(self, "Eliminado", "Garante eliminado correctamente")
                self.close()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el garante:\n{e}")

    def mostrar_alerta(self, campo):
        nombre_legible = campo.replace('_', ' ').capitalize()
        QMessageBox.warning(self, "Campo requerido", f"Por favor completá el campo: {nombre_legible}")
        self.campos[campo].setFocus()

    def limpiar_formulario(self):
        for key, widget in self.campos.items():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, ComboBoxSinScroll):
                widget.setCurrentIndex(0)
            elif isinstance(widget, DateEditSinScroll):
                widget.setDate(QDate.currentDate())
            widget.setStyleSheet("")
