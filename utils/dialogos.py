from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt
from utils.estilos import PALETA, qss_boton_dialogo

_QSS_BTN = qss_boton_dialogo(PALETA)


def confirmar(parent, titulo: str, mensaje: str,
              default_no: bool = True, rich_text: bool = False) -> bool:
    """Confirmación Sí/No en español. Devuelve True si el usuario eligió Sí.
    default_no=True deja 'No' como botón por defecto (más seguro para borrados).
    rich_text=True habilita HTML en el mensaje."""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Question)
    msg.setWindowTitle(titulo)
    if rich_text:
        msg.setTextFormat(Qt.RichText)
    msg.setText(mensaje)
    btn_si = msg.addButton("Sí", QMessageBox.YesRole)
    btn_no = msg.addButton("No", QMessageBox.NoRole)
    btn_si.setStyleSheet(_QSS_BTN)
    btn_no.setStyleSheet(_QSS_BTN)
    msg.setDefaultButton(btn_no if default_no else btn_si)
    msg.exec()
    return msg.clickedButton() is btn_si
