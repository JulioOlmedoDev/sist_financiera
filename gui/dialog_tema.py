# gui/dialog_tema.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QHBoxLayout, QMessageBox
from database import get_session
from models import get_setting, set_setting
from utils.permisos import es_admin
from utils.estilos import NOMBRES_TEMAS


class DialogTema(QDialog):
    """
    Permite elegir el tema de color activo del sistema (violeta, crema,
    naranja, celeste). Es una configuracion GLOBAL (no por usuario),
    pensada para poder mostrar variantes visuales distintas a diferentes
    clientes eventuales de reventa.

    Solo administradores pueden cambiarla: es una decision de identidad
    visual de toda la instalacion, no un permiso otorgable pieza por pieza.
    """
    def __init__(self, usuario=None, parent=None):
        super().__init__(parent)
        self.usuario = usuario

        if not es_admin(usuario):
            QMessageBox.warning(self, "Acceso denegado",
                                 "Solo un administrador puede cambiar el tema del sistema.")
            self.reject()
            return

        self.setWindowTitle("Apariencia del sistema")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Elegí el tema de color del sistema:"))

        self.combo_tema = QComboBox()
        self._claves_tema = list(NOMBRES_TEMAS.keys())
        for clave in self._claves_tema:
            self.combo_tema.addItem(NOMBRES_TEMAS[clave], userData=clave)

        with get_session() as session:
            tema_actual = get_setting(session, "tema_activo", "violeta")
        idx = self.combo_tema.findData(tema_actual)
        if idx >= 0:
            self.combo_tema.setCurrentIndex(idx)

        layout.addWidget(self.combo_tema)

        nota = QLabel(
            "El cambio se aplica a toda la instalación (no es una preferencia "
            "personal). Hay que reiniciar la aplicación para verlo reflejado "
            "por completo."
        )
        nota.setWordWrap(True)
        nota.setStyleSheet("color: #666666; font-size: 12px;")
        layout.addWidget(nota)

        botones = QHBoxLayout()
        botones.addStretch()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_guardar = QPushButton("Guardar")
        self.btn_guardar.clicked.connect(self._guardar)
        botones.addWidget(self.btn_cancelar)
        botones.addWidget(self.btn_guardar)
        layout.addLayout(botones)

    def _guardar(self):
        tema_elegido = self.combo_tema.currentData()
        try:
            with get_session() as session:
                set_setting(session, "tema_activo", tema_elegido)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el tema:\n{e}")
            return
        QMessageBox.information(
            self, "Tema guardado",
            f"Tema '{NOMBRES_TEMAS[tema_elegido]}' guardado. "
            "Reiniciá la aplicación para ver el cambio completo."
        )
        self.accept()
