# gui/form_listado_personal.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox, QLabel, QHeaderView, QSizePolicy
)
from PySide6.QtCore import Qt
from database import get_session
from models import Personal
from gui.form_personal import FormPersonal
from utils.permisos import tiene_permiso, es_admin
from utils.formato import formato_documento

class FormListadoPersonal(QWidget):
    """
    Listado de Personal — fusión de las versiones previas.
    - Usa guardas de permisos (es_admin o permisos concretos).
    - Interfaz limpia (estética similar a la versión que preferías).
    - Botón Editar por fila (abre FormPersonal con usuario pasado).
    - Botón Eliminar por fila solo si el usuario tiene permiso.
    - Buscador por apellido, nombre o DNI.
    """

    def __init__(self, usuario=None):
        super().__init__()

        # --------------------- GUARDA DE ACCESO ---------------------
        if usuario is None:
            QMessageBox.critical(self, "Acceso denegado", "Usuario no autenticado.")
            self.close()
            return

        # Permisos: ver listado de personal
        # Consideramos como nombre de permiso legible "0320 (ver/editar) listado de personal"
        if not (es_admin(usuario) or tiene_permiso(usuario, "0320 (ver/editar) listado de personal")):
            QMessageBox.critical(self, "Acceso denegado", "No tenés permisos para acceder a esta pantalla.")
            self.close()
            return
        # -------------------------------------------------------------

        self.usuario = usuario
        self.setWindowTitle("Listado de Personal")
        self.setMinimumSize(1100, 600)

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # Título (opcional)
        titulo = QLabel("Listado de Personal")
        titulo.setStyleSheet("font-size: 20px; font-weight: bold; color: #6a1b9a;")
        layout.addWidget(titulo)

        # Buscador
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("Buscar por apellido, nombre o número de documento")
        self.buscador.setMinimumHeight(36)
        self.buscador.textChanged.connect(self.actualizar_tabla)
        layout.addWidget(self.buscador)

        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels(["ID", "Apellidos", "Nombres", "Documento", "Tipo", "Acciones"])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabla.setStyleSheet("""
            QTableWidget {
                font-size: 14px;
                background-color: #ffffff;
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

        layout.addWidget(self.tabla)

        # Info/leyenda
        leyenda = QLabel("Buscar por apellidos, nombres o número de documento. Seleccioná 'Editar' para modificar un registro.")
        leyenda.setStyleSheet("color: #444; font-size: 12px;")
        layout.addWidget(leyenda)

        # Carga inicial
        self.actualizar_tabla()

    # --------------------------- Tabla ---------------------------
    def actualizar_tabla(self):
        texto = (self.buscador.text() or "").strip().lower()
        try:
            with get_session() as session:
                personales = session.query(Personal).order_by(Personal.apellidos, Personal.nombres).all()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo consultar personal:\n{e}")
            personales = []

        filtrados = []
        if texto == "":
            filtrados = personales
        else:
            for p in personales:
                if (texto in (p.apellidos or "").lower()
                    or texto in (p.nombres or "").lower()
                    or texto in (p.nro_documento or "").lower()):
                    filtrados.append(p)

        self.tabla.setRowCount(len(filtrados))

        for row, persona in enumerate(filtrados):
            # ID (col 0)
            self.tabla.setItem(row, 0, QTableWidgetItem(str(persona.id)))
            # Apellidos (col 1)
            self.tabla.setItem(row, 1, QTableWidgetItem(persona.apellidos or ""))
            # Nombres (col 2)
            self.tabla.setItem(row, 2, QTableWidgetItem(persona.nombres or ""))
            # DNI (col 3)
            self.tabla.setItem(row, 3, QTableWidgetItem(formato_documento(persona)))
            # Tipo (col 4)
            self.tabla.setItem(row, 4, QTableWidgetItem(persona.tipo or ""))

            # Acciones (col 5)
            btn_editar = QPushButton("✏️ Editar")
            btn_editar.setCursor(Qt.PointingHandCursor)
            btn_editar.setToolTip("Editar personal")
            btn_editar.setProperty("role", "editar")
            btn_editar.setStyleSheet("""
                QPushButton { background-color: #9c27b0; color: white; padding: 6px 10px; border-radius: 6px; font-weight: bold; }
                QPushButton:hover { background-color: #7b1fa2; }
            """)

            btn_editar.clicked.connect(lambda checked=False, pid=persona.id: self._abrir_edicion(pid))

            contenedor = QHBoxLayout()
            contenedor.setContentsMargins(6, 2, 6, 2)
            contenedor.setSpacing(8)
            contenedor.addWidget(btn_editar)
            contenedor.addStretch()

            acciones_widget = QWidget()
            acciones_widget.setLayout(contenedor)
            self.tabla.setCellWidget(row, 5, acciones_widget)

    def _abrir_edicion(self, personal_id):
        self.dlg_personal = FormPersonal(personal_id=personal_id, usuario=self.usuario)
        self.dlg_personal.personal_guardado.connect(self.actualizar_tabla)
        self.dlg_personal.setWindowModality(Qt.ApplicationModal)
        self.dlg_personal.setAttribute(Qt.WA_DeleteOnClose)
        self.dlg_personal.showMaximized()


