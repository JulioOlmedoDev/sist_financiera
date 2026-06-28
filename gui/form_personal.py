import re
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QVBoxLayout, QPushButton, QComboBox,
    QMessageBox, QScrollArea, QGridLayout, QSizePolicy, QHBoxLayout
)
from PySide6.QtCore import Qt, QRegularExpression, Signal
from datetime import date
from PySide6.QtGui import QRegularExpressionValidator

from sqlalchemy.exc import IntegrityError
from database import get_session
from models import Personal
from utils.permisos import es_admin, tiene_permiso
from utils.widgets_custom import parsear_fecha

TIPOS_DOC = ["SELECCIONAR", "CF", "CI", "CP", "DNI", "LC", "LE", "MI", "OTROS", "PASAPORTE"]

class FormPersonal(QWidget):
    personal_guardado  = Signal()
    personal_cancelado = Signal()

    def __init__(self, personal_id=None, usuario=None):
        super().__init__()
        self.usuario = usuario
        self.personal_id = personal_id
        self.editando = personal_id is not None

        # --- GUARDA DE PERMISOS ---
        if not usuario:
            QMessageBox.critical(self, "Acceso denegado", "Usuario no autenticado.")
            self.close()
            return

        # crear nuevo personal
        if not self.editando:
            if not (es_admin(usuario) or tiene_permiso(usuario, "0310 (crear) personal")):
                QMessageBox.critical(self, "Acceso denegado", "No tenés permiso para crear personal.")
                self.close()
                return

        # editar personal existente
        if self.editando:
            if not (es_admin(usuario) or tiene_permiso(usuario, "0320 (ver/editar) listado de personal")):
                QMessageBox.critical(self, "Acceso denegado", "No tenés permiso para editar personal.")
                self.close()
                return
        # ----------------------------------------------------

        self.setWindowTitle("Gestión de Personal")

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
            ("Domicilio personal", "domicilio_personal", True),
            ("Localidad", "localidad", True),
            ("Provincia", "provincia", True),
            ("Sexo", "sexo", True, "combo", ["Masculino", "Femenino", "Otro"]),
            ("Estado civil", "estado_civil", True, "combo", ["Soltero", "Casado", "Divorciado", "Viudo"]),
            ("Celular personal", "celular_personal", True),
            ("Celular alternativo", "celular_alternativo", False),
            ("Email", "email", False),
            ("CUIL", "cuil", False),
            ("Fecha de ingreso", "fecha_ingreso", True, "date"),
            ("Cargo", "tipo", True, "combo", ["Gerente", "Coordinador", "Administrativo", "Vendedor", "Cobrador"]),
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
                input_widget = QLineEdit()
                input_widget.setInputMask("00/00/0000;_")

            else:
                input_widget = QLineEdit()
                if key.startswith("celular"):
                    input_widget.setValidator(QRegularExpressionValidator(QRegularExpression("^[0-9+\\-\\s]+$")))
                elif key == "cuil":
                    input_widget.setInputMask("00-00000000-0;_")

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
        self.btn_cancelar.clicked.connect(self.cancelar_formulario)

        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
                background-color: #fdfdfd;
            }
            QLabel {
                font-weight: bold;
            }
            QLineEdit, QComboBox {
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
            personal = session.query(Personal).get(self.personal_id)
            if not personal:
                QMessageBox.warning(self, "Error", "Personal no encontrado")
                return
            for key, widget in self.campos.items():
                value = getattr(personal, key, "")
                if key in ("fecha_nacimiento", "fecha_ingreso"):
                    widget.setText(value.strftime("%d/%m/%Y") if value else "")
                elif key == "cuil":
                    widget.setText(value if value and re.fullmatch(r'\d{2}-\d{8}-\d', str(value)) else "")
                elif isinstance(widget, QLineEdit):
                    widget.setText(value or "")
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(value or "")

    def guardar_personal(self):
        campos_requeridos = [
            "apellidos", "nombres",
            "domicilio_personal", "localidad", "provincia",
            "sexo", "estado_civil", "celular_personal",
            "tipo"
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

        # ── Validación del par de documento (obligatorio en personal) ──
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

        fecha_ing_w = self.campos["fecha_ingreso"]
        fecha_ing_w.setStyleSheet("")
        if not fecha_ing_w.hasAcceptableInput():
            fecha_ing_w.setStyleSheet("border: 2px solid red;")
            QMessageBox.warning(self, "Campo requerido",
                "Ingresá la fecha de ingreso completa en formato dd/mm/aaaa.")
            fecha_ing_w.setFocus()
            return
        fecha_ing = parsear_fecha(fecha_ing_w.text())
        if not fecha_ing:
            fecha_ing_w.setStyleSheet("border: 2px solid red;")
            QMessageBox.warning(self, "Fecha inválida",
                "La fecha de ingreso no existe. Verificá día y mes.")
            fecha_ing_w.setFocus()
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

        cuil_widget = self.campos["cuil"]
        cuil_widget.setStyleSheet("")
        cuil_digitos = re.sub(r'\D', '', cuil_widget.text())
        if cuil_digitos:
            if not re.fullmatch(r'\d{2}-\d{8}-\d', cuil_widget.text()):
                cuil_widget.setStyleSheet("border: 2px solid red;")
                QMessageBox.warning(self, "CUIL inválido",
                    "El CUIL no respeta el formato. Debe ser XX-XXXXXXXX-X (ej. 20-12345678-9).")
                cuil_widget.setFocus()
                return

        try:
            with get_session() as session:
                personal = session.query(Personal).get(self.personal_id) if self.editando else Personal()
                for key, widget in self.campos.items():
                    if key in ("fecha_nacimiento", "fecha_ingreso"):
                        setattr(personal, key, parsear_fecha(widget.text()))
                    elif key == "cuil":
                        digitos = re.sub(r'\D', '', widget.text())
                        setattr(personal, key, widget.text() if digitos else None)
                    elif key == "tipo_documento":
                        val = widget.currentText()
                        setattr(personal, key, val if val != "SELECCIONAR" else None)
                    elif key == "nro_documento":
                        val = widget.text().strip()
                        setattr(personal, key, val or None)
                    elif isinstance(widget, QLineEdit):
                        setattr(personal, key, widget.text())
                    elif isinstance(widget, QComboBox):
                        setattr(personal, key, widget.currentText())

                if not self.editando:
                    session.add(personal)

                session.commit()
            QMessageBox.information(self, "Éxito", f"Personal {'actualizado' if self.editando else 'guardado'} correctamente")
            self.personal_guardado.emit()
            self.close()
        except IntegrityError as e:
            if "uq_personal_tipo_nro" in str(e).lower():
                QMessageBox.critical(self, "Documento duplicado",
                    "Ya existe un registro de personal con ese tipo y número de documento.")
            else:
                QMessageBox.critical(self, "Error", f"No se pudo guardar el personal:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el personal:\n{e}")

    def eliminar_personal(self):
        confirmacion = QMessageBox.question(self, "Eliminar", "¿Estás seguro de eliminar este personal?", QMessageBox.Yes | QMessageBox.No)
        if confirmacion == QMessageBox.Yes:
            try:
                with get_session() as session:
                    personal = session.query(Personal).get(self.personal_id)
                    session.delete(personal)
                    session.commit()
                QMessageBox.information(self, "Eliminado", "Personal eliminado correctamente")
                self.close()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el personal:\n{e}")

    def cancelar_formulario(self):
        self.personal_cancelado.emit()
        self.close()

    def mostrar_alerta(self, campo):
        nombre_legible = campo.replace("_", " ").capitalize()
        QMessageBox.warning(self, "Campo requerido", f"Por favor completá el campo: {nombre_legible}")
        self.campos[campo].setFocus()
