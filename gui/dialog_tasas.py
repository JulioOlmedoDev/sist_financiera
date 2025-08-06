from PySide6.QtWidgets import QDialog, QFormLayout, QLabel, QDoubleSpinBox, QDialogButtonBox, QMessageBox
from PySide6.QtCore import Qt
from database import session
from models import Tasa

class DialogTasas(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configurar Tasas")
        layout = QFormLayout(self)
        self.spinboxes = {}
        for plan in ("mensual","semanal","diaria"):
            # cargas actuales o 0
            tasa = session.query(Tasa).filter_by(plan=plan).first()
            tem = tasa.tem if tasa else 0
            tna = tasa.tna if tasa else 0
            tea = tasa.tea if tasa else 0

            sb_tem = QDoubleSpinBox(); sb_tem.setSuffix(" %"); sb_tem.setValue(tem)
            sb_tna = QDoubleSpinBox(); sb_tna.setSuffix(" %"); sb_tna.setValue(tna)
            sb_tea = QDoubleSpinBox(); sb_tea.setSuffix(" %"); sb_tea.setValue(tea)

            layout.addRow(QLabel(f"{plan.capitalize()} TEM:"), sb_tem)
            layout.addRow(QLabel(f"{plan.capitalize()} TNA:"), sb_tna)
            layout.addRow(QLabel(f"{plan.capitalize()} TEA:"), sb_tea)
            self.spinboxes[plan] = (sb_tem, sb_tna, sb_tea)

        buttons = QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_save(self):
        try:
            for plan,(sb_tem,sb_tna,sb_tea) in self.spinboxes.items():
                tasa = session.query(Tasa).filter_by(plan=plan).first()
                if not tasa:
                    tasa = Tasa(plan=plan, tem=sb_tem.value(), tna=sb_tna.value(), tea=sb_tea.value())
                    session.add(tasa)
                else:
                    tasa.tem = sb_tem.value()
                    tasa.tna = sb_tna.value()
                    tasa.tea = sb_tea.value()
            session.commit()
            QMessageBox.information(self, "Guardado", "Tasas actualizadas correctamente.")
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
