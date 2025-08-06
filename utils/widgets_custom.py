from PySide6.QtWidgets import QComboBox, QDateEdit, QDoubleSpinBox

class ComboBoxSinScroll(QComboBox):
    def wheelEvent(self, event):
        event.ignore()

class DateEditSinScroll(QDateEdit):
    def wheelEvent(self, event):
        event.ignore()

class DoubleSpinBoxSinScroll(QDoubleSpinBox):
    def wheelEvent(self, event):
        event.ignore()
