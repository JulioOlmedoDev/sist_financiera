import re
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QVBoxLayout, QPushButton, QScrollArea,
    QGridLayout, QSizePolicy, QTextEdit, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt, QRegularExpression, Signal
from datetime import date
from PySide6.QtGui import QRegularExpressionValidator

from utils.widgets_custom import ComboBoxSinScroll, parsear_fecha
from sqlalchemy.exc import IntegrityError
from database import get_session
from models import Cliente
from utils.dialogos import confirmar
from utils.estilos import PALETA

TIPOS_DOC = ["SELECCIONAR", "CF", "CI", "CP", "DNI", "LC", "LE", "MI", "OTROS", "PASAPORTE"]

class FormCliente(QWidget):
    cliente_guardado  = Signal()
    cliente_cancelado = Signal()

    def __init__(self, cliente_id=None):
        super().__init__()
        self.cliente_id = cliente_id
        self.editando = cliente_id is not None

        self.setWindowTitle("Gestión de Clientes")

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
            ("Tipo de Documento", "tipo_documento", True, "combo", TIPOS_DOC),
            ("N° de Documento",   "nro_documento",  True),
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
                input_widget = QLineEdit()
                input_widget.setInputMask("00/00/0000;_")
            else:
                input_widget = QLineEdit()
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
        a = PALETA["acciones"]

        if self.editando:
            eliminar_layout = QHBoxLayout()
            eliminar_layout.addWidget(QLabel())
            self.btn_eliminar = QPushButton("Eliminar")
            self.btn_eliminar.setStyleSheet(f"""
                QPushButton {{ background-color: {a['eliminar']}; }}
                QPushButton:hover {{ background-color: {a['eliminar_hover']}; }}
            """)
            self.btn_eliminar.clicked.connect(self.eliminar_cliente)
            eliminar_layout.addWidget(self.btn_eliminar)
            eliminar_layout.addStretch()
            botones_principales.addLayout(eliminar_layout)
        else:
            botones_principales.addStretch()

        acciones_layout = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_guardar = QPushButton("Actualizar" if self.editando else "Guardar")
        self.btn_cancelar.setStyleSheet(f"""
            QPushButton {{ background-color: {a['cancelar']}; }}
            QPushButton:hover {{ background-color: {a['cancelar_hover']}; }}
        """)
        self.btn_guardar.setStyleSheet(f"""
            QPushButton {{ background-color: {a['guardar']}; }}
            QPushButton:hover {{ background-color: {a['guardar_hover']}; }}
        """)
        acciones_layout.addWidget(self.btn_cancelar)
        acciones_layout.addWidget(self.btn_guardar)

        botones_principales.addLayout(acciones_layout)
        layout.addLayout(botones_principales)

        self.btn_guardar.clicked.connect(self.guardar_cliente)
        self.btn_cancelar.clicked.connect(self.cancelar_formulario)

        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
                background-color: #fdfdfd;
            }
            QLabel {
                font-weight: bold;
            }
            QLineEdit, QComboBox, QTextEdit {
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
        with get_session() as session:
            cliente = session.query(Cliente).get(self.cliente_id)
            if not cliente:
                QMessageBox.warning(self, "Error", "Cliente no encontrado")
                return
            for key, widget in self.campos.items():
                value = getattr(cliente, key, "")
                if key == "fecha_nacimiento":
                    widget.setText(value.strftime("%d/%m/%Y") if value else "")
                elif isinstance(widget, QLineEdit):
                    widget.setText(value or "")
                elif isinstance(widget, ComboBoxSinScroll):
                    widget.setCurrentText(value or "")

    def guardar_cliente(self):
        campos_requeridos = [
            "apellidos", "nombres",
            "domicilio_personal", "localidad", "provincia",
            "sexo", "estado_civil", "celular_personal"
        ]

        for campo in campos_requeridos:
            widget = self.campos.get(campo)
            widget.setStyleSheet("")
            if isinstance(widget, QLineEdit) and not widget.text().strip():
                widget.setStyleSheet("border: 2px solid red;")
                return self.mostrar_alerta(campo)
            elif isinstance(widget, ComboBoxSinScroll) and not widget.currentText().strip():
                widget.setStyleSheet("border: 2px solid red;")
                return self.mostrar_alerta(campo)

        # ── Validación del par de documento (obligatorio en cliente) ──
        tipo_doc_w = self.campos["tipo_documento"]
        nro_doc_w  = self.campos["nro_documento"]
        tipo_doc_w.setStyleSheet("")
        nro_doc_w.setStyleSheet("")
        tipo_val = tipo_doc_w.currentText()
        nro_val  = nro_doc_w.text().strip()
        if tipo_val == "SELECCIONAR" and not nro_val:
            tipo_doc_w.setStyleSheet("border: 2px solid red;")
            nro_doc_w.setStyleSheet("border: 2px solid red;")
            QMessageBox.warning(self, "Campo requerido",
                "El documento es obligatorio. Elegí el tipo e ingresá el número.")
            return
        if tipo_val == "SELECCIONAR":
            tipo_doc_w.setStyleSheet("border: 2px solid red;")
            QMessageBox.warning(self, "Campo requerido", "Elegí el tipo de documento.")
            return
        if not nro_val:
            nro_doc_w.setStyleSheet("border: 2px solid red;")
            QMessageBox.warning(self, "Campo requerido", "Ingresá el número de documento.")
            return

        fecha_nac_w = self.campos["fecha_nacimiento"]
        fecha_nac_w.setStyleSheet("")
        if not fecha_nac_w.hasAcceptableInput():
            fecha_nac_w.setStyleSheet("border: 2px solid red;")
            QMessageBox.warning(self, "Campo requerido",
                "Ingresá la fecha de nacimiento completa en formato dd/mm/aaaa.")
            fecha_nac_w.setFocus()
            return
        fecha_nac = parsear_fecha(fecha_nac_w.text())
        if not fecha_nac:
            fecha_nac_w.setStyleSheet("border: 2px solid red;")
            QMessageBox.warning(self, "Fecha inválida",
                "La fecha de nacimiento no existe. Verificá día y mes (por ej. no existe el 31/02).")
            fecha_nac_w.setFocus()
            return
        if fecha_nac >= date.today():
            fecha_nac_w.setStyleSheet("border: 2px solid red;")
            QMessageBox.warning(self, "Fecha inválida",
                "La fecha de nacimiento no puede ser la fecha de hoy ni futura.")
            fecha_nac_w.setFocus()
            return
        if fecha_nac.year < 1900:
            fecha_nac_w.setStyleSheet("border: 2px solid red;")
            QMessageBox.warning(self, "Fecha inválida",
                "La fecha de nacimiento no puede ser anterior a 1900.")
            fecha_nac_w.setFocus()
            return

        email_widget = self.campos.get("email")
        email_text = email_widget.text().strip()
        if email_text:
            patron = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
            if not re.match(patron, email_text):
                email_widget.setStyleSheet("border: 2px solid red;")
                QMessageBox.warning(self, "Email inválido",
                    "El email ingresado no es válido. Usá el formato nombre@dominio.com.")
                email_widget.setFocus()
                return

        try:
            with get_session() as session:
                cliente = session.query(Cliente).get(self.cliente_id) if self.editando else Cliente()
                for key, widget in self.campos.items():
                    if key == "fecha_nacimiento":
                        setattr(cliente, key, parsear_fecha(widget.text()))
                    elif key == "tipo_documento":
                        val = widget.currentText()
                        setattr(cliente, key, val if val != "SELECCIONAR" else None)
                    elif key == "nro_documento":
                        val = widget.text().strip()
                        setattr(cliente, key, val or None)
                    elif isinstance(widget, QLineEdit):
                        setattr(cliente, key, widget.text())
                    elif isinstance(widget, ComboBoxSinScroll):
                        setattr(cliente, key, widget.currentText())

                if not self.editando:
                    session.add(cliente)

                session.commit()
            QMessageBox.information(self, "Éxito", f"Cliente {'actualizado' if self.editando else 'guardado'} correctamente")
            self.cliente_guardado.emit()
            if self.editando:
                self.close()
            else:
                self.limpiar_formulario()
        except IntegrityError as e:
            if "uq_clientes_tipo_nro" in str(e).lower():
                QMessageBox.critical(self, "Documento duplicado",
                    "Ya existe un cliente con ese tipo y número de documento.")
            else:
                QMessageBox.critical(self, "Error", f"No se pudo guardar el cliente:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el cliente:\n{e}")

    def eliminar_cliente(self):
        if confirmar(self, "Eliminar", "¿Estás seguro de eliminar este cliente?"):
            try:
                with get_session() as session:
                    cliente = session.query(Cliente).get(self.cliente_id)
                    session.delete(cliente)
                    session.commit()
                QMessageBox.information(self, "Eliminado", "Cliente eliminado correctamente")
                self.close()
            except IntegrityError:
                QMessageBox.warning(self, "No se puede eliminar",
                                    "Este cliente tiene ventas registradas y no puede eliminarse.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el cliente:\n{e}")

    def mostrar_alerta(self, campo):
        nombre_legible = campo.replace("_", " ").capitalize()
        QMessageBox.warning(self, "Campo requerido", f"Por favor completá el campo: {nombre_legible}")
        self.campos[campo].setFocus()

    def limpiar_formulario(self):
        for widget in self.campos.values():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, ComboBoxSinScroll):
                widget.setCurrentIndex(0)
            widget.setStyleSheet("")

    def cancelar_formulario(self):
        self.cliente_cancelado.emit()
        self.close()
