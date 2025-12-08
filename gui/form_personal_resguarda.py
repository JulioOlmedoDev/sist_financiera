# gui/form_personal.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QVBoxLayout, QPushButton, QComboBox,
    QDateEdit, QMessageBox, QScrollArea, QGridLayout, QSizePolicy, QHBoxLayout
)
from PySide6.QtCore import QDate, Qt, QRegularExpression, Signal
from PySide6.QtGui import QRegularExpressionValidator

from database import session
from models import Personal
from utils.permisos import es_admin, tiene_permiso


class FormPersonal(QWidget):
    personal_guardado = Signal()

    def __init__(self, personal_id=None, usuario=None):
        super().__init__()

        # ---------------------- GUARDA DE ACCESO ----------------------
        if usuario is None:
            QMessageBox.critical(self, "Acceso denegado", "Usuario no autenticado.")
            self.close()
            return

        if not (es_admin(usuario) or tiene_permiso(usuario, "personal.editar")):
            QMessageBox.critical(
                self, "Acceso denegado",
                "No tenés permisos para gestionar personal."
            )
            self.close()
            return
        # --------------------------------------------------------------

        self.usuario = usuario
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

            elif tipo and tipo[0] == "date":
                input_widget = QDateEdit()
                input_widget.setCalendarPopup(True)
                input_widget.setDate(QDate.currentDate())

            else:
                input_widget = QLineEdit()

            input_widget.setMinimumHeight(30)
            input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            grid.addWidget(label, row, col * 2)
            grid.addWidget(input_widget, row, col * 2 + 1)
            self.campos[key] = input_widget

        layout.addLayout(grid)

        botones_principales = QHBoxLayout()
        botones_principales.setContentsMargins(0, 20, 0, 0)
        botones_principales.setSpacing(40)

        if self.editando:
            self.btn_eliminar = QPushButton("Eliminar Personal")
            botones_principales.addWidget(self.btn_eliminar)
            self.btn_eliminar.clicked.connect(self.eliminar_personal)
        else:
            botones_principales.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_guardar = QPushButton("Actualizar Personal" if self.editando else "Guardar Personal")
        botones_principales.addWidget(self.btn_cancelar)
        botones_principales.addWidget(self.btn_guardar)

        layout.addLayout(botones_principales)

        self.btn_guardar.clicked.connect(self.guardar_personal)
        self.btn_cancelar.clicked.connect(self.close)

        if self.editando:
            self.cargar_datos()

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
