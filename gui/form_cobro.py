from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QTextEdit,
    QDoubleSpinBox, QInputDialog, QMessageBox, QHBoxLayout, QDialog,
    QFormLayout, QDialogButtonBox
)
from PySide6.QtCore import QDate, Qt
from datetime import date
from dateutil.relativedelta import relativedelta

from database import session
from models import Venta, Cuota, Cobro
from utils.widgets_custom import ComboBoxSinScroll, DateEditSinScroll, DoubleSpinBoxSinScroll


class DialogCuotaMora(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nueva Cuota por Mora")
        self.setMinimumWidth(300)

        layout = QFormLayout(self)
        self.monto_input = DoubleSpinBoxSinScroll()
        self.monto_input.setPrefix("$ ")
        self.monto_input.setMaximum(999_999_999.99)
        self.monto_input.setButtonSymbols(QDoubleSpinBox.NoButtons)
        layout.addRow("Monto:", self.monto_input)

        self.fecha_input = DateEditSinScroll(QDate.currentDate())
        self.fecha_input.setCalendarPopup(True)
        layout.addRow("Fecha de Vencimiento:", self.fecha_input)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def get_data(self):
        return self.monto_input.value(), self.fecha_input.date().toPython()


class FormCobro(QWidget):
    def __init__(self, venta_id=None):
        super().__init__()
        self.venta_id = venta_id
        self.venta = session.query(Venta).get(self.venta_id) if self.venta_id else None

        if self.venta:
            cliente = self.venta.cliente
            self.setWindowTitle(f"Gestión de Cobros – Venta #{self.venta.id} – {cliente.apellidos}, {cliente.nombres}")
        else:
            self.setWindowTitle("Gestión de Cobros")

        self.setMinimumSize(850, 700)
        layout = QVBoxLayout(self)

        if not self.venta_id:
            layout.addWidget(QLabel("Seleccionar Venta:"))
            self.ventas_combo = ComboBoxSinScroll()
            self.ventas = session.query(Venta).filter_by(anulada=False).all()
            for v in self.ventas:
                label = f"Venta #{v.id} – {v.cliente.apellidos}, {v.cliente.nombres}"
                self.ventas_combo.addItem(label, userData=v.id)
            self.ventas_combo.currentIndexChanged.connect(self.cargar_cuotas)
            layout.addWidget(self.ventas_combo)
        else:
            self.ventas_combo = None
            label = QLabel(f"Venta #{self.venta.id} – {self.venta.cliente.apellidos}, {self.venta.cliente.nombres}")
            label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333; margin-bottom: 10px;")
            layout.addWidget(label)

        self.tabla_cuotas = QTableWidget()
        self.tabla_cuotas.setMinimumHeight(300)
        self.tabla_cuotas.setColumnCount(7)
        self.tabla_cuotas.setHorizontalHeaderLabels([
            "N°", "Vencimiento", "Fecha Pago", "Monto Original", "Pagado", "Estado", "Concepto"
        ])
        self.tabla_cuotas.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tabla_cuotas)

        layout.addWidget(QLabel("Fecha de Cobro:"))
        self.fecha_input = DateEditSinScroll(QDate.currentDate())
        self.fecha_input.setCalendarPopup(True)
        layout.addWidget(self.fecha_input)

        layout.addWidget(QLabel("Monto Abonado:"))
        self.monto_input = DoubleSpinBoxSinScroll()
        self.monto_input.setPrefix("$ ")
        self.monto_input.setMaximum(999_999_999.99)
        self.monto_input.setButtonSymbols(QDoubleSpinBox.NoButtons)
        layout.addWidget(self.monto_input)

        layout.addWidget(QLabel("Tipo de Cobro:"))
        self.tipo_combo = ComboBoxSinScroll()
        self.tipo_combo.addItems(["entrega", "pago_total", "refinanciacion"])
        layout.addWidget(self.tipo_combo)

        layout.addWidget(QLabel("Observaciones:"))
        self.observaciones_input = QTextEdit()
        self.observaciones_input.setFixedHeight(50)
        layout.addWidget(self.observaciones_input)

        botones_layout = QHBoxLayout()
        self.btn_guardar = QPushButton("Registrar Cobro")
        self.btn_guardar.clicked.connect(self.registrar_cobro)
        self.btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        botones_layout.addWidget(self.btn_guardar)

        self.btn_finalizar = QPushButton("Finalizar Venta")
        self.btn_finalizar.setEnabled(False)
        self.btn_finalizar.clicked.connect(self.finalizar_venta)
        self.btn_finalizar.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7E7E7E;
            }
        """)
        botones_layout.addWidget(self.btn_finalizar)

        self.btn_mora = QPushButton("Agregar Cuota por Mora")
        self.btn_mora.setEnabled(False)
        self.btn_mora.clicked.connect(self.agregar_cuota_mora)
        self.btn_mora.setStyleSheet("""
            QPushButton {
                background-color: #FFEB3B;
                color: black;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FDD835;
            }
        """)
        botones_layout.addWidget(self.btn_mora)

        layout.addLayout(botones_layout)
        self.cargar_cuotas()

    def cargar_cuotas(self):
        venta_id = self.venta_id or (self.ventas_combo.currentData() if self.ventas_combo else None)
        if not venta_id:
            return

        self.venta = session.query(Venta).get(venta_id)
        if not self.venta:
            return

        self.cuotas = session.query(Cuota)\
            .filter_by(venta_id=self.venta.id)\
            .order_by(Cuota.numero)\
            .all()

        self.tabla_cuotas.setRowCount(len(self.cuotas))
        for i, c in enumerate(self.cuotas):
            if c.pagada:
                pagada_con_mora = c.fecha_pago and c.fecha_pago > c.fecha_vencimiento
                estado = "Con Mora" if pagada_con_mora else "Pagada"
                color  = Qt.yellow     if pagada_con_mora else Qt.green
            elif c.fecha_vencimiento < date.today():
                estado = "Vencida";  color = Qt.red
            else:
                estado = "Pendiente"; color = Qt.white

            self.tabla_cuotas.setItem(i, 0, QTableWidgetItem(str(c.numero)))
            self.tabla_cuotas.setItem(i, 1, QTableWidgetItem(c.fecha_vencimiento.strftime("%d/%m/%Y")))
            self.tabla_cuotas.setItem(i, 2, QTableWidgetItem(c.fecha_pago.strftime("%d/%m/%Y") if c.fecha_pago else ""))
            self.tabla_cuotas.setItem(i, 3, QTableWidgetItem(f"$ {c.monto_original:.2f}"))
            self.tabla_cuotas.setItem(i, 4, QTableWidgetItem(f"$ {c.monto_pagado:.2f}"))
            item_estado = QTableWidgetItem(estado)
            item_estado.setBackground(color)
            self.tabla_cuotas.setItem(i, 5, item_estado)
            self.tabla_cuotas.setItem(i, 6, QTableWidgetItem(c.concepto or ""))

        cuotas_normales = [c for c in self.cuotas if not getattr(c, 'refinanciada', False)]

        todas_pagadas   = all(c.pagada for c in self.cuotas)
        mora_normales   = any(
            c.pagada and c.fecha_pago and c.fecha_pago > c.fecha_vencimiento
            for c in cuotas_normales
        )

        self.btn_guardar.setEnabled(True)
        self.btn_finalizar.setEnabled(todas_pagadas)
        self.btn_mora.setEnabled(mora_normales)

        if self.venta.finalizada and not self.ventas_combo:
            self._deshabilitar_formulario_finalizado()

    def registrar_cobro(self):
        monto = self.monto_input.value()
        if monto <= 0:
            QMessageBox.warning(self, "Error", "Ingresá un monto mayor a $0.")
            return

        cobro = Cobro(
            venta_id=self.venta.id,
            fecha=self.fecha_input.date().toPython(),
            monto=monto,
            tipo=self.tipo_combo.currentText(),
            observaciones=self.observaciones_input.toPlainText()
        )
        session.add(cobro)

        restante = monto
        for cuota in self.cuotas:
            if cuota.pagada:
                continue
            saldo = cuota.monto_original - cuota.monto_pagado
            pago = min(saldo, restante)
            cuota.monto_pagado += pago
            restante -= pago
            if cuota.monto_pagado >= cuota.monto_original:
                cuota.pagada = True
                cuota.fecha_pago = self.fecha_input.date().toPython()
            if restante <= 0:
                break

        session.commit()
        QMessageBox.information(self, "Éxito", "Cobro registrado correctamente.")
        self.cargar_cuotas()

    def finalizar_venta(self):
        cuotas_normales = [c for c in self.cuotas if not getattr(c, 'refinanciada', False)]
        cuotas_mora     = [c for c in self.cuotas if getattr(c, 'refinanciada', False)]

        if any(not c.pagada for c in self.cuotas):
            QMessageBox.warning(self, "No se puede finalizar",
                                "Existen cuotas impagas. Deben estar todas pagadas antes de finalizar.")
            return

        mora_normal = any(c.pagada and c.fecha_pago and c.fecha_pago > c.fecha_vencimiento
                          for c in cuotas_normales)
        mora_en_mora = any(c.pagada and c.fecha_pago and c.fecha_pago > c.fecha_vencimiento
                           for c in cuotas_mora)

        if mora_normal or mora_en_mora:
            mensaje = ("Se detectaron cuotas pagadas fuera de término.\n"
                       "¿Deseás generar cuotas por mora antes de finalizar?")
            resp = QMessageBox.question(self, "Cuotas con Mora", mensaje,
                                        QMessageBox.Yes | QMessageBox.No)
            if resp == QMessageBox.Yes:
                return
            if mora_en_mora:
                mensaje = (
                    "Las cuotas por mora también fueron pagadas fuera de término.\n"
                    "¿Deseás generar nuevas cuotas por mora?"
                )
                resp = QMessageBox.question(self, "Mora en mora", mensaje,
                                            QMessageBox.Yes | QMessageBox.No)
                if resp == QMessageBox.Yes:
                    return  # No finaliza, el usuario quiere seguir generando


        self.venta.finalizada = True
        session.commit()

        opciones = ["Excelente", "Bueno", "Riesgoso", "Incobrable"]
        calif, ok = QInputDialog.getItem(self, "Calificación Cliente",
                                         "Seleccionar calificación final:", opciones, 0, False)
        if ok:
            self.venta.cliente.calificacion = calif

        if self.venta.garante:
            calif_g, ok_g = QInputDialog.getItem(self, "Calificación Garante",
                                                 "Seleccionar calificación del garante:", opciones, 0, False)
            if ok_g:
                self.venta.garante.calificacion = calif_g

        session.commit()
        QMessageBox.information(self, "Finalizado", "La venta fue finalizada correctamente.")
        self.close()

    def agregar_cuota_mora(self):
        dialogo = DialogCuotaMora()
        if dialogo.exec() == QDialog.Accepted:
            monto, fecha = dialogo.get_data()
            if monto <= 0:
                QMessageBox.warning(self, "Error", "El monto debe ser mayor a cero.")
                return

            nueva_cuota = Cuota(
                venta_id=self.venta.id,
                numero=len(self.cuotas) + 1,
                fecha_vencimiento=fecha,
                monto_original=monto,
                monto_pagado=0.0,
                pagada=False,
                refinanciada=True,
                concepto="Cuota por mora e intereses"
            )
            session.add(nueva_cuota)
            session.commit()
            QMessageBox.information(self, "Éxito", "Cuota por mora generada correctamente.")
            self.cargar_cuotas()
            self.btn_finalizar.setEnabled(False)

    def _deshabilitar_formulario_finalizado(self):
        self.fecha_input.setDisabled(True)
        self.monto_input.setDisabled(True)
        self.tipo_combo.setDisabled(True)
        self.observaciones_input.setDisabled(True)
        self.btn_guardar.setDisabled(True)
        self.btn_finalizar.setDisabled(True)
        self.btn_mora.setDisabled(True)
