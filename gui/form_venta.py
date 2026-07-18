from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QTextEdit, QPushButton, QVBoxLayout,
    QFormLayout, QSpinBox, QDoubleSpinBox, QHBoxLayout, QCompleter, QMessageBox,
    QCheckBox, QScrollArea, QFrame, QDialog, QDialogButtonBox, QToolTip, QSizePolicy
)
from PySide6.QtGui import QCursor
from PySide6.QtCore import Signal, QDate, QTimer, Qt, QEvent
from database import get_session
from models import Cliente, Garante, Producto, Personal, Venta, Cuota, Cobro
from sqlalchemy.orm import joinedload
from gui.form_cliente import FormCliente
from gui.form_garante import FormGarante
from datetime import date
from dateutil.relativedelta import relativedelta
from utils.finanzas import tasa_efectiva_por_plan, calcular_cuota_frances
from utils.guards import require_perm_or_close
import os
from utils.widgets_custom import ComboBoxSinScroll, DateEditSinScroll
from utils.pdf_utils import generar_docs_word, generar_docs_pdf
from utils.formato import formato_documento
from sqlalchemy import desc
from utils.estilos import PALETA
from utils.archivos import abrir_archivo


def _display_persona(obj) -> str:
    doc = formato_documento(obj)
    base = f"{obj.apellidos}, {obj.nombres}"
    return f"{base} ({doc})" if doc else base


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
        a = PALETA["acciones"]
        self.btn_no = QPushButton("No")
        self.btn_si = QPushButton("Sí")
        self.btn_no.setStyleSheet(f"""
            QPushButton {{ background-color: {a['cancelar']}; color: white; }}
            QPushButton:hover {{ background-color: {a['cancelar_hover']}; }}
        """)
        self.btn_si.setStyleSheet(f"""
            QPushButton {{ background-color: {a['guardar']}; color: white; }}
            QPushButton:hover {{ background-color: {a['guardar_hover']}; }}
        """)
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

        tokens = ("0052", "editar venta") if venta_id else ("0060", "crear nueva venta")
        if not require_perm_or_close(self, self.usuario_actual, *tokens):
            return

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
        self.form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
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

        i = PALETA["identidad"]
        a = PALETA["acciones"]

        # --- Cliente (requerido) ---
        lbl = QLabel("Cliente:"); lbl.setStyleSheet(label_style)
        self.cliente_input = QLineEdit()
        self.cliente_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btns = QHBoxLayout()
        self.btn_nuevo_cliente = QPushButton("+")
        self.btn_nuevo_cliente.setStyleSheet(f"""
            QPushButton {{ background-color: {i['primario']}; color: white; }}
            QPushButton:hover {{ background-color: {i['primario_hover']}; }}
        """)
        self.btn_nuevo_cliente.setToolTip("Agregar un nuevo cliente")

        self.btn_refresh_cliente = QPushButton("↺")
        self.btn_refresh_cliente.setStyleSheet(f"""
            QPushButton {{ background-color: {i['primario']}; color: white; }}
            QPushButton:hover {{ background-color: {i['primario_hover']}; }}
        """)
        self.btn_refresh_cliente.setToolTip("Actualizar listado de clientes")

        self.btn_nuevo_cliente.clicked.connect(self.abrir_form_cliente)
        self.btn_refresh_cliente.clicked.connect(self.cargar_clientes)
        btns.addWidget(self.cliente_input)
        btns.addWidget(self.btn_nuevo_cliente)
        btns.addWidget(self.btn_refresh_cliente)
        self.form.addRow(lbl, btns)
        self.form.addRow("", QLabel("Buscar por apellido o N° documento", styleSheet="font-size:11px;color:gray;"))

        # --- Garante (opcional) ---
        lbl = QLabel("Garante:"); lbl.setStyleSheet(label_style)
        self.garante_input = QLineEdit()
        self.garante_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btns2 = QHBoxLayout()
        self.btn_nuevo_garante = QPushButton("+")
        self.btn_nuevo_garante.setStyleSheet(f"""
            QPushButton {{ background-color: {i['primario']}; color: white; }}
            QPushButton:hover {{ background-color: {i['primario_hover']}; }}
        """)
        self.btn_nuevo_garante.setToolTip("Agregar un nuevo garante")

        self.btn_refresh_garante = QPushButton("↺")
        self.btn_refresh_garante.setStyleSheet(f"""
            QPushButton {{ background-color: {i['primario']}; color: white; }}
            QPushButton:hover {{ background-color: {i['primario_hover']}; }}
        """)
        self.btn_refresh_garante.setToolTip("Actualizar listado de garantes")

        self.btn_nuevo_garante.clicked.connect(self.abrir_form_garante)
        self.btn_refresh_garante.clicked.connect(self.cargar_garantes)
        btns2.addWidget(self.garante_input)
        btns2.addWidget(self.btn_nuevo_garante)
        btns2.addWidget(self.btn_refresh_garante)
        self.form.addRow(lbl, btns2)
        self.form.addRow("", QLabel("Buscar por apellido o N° documento", styleSheet="font-size:11px;color:gray;"))

        # --- Producto / Plan (requeridos) ---
        lbl = QLabel("Producto:"); lbl.setStyleSheet(label_style)
        self.producto_combo = ComboBoxSinScroll()
        self.producto_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.form.addRow(lbl, self.producto_combo)

        lbl = QLabel("Plan de Pago:"); lbl.setStyleSheet(label_style)
        self.plan_pago_combo = ComboBoxSinScroll()
        self.plan_pago_combo.addItems(["mensual", "semanal", "diaria"])
        self.plan_pago_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.form.addRow(lbl, self.plan_pago_combo)

        # --- Personal (requerido) ---
        for text, attr in [("Coordinador:", 'coordinador_combo'),
                           ("Vendedor:", 'vendedor_combo'),
                           ("Cobrador:", 'cobrador_combo')]:
            lbl = QLabel(text); lbl.setStyleSheet(label_style)
            setattr(self, attr, ComboBoxSinScroll())
            getattr(self, attr).setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.form.addRow(lbl, getattr(self, attr))

        # --- Monto / Cuotas (requeridos y > 0) ---
        for text, attr in [("Monto:", 'monto_input'),
                           ("Cuotas:", 'cuotas_input')]:
            lbl = QLabel(text); lbl.setStyleSheet(label_style)
            w = QDoubleSpinBox() if 'monto' in attr else QSpinBox()
            if isinstance(w, QDoubleSpinBox):
                w.setPrefix("$ "); w.setMaximum(1e9); w.setDecimals(2)
            else:
                w.setMaximum(60)
            w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            setattr(self, attr, w)
            w.installEventFilter(self)
            self.form.addRow(lbl, w)

        # Valor de Cuota se crea aca (mismo estilo que Monto), pero se agrega
        # al formulario mas abajo, despues de las tasas y del boton
        # "Calcular Cuota Sugerida": es un resultado, no un dato inicial.
        self.valor_cuota_input = QDoubleSpinBox()
        self.valor_cuota_input.setPrefix("$ "); self.valor_cuota_input.setMaximum(1e9); self.valor_cuota_input.setDecimals(2)
        self.valor_cuota_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.valor_cuota_input.installEventFilter(self)

        # --- Tasas (requeridas) ---
        lbl = QLabel("T.E.M. (% mensual, incluye IVA):"); lbl.setStyleSheet(label_style)
        self.tem_input = QDoubleSpinBox(self); self.tem_input.setDecimals(3)
        self.tem_input.setRange(0, 100); self.tem_input.setSuffix(" %")
        self.tem_input.installEventFilter(self)
        self.tem_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tem_input.valueChanged.connect(self._tasas_changed)
        self.form.addRow(lbl, self.tem_input)

        lbl = QLabel("T.N.A. (% anual, incluye IVA):"); lbl.setStyleSheet(label_style)
        self.tna_input = QDoubleSpinBox(self); self.tna_input.setDecimals(3)
        self.tna_input.setRange(0, 1200); self.tna_input.setSuffix(" %")
        self.tna_input.installEventFilter(self)
        self.tna_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tna_input.valueChanged.connect(self._tasas_changed)
        self.form.addRow(lbl, self.tna_input)

        lbl = QLabel("T.E.A. (% anual, incluye IVA):"); lbl.setStyleSheet(label_style)
        self.tea_input = QDoubleSpinBox(self); self.tea_input.setDecimals(3)
        self.tea_input.setRange(0, 5000); self.tea_input.setSuffix(" %")
        self.tea_input.installEventFilter(self)
        self.tea_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tea_input.valueChanged.connect(self._tasas_changed)
        self.form.addRow(lbl, self.tea_input)

        self.plan_pago_combo.currentTextChanged.connect(self._on_plan_changed)
        self._on_plan_changed(self.plan_pago_combo.currentText())

        # --- Calcular Cuota Sugerida (sistema frances) — paso recomendado ---
        self.btn_cuota_sugerida = QPushButton("Calcular Cuota Sugerida (sist. francés)")
        self.btn_cuota_sugerida.setStyleSheet(f"""
            QPushButton {{ background-color: {i['primario']}; color: white; }}
            QPushButton:hover {{ background-color: {i['primario_hover']}; }}
        """)
        self.btn_cuota_sugerida.setToolTip(
            "Paso recomendado: calcula automaticamente el Valor de Cuota "
            "a partir del Monto, la TEM y la cantidad de Cuotas (sistema frances). "
            "El resultado queda cargado en Valor de Cuota y se puede editar despues si hace falta."
        )
        self.btn_cuota_sugerida.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_cuota_sugerida.clicked.connect(self.calcular_cuota_sugerida)
        self.form.addRow("", self.btn_cuota_sugerida)

        lbl = QLabel("Valor de Cuota:"); lbl.setStyleSheet(label_style)
        self.form.addRow(lbl, self.valor_cuota_input)

        # --- Calcular PTF / Interés (verificacion, requerido antes de guardar) ---
        self.btn_calcular = QPushButton("Calcular PTF / Interés")
        self.btn_calcular.setStyleSheet(f"""
            QPushButton {{ background-color: {i['primario']}; color: white; }}
            QPushButton:hover {{ background-color: {i['primario_hover']}; }}
        """)
        self.btn_calcular.setToolTip(
            "Muestra el Precio Total Financiado y el interes efectivo resultante "
            "del Valor de Cuota actual (el sugerido, o uno cargado manualmente). "
            "Usalo para verificar el resultado antes de guardar la venta."
        )
        self.btn_calcular.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_calcular.clicked.connect(self.calcular_ptf)
        self.form.addRow("", self.btn_calcular)

        # --- Salidas ---
        for text, attr in [("PTF:", 'ptf_output'), ("Interés (%):", 'interes_output')]:
            lbl = QLabel(text); lbl.setStyleSheet(label_style)
            out = QLineEdit(readOnly=True); out.setStyleSheet("background:#f5f5f5;")
            out.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            setattr(self, attr, out)
            self.form.addRow(lbl, out)

        # --- Fecha inicio (requerida) y domicilio (requerido) ---
        lbl = QLabel("Fecha de Primer Pago:"); lbl.setStyleSheet(label_style)
        self.fecha_inicio_input = DateEditSinScroll(QDate.currentDate())
        self.fecha_inicio_input.setCalendarPopup(True)
        self.fecha_inicio_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.form.addRow(lbl, self.fecha_inicio_input)

        lbl = QLabel("Domicilio de Cobro:"); lbl.setStyleSheet(label_style)
        self.domicilio_combo = ComboBoxSinScroll(); self.domicilio_combo.addItems(["personal", "laboral"])
        self.domicilio_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
        self.btn_guardar = QPushButton("Guardar" if not venta_id else "Actualizar")
        self.btn_guardar.setStyleSheet(f"""
            QPushButton {{ background-color: {a['guardar']}; color: white; }}
            QPushButton:hover {{ background-color: {a['guardar_hover']}; }}
        """)
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
        self.producto_combo.currentIndexChanged.connect(self._on_producto_changed)
        self._on_producto_changed(self.producto_combo.currentIndex())
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

    def _calcular_desvio_cuota(self):
        """Compara la cuota cargada contra la cuota teorica (sistema frances)
        segun TEM + plan + cuotas. Devuelve (cuota_teorica, desvio_pct) o
        (None, None) si no se puede calcular (datos incompletos)."""
        monto = self.monto_input.value()
        n_cuotas = self.cuotas_input.value()
        cuota_cargada = self.valor_cuota_input.value()
        if monto <= 0 or n_cuotas <= 0 or cuota_cargada <= 0:
            return None, None
        try:
            tem = self.tem_input.value() / 100
            plan = self.plan_pago_combo.currentText()
            tasa_periodo = tasa_efectiva_por_plan(tem, plan)
            cuota_teorica = calcular_cuota_frances(monto, tasa_periodo, n_cuotas)
        except (ValueError, ZeroDivisionError):
            return None, None
        if cuota_teorica == 0:
            return None, None
        desvio_pct = abs(cuota_cargada - cuota_teorica) / cuota_teorica * 100
        return cuota_teorica, desvio_pct

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

        cuota_teorica, desvio_pct = self._calcular_desvio_cuota()
        if desvio_pct is not None and desvio_pct > 1.0:
            items.append((
                "⚠ Desvío de tasa",
                f"Cuota cargada difiere {desvio_pct:.2f}% de la teórica "
                f"(${cuota_teorica:.2f} según TEM {self.tem_input.value():.3f}%)"
            ))

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

        if event.type() == QEvent.FocusIn and isinstance(obj, (QSpinBox, QDoubleSpinBox)):
            # Selecciona todo el contenido al entrar al campo, para que al
            # escribir o borrar no queden restos del numero anterior
            # (ej. borrar "2000000" a mano podia dejar un "2" suelto).
            QTimer.singleShot(0, obj.selectAll)
            return False

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
        # El plan de pago ya no trae tasas propias: TEM/TNA/TEA vienen
        # del producto elegido (ver _on_producto_changed). El plan solo
        # define la frecuencia de cobro y la tasa efectiva por periodo
        # al calcular la cuota sugerida (ver calcular_cuota_sugerida).
        pass

    def _on_producto_changed(self, index=None):
        """Al elegir un producto, precarga su TEM base en el campo TEM.
        Esto dispara _tasas_changed, que deriva TNA y TEA automaticamente."""
        producto_id = self.producto_combo.currentData()
        if producto_id is None:
            return
        with get_session() as session:
            producto = session.get(Producto, producto_id)
            tem_base = float(producto.tem_base) if producto and producto.tem_base is not None else 0.0
        self.tem_input.setValue(round(tem_base * 100, 3))

    # --- Abrir formularios ---
    def abrir_form_cliente(self):
        self.nuevo_cliente = FormCliente(usuario=self.usuario_actual)
        self.nuevo_cliente.showMaximized()
        self.nuevo_cliente.destroyed.connect(lambda: QTimer.singleShot(100, self.cargar_clientes))

    def abrir_form_garante(self):
        self.nuevo_garante = FormGarante(usuario=self.usuario_actual)
        self.nuevo_garante.showMaximized()
        self.nuevo_garante.destroyed.connect(lambda: QTimer.singleShot(100, self.cargar_garantes))

    # --- Carga de edición ---
    def cargar_venta_existente(self):
        with get_session() as _s:
            venta = (
                _s.query(Venta)
                .options(
                    joinedload(Venta.cliente),
                    joinedload(Venta.garante),
                    joinedload(Venta.creada_por),
                )
                .filter_by(id=self.venta_id)
                .first()
            )
            if not venta:
                QMessageBox.critical(self, "Error", "Venta no encontrada.")
                return self.close()
            ultimo_cobro = (
                _s.query(Cobro)
                .filter_by(venta_id=venta.id)
                .options(joinedload(Cobro.registrado_por))
                .order_by(desc(Cobro.id))
                .first()
            )
            _uc_nombre = ultimo_cobro.registrado_por.nombre if (ultimo_cobro and ultimo_cobro.registrado_por) else None

        self.venta_existente = venta
        es_finalizada = venta.finalizada
        es_activa = (not venta.anulada) and (not venta.finalizada)

        # --- Datos base ---
        self.cliente_input.setText(_display_persona(venta.cliente))
        if venta.garante:
            self.garante_input.setText(_display_persona(venta.garante))

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

        if _uc_nombre:
            lbl_uc = QLabel("Último cobro cargado por:"); lbl_uc.setStyleSheet(self.label_style)
            self.form.addRow(lbl_uc, QLabel(_uc_nombre))

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
        with get_session() as session:
            self.clientes = session.query(Cliente).all()
        lista = [_display_persona(c) for c in self.clientes]
        comp = QCompleter(lista); comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        self.cliente_input.setCompleter(comp)
        comp.popup().installEventFilter(self)

    def cargar_garantes(self):
        with get_session() as session:
            self.garantes = session.query(Garante).all()
        lista = [_display_persona(g) for g in self.garantes]
        comp = QCompleter(lista); comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        self.garante_input.setCompleter(comp)
        comp.popup().installEventFilter(self)

    def cargar_productos(self):
        self.producto_combo.clear()
        with get_session() as session:
            for p in session.query(Producto).all():
                self.producto_combo.addItem(p.nombre, userData=p.id)

    def cargar_personal(self):
        with get_session() as session:
            for tipo, combo in [("Coordinador", self.coordinador_combo),
                                ("Vendedor", self.vendedor_combo),
                                ("Cobrador", self.cobrador_combo)]:
                combo.clear()
                if combo is not self.vendedor_combo:
                    combo.addItem("Sin asignar", None)
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

    def calcular_cuota_sugerida(self):
        """Calcula el valor de cuota exacto (sistema frances) a partir
        de monto + TEM + cantidad de cuotas, respetando el plan de pago
        (mensual/semanal/diaria) para derivar la tasa efectiva del periodo.
        El resultado se carga en Valor de Cuota, editable despues."""
        if self.monto_input.value() <= 0:
            QMessageBox.warning(self, "Dato requerido", "El monto debe ser mayor que 0."); return
        if self.cuotas_input.value() <= 0:
            QMessageBox.warning(self, "Dato requerido", "La cantidad de cuotas debe ser mayor que 0."); return

        tem = self.tem_input.value() / 100
        plan = self.plan_pago_combo.currentText()
        try:
            tasa_periodo = tasa_efectiva_por_plan(tem, plan)
            cuota = calcular_cuota_frances(self.monto_input.value(), tasa_periodo, self.cuotas_input.value())
        except ValueError as e:
            QMessageBox.warning(self, "Error de calculo", str(e)); return

        self.valor_cuota_input.setValue(round(cuota, 2))
        self.calcular_ptf()

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
                        nueva_cc = self.calif_cliente_combo.currentText() if hasattr(self, 'calif_cliente_combo') else None
                        nueva_cg = self.calif_garante_combo.currentText() if hasattr(self, 'calif_garante_combo') else None
                        with get_session() as _s:
                            _v = _s.query(Venta).get(self.venta_id)
                            if nueva_cc and _v.cliente and _v.cliente.calificacion != nueva_cc:
                                _v.cliente.calificacion = nueva_cc
                            if nueva_cg and _v.garante and _v.garante.calificacion != nueva_cg:
                                _v.garante.calificacion = nueva_cg
                            _s.commit()
                        QMessageBox.information(self, "Actualizado", "Se actualizaron: " + ", ".join(cambios) + ".")
                    else:
                        QMessageBox.information(self, "Sin cambios", "No se detectaron cambios de calificación.")
                    self.close()
                    return

                # 2) Si la venta está ACTIVA: desde Editar sólo se permite ANULAR.
                if not venta.anulada:  # venta activa
                    if hasattr(self, 'chk_anulada') and self.chk_anulada.isChecked():
                        with get_session() as _s:
                            _v = _s.query(Venta).get(self.venta_id)
                            _v.anulada = True
                            _v.descripcion = (self.motivo_anulacion.toPlainText() or "").strip() or None
                            _s.commit()
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
                            if _display_persona(c) == texto), None)
            if not cliente:
                QMessageBox.warning(self, "Dato requerido", "Seleccioná un cliente válido."); return

            if self.producto_combo.currentData() is None:
                QMessageBox.warning(self, "Dato requerido", "Seleccioná un producto."); return
            if not self.plan_pago_combo.currentText():
                QMessageBox.warning(self, "Dato requerido", "Seleccioná un plan de pago."); return

            if self.vendedor_combo.currentData() is None:
                QMessageBox.warning(self, "Dato requerido", "Seleccioná un vendedor."); return

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
                            if _display_persona(g) == texto2), None)

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
            with get_session() as session:
                session.add(venta)
                session.flush()  # obtiene venta.id sin cerrar la transacción

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

            # Re-cargar con todas las relaciones para los generadores de documentos
            with get_session() as _rs:
                venta = (
                    _rs.query(Venta)
                    .options(
                        joinedload(Venta.cliente),
                        joinedload(Venta.garante),
                        joinedload(Venta.producto),
                        joinedload(Venta.cuotas),
                        joinedload(Venta.coordinador),
                        joinedload(Venta.vendedor),
                        joinedload(Venta.cobrador),
                    )
                    .filter_by(id=venta.id)
                    .first()
                )

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
                btn_pdf = QPushButton("PDF")
                layout.addWidget(btn_word); layout.addWidget(btn_pdf)
                btn_cancel = QDialogButtonBox(QDialogButtonBox.Close)
                btn_cancel.rejected.connect(dlg.reject)
                layout.addWidget(btn_cancel)

                def on_word():
                    try:
                        path_c, path_p = generar_docs_word(venta)
                    except Exception as e:
                        QMessageBox.critical(dlg, "Error al generar Word", str(e))
                        return
                    for p in (path_c, path_p):
                        if os.path.exists(p): abrir_archivo(p)
                    dlg.accept()

                def on_pdf():
                    try:
                        pdf_c, pdf_p = generar_docs_pdf(venta)
                    except Exception as e:
                        QMessageBox.critical(dlg, "Error al generar PDF", str(e))
                        return
                    for p in (pdf_c, pdf_p):
                        if os.path.exists(p): abrir_archivo(p)
                    dlg.accept()

                btn_word.clicked.connect(on_word)
                btn_pdf.clicked.connect(on_pdf)
                dlg.exec()

            self.close(); self.sale_saved.emit()

        except Exception as e:
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



