from PySide6.QtWidgets import QComboBox, QDateEdit, QDoubleSpinBox
from datetime import datetime

class ComboBoxSinScroll(QComboBox):
    def wheelEvent(self, event):
        event.ignore()

class DateEditSinScroll(QDateEdit):
    def wheelEvent(self, event):
        event.ignore()

class DoubleSpinBoxSinScroll(QDoubleSpinBox):
    def wheelEvent(self, event):
        event.ignore()

def parsear_fecha(texto: str):
    """Convierte 'dd/mm/aaaa' a date. Devuelve None si la fecha no existe."""
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        return None
