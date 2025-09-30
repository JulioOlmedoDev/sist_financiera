from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLineEdit, QHeaderView, QFrame
)
from PySide6.QtCore import Qt, QTimer
from database import session
from models import Garante
from gui.form_garante import FormGarante

class FormGestionGarantes(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Garantes")

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Título
        titulo = QLabel("Listado de Garantes")
        titulo.setObjectName("titulo")
        layout.addWidget(titulo)

        # Buscador
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("Buscar por apellido, nombre o DNI")
        self.buscador.textChanged.connect(self.filtrar_garantes)
        layout.addWidget(self.buscador)

        # Tabla (mismas columnas que Clientes)
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels(["ID", "Apellidos", "Nombres", "DNI", "Calificación", "Acciones"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setAlternatingRowColors(True)
        layout.addWidget(self.tabla)

        # --- Carga diferida con overlay (igual a Clientes) ---
        self._show_loading("Cargando garantes…")
        QTimer.singleShot(0, self._load_after_paint)

        # Estilo (igual a Clientes)
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

    # ---------- Carga diferida ----------
    def _load_after_paint(self):
        self.setUpdatesEnabled(False)
        try:
            self.cargar_datos()
        finally:
            self.setUpdatesEnabled(True)
            self._hide_loading()

    def _show_loading(self, text="Cargando…"):
        if getattr(self, "_loading_overlay", None):
            self._loading_overlay.show()
            self._loading_label.setText(text)
            self._position_loading()
            return

        self._loading_overlay = QFrame(self)
        self._loading_overlay.setStyleSheet(
            "QFrame { background: rgba(255,255,255,220); border: 1px solid #ddd; border-radius: 8px; }"
        )
        self._loading_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        lay = QVBoxLayout(self._loading_overlay)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.addStretch()
        self._loading_label = QLabel(text, self._loading_overlay)
        self._loading_label.setAlignment(Qt.AlignCenter)
        self._loading_label.setStyleSheet("QLabel { font-size: 16px; color: #555; }")
        lay.addWidget(self._loading_label)
        lay.addStretch()

        self._position_loading()
        self._loading_overlay.show()

    def _position_loading(self):
        self._loading_overlay.setGeometry(self.rect())

    def _hide_loading(self):
        if getattr(self, "_loading_overlay", None):
            self._loading_overlay.hide()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if getattr(self, "_loading_overlay", None):
            self._position_loading()

    # ---------- Datos ----------
    def cargar_datos(self):
        self.todos_los_garantes = session.query(Garante).all()
        self.mostrar_garantes(self.todos_los_garantes)

    def mostrar_garantes(self, lista):
        self.tabla.setUpdatesEnabled(False)
        try:
            if hasattr(self.tabla, "setSortingEnabled"):
                self.tabla.setSortingEnabled(False)
            self.tabla.clearContents()
            self.tabla.setRowCount(len(lista))

            for row_index, garante in enumerate(lista):
                self.tabla.setItem(row_index, 0, QTableWidgetItem(str(garante.id)))
                self.tabla.setItem(row_index, 1, QTableWidgetItem(garante.apellidos or ""))
                self.tabla.setItem(row_index, 2, QTableWidgetItem(garante.nombres or ""))
                self.tabla.setItem(row_index, 3, QTableWidgetItem(garante.dni or ""))
                # Nueva columna: Calificación (igual a Clientes)
                self.tabla.setItem(row_index, 4, QTableWidgetItem(getattr(garante, "calificacion", "") or ""))

                # Botón Editar (misma UI que Clientes)
                btn_editar = QPushButton("Editar")
                btn_editar.clicked.connect(self.generar_callback_editar(garante.id))

                acciones_layout = QHBoxLayout()
                acciones_layout.setContentsMargins(0, 0, 0, 0)
                acciones_layout.setSpacing(5)
                acciones_layout.addWidget(btn_editar)

                acciones_widget = QWidget()
                acciones_widget.setLayout(acciones_layout)
                self.tabla.setCellWidget(row_index, 5, acciones_widget)
        finally:
            if hasattr(self.tabla, "setSortingEnabled"):
                self.tabla.setSortingEnabled(True)
            self.tabla.setUpdatesEnabled(True)

    # ---------- Acciones ----------
    def generar_callback_editar(self, garante_id):
        return lambda checked=False: self.editar_garante(garante_id)

    def editar_garante(self, garante_id):
        self.form = FormGarante(garante_id=garante_id)
        self.form.setWindowModality(Qt.ApplicationModal)
        self.form.setAttribute(Qt.WA_DeleteOnClose)
        self.form.showMaximized()
        # Al cerrar, refrescar listado con overlay (como en Clientes)
        self.form.closeEvent = self._refrescar_al_cerrar

    # ---------- Filtro ----------
    def filtrar_garantes(self):
        if not hasattr(self, "todos_los_garantes"):
            return
        texto = (self.buscador.text() or "").lower().strip()
        if not texto:
            self.mostrar_garantes(self.todos_los_garantes)
            return

        filtrados = [
            g for g in self.todos_los_garantes
            if (g.apellidos and texto in g.apellidos.lower()) or
               (g.nombres and texto in g.nombres.lower()) or
               (g.dni and texto in g.dni.lower())
        ]
        self.mostrar_garantes(filtrados)

    # ---------- Refresh ----------
    def _refrescar_al_cerrar(self, event):
        self._show_loading("Actualizando…")
        QTimer.singleShot(0, self._load_after_paint)
        event.accept()