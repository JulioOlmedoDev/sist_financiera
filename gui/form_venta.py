from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QTextEdit, QPushButton, QVBoxLayout,
    QFormLayout, QSpinBox, QDoubleSpinBox, QHBoxLayout, QCompleter, QMessageBox,
    QCheckBox, QScrollArea, QFrame, QDialog, QDialogButtonBox, QToolTip, QSizePolicy
)
from PySide6.QtGui import QCursor
from PySide6.QtCore import Signal, QDate, QTimer, Qt, QEvent
from database import session
from models import Cliente, Garante, Producto, Personal, Venta, Cuota, Tasa, Cobro
from gui.form_cliente import FormCliente
from gui.form_garante import FormGarante
from datetime import date
from dateutil.relativedelta import relativedelta
import os
from utils.widgets_custom import ComboBoxSinScroll, DateEditSinScroll
from utils.generador_contrato import generar_contrato_word, generar_contrato_excel
from utils.generador_pagare import generar_pagare_word, generar_pagare_excel
from sqlalchemy import desc


class ConfirmarVentaDialog(QDialog):
    def __init__(self, parent, items):
        super().__init__(parent)
        self.setWindowTitle("Revisar datos de la venta")
        self.setModal(True)

        lay = QVBoxLayout(self)
        form = QFormLayout()
        for label, value in items:
            form.addRow(QLabel(label + ":"), QLabel(value))
        lay.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_no = QPushButton("No")
        self.btn_si = QPushButton("Sí")
        self.btn_no.setDefault(True)  # por seguridad, default "No"
        self.btn_no.setAutoDefault(True)
        self.btn_no.clicked.connect(self.reject)
        self.btn_si.clicked.connect(self.accept)
        btns.addWidget(self.btn_no)
        btns.addWidget(self.btn_si)
        lay.addLayout(btns)

        self.resize(520, self.sizeHint().height())


class FormVenta(QWidget):
    sale_saved = Signal()

    def __init__(self, venta_id=None, usuario_actual=None):
        super().__init__()
        self.usuario_actual = usuario_actual
        self.setWindowTitle("Crear Venta" if not venta_id else "Editar Venta")
        self.setGeometry(300, 200, 600, 800)
        self.venta_id = venta_id
        self.venta_existente = None
        self._tooltip_buttons = []
        self._ptf_calculado = False  # se exige calcular antes de guardar

        # --- Scroll container ---
        scroll_area = QScrollArea(self)
        self.scroll_area = scroll_area
        scroll_area.setWidgetResizable(True)
        scroll_widget = QFrame()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(20, 20, 20, 20)
        scroll_layout.setSpacing(15)
        scroll_area.setWidget(scroll_widget)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)

        title = QLabel("Registro de Venta" if not venta_id else "Edición de Venta")
        title.setStyleSheet("color:#4a148c; font-size:18px; font-weight:bold;")
        scroll_layout.addWidget(title)

        # --- Form ---
        self.form = QFormLayout()
        self.form.setVerticalSpacing(12)
        self.form.setHorizontalSpacing(15)
        self.form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        scroll_layout.addLayout(self.form)

        label_style = "font-weight:bold; color:#7b1fa2;"
        self.label_style = label_style

        # Estilos
        self.setStyleSheet("""
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                border:1px solid #bdbdbd; border-radius:4px; padding:5px;
                background:white; min-height:25px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus,
            QSpinBox:focus, QDoubleSpinBox:focus {
                border:2px solid #9c27b0;
            }
            QToolTip {
                background-color: #4a148c;
                color: white;
                border: 1px solid #bdbdbd;
                padding: 6px;
                border-radius: 4px;
            }
        """)

        # --- Cliente (requerido) ---
        lbl = QLabel("Cliente:"); lbl.setStyleSheet(label_style)
        self.cliente_input = QLineEdit()
        btns = QHBoxLayout()
        self.btn_nuevo_cliente = QPushButton("+")
        self.btn_nuevo_cliente.setStyleSheet("background:#9c27b0;color:white;")
        self.btn_nuevo_cliente.setToolTip("Agregar un nuevo cliente")

        self.btn_refresh_cliente = QPushButton("🔄")
        self.btn_refresh_cliente.setStyleSheet("background:#673ab7;color:white;")
        self.btn_refresh_cliente.setToolTip("Actualizar listado de clientes")

        self.btn_nuevo_cliente.clicked.connect(self.abrir_form_cliente)
        self.btn_refresh_cliente.clicked.connect(self.cargar_clientes)
        btns.addWidget(self.cliente_input)
        btns.addWidget(self.btn_nuevo_cliente)
        btns.addWidget(self.btn_refresh_cliente)
        self.form.addRow(lbl, btns)
        self.form.addRow("", QLabel("Buscar por apellido o DNI", styleSheet="font-size:11px;color:gray;"))

        # --- Garante (opcional) ---
        lbl = QLabel("Garante:"); lbl.setStyleSheet(label_style)
        self.garante_input = QLineEdit()
        btns2 = QHBoxLayout()
        self.btn_nuevo_garante = QPushButton("+")
        self.btn_nuevo_garante.setStyleSheet(self.btn_nuevo_cliente.styleSheet())
        self.btn_nuevo_garante.setToolTip("Agregar un nuevo garante")

        self.btn_refresh_garante = QPushButton("🔄")
        self.btn_refresh_garante.setStyleSheet(self.btn_refresh_cliente.styleSheet())
        self.btn_refresh_garante.setToolTip("Actualizar listado de garantes")

        self.btn_nuevo_garante.clicked.connect(self.abrir_form_garante)
        self.btn_refresh_garante.clicked.connect(self.cargar_garantes)
        btns2.addWidget(self.garante_input)
        btns2.addWidget(self.btn_nuevo_garante)
        btns2.addWidget(self.btn_refresh_garante)
        self.form.addRow(lbl, btns2)
        self.form.addRow("", QLabel("Buscar por apellido o DNI", styleSheet="font-size:11px;color:gray;"))

        # --- Producto / Plan (requeridos) ---
        lbl = QLabel("Producto:"); lbl.setStyleSheet(label_style)
        self.producto_combo = ComboBoxSinScroll()
        self.form.addRow(lbl, self.producto_combo)

        lbl = QLabel("Plan de Pago:"); lbl.setStyleSheet(label_style)
        self.plan_pago_combo = ComboBoxSinScroll()
        self.plan_pago_combo.addItems(["mensual", "semanal", "diaria"])
        self.form.addRow(lbl, self.plan_pago_combo)

        # --- Personal (requerido) ---
        for text, attr in [("Coordinador:", 'coordinador_combo'),
                           ("Vendedor:", 'vendedor_combo'),
                           ("Cobrador:", 'cobrador_combo')]:
            lbl = QLabel(text); lbl.setStyleSheet(label_style)
            setattr(self, attr, ComboBoxSinScroll())
            self.form.addRow(lbl, getattr(self, attr))

        # --- Monto / Cuotas / Valor (requeridos y > 0) ---
        for text, attr in [("Monto:", 'monto_input'),
                           ("Cuotas:", 'cuotas_input'),
                           ("Valor de Cuota:", 'valor_cuota_input')]:
            lbl = QLabel(text); lbl.setStyleSheet(label_style)
            w = QDoubleSpinBox() if 'monto' in attr or 'valor' in attr else QSpinBox()
            if isinstance(w, QDoubleSpinBox):
                w.setPrefix("$ "); w.setMaximum(1e9); w.setDecimals(2)
            else:
                w.setMaximum(60)
            setattr(self, attr, w)
            w.installEventFilter(self)
            self.form.addRow(lbl, w)

        # --- Tasas (requeridas) ---
        lbl = QLabel("T.E.M. (% mensual, incluye IVA):"); lbl.setStyleSheet(label_style)
        self.tem_input = QDoubleSpinBox(self); self.tem_input.setDecimals(3)
        self.tem_input.setRange(0, 100); self.tem_input.setSuffix(" %")
        self.tem_input.installEventFilter(self)
        self.tem_input.valueChanged.connect(self._tasas_changed)
        self.form.addRow(lbl, self.tem_input)

        lbl = QLabel("T.N.A. (% anual, incluye IVA):"); lbl.setStyleSheet(label_style)
        self.tna_input = QDoubleSpinBox(self); self.tna_input.setDecimals(3)
        self.tna_input.setRange(0, 300); self.tna_input.setSuffix(" %")
        self.tna_input.installEventFilter(self)
        self.tna_input.valueChanged.connect(self._tasas_changed)
        self.form.addRow(lbl, self.tna_input)

        lbl = QLabel("T.E.A. (% anual, incluye IVA):"); lbl.setStyleSheet(label_style)
        self.tea_input = QDoubleSpinBox(self); self.tea_input.setDecimals(3)
        self.tea_input.setRange(0, 300); self.tea_input.setSuffix(" %")
        self.tea_input.installEventFilter(self)
        self.tea_input.valueChanged.connect(self._tasas_changed)
        self.form.addRow(lbl, self.tea_input)

        self.plan_pago_combo.currentTextChanged.connect(self._on_plan_changed)
        self._on_plan_changed(self.plan_pago_combo.currentText())

        # --- Calcular PTF / Interés (requerido antes de guardar) ---
        self.btn_calcular = QPushButton("Calcular PTF / Interés")
        self.btn_calcular.setStyleSheet("background:#9c27b0;color:white;")
        self.btn_calcular.setToolTip("Calcular Precio Total Financiado e interés")
        self.btn_calcular.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_calcular.clicked.connect(self.calcular_ptf)
        self.form.addRow("", self.btn_calcular)

        # --- Salidas ---
        for text, attr in [("PTF:", 'ptf_output'), ("Interés (%):", 'interes_output')]:
            lbl = QLabel(text); lbl.setStyleSheet(label_style)
            out = QLineEdit(readOnly=True); out.setStyleSheet("background:#f5f5f5;")
            setattr(self, attr, out)
            self.form.addRow(lbl, out)

        # --- Fecha inicio (requerida) y domicilio (requerido) ---
        lbl = QLabel("Fecha de Primer Pago:"); lbl.setStyleSheet(label_style)
        self.fecha_inicio_input = DateEditSinScroll(QDate.currentDate())
        self.fecha_inicio_input.setCalendarPopup(True)
        self.form.addRow(lbl, self.fecha_inicio_input)

        lbl = QLabel("Domicilio de Cobro:"); lbl.setStyleSheet(label_style)
        self.domicilio_combo = ComboBoxSinScroll(); self.domicilio_combo.addItems(["personal", "laboral"])
        self.form.addRow(lbl, self.domicilio_combo)

        # — Anulación (si es edición) —
        if venta_id:
            self.chk_anulada = QCheckBox("Anular esta venta")
            self.form.addRow("", self.chk_anulada)
            self.motivo_anulacion_label = QLabel("Motivo de anulación:"); self.motivo_anulacion_label.setStyleSheet(label_style)
            self.motivo_anulacion = QTextEdit(); self.motivo_anulacion.setMaximumHeight(60)
            self.form.addRow(self.motivo_anulacion_label, self.motivo_anulacion)
            self.motivo_anulacion_label.setVisible(False); self.motivo_anulacion.setVisible(False)
            self.chk_anulada.toggled.connect(lambda chk: (
                self.motivo_anulacion.setVisible(chk),
                self.motivo_anulacion_label.setVisible(chk)
            ))

        # — Guardar (misma columna, un poco más alto) —
        self.btn_guardar = QPushButton("Guardar Venta" if not venta_id else "Actualizar Venta")
        self.btn_guardar.setStyleSheet("background:#9c27b0;color:white;")
        self.btn_guardar.setToolTip("Guardar la venta")
        self.btn_guardar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_guardar.clicked.connect(self.guardar_venta)
        self.form.addRow("", self.btn_guardar)

        # Tooltips inmediatos
        self._setup_tooltips_instant([
            self.btn_nuevo_cliente, self.btn_refresh_cliente,
            self.btn_nuevo_garante, self.btn_refresh_garante,
            self.btn_calcular, self.btn_guardar
        ])

        # Invalida cálculo ante cambios
        self.monto_input.valueChanged.connect(self._ptf_dirty)
        self.cuotas_input.valueChanged.connect(self._ptf_dirty)
        self.valor_cuota_input.valueChanged.connect(self._ptf_dirty)
        self.tem_input.valueChanged.connect(self._ptf_dirty)
        self.tna_input.valueChanged.connect(self._ptf_dirty)
        self.tea_input.valueChanged.connect(self._ptf_dirty)
        self.plan_pago_combo.currentTextChanged.connect(self._ptf_dirty)
        
        self._lock_focus_to_tab_click()
        QTimer.singleShot(0, self._sync_button_sizes)

        # Carga inicial
        self.cargar_clientes()
        self.cargar_garantes()
        self.cargar_productos()
        self.cargar_personal()

        if venta_id:
            self.cargar_venta_existente()

    # --- Helpers de UI ---
    def _setup_tooltips_instant(self, buttons):
        self._tooltip_buttons = list(buttons)
        for b in self._tooltip_buttons:
            b.installEventFilter(self)

    def _sync_button_sizes(self):
        self.btn_calcular.adjustSize()
        self.btn_guardar.adjustSize()
        alto = self.btn_calcular.sizeHint().height() + 8
        self.btn_guardar.setMinimumHeight(alto)

    def _lock_focus_to_tab_click(self):
        """Evita que la rueda del mouse cambie el foco: quita WheelFocus de los inputs."""
        clases = (QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, ComboBoxSinScroll, DateEditSinScroll)
        for cls in clases:
            for w in self.findChildren(cls):
                if w.focusPolicy() == Qt.WheelFocus:
                    w.setFocusPolicy(Qt.StrongFocus)

    def _ptf_dirty(self, *args):
        self._ptf_calculado = False
        if hasattr(self, "ptf_output"): self.ptf_output.clear()
        if hasattr(self, "interes_output"): self.interes_output.clear()

    def _mostrar_confirmacion_guardado(self, texto_cliente, texto_garante):
        items = [
            ("Cliente", texto_cliente),
            ("Garante", texto_garante or "—"),
            ("Producto", self.producto_combo.currentText()),
            ("Plan de pago", self.plan_pago_combo.currentText()),
            ("Coordinador", self.coordinador_combo.currentText()),
            ("Vendedor", self.vendedor_combo.currentText()),
            ("Cobrador", self.cobrador_combo.currentText()),
            ("Monto", f"$ {self.monto_input.value():.2f}"),
            ("Cuotas", str(self.cuotas_input.value())),
            ("Valor de cuota", f"$ {self.valor_cuota_input.value():.2f}"),
            ("PTF", self.ptf_output.text() or "—"),
            ("Interés", (self.interes_output.text() + " %") if self.interes_output.text() else "—"),
            ("TEM/TNA/TEA", f"{self.tem_input.value():.3f}% / {self.tna_input.value():.3f}% / {self.tea_input.value():.3f}%"),
            ("Primer pago", self.fecha_inicio_input.date().toString("dd/MM/yyyy")),
            ("Domicilio", self.domicilio_combo.currentText()),
        ]
        dlg = ConfirmarVentaDialog(self, items)
        return dlg.exec() == QDialog.Accepted

    # --- Eventos / lógica ---
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel and isinstance(
            obj, (
                QSpinBox, QDoubleSpinBox,
                ComboBoxSinScroll, DateEditSinScroll,
                QLineEdit, QTextEdit
            )
        ):
            # Redirigimos la rueda al scroll principal
            from PySide6.QtWidgets import QApplication
            if hasattr(self, "scroll_area") and self.scroll_area is not None:
                QApplication.sendEvent(self.scroll_area.viewport(), event)
            return True
        # Si la rueda ocurre sobre el popup del QCompleter, también la pasamos al scroll
        from PySide6.QtWidgets import QAbstractItemView
        if event.type() == QEvent.Wheel and isinstance(obj, QAbstractItemView):
            from PySide6.QtWidgets import QApplication
            if hasattr(self, "scroll_area") and self.scroll_area is not None:
                QApplication.sendEvent(self.scroll_area.viewport(), event)
            return True

        if event.type() == QEvent.Enter and obj in getattr(self, "_tooltip_buttons", []):
            text = obj.toolTip() or ""
            if text.strip():
                QToolTip.showText(QCursor.pos(), text, obj)
            return False
        if event.type() == QEvent.Leave and obj in getattr(self, "_tooltip_buttons", []):
            QToolTip.hideText()
            return False
        return super().eventFilter(obj, event)

    def _tasas_changed(self):
        tem = self.tem_input.value() / 100
        tna = self.tna_input.value() / 100
        tea = self.tea_input.value() / 100
        sender = self.sender()
        if sender == self.tem_input:
            self.tna_input.blockSignals(True); self.tea_input.blockSignals(True)
            self.tna_input.setValue(round(tem * 12 * 100, 3))
            self.tea_input.setValue(round(((1 + tem) ** 12 - 1) * 100, 3))
            self.tna_input.blockSignals(False); self.tea_input.blockSignals(False)
        elif sender == self.tna_input:
            tem_c = tna / 12
            self.tem_input.blockSignals(True); self.tea_input.blockSignals(True)
            self.tem_input.setValue(round(tem_c * 100, 3))
            self.tea_input.setValue(round(((1 + tem_c) ** 12 - 1) * 100, 3))
            self.tem_input.blockSignals(False); self.tea_input.blockSignals(False)
        else:
            tem_c = (1 + tea) ** (1 / 12) - 1
            self.tem_input.blockSignals(True); self.tna_input.blockSignals(True)
            self.tem_input.setValue(round(tem_c * 100, 3))
            self.tna_input.setValue(round(tem_c * 12 * 100, 3))
            self.tem_input.blockSignals(False); self.tna_input.blockSignals(False)

    def _on_plan_changed(self, plan: str):
        tasa = session.query(Tasa).filter_by(plan=plan).first()
        tem_val, tna_val, tea_val = (tasa.tem, tasa.tna, tasa.tea) if tasa else (0.0, 0.0, 0.0)
        for spin, val in ((self.tem_input, tem_val), (self.tna_input, tna_val), (self.tea_input, tea_val)):
            spin.blockSignals(True); spin.setValue(val); spin.blockSignals(False)

    # --- Abrir formularios ---
    def abrir_form_cliente(self):
        self.nuevo_cliente = FormCliente()
        self.nuevo_cliente.showMaximized()
        self.nuevo_cliente.destroyed.connect(lambda: QTimer.singleShot(100, self.cargar_clientes))

    def abrir_form_garante(self):
        self.nuevo_garante = FormGarante()
        self.nuevo_garante.showMaximized()
        self.nuevo_garante.destroyed.connect(lambda: QTimer.singleShot(100, self.cargar_garantes))

    # --- Carga de edición ---
    def cargar_venta_existente(self):
        venta = session.query(Venta).get(self.venta_id)
        if not venta:
            QMessageBox.critical(self, "Error", "Venta no encontrada.")
            return self.close()

        self.venta_existente = venta
        es_finalizada = venta.finalizada
        es_activa = (not venta.anulada) and (not venta.finalizada)

        # --- Datos base ---
        self.cliente_input.setText(f"{venta.cliente.apellidos}, {venta.cliente.nombres} (DNI {venta.cliente.dni})")
        if venta.garante:
            self.garante_input.setText(f"{venta.garante.apellidos}, {venta.garante.nombres} (DNI {venta.garante.dni})")

        campos_bloqueados = [
            self.cliente_input, self.garante_input, self.producto_combo, self.plan_pago_combo,
            self.coordinador_combo, self.vendedor_combo, self.cobrador_combo,
            self.monto_input, self.cuotas_input, self.valor_cuota_input,
            self.tem_input, self.tna_input, self.tea_input, self.fecha_inicio_input,
            self.domicilio_combo, self.btn_nuevo_cliente, self.btn_refresh_cliente,
            self.btn_nuevo_garante, self.btn_refresh_garante, self.btn_calcular
        ]

        # 🔒 Bloqueo/permiso según estado
        if es_finalizada:
            # Finalizada: todo bloqueado (no se puede anular). Luego se agregan combos de calificación.
            for w in campos_bloqueados:
                w.setDisabled(True)
            if hasattr(self, 'chk_anulada'):
                self.chk_anulada.setChecked(False)
                self.chk_anulada.setDisabled(True)
                self.motivo_anulacion.setText("")
                self.motivo_anulacion.setDisabled(True)
                self.motivo_anulacion_label.setDisabled(True)
                self.motivo_anulacion.setVisible(False)
                self.motivo_anulacion_label.setVisible(False)

        elif es_activa:
            # Activa: desde Editar solo permitir ANULAR (check + motivo). Todo lo demás bloqueado.
            for w in campos_bloqueados:
                w.setDisabled(True)
            if hasattr(self, 'chk_anulada'):
                self.chk_anulada.setEnabled(True)
                self.chk_anulada.setChecked(False)  # activa ⇒ por defecto no anulada
                self.motivo_anulacion.setText(venta.descripcion or "")
                # Motivo visible/habilitado solo si el check está tildado
                mostrar = self.chk_anulada.isChecked()
                self.motivo_anulacion.setVisible(mostrar)
                self.motivo_anulacion_label.setVisible(mostrar)
                self.motivo_anulacion.setEnabled(mostrar)
                self.motivo_anulacion_label.setEnabled(mostrar)
                # Reaccionar al toggle
                self.chk_anulada.toggled.connect(lambda v: (
                    self.motivo_anulacion.setVisible(v),
                    self.motivo_anulacion_label.setVisible(v),
                    self.motivo_anulacion.setEnabled(v),
                    self.motivo_anulacion_label.setEnabled(v)
                ))

        else:
            # Anulada: no editable (mostrar motivo como referencia)
            for w in campos_bloqueados:
                w.setDisabled(True)
            if hasattr(self, 'chk_anulada'):
                self.chk_anulada.setChecked(True)
                self.chk_anulada.setDisabled(True)
                self.motivo_anulacion.setText(venta.descripcion or "")
                self.motivo_anulacion.setDisabled(True)
                self.motivo_anulacion_label.setDisabled(True)
                self.motivo_anulacion.setVisible(True)
                self.motivo_anulacion_label.setVisible(True)

        for attr, combo in [('coordinador_id', self.coordinador_combo),
                            ('vendedor_id', self.vendedor_combo),
                            ('cobrador_id', self.cobrador_combo)]:
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

        # --- Trazabilidad (siempre visible) ---
        if venta.creada_por:
            lbl_cp = QLabel("Creada por:"); lbl_cp.setStyleSheet(self.label_style)
            self.form.addRow(lbl_cp, QLabel(venta.creada_por.nombre))

        ultimo_cobro = (
            session.query(Cobro)
            .filter_by(venta_id=venta.id)
            .order_by(desc(Cobro.id))
            .first()
        )
        if ultimo_cobro and ultimo_cobro.registrado_por:
            lbl_uc = QLabel("Último cobro cargado por:"); lbl_uc.setStyleSheet(self.label_style)
            self.form.addRow(lbl_uc, QLabel(ultimo_cobro.registrado_por.nombre))

        # --- Controles extra si está finalizada ---
        if venta.finalizada:
            lbl_cli = QLabel("Calificación Cliente:"); lbl_cli.setStyleSheet(self.label_style)
            self.calif_cliente_combo = ComboBoxSinScroll()
            self.calif_cliente_combo.addItems(["Excelente", "Bueno", "Riesgoso", "Incobrable"])
            if venta.cliente.calificacion:
                idx = self.calif_cliente_combo.findText(venta.cliente.calificacion)
                if idx >= 0:
                    self.calif_cliente_combo.setCurrentIndex(idx)
            self.form.addRow(lbl_cli, self.calif_cliente_combo)

            if venta.garante:
                lbl_gar = QLabel("Calificación Garante:"); lbl_gar.setStyleSheet(self.label_style)
                self.calif_garante_combo = ComboBoxSinScroll()
                self.calif_garante_combo.addItems(["Excelente", "Bueno", "Riesgoso", "Incobrable"])
                if venta.garante.calificacion:
                    idx2 = self.calif_garante_combo.findText(venta.garante.calificacion)
                    if idx2 >= 0:
                        self.calif_garante_combo.setCurrentIndex(idx2)
                self.form.addRow(lbl_gar, self.calif_garante_combo)

        # 🧩 Mover "Actualizar Venta" al final de forma SEGURA
        if es_finalizada or es_activa:
            self._mover_boton_guardar_al_final()

        self._lock_focus_to_tab_click()

    # --- Cargas ---
    def cargar_clientes(self):
        self.clientes = session.query(Cliente).all()
        lista = [f"{c.apellidos}, {c.nombres} (DNI {c.dni})" for c in self.clientes]
        comp = QCompleter(lista); comp.setCaseSensitivity(Qt.CaseInsensitive)
        self.cliente_input.setCompleter(comp)
        comp.popup().installEventFilter(self)

    def cargar_garantes(self):
        self.garantes = session.query(Garante).all()
        lista = [f"{g.apellidos}, {g.nombres} (DNI {g.dni})" for g in self.garantes]
        comp = QCompleter(lista); comp.setCaseSensitivity(Qt.CaseInsensitive)
        self.garante_input.setCompleter(comp)
        comp.popup().installEventFilter(self)

    def cargar_productos(self):
        self.producto_combo.clear()
        for p in session.query(Producto).all():
            self.producto_combo.addItem(p.nombre, userData=p.id)

    def cargar_personal(self):
        for tipo, combo in [("Coordinador", self.coordinador_combo),
                            ("Vendedor", self.vendedor_combo),
                            ("Cobrador", self.cobrador_combo)]:
            combo.clear()
            for per in session.query(Personal).filter_by(tipo=tipo).all():
                combo.addItem(per.nombres, userData=per.id)

    # --- Cálculo ---
    def calcular_ptf(self):
        if self.monto_input.value() <= 0:
            QMessageBox.warning(self, "Dato requerido", "El monto debe ser mayor que 0."); return
        if self.cuotas_input.value() <= 0:
            QMessageBox.warning(self, "Dato requerido", "La cantidad de cuotas debe ser mayor que 0."); return
        if self.valor_cuota_input.value() <= 0:
            QMessageBox.warning(self, "Dato requerido", "El valor de la cuota debe ser mayor que 0."); return

        cuotas = self.cuotas_input.value()
        val = self.valor_cuota_input.value()
        ptf = cuotas * val
        self.ptf_output.setText(f"{ptf:.2f}")
        monto = self.monto_input.value()
        interes = ((ptf - monto) / monto * 100) if monto > 0 else 0
        self.interes_output.setText(f"{interes:.2f}")
        self._ptf_calculado = True

    # --- Guardar ---
    def guardar_venta(self):
        try:
            # --- MODO EDICIÓN ---
            if self.venta_id and self.venta_existente:
                venta = self.venta_existente

                # 1) Si la venta está FINALIZADA: solo se actualizan calificaciones.
                if venta.finalizada:
                    cambios = []
                    if hasattr(self, 'calif_cliente_combo'):
                        nueva = self.calif_cliente_combo.currentText()
                        if venta.cliente and venta.cliente.calificacion != nueva:
                            venta.cliente.calificacion = nueva
                            cambios.append("calificación del cliente")
                    if venta.garante and hasattr(self, 'calif_garante_combo'):
                        nueva = self.calif_garante_combo.currentText()
                        if venta.garante.calificacion != nueva:
                            venta.garante.calificacion = nueva
                            cambios.append("calificación del garante")

                    if cambios:
                        session.commit()
                        QMessageBox.information(self, "Actualizado", "Se actualizaron: " + ", ".join(cambios) + ".")
                    else:
                        QMessageBox.information(self, "Sin cambios", "No se detectaron cambios de calificación.")
                    self.close()
                    return

                # 2) Si la venta está ACTIVA: desde Editar sólo se permite ANULAR.
                if not venta.anulada:  # venta activa
                    if hasattr(self, 'chk_anulada') and self.chk_anulada.isChecked():
                        venta.anulada = True
                        venta.descripcion = (self.motivo_anulacion.toPlainText() or "").strip() or None
                        session.commit()
                        QMessageBox.information(self, "Venta anulada", "La venta fue anulada correctamente.")
                        self.close()
                        return
                    else:
                        QMessageBox.warning(
                            self, "Edición limitada",
                            "Desde esta pantalla solo podés ANULAR ventas activas. "
                            "Si necesitás modificar importes, cuotas, etc., usá los módulos correspondientes."
                        )
                        return

                # 3) Si llegó aquí es porque la venta ya estaba anulada (no editable).
                QMessageBox.warning(self, "Restringido", "No se pueden modificar ventas anuladas.")
                return

            # --- MODO CREACIÓN (nueva venta) ---
            # A partir de acá se aplican las validaciones completas y el requisito de PTF.
            texto = self.cliente_input.text()
            cliente = next((c for c in self.clientes
                            if f"{c.apellidos}, {c.nombres} (DNI {c.dni})" == texto), None)
            if not cliente:
                QMessageBox.warning(self, "Dato requerido", "Seleccioná un cliente válido."); return

            if self.producto_combo.currentData() is None:
                QMessageBox.warning(self, "Dato requerido", "Seleccioná un producto."); return
            if not self.plan_pago_combo.currentText():
                QMessageBox.warning(self, "Dato requerido", "Seleccioná un plan de pago."); return

            if self.coordinador_combo.currentData() is None or \
            self.vendedor_combo.currentData() is None or \
            self.cobrador_combo.currentData() is None:
                QMessageBox.warning(self, "Dato requerido", "Seleccioná coordinador, vendedor y cobrador."); return

            if self.monto_input.value() <= 0:
                QMessageBox.warning(self, "Dato requerido", "El monto debe ser mayor que 0."); return
            if self.cuotas_input.value() <= 0:
                QMessageBox.warning(self, "Dato requerido", "La cantidad de cuotas debe ser mayor que 0."); return
            if self.valor_cuota_input.value() <= 0:
                QMessageBox.warning(self, "Dato requerido", "El valor de la cuota debe ser mayor que 0."); return

            if not self.domicilio_combo.currentText():
                QMessageBox.warning(self, "Dato requerido", "Seleccioná el domicilio de cobro."); return

            if not self._ptf_calculado:
                QMessageBox.warning(self, "Falta calcular", "Antes de guardar, presioná “Calcular PTF / Interés”.")
                return

            # Garante opcional
            texto2 = self.garante_input.text()
            garante = next((g for g in self.garantes
                            if f"{g.apellidos}, {g.nombres} (DNI {g.dni})" == texto2), None)

            # Confirmación previa (ventana detalle)
            if not self._mostrar_confirmacion_guardado(texto, texto2):
                return

            # Crear nueva venta
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
                descripcion=None,
                creada_por_id=(self.usuario_actual.id if getattr(self, "usuario_actual", None) else None)
            )
            session.add(venta); session.commit()

            # Generar cuotas…
            freq = venta.plan_pago
            inicio = venta.fecha_inicio_pago or venta.fecha
            for i in range(venta.num_cuotas):
                if freq == "mensual": fv = inicio + relativedelta(months=i)
                elif freq == "semanal": fv = inicio + relativedelta(weeks=i)
                else: fv = inicio + relativedelta(days=i)
                cuota = Cuota(
                    venta_id=venta.id, numero=i + 1, fecha_vencimiento=fv,
                    monto_original=venta.valor_cuota, monto_pagado=0.0, pagada=False
                )
                session.add(cuota)
            session.commit()

            # Diálogo de docs (igual que antes)...
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle("Venta registrada")
            msg.setText("¡La venta fue registrada correctamente!")
            msg.setInformativeText("¿Deseás generar y abrir los documentos ahora?")
            btn_si = msg.addButton("Sí", QMessageBox.YesRole)
            btn_no = msg.addButton("No", QMessageBox.NoRole)
            msg.setDefaultButton(btn_no)
            msg.exec()

            if msg.clickedButton() == btn_si:
                dlg = QDialog(self)
                dlg.setWindowTitle("Seleccionar formato")
                dlg.setMinimumWidth(300)
                layout = QHBoxLayout(dlg)
                btn_word = QPushButton("Word")
                btn_excel = QPushButton("Excel")
                layout.addWidget(btn_word); layout.addWidget(btn_excel)
                btn_cancel = QDialogButtonBox(QDialogButtonBox.Close)
                btn_cancel.rejected.connect(dlg.reject)
                layout.addWidget(btn_cancel)

                def open_file(path):
                    if os.name == 'nt': os.startfile(path)
                    else: os.system(f"xdg-open '{path}'")

                def on_word():
                    path_c = generar_contrato_word(venta, "plantillas/plantilla_contrato_mutuo.docx")
                    path_p = generar_pagare_word(venta, "plantillas/plantilla_pagare_con_garante.docx")
                    for p in (path_c, path_p):
                        if os.path.exists(p): open_file(p)
                    dlg.accept()

                def on_excel():
                    path_c = generar_contrato_excel(venta)
                    path_p = generar_pagare_excel(venta)
                    for p in (path_c, path_p):
                        if os.path.exists(p): open_file(p)
                    dlg.accept()

                btn_word.clicked.connect(on_word)
                btn_excel.clicked.connect(on_excel)
                dlg.exec()

            self.close(); self.sale_saved.emit()

        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo guardar la venta:\n{e}")

    def _mover_boton_guardar_al_final(self):
        # Mueve el botón al final del QFormLayout sin que Qt lo destruya
        from PySide6.QtWidgets import QFormLayout
        fila_boton = None
        for i in range(self.form.rowCount()):
            item_field = self.form.itemAt(i, QFormLayout.FieldRole)
            if item_field and item_field.widget() is self.btn_guardar:
                fila_boton = i
                break
        if fila_boton is None:
            return

        # Reparentar para que no sea destruido al remover la fila
        self.btn_guardar.setParent(self)

        # Quitar widgets de la fila (si existen) y luego la fila
        item_label = self.form.itemAt(fila_boton, QFormLayout.LabelRole)
        if item_label and item_label.widget():
            self.form.removeWidget(item_label.widget())
        item_field = self.form.itemAt(fila_boton, QFormLayout.FieldRole)
        if item_field and item_field.widget():
            self.form.removeWidget(item_field.widget())

        self.form.removeRow(fila_boton)

        # Volver a insertarlo al final
        self.form.addRow("", self.btn_guardar)



