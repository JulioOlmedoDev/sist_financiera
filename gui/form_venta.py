from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QTextEdit, QPushButton, QVBoxLayout,
    QFormLayout, QSpinBox, QDoubleSpinBox, QHBoxLayout, QCompleter, QMessageBox,
    QCheckBox, QScrollArea, QFrame, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Signal, QDate, QTimer, Qt, QEvent
from database import session
from models import Cliente, Garante, Producto, Personal, Venta, Cuota, Tasa
from gui.form_cliente import FormCliente
from gui.form_garante import FormGarante
from datetime import date
from dateutil.relativedelta import relativedelta
import os, platform
from utils.widgets_custom import ComboBoxSinScroll, DateEditSinScroll
from utils.generador_contrato import generar_contrato_word, generar_contrato_excel
from utils.generador_pagare import generar_pagare_word, generar_pagare_excel

class FormVenta(QWidget):
    sale_saved = Signal()
    def __init__(self, venta_id=None):
        super().__init__()
        self.setWindowTitle("Crear Venta" if not venta_id else "Editar Venta")
        self.setGeometry(300, 200, 600, 800)
        self.venta_id = venta_id
        self.venta_existente = None

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_widget = QFrame()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(20,20,20,20)
        scroll_layout.setSpacing(15)
        scroll_area.setWidget(scroll_widget)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)

        title = QLabel("Registro de Venta" if not venta_id else "Edición de Venta")
        title.setStyleSheet("color:#4a148c; font-size:18px; font-weight:bold;")
        scroll_layout.addWidget(title)

        self.form = QFormLayout()
        self.form.setVerticalSpacing(12)
        self.form.setHorizontalSpacing(15)
        self.form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        scroll_layout.addLayout(self.form)

        label_style = "font-weight:bold; color:#7b1fa2;"
        input_style = """
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                border:1px solid #bdbdbd; border-radius:4px; padding:5px;
                background:white; min-height:25px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus,
            QSpinBox:focus, QDoubleSpinBox:focus {
                border:2px solid #9c27b0;
            }
        """
        self.setStyleSheet(input_style)

        lbl = QLabel("Cliente:"); lbl.setStyleSheet(label_style)
        self.cliente_input = QLineEdit()
        btns = QHBoxLayout()
        self.btn_nuevo_cliente = QPushButton("+")
        self.btn_nuevo_cliente.setStyleSheet("background:#9c27b0;color:white;")
        self.btn_refresh_cliente = QPushButton("🔄")
        self.btn_refresh_cliente.setStyleSheet("background:#673ab7;color:white;")
        self.btn_nuevo_cliente.clicked.connect(self.abrir_form_cliente)
        self.btn_refresh_cliente.clicked.connect(self.cargar_clientes)
        btns.addWidget(self.cliente_input)
        btns.addWidget(self.btn_nuevo_cliente)
        btns.addWidget(self.btn_refresh_cliente)
        self.form.addRow(lbl, btns)
        self.form.addRow("", QLabel("Buscar por apellido o DNI", styleSheet="font-size:11px;color:gray;"))

        lbl = QLabel("Garante:"); lbl.setStyleSheet(label_style)
        self.garante_input = QLineEdit()
        btns2 = QHBoxLayout()
        self.btn_nuevo_garante = QPushButton("+")
        self.btn_nuevo_garante.setStyleSheet(self.btn_nuevo_cliente.styleSheet())
        self.btn_refresh_garante = QPushButton("🔄")
        self.btn_refresh_garante.setStyleSheet(self.btn_refresh_cliente.styleSheet())
        self.btn_nuevo_garante.clicked.connect(self.abrir_form_garante)
        self.btn_refresh_garante.clicked.connect(self.cargar_garantes)
        btns2.addWidget(self.garante_input)
        btns2.addWidget(self.btn_nuevo_garante)
        btns2.addWidget(self.btn_refresh_garante)
        self.form.addRow(lbl, btns2)
        self.form.addRow("", QLabel("Buscar por apellido o DNI", styleSheet="font-size:11px;color:gray;"))

        lbl = QLabel("Producto:"); lbl.setStyleSheet(label_style)
        self.producto_combo = ComboBoxSinScroll()
        self.form.addRow(lbl, self.producto_combo)

        lbl = QLabel("Plan de Pago:"); lbl.setStyleSheet(label_style)
        self.plan_pago_combo = ComboBoxSinScroll()
        self.plan_pago_combo.addItems(["mensual","semanal","diaria"])
        self.form.addRow(lbl, self.plan_pago_combo)

        for text, attr in [("Coordinador:",'coordinador_combo'),
                           ("Vendedor:",  'vendedor_combo'),
                           ("Cobrador:",  'cobrador_combo')]:
            lbl = QLabel(text); lbl.setStyleSheet(label_style)
            setattr(self, attr, ComboBoxSinScroll())
            self.form.addRow(lbl, getattr(self, attr))

        for text, attr in [("Monto:",'monto_input'),
                           ("Cuotas:",'cuotas_input'),
                           ("Valor de Cuota:",'valor_cuota_input')]:
            lbl = QLabel(text); lbl.setStyleSheet(label_style)
            w = QDoubleSpinBox() if 'monto' in attr or 'valor' in attr else QSpinBox()
            if isinstance(w, QDoubleSpinBox):
                w.setPrefix("$ "); w.setMaximum(1e9)
            else:
                w.setMaximum(60)
            setattr(self, attr, w)
            w.installEventFilter(self)
            self.form.addRow(lbl, w)

        lbl = QLabel("T.E.M. (% mensual, incluye IVA):"); lbl.setStyleSheet(label_style)
        self.tem_input = QDoubleSpinBox(self)
        self.tem_input.setDecimals(3)
        self.tem_input.setRange(0, 100)
        self.tem_input.setSuffix(" %")
        self.tem_input.installEventFilter(self)
        self.tem_input.valueChanged.connect(self._tasas_changed)
        self.form.addRow(lbl, self.tem_input)

        lbl = QLabel("T.N.A. (% anual, incluye IVA):"); lbl.setStyleSheet(label_style)
        self.tna_input = QDoubleSpinBox(self)
        self.tna_input.setDecimals(3)
        self.tna_input.setRange(0, 300)
        self.tna_input.setSuffix(" %")
        self.tna_input.installEventFilter(self)
        self.tna_input.valueChanged.connect(self._tasas_changed)
        self.form.addRow(lbl, self.tna_input)

        lbl = QLabel("T.E.A. (% anual, incluye IVA):"); lbl.setStyleSheet(label_style)
        self.tea_input = QDoubleSpinBox(self)
        self.tea_input.setDecimals(3)
        self.tea_input.setRange(0, 300)
        self.tea_input.setSuffix(" %")
        self.tea_input.installEventFilter(self)
        self.tea_input.valueChanged.connect(self._tasas_changed)
        self.form.addRow(lbl, self.tea_input)

        self.plan_pago_combo.currentTextChanged.connect(self._on_plan_changed)
        self._on_plan_changed(self.plan_pago_combo.currentText())

        self.btn_calcular = QPushButton("Calcular PTF / Interés")
        self.btn_calcular.setStyleSheet("background:#9c27b0;color:white;")
        self.btn_calcular.clicked.connect(self.calcular_ptf)
        self.form.addRow("", self.btn_calcular)

        for text, attr in [("PTF:",'ptf_output'),("Interés (%):",'interes_output')]:
            lbl = QLabel(text); lbl.setStyleSheet(label_style)
            out = QLineEdit(readOnly=True)
            out.setStyleSheet("background:#f5f5f5;")
            setattr(self, attr, out)
            self.form.addRow(lbl, out)

        lbl = QLabel("Fecha de Primer Pago:"); lbl.setStyleSheet(label_style)
        self.fecha_inicio_input = DateEditSinScroll(QDate.currentDate())
        self.fecha_inicio_input.setCalendarPopup(True)
        self.form.addRow(lbl, self.fecha_inicio_input)

        lbl = QLabel("Domicilio de Cobro:"); lbl.setStyleSheet(label_style)
        self.domicilio_combo = ComboBoxSinScroll()
        self.domicilio_combo.addItems(["personal","laboral"])
        self.form.addRow(lbl, self.domicilio_combo)

        # — Anulación (si es edición) —
        if venta_id:
            self.chk_anulada = QCheckBox("Anular esta venta")
            self.form.addRow("", self.chk_anulada)
            self.motivo_anulacion_label = QLabel("Motivo de anulación:")
            self.motivo_anulacion_label.setStyleSheet(label_style)
            self.motivo_anulacion = QTextEdit()
            self.motivo_anulacion.setMaximumHeight(60)
            self.form.addRow(self.motivo_anulacion_label, self.motivo_anulacion)
            self.motivo_anulacion_label.setVisible(False)
            self.motivo_anulacion.setVisible(False)
            self.chk_anulada.toggled.connect(lambda chk: (
                self.motivo_anulacion.setVisible(chk),
                self.motivo_anulacion_label.setVisible(chk)
            ))

        # — Guardar —
        self.btn_guardar = QPushButton("Guardar Venta" if not venta_id else "Actualizar Venta")
        self.btn_guardar.setStyleSheet("background:#9c27b0;color:white;")
        self.btn_guardar.clicked.connect(self.guardar_venta)
        scroll_layout.addWidget(self.btn_guardar)

        # — Carga inicial de datos —
        self.cargar_clientes()
        self.cargar_garantes()
        self.cargar_productos()
        self.cargar_personal()

        if venta_id:
            self.cargar_venta_existente()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel and isinstance(obj, (QSpinBox, QDoubleSpinBox)):
            return True
        return super().eventFilter(obj, event)

    def _tasas_changed(self):
        tem = self.tem_input.value() / 100
        tna = self.tna_input.value() / 100
        tea = self.tea_input.value() / 100
        sender = self.sender()
        if sender == self.tem_input:
            self.tna_input.blockSignals(True)
            self.tea_input.blockSignals(True)
            self.tna_input.setValue(round(tem * 12 * 100, 3))
            self.tea_input.setValue(round(((1 + tem) ** 12 - 1) * 100, 3))
            self.tna_input.blockSignals(False)
            self.tea_input.blockSignals(False)
        elif sender == self.tna_input:
            tem_c = tna / 12
            self.tem_input.blockSignals(True)
            self.tea_input.blockSignals(True)
            self.tem_input.setValue(round(tem_c * 100, 3))
            self.tea_input.setValue(round(((1 + tem_c) ** 12 - 1) * 100, 3))
            self.tem_input.blockSignals(False)
            self.tea_input.blockSignals(False)
        else:
            tem_c = (1 + tea) ** (1/12) - 1
            self.tem_input.blockSignals(True)
            self.tna_input.blockSignals(True)
            self.tem_input.setValue(round(tem_c * 100, 3))
            self.tna_input.setValue(round(tem_c * 12 * 100, 3))
            self.tem_input.blockSignals(False)
            self.tna_input.blockSignals(False)

    def _on_plan_changed(self, plan: str):
        """Carga las tasas TEM/TNA/TEA según el plan seleccionado,
        bloqueando señales para que no se disparen auto-cálculos."""
        tasa = session.query(Tasa).filter_by(plan=plan).first()
        tem_val, tna_val, tea_val = (tasa.tem, tasa.tna, tasa.tea) if tasa else (0.0, 0.0, 0.0)

        for spin, val in (
            (self.tem_input, tem_val),
            (self.tna_input, tna_val),
            (self.tea_input, tea_val),
        ):
            spin.blockSignals(True)
            spin.setValue(val)
            spin.blockSignals(False)

    def cargar_venta_existente(self):
        venta = session.query(Venta).get(self.venta_id)
        if not venta:
            QMessageBox.critical(self, "Error", "Venta no encontrada.")
            return self.close()
        self.venta_existente = venta
        es_finalizada = venta.finalizada
        es_activa = not venta.anulada and not venta.finalizada

        # Rellenar campos
        self.cliente_input.setText(f"{venta.cliente.apellidos}, {venta.cliente.nombres} (DNI {venta.cliente.dni})")
        if venta.garante:
            self.garante_input.setText(f"{venta.garante.apellidos}, {venta.garante.nombres} (DNI {venta.garante.dni})")

        # Bloquear si ya finalizada o anulada
        campos_bloqueados = [
            self.cliente_input, self.garante_input, self.producto_combo, self.plan_pago_combo,
            self.coordinador_combo, self.vendedor_combo, self.cobrador_combo,
            self.monto_input, self.cuotas_input, self.valor_cuota_input,
            self.tem_input, self.tna_input, self.tea_input, self.fecha_inicio_input,
            self.domicilio_combo, self.btn_nuevo_cliente, self.btn_refresh_cliente,
            self.btn_nuevo_garante, self.btn_refresh_garante, self.btn_calcular
        ]
        if es_finalizada or not es_activa:
            for w in campos_bloqueados:
                w.setDisabled(True)

        # Anulación
        if hasattr(self, 'chk_anulada'):
            self.chk_anulada.setChecked(venta.anulada)
            self.chk_anulada.setEnabled(es_activa)
            self.motivo_anulacion.setText(venta.descripcion or "")
            self.motivo_anulacion.setEnabled(es_activa)
            self.motivo_anulacion_label.setEnabled(es_activa)

        # Valores previos
        for attr, combo in [
            ('coordinador_id', self.coordinador_combo),
            ('vendedor_id',    self.vendedor_combo),
            ('cobrador_id',    self.cobrador_combo)
        ]:
            val = getattr(venta, attr)
            if val:
                idx = combo.findData(val)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

        self.plan_pago_combo.setCurrentText(venta.plan_pago)
        self.monto_input.setValue(venta.monto or 0)
        self.cuotas_input.setValue(venta.num_cuotas or 0)
        self.valor_cuota_input.setValue(venta.valor_cuota or 0)
        self.ptf_output.setText(str(venta.ptf or ""))
        self.interes_output.setText(str(venta.interes or ""))
        self.tem_input.setValue(venta.tem or 0)
        self.tna_input.setValue(venta.tna or 0)
        self.tea_input.setValue(venta.tea or 0)
        idx = self.domicilio_combo.findText(venta.domicilio_cobro_preferido or "")
        if idx >= 0:
            self.domicilio_combo.setCurrentIndex(idx)
        if venta.fecha_inicio_pago:
            self.fecha_inicio_input.setDate(QDate(venta.fecha_inicio_pago))

        # --- Calificaciones si finalizada ---
        if venta.finalizada:
            # Cliente
            lbl_cli = QLabel("Calificación Cliente:")
            lbl_cli.setStyleSheet(self.label_style)
            self.calif_cliente_combo = ComboBoxSinScroll()
            self.calif_cliente_combo.addItems(["Excelente", "Bueno", "Riesgoso", "Incobrable"])
            if venta.cliente.calificacion:
                idx = self.calif_cliente_combo.findText(venta.cliente.calificacion)
                if idx >= 0:
                    self.calif_cliente_combo.setCurrentIndex(idx)
            self.form.addRow(lbl_cli, self.calif_cliente_combo)

            # Garante
            if venta.garante:
                lbl_gar = QLabel("Calificación Garante:")
                lbl_gar.setStyleSheet(self.label_style)
                self.calif_garante_combo = ComboBoxSinScroll()
                self.calif_garante_combo.addItems(["Excelente", "Bueno", "Riesgoso", "Incobrable"])
                if venta.garante.calificacion:
                    idx2 = self.calif_garante_combo.findText(venta.garante.calificacion)
                    if idx2 >= 0:
                        self.calif_garante_combo.setCurrentIndex(idx2)
                self.form.addRow(lbl_gar, self.calif_garante_combo)

    def cargar_clientes(self):
        self.clientes = session.query(Cliente).all()
        lista = [f"{c.apellidos}, {c.nombres} (DNI {c.dni})" for c in self.clientes]
        comp = QCompleter(lista); comp.setCaseSensitivity(Qt.CaseInsensitive)
        self.cliente_input.setCompleter(comp)

    def cargar_garantes(self):
        self.garantes = session.query(Garante).all()
        lista = [f"{g.apellidos}, {g.nombres} (DNI {g.dni})" for g in self.garantes]
        comp = QCompleter(lista); comp.setCaseSensitivity(Qt.CaseInsensitive)
        self.garante_input.setCompleter(comp)

    def cargar_productos(self):
        self.producto_combo.clear()
        for p in session.query(Producto).all():
            self.producto_combo.addItem(p.nombre, userData=p.id)

    def cargar_personal(self):
        for tipo, combo in [("Coordinador", self.coordinador_combo),
                            ("Vendedor",    self.vendedor_combo),
                            ("Cobrador",    self.cobrador_combo)]:
            combo.clear()
            for per in session.query(Personal).filter_by(tipo=tipo).all():
                combo.addItem(per.nombres, userData=per.id)

    def calcular_ptf(self):
        cuotas = self.cuotas_input.value()
        val    = self.valor_cuota_input.value()
        ptf    = cuotas * val
        self.ptf_output.setText(f"{ptf:.2f}")
        monto  = self.monto_input.value()
        interes= ((ptf - monto) / monto * 100) if monto > 0 else 0
        self.interes_output.setText(f"{interes:.2f}")

    def abrir_form_cliente(self):
        self.nuevo_cliente = FormCliente()
        self.nuevo_cliente.showMaximized()
        self.nuevo_cliente.destroyed.connect(lambda: QTimer.singleShot(100, self.cargar_clientes))

    def abrir_form_garante(self):
        self.nuevo_garante = FormGarante()
        self.nuevo_garante.showMaximized()
        self.nuevo_garante.destroyed.connect(lambda: QTimer.singleShot(100, self.cargar_garantes))

    def guardar_venta(self):
        try:
            # --- Validación de cliente ---
            texto = self.cliente_input.text()
            cliente = next((c for c in self.clientes
                            if f"{c.apellidos}, {c.nombres} (DNI {c.dni})" == texto), None)
            if not cliente:
                QMessageBox.warning(self, "Error", "Seleccioná un cliente válido.")
                return

            # --- Validación de garante (opcional) ---
            texto2 = self.garante_input.text()
            garante = next((g for g in self.garantes
                            if f"{g.apellidos}, {g.nombres} (DNI {g.dni})" == texto2), None)

            # --- Actualizar venta existente ---
            if self.venta_id and self.venta_existente:
                venta = self.venta_existente

                if venta.finalizada:
                    # Solo actualizar calificaciones
                    if hasattr(self, 'calif_cliente_combo'):
                        venta.cliente.calificacion = self.calif_cliente_combo.currentText()
                    if venta.garante and hasattr(self, 'calif_garante_combo'):
                        venta.garante.calificacion = self.calif_garante_combo.currentText()
                    session.commit()
                    QMessageBox.information(self, "Actualizado", "Calificaciones actualizadas.")
                    self.close()
                    return

                if not venta.anulada:
                    # Marcar anulación
                    venta.anulada = self.chk_anulada.isChecked()
                    venta.descripcion = self.motivo_anulacion.toPlainText() if venta.anulada else None
                    session.commit()
                    QMessageBox.information(self, "Actualizado", "Venta actualizada correctamente.")
                    self.close()
                    return

                QMessageBox.warning(self, "Restringido", "No se pueden modificar ventas anuladas.")
                return

            # --- Crear nueva venta ---
            venta = Venta(
                cliente_id=cliente.id,
                garante_id=(garante.id if garante else None),
                producto_id=self.producto_combo.currentData(),
                plan_pago=self.plan_pago_combo.currentText(),
                coordinador_id=self.coordinador_combo.currentData(),
                vendedor_id=self.vendedor_combo.currentData(),
                cobrador_id=self.cobrador_combo.currentData(),
                fecha=date.today(),
                fecha_inicio_pago=self.fecha_inicio_input.date().toPython(),
                monto=self.monto_input.value(),
                num_cuotas=self.cuotas_input.value(),
                valor_cuota=self.valor_cuota_input.value(),
                ptf=float(self.ptf_output.text() or 0),
                interes=float(self.interes_output.text() or 0),
                tem=self.tem_input.value(),
                tna=self.tna_input.value(),
                tea=self.tea_input.value(),
                domicilio_cobro_preferido=self.domicilio_combo.currentText(),
                anulada=False,
                descripcion=None
            )
            session.add(venta)
            session.commit()

            # --- Generar cuotas ---
            freq = venta.plan_pago
            inicio = venta.fecha_inicio_pago or venta.fecha
            for i in range(venta.num_cuotas):
                if freq == "mensual":
                    fv = inicio + relativedelta(months=i)
                elif freq == "semanal":
                    fv = inicio + relativedelta(weeks=i)
                else:
                    fv = inicio + relativedelta(days=i)
                cuota = Cuota(
                    venta_id=venta.id,
                    numero=i + 1,
                    fecha_vencimiento=fv,
                    monto_original=venta.valor_cuota,
                    monto_pagado=0.0,
                    pagada=False
                )
                session.add(cuota)
            session.commit()

            # --- Diálogo de generación y apertura ---
            respuesta = QMessageBox.question(
                self,
                "Venta registrada",
                "¡La venta fue registrada correctamente!\n\n¿Deseás generar y abrir los documentos ahora?",
                QMessageBox.Yes | QMessageBox.No
            )
            if respuesta == QMessageBox.Yes:
                dlg = QDialog(self)
                dlg.setWindowTitle("Seleccionar formato")
                dlg.setMinimumWidth(300)
                layout = QHBoxLayout(dlg)

                btn_word = QPushButton("Word")
                btn_excel = QPushButton("Excel")
                layout.addWidget(btn_word)
                layout.addWidget(btn_excel)

                btn_cancel = QDialogButtonBox(QDialogButtonBox.Close)
                btn_cancel.rejected.connect(dlg.reject)
                layout.addWidget(btn_cancel)

                # helper para abrir archivos cross-platform
                def open_file(path):
                    if os.name == 'nt':  # Windows
                        os.startfile(path)
                    else:
                        os.system(f"xdg-open '{path}'")

                def on_word():
                    # generar y abrir Word
                    path_c = generar_contrato_word(
                        venta, "plantillas/plantilla_contrato_mutuo.docx"
                    )
                    path_p = generar_pagare_word(
                        venta, "plantillas/plantilla_pagare_con_garante.docx"
                    )
                    for p in (path_c, path_p):
                        if os.path.exists(p):
                            open_file(p)
                    dlg.accept()

                def on_excel():
                    # generar y abrir Excel
                    path_c = generar_contrato_excel(venta)
                    path_p = generar_pagare_excel(venta)
                    for p in (path_c, path_p):
                        if os.path.exists(p):
                            open_file(p)
                    dlg.accept()

                btn_word.clicked.connect(on_word)
                btn_excel.clicked.connect(on_excel)
                dlg.exec()
                # cerramos ANTES de emitir la señal
                self.close()
                self.sale_saved.emit()
            else:
                # también cerramos y emitimos
                self.close()
                self.sale_saved.emit()

        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo guardar la venta:\n{e}")
