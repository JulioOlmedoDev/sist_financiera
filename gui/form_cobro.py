# gui/form_cobro.py

import unicodedata
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QCompleter,
    QDoubleSpinBox, QInputDialog, QMessageBox, QHBoxLayout, QDialog,
    QFormLayout, QDialogButtonBox, QSizePolicy, QComboBox
)
from PySide6.QtCore import QDate, Qt, Signal
from database import session
from models import Venta, Cuota, Cobro, Usuario
from utils.widgets_custom import ComboBoxSinScroll, DateEditSinScroll, DoubleSpinBoxSinScroll

# ---------- Constantes de layout fijo ----------
HEIGHT_SEARCH   = 30   # Buscar Venta (alto de controles)
HEIGHT_TITLE    = 22   # "Venta #..."
ROW_HEIGHT      = 24   # alto de cada fila de la tabla
VISIBLE_ROWS    = 12   # filas visibles fijas
HEIGHT_FIELDS   = 38   # Fecha/Monto/Tipo/Método/Lugar/Comprobante
HEIGHT_OBS      = 30   # Observaciones
HEIGHT_BUTTONS  = 40   # Botonera
ROOT_MARGINS    = (8, 6, 8, 8)  # l, t, r, b

# Estilo común para inputs del renglón de carga
INPUTS_CSS = """
QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit {
    font-size: 14px;
    /* bajar un poco el padding vertical para centrar el texto visualmente */
    padding: 4px 8px;            /* antes 6px 8px */
    /* permitir que el alto fijo del layout mande */
    min-height: 0px;             /* antes 34px */
}
QComboBox::drop-down { width: 22px; }
"""


# ---------------- Diálogo para nueva cuota por mora ----------------
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


# ---------------- Formulario principal de cobros (bloques fijos) ----------------
class FormCobro(QWidget):
    # Señales para refrescar listado/otras vistas (si las necesitás)
    cobro_registrado = Signal(int)       # venta_id
    cuotas_actualizadas = Signal(int)    # venta_id
    venta_finalizada = Signal(int)       # venta_id

    def __init__(self, venta_id=None, usuario_actual: Usuario | None = None):
        super().__init__()
        self.venta_id = venta_id
        self.usuario_actual = usuario_actual
        self.venta = session.query(Venta).get(self.venta_id) if self.venta_id else None

        # Título de ventana
        if self.venta:
            c = self.venta.cliente
            self.setWindowTitle(f"Gestión de Cobros – Venta #{self.venta.id} – {c.apellidos}, {c.nombres}")
        else:
            self.setWindowTitle("Gestión de Cobros")

        # --- Layout raíz (márgenes y espacios fijos) ---
        self.setMinimumSize(850, 700)
        root = QVBoxLayout(self)
        l, t, r, b = ROOT_MARGINS
        root.setContentsMargins(l, t, r, b)
        root.setSpacing(6)

        # ===== Bloque: Buscar venta =====
        fila_busqueda = QHBoxLayout()
        fila_busqueda.setContentsMargins(0, 0, 0, 0)
        fila_busqueda.setSpacing(8)

        lbl_buscar = QLabel("Buscar Venta:")
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("Apellido, DNI o #ID (ej.: Pérez · 30123456 · #125)")
        self.btn_cargar_busqueda = QPushButton("Cargar")

        # Alturas y policies fijos
        for w in (lbl_buscar, self.buscador, self.btn_cargar_busqueda):
            w.setSizePolicy(QSizePolicy.Fixed if w is not self.buscador else QSizePolicy.Expanding,
                            QSizePolicy.Fixed)
            w.setFixedHeight(HEIGHT_SEARCH)
        self.btn_cargar_busqueda.setFixedWidth(90)

        fila_busqueda.addWidget(lbl_buscar)
        fila_busqueda.addWidget(self.buscador, 1)
        fila_busqueda.addWidget(self.btn_cargar_busqueda)

        row_busqueda = QWidget()
        row_busqueda.setLayout(fila_busqueda)
        row_busqueda.setFixedHeight(HEIGHT_SEARCH)
        root.addWidget(row_busqueda)

        # Datos para autocompletar
        self._display_map = {}
        opciones = []
        for v in session.query(Venta).filter_by(anulada=False).all():
            cli = v.cliente
            ap = (cli.apellidos or "").strip()
            no = (cli.nombres or "").strip()
            dni = (cli.dni or "").strip()
            display = f"Venta #{v.id} – {ap}, {no}" + (f" (DNI {dni})" if dni else "")
            self._display_map[self._normalize(display)] = v.id
            opciones.append(display)
        self._completer = QCompleter(opciones, self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self.buscador.setCompleter(self._completer)
        self._completer.activated[str].connect(self._on_busqueda_activada)
        self.btn_cargar_busqueda.clicked.connect(self._cargar_desde_texto)
        self.buscador.returnPressed.connect(self._cargar_desde_texto)

        # Registrará como (exige sesión)
        if not (self.usuario_actual and getattr(self.usuario_actual, "id", None)):
            QMessageBox.critical(self, "Sesión requerida", "Debés iniciar sesión para registrar cobros.")
            self.close()
            return

        self.lbl_user = QLabel(f"Registrará como: <b>{self.usuario_actual.nombre}</b>")
        self.lbl_user.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        fila_user = QHBoxLayout()
        fila_user.setContentsMargins(0, 0, 0, 0)
        fila_user.addStretch(1)
        fila_user.addWidget(self.lbl_user)

        urow = QWidget()
        urow.setLayout(fila_user)
        urow.setFixedHeight(24)
        root.addWidget(urow)


        # Si vino con venta_id, mostrar en el buscador
        if self.venta:
            cli = self.venta.cliente
            self.buscador.setText(f"Venta #{self.venta.id} – {cli.apellidos}, {cli.nombres}" + (f" (DNI {cli.dni})" if cli.dni else ""))

        # ===== Bloque: Título "Venta #…" =====
        self.lbl_info_venta = QLabel(self._venta_label_text())
        self.lbl_info_venta.setWordWrap(False)
        self.lbl_info_venta.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_info_venta.setStyleSheet("font-weight:600; font-size:13px; color:#333; margin:0; padding:0;")

        row_titulo = QWidget()
        lay_titulo = QHBoxLayout(row_titulo)
        lay_titulo.setContentsMargins(0, 0, 0, 0)
        lay_titulo.addWidget(self.lbl_info_venta)
        row_titulo.setFixedHeight(HEIGHT_TITLE)
        root.addWidget(row_titulo)

        # ===== Bloque: Tabla de cuotas =====
        self.tabla_cuotas = QTableWidget()
        self.tabla_cuotas.setColumnCount(11)
        self.tabla_cuotas.setHorizontalHeaderLabels([
            "N°", "Vencimiento", "Fecha Pago", "Monto Original", "Pagado", "Estado",
            "Concepto", "Método", "Lugar", "Comp.", "Usuario"
        ])
        self.tabla_cuotas.setAlternatingRowColors(True)
        self.tabla_cuotas.horizontalHeader().setStretchLastSection(True)
        self.tabla_cuotas.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.tabla_cuotas.verticalHeader().setMinimumSectionSize(ROW_HEIGHT)
        self.tabla_cuotas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        tabla_alto = self._height_for_rows(VISIBLE_ROWS)
        self.tabla_cuotas.setFixedHeight(tabla_alto)
        root.addWidget(self.tabla_cuotas)

        # ===== Bloque: Fecha / Monto / Tipo / Método / Lugar / Comprobante =====
        fila_campos = QHBoxLayout()
        fila_campos.setContentsMargins(0, 0, 0, 0)
        fila_campos.setSpacing(10)

        lbl_fecha = QLabel("Fecha:")
        self.fecha_input = DateEditSinScroll(QDate.currentDate())
        self.fecha_input.setCalendarPopup(True)

        lbl_monto = QLabel("Monto:")
        self.monto_input = DoubleSpinBoxSinScroll()
        self.monto_input.setPrefix("$ ")
        self.monto_input.setMaximum(999_999_999.99)
        self.monto_input.setButtonSymbols(QDoubleSpinBox.NoButtons)

        lbl_tipo = QLabel("Tipo:")
        self.tipo_combo = ComboBoxSinScroll()
        self.tipo_combo.addItems(["entrega", "pago_total", "refinanciacion"])

        lbl_metodo = QLabel("Método:")
        self.metodo_combo = ComboBoxSinScroll()
        self.metodo_combo.addItems(["Sin especificar", "Efectivo", "Transferencia", "Depósito", "Tarjeta", "Cheque"])

        lbl_lugar = QLabel("Lugar:")
        self.lugar_combo = ComboBoxSinScroll()
        self.lugar_combo.addItems(["Sin especificar", "Oficina", "Cobrador", "Banco", "Pago Fácil", "Rapipago"])

        lbl_comp = QLabel("Comprobante:")
        self.comprobante_input = QLineEdit()
        self.comprobante_input.setPlaceholderText("Opcional")

        # Alinear verticalmente los labels y unificar aspecto
        for lab in (lbl_fecha, lbl_monto, lbl_tipo, lbl_metodo, lbl_lugar, lbl_comp):
            lab.setAlignment(Qt.AlignVCenter)
            lab.setStyleSheet("font-size: 14px; margin: 0; padding: 0;")


        # estilo/altura
        for w in (self.fecha_input, self.monto_input, self.tipo_combo,
                  self.metodo_combo, self.lugar_combo, self.comprobante_input):
            w.setStyleSheet(INPUTS_CSS)

        for w in (lbl_fecha, self.fecha_input, lbl_monto, self.monto_input, lbl_tipo, self.tipo_combo,
                  lbl_metodo, self.metodo_combo, lbl_lugar, self.lugar_combo, lbl_comp, self.comprobante_input):
            w.setFixedHeight(HEIGHT_FIELDS)

        # anchos máximos controlados para evitar saltos de línea
        if hasattr(self.fecha_input, "setMaximumWidth"):        self.fecha_input.setMaximumWidth(150)
        if hasattr(self.monto_input, "setMaximumWidth"):        self.monto_input.setMaximumWidth(170)
        if hasattr(self.tipo_combo, "setMaximumWidth"):         self.tipo_combo.setMaximumWidth(160)
        if hasattr(self.metodo_combo, "setMaximumWidth"):       self.metodo_combo.setMaximumWidth(180)
        if hasattr(self.lugar_combo, "setMaximumWidth"):        self.lugar_combo.setMaximumWidth(180)
        if hasattr(self.comprobante_input, "setMaximumWidth"):  self.comprobante_input.setMaximumWidth(200)

        # Alineación vertical a nivel de layout para cada control (evita “caída” visual)
        for w in (lbl_fecha, self.fecha_input,
                lbl_monto, self.monto_input,
                lbl_tipo, self.tipo_combo,
                lbl_metodo, self.metodo_combo,
                lbl_lugar, self.lugar_combo,
                lbl_comp, self.comprobante_input):
            fila_campos.setAlignment(w, Qt.AlignVCenter)

        fila_campos.addWidget(lbl_fecha); fila_campos.addWidget(self.fecha_input)
        fila_campos.addWidget(lbl_monto); fila_campos.addWidget(self.monto_input)
        fila_campos.addWidget(lbl_tipo);  fila_campos.addWidget(self.tipo_combo)
        fila_campos.addWidget(lbl_metodo); fila_campos.addWidget(self.metodo_combo)
        fila_campos.addWidget(lbl_lugar);  fila_campos.addWidget(self.lugar_combo)
        fila_campos.addWidget(lbl_comp);   fila_campos.addWidget(self.comprobante_input)
        fila_campos.addStretch(1)

        fila_campos.setAlignment(Qt.AlignVCenter)
        row_campos = QWidget()
        row_campos.setLayout(fila_campos)
        row_campos.setFixedHeight(HEIGHT_FIELDS)
        root.addWidget(row_campos)

        # ===== Bloque: Observaciones =====
        fila_obs = QHBoxLayout()
        fila_obs.setContentsMargins(0, 0, 0, 0)
        fila_obs.setSpacing(8)
        fila_obs.addWidget(QLabel("Observaciones:"))
        self.observaciones_input = QLineEdit()
        self.observaciones_input.setPlaceholderText("Opcional")
        self.observaciones_input.setFixedHeight(HEIGHT_OBS)
        fila_obs.addWidget(self.observaciones_input, 1)

        row_obs = QWidget()
        row_obs.setLayout(fila_obs)
        row_obs.setFixedHeight(HEIGHT_OBS)
        root.addWidget(row_obs)

        # ===== Botones =====
        botones = QHBoxLayout()
        botones.setContentsMargins(0, 0, 0, 0)
        botones.setSpacing(8)

        self.btn_guardar = QPushButton("Registrar Cobro")
        self.btn_guardar.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; border-radius: 5px; padding: 6px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.btn_guardar.clicked.connect(self.registrar_cobro)
        botones.addWidget(self.btn_guardar)

        self.btn_finalizar = QPushButton("Finalizar Venta")
        self.btn_finalizar.setEnabled(False)
        self.btn_finalizar.setStyleSheet("""
            QPushButton { background-color: #9E9E9E; color: white; border-radius: 5px; padding: 6px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #7E7E7E; }
        """)
        self.btn_finalizar.clicked.connect(self.finalizar_venta)
        botones.addWidget(self.btn_finalizar)

        self.btn_mora = QPushButton("Agregar Cuota por Mora")
        self.btn_mora.setEnabled(False)
        self.btn_mora.setStyleSheet("""
            QPushButton { background-color: #FFEB3B; color: black; border-radius: 5px; padding: 6px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #FDD835; }
        """)
        self.btn_mora.clicked.connect(self.agregar_cuota_mora)
        botones.addWidget(self.btn_mora)

        botones.addStretch(1)

        row_botones = QWidget()
        row_botones.setLayout(botones)
        row_botones.setFixedHeight(HEIGHT_BUTTONS)
        root.addWidget(row_botones)

        # Carga inicial
        self.cargar_cuotas()

    # ---------------- Utilidades ----------------
    def _normalize(self, texto: str) -> str:
        if not texto:
            return ""
        return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()

    def _venta_label_text(self) -> str:
        if not self.venta:
            return ""
        c = self.venta.cliente
        return f"Venta #{self.venta.id} – {c.apellidos}, {c.nombres}"

    def _height_for_rows(self, rows: int) -> int:
        header_h = 24
        frame = 2
        return header_h + (rows * ROW_HEIGHT) + frame + 2
    
    def _prefill_observaciones(self):
        """Rellena el campo 'Observaciones' con la última observación NO vacía de esta venta."""
        if not self.venta:
            self.observaciones_input.setText("")
            return

        ultimo_con_obs = (
            session.query(Cobro)
            .filter(
                Cobro.venta_id == self.venta.id,
                Cobro.observaciones.isnot(None),
                Cobro.observaciones != ""
            )
            .order_by(Cobro.id.desc())
            .first()
        )
        self.observaciones_input.setText(ultimo_con_obs.observaciones if ultimo_con_obs else "")

    # ---------------- Buscar / seleccionar ----------------
    def _on_busqueda_activada(self, texto):
        vid = self._display_map.get(self._normalize(texto))
        if vid:
            self._cargar_venta(vid)

    def _cargar_desde_texto(self):
        txt = self._normalize((self.buscador.text() or "").strip())
        if txt in self._display_map:
            self._cargar_venta(self._display_map[txt]); return
        num = "".join(ch for ch in txt if ch.isdigit())
        if num.isdigit():
            v = session.query(Venta).get(int(num))
            if v and not v.anulada:
                self._cargar_venta(v.id); return
        QMessageBox.warning(self, "Sin coincidencias", "No se encontraron ventas que coincidan.")

    def _cargar_venta(self, venta_id: int):
        self.venta = session.query(Venta).get(venta_id)
        if not self.venta:
            return
        c = self.venta.cliente
        self.setWindowTitle(f"Gestión de Cobros – Venta #{self.venta.id} – {c.apellidos}, {c.nombres}")
        self.lbl_info_venta.setText(self._venta_label_text())
        self._prefill_observaciones()
        self.cargar_cuotas()

    # ---------------- Carga de cuotas + habilitaciones ----------------
    def cargar_cuotas(self):
        if not self.venta:
            self.tabla_cuotas.setRowCount(0)
            self._deshabilitar_campos_carga()
            self.btn_finalizar.setEnabled(False)
            self.btn_mora.setEnabled(False)
            self.btn_guardar.setEnabled(False)
            return

        self.cuotas = (
            session.query(Cuota)
            .filter_by(venta_id=self.venta.id)
            .order_by(Cuota.numero)
            .all()
        )

        self.tabla_cuotas.setRowCount(len(self.cuotas))
        for i, c in enumerate(self.cuotas):
            if c.pagada:
                pagada_con_mora = c.fecha_pago and c.fecha_pago > c.fecha_vencimiento
                estado = "Con Mora" if pagada_con_mora else "Pagada"
                color = Qt.yellow if pagada_con_mora else Qt.green
            elif c.fecha_vencimiento < date.today():
                estado, color = "Vencida", Qt.red
            else:
                estado, color = "Pendiente", Qt.white

            # Último cobro por CUOTA (si existe), para método/lugar/comp/usuario
            ultimo = (
                session.query(Cobro)
                .filter_by(venta_id=self.venta.id, cuota_id=c.id)
                .order_by(Cobro.id.desc())
                .first()
            )

            self.tabla_cuotas.setItem(i, 0, QTableWidgetItem(str(c.numero)))
            self.tabla_cuotas.setItem(i, 1, QTableWidgetItem(c.fecha_vencimiento.strftime("%d/%m/%Y")))
            self.tabla_cuotas.setItem(i, 2, QTableWidgetItem(c.fecha_pago.strftime("%d/%m/%Y") if c.fecha_pago else ""))
            self.tabla_cuotas.setItem(i, 3, QTableWidgetItem(f"$ {c.monto_original:.2f}"))
            self.tabla_cuotas.setItem(i, 4, QTableWidgetItem(f"$ {c.monto_pagado:.2f}"))
            item_estado = QTableWidgetItem(estado)
            item_estado.setBackground(color)
            self.tabla_cuotas.setItem(i, 5, item_estado)
            self.tabla_cuotas.setItem(i, 6, QTableWidgetItem(c.concepto or ""))  # Concepto
            self.tabla_cuotas.setItem(i, 7, QTableWidgetItem(ultimo.metodo if ultimo and ultimo.metodo else ""))   # Método
            self.tabla_cuotas.setItem(i, 8, QTableWidgetItem(ultimo.lugar if ultimo and ultimo.lugar else ""))     # Lugar
            self.tabla_cuotas.setItem(i, 9, QTableWidgetItem(ultimo.comprobante if ultimo and ultimo.comprobante else ""))  # Comp.
            self.tabla_cuotas.setItem(i, 10, QTableWidgetItem(
                ultimo.registrado_por.nombre if (ultimo and getattr(ultimo, "registrado_por", None)) else ""
            ))

        # Habilitaciones
        cuotas_normales = [c for c in self.cuotas if not getattr(c, 'refinanciada', False)]
        todas_pagadas = all(c.pagada for c in self.cuotas)
        mora_normales = any(
            c.pagada and c.fecha_pago and c.fecha_pago > c.fecha_vencimiento
            for c in cuotas_normales
        )

        if self.venta.finalizada:
            self._deshabilitar_formulario_finalizado()
        else:
            self._habilitar_formulario_activo()
            self.btn_finalizar.setEnabled(todas_pagadas)
            self.btn_mora.setEnabled(mora_normales)

        self.btn_guardar.setEnabled(True)
        self._prefill_observaciones()

    # ---------------- Acciones ----------------
    def registrar_cobro(self):
        if not self.venta:
            QMessageBox.warning(self, "Venta no seleccionada", "Primero seleccioná una venta.")
            return
        if self.venta.finalizada:
            QMessageBox.warning(self, "Venta finalizada", "No se pueden registrar cobros en una venta finalizada.")
            return

        monto = self.monto_input.value()
        if monto <= 0:
            QMessageBox.warning(self, "Error", "Ingresá un monto mayor a $0.")
            return

        # ======== Confirmación previa ========
        fecha_cobro = self.fecha_input.date().toPython()
        tipo = self.tipo_combo.currentText()
        metodo = self.metodo_combo.currentText()
        lugar = self.lugar_combo.currentText()
        comp = self.comprobante_input.text() or None
        obs = self.observaciones_input.text() or None
        user_id = getattr(self.usuario_actual, "id", None)

        venta_nro = f"#{self.venta.id}"
        monto_html = f"<span style='font-size:15px; font-weight:700;'>$ {monto:,.2f}</span>"
        detalle_html = " &nbsp;•&nbsp; ".join([
            f"<b>Fecha:</b> {fecha_cobro.strftime('%d/%m/%Y')}",
            f"<b>Tipo:</b> {tipo}",
            f"<b>Método:</b> {metodo}",
            f"<b>Lugar:</b> {lugar}" if lugar else "",
            f"<b>Comp.:</b> {comp}" if comp else "",
            f"<b>Obs.:</b> {obs}" if obs else ""
        ]).strip(" &nbsp;•&nbsp;")

        mb = QMessageBox(self)
        mb.setWindowTitle("Confirmar registro de cobro")
        mb.setIcon(QMessageBox.Question)
        mb.setTextFormat(Qt.RichText)
        mb.setText(
            f"Está a punto de registrar un cobro por {monto_html} en la venta <b>{venta_nro}</b>."
            "<br><br>"
            f"{detalle_html}"
            "<br><br>"
            "¿Desea continuar?"
        )
        mb.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        mb.setDefaultButton(QMessageBox.No)
        if mb.exec() != QMessageBox.Yes:
            return
        # =====================================

        restante = monto

        for cuota in self.cuotas:
            if cuota.pagada:
                continue

            saldo = max(cuota.monto_original - cuota.monto_pagado, 0.0)
            if saldo <= 0:
                continue

            pago = min(saldo, restante)
            if pago <= 0:
                break

            cobro = Cobro(
                venta_id=self.venta.id,
                cuota_id=cuota.id,
                fecha=fecha_cobro,
                monto=pago,
                tipo=tipo,
                observaciones=obs,
                registrado_por_id=user_id,
                metodo=None if metodo == "Sin especificar" else metodo,
                lugar=None if lugar == "Sin especificar" else lugar,
                comprobante=comp
            )
            session.add(cobro)

            cuota.monto_pagado += pago
            if cuota.monto_pagado >= cuota.monto_original - 1e-6:
                cuota.pagada = True
                cuota.fecha_pago = fecha_cobro

            restante -= pago
            if restante <= 0:
                break

        session.commit()
        self.cobro_registrado.emit(self.venta.id)
        self.cargar_cuotas()

        # ======== Mensajes finales ========
        # Siempre mostramos éxito
        QMessageBox.information(self, "Éxito", "Cobro registrado correctamente.")

        # Si todas las cuotas quedaron pagadas y la venta NO está finalizada → sugerimos finalizar
        if not self.venta.finalizada and all(c.pagada for c in self.cuotas):
            QMessageBox.information(
                self,
                "Sugerencia",
                "Todas las cuotas de esta venta están pagadas.\n"
                "Podés marcar ahora la venta como 'Finalizada' usando el botón correspondiente."
            )



    def finalizar_venta(self):
        if not self.venta:
            QMessageBox.warning(self, "Venta no seleccionada", "Primero seleccioná una venta.")
            return

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
            resp = QMessageBox.question(self, "Cuotas con Mora",
                                        "¿Deseás generar cuotas por mora antes de finalizar?",
                                        QMessageBox.Yes | QMessageBox.No)
            if resp == QMessageBox.Yes:
                return
            if mora_en_mora:
                resp = QMessageBox.question(self, "Mora en mora",
                                            "Las cuotas por mora también fueron pagadas fuera de término.\n"
                                            "¿Deseás generar nuevas cuotas por mora?",
                                            QMessageBox.Yes | QMessageBox.No)
                if resp == QMessageBox.Yes:
                    return

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
        self.venta_finalizada.emit(self.venta.id)
        QMessageBox.information(self, "Finalizado", "La venta fue finalizada correctamente.")
        self.close()

    def agregar_cuota_mora(self):
        if not self.venta:
            QMessageBox.warning(self, "Venta no seleccionada", "Primero seleccioná una venta.")
            return
        if self.venta.finalizada:
            QMessageBox.warning(self, "Venta finalizada", "No se pueden generar cuotas por mora.")
            return

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
            self.cuotas_actualizadas.emit(self.venta.id)
            QMessageBox.information(self, "Éxito", "Cuota por mora generada correctamente.")
            self.cargar_cuotas()
            self.btn_finalizar.setEnabled(False)

    # ---------------- Habilitar/Deshabilitar campos ----------------
    def _deshabilitar_formulario_finalizado(self):
        self.fecha_input.setDisabled(True)
        self.monto_input.setDisabled(True)
        self.tipo_combo.setDisabled(True)
        self.metodo_combo.setDisabled(True)
        self.lugar_combo.setDisabled(True)
        self.comprobante_input.setDisabled(True)
        self.observaciones_input.setDisabled(True)
        self.btn_guardar.setDisabled(True)
        self.btn_finalizar.setDisabled(True)
        self.btn_mora.setDisabled(True)

    def _deshabilitar_campos_carga(self):
        self.fecha_input.setDisabled(True)
        self.monto_input.setDisabled(True)
        self.tipo_combo.setDisabled(True)
        self.metodo_combo.setDisabled(True)
        self.lugar_combo.setDisabled(True)
        self.comprobante_input.setDisabled(True)
        self.observaciones_input.setDisabled(True)

    def _habilitar_formulario_activo(self):
        self.fecha_input.setDisabled(False)
        self.monto_input.setDisabled(False)
        self.tipo_combo.setDisabled(False)
        self.metodo_combo.setDisabled(False)
        self.lugar_combo.setDisabled(False)
        self.comprobante_input.setDisabled(False)
        self.observaciones_input.setDisabled(False)
        self.btn_guardar.setDisabled(False)
