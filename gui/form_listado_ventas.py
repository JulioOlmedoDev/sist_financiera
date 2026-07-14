from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox,
    QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, QTimer

from database import get_session
from models import Venta, Cobro, Cliente
from utils.formato import formato_documento
from sqlalchemy.orm import joinedload
from gui.form_venta import FormVenta
from utils.pdf_utils import generar_docs_word, generar_docs_pdf
from utils.permisos import tiene_permiso_match
from utils.estilos import PALETA
from utils.archivos import abrir_archivo
import unicodedata
from sqlalchemy import desc
from utils.dialogos import confirmar


class FormVentas(QWidget):
    def __init__(self, usuario_actual=None):
        super().__init__()
        self.usuario_actual = usuario_actual
        self.setWindowTitle("Gestión de Ventas")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        titulo = QLabel("Listado de Ventas")
        titulo.setObjectName("titulo")
        layout.addWidget(titulo)

        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText(
            "Buscar por apellido, nombre, N° documento, producto o estado (activa, finalizada, anulada, mora)"
        )
        self.buscador.textChanged.connect(self.filtrar_ventas)
        layout.addWidget(self.buscador)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(10)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Fecha", "Cliente", "Monto", "Estado", "Personal", "Detalle", "Acciones", "Documentos", "Cobros"
        ])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setAlternatingRowColors(True)
        layout.addWidget(self.tabla)

        self._show_loading("Cargando ventas…")
        QTimer.singleShot(0, self._load_after_paint)

        self.setStyleSheet(f"""
            QLabel#titulo {{
                font-size: 22px;
                font-weight: bold;
                color: #6a1b9a;
            }}
            QTableWidget {{
                background-color: #ffffff;
                border: 1px solid #dddddd;
                border-radius: 6px;
                font-size: 14px;
            }}
            QPushButton {{
                background-color: {PALETA['identidad']['primario']};
                color: {PALETA['neutros']['texto_blanco']};
                padding: 4px 12px;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {PALETA['identidad']['primario_hover']};
            }}
        """)

    # ---------- util ----------

    def _open_file(self, path: str):
        return abrir_archivo(path)

    # ---------- datos ----------

    def cargar_datos(self):
        with get_session() as session:
            self.todas_las_ventas = (
                session.query(Venta)
                .options(
                    joinedload(Venta.cliente),
                    joinedload(Venta.producto),
                    joinedload(Venta.cuotas),
                    joinedload(Venta.coordinador),
                    joinedload(Venta.vendedor),
                    joinedload(Venta.cobrador),
                )
                .all()
            )
        self.mostrar_ventas(self.todas_las_ventas)

    def mostrar_ventas(self, lista):
        self.tabla.setUpdatesEnabled(False)
        try:
            self.tabla.clearContents()
            self.tabla.setRowCount(len(lista))

            for row_index, venta in enumerate(lista):
                self.tabla.setItem(row_index, 0, QTableWidgetItem(str(venta.id)))
                fecha_str = venta.fecha.strftime("%d/%m/%Y") if venta.fecha else ""
                self.tabla.setItem(row_index, 1, QTableWidgetItem(fecha_str))
                cliente = venta.cliente
                if cliente:
                    doc = formato_documento(cliente)
                    cliente_str = f"{cliente.apellidos}, {cliente.nombres}" + (f" ({doc})" if doc else "")
                else:
                    cliente_str = ""
                self.tabla.setItem(row_index, 2, QTableWidgetItem(cliente_str))
                self.tabla.setItem(row_index, 3, QTableWidgetItem(f"${venta.monto:,.2f}" if venta.monto else ""))

                # Estado
                cuotas = venta.cuotas
                if venta.anulada:
                    estado = "Anulada"
                elif venta.finalizada:
                    estado = "Finalizada"
                else:
                    estado = "Activa"
                con_mora = any(c.pagada and c.fecha_pago and c.fecha_pago > c.fecha_vencimiento for c in cuotas)
                if con_mora:
                    estado += " ⚠ Mora"
                item_estado = QTableWidgetItem(estado)
                if "Mora" in estado:
                    item_estado.setBackground(Qt.yellow)
                elif estado == "Anulada":
                    item_estado.setBackground(Qt.lightGray)
                elif estado == "Finalizada":
                    item_estado.setBackground(Qt.green)
                self.tabla.setItem(row_index, 4, item_estado)

                # Personal
                personal = []
                if venta.coordinador:
                    personal.append(f"C: {venta.coordinador.nombres}")
                if venta.vendedor:
                    personal.append(f"V: {venta.vendedor.nombres}")
                if venta.cobrador:
                    personal.append(f"Cob: {venta.cobrador.nombres}")
                self.tabla.setItem(row_index, 5, QTableWidgetItem(" / ".join(personal)))

                # Botones condicionados por permisos
                # 0051: Detalle
                if tiene_permiso_match(self.usuario_actual, "0051", "detalle de venta"):
                    btn_ver = QPushButton("Detalle")
                    btn_ver.clicked.connect(lambda checked=False, vid=venta.id: self.ver_detalle_venta(vid))
                    self.tabla.setCellWidget(row_index, 6, btn_ver)
                else:
                    self.tabla.setCellWidget(row_index, 6, None)

                # 0052: Editar
                if tiene_permiso_match(self.usuario_actual, "0052", "editar venta"):
                    btn_editar = QPushButton("Editar")
                    btn_editar.clicked.connect(lambda checked=False, vid=venta.id: self.editar_venta(vid))
                    self.tabla.setCellWidget(row_index, 7, btn_editar)
                else:
                    self.tabla.setCellWidget(row_index, 7, None)

                # 0053: Abrir documentos
                if tiene_permiso_match(self.usuario_actual, "0053", "abrir documentos"):
                    btn_doc = QPushButton("Abrir Docs")
                    btn_doc.clicked.connect(lambda checked=False, vid=venta.id: self.abrir_documentos_venta(vid))
                    self.tabla.setCellWidget(row_index, 8, btn_doc)
                else:
                    self.tabla.setCellWidget(row_index, 8, None)

                # 0054: Registrar cobros
                if tiene_permiso_match(self.usuario_actual, "0054", "registrar cobros"):
                    btn_cobros = QPushButton("Cobros")
                    btn_cobros.clicked.connect(lambda checked=False, vid=venta.id: self.abrir_cobros(vid))
                    self.tabla.setCellWidget(row_index, 9, btn_cobros)
                else:
                    self.tabla.setCellWidget(row_index, 9, None)

        finally:
            self.tabla.setUpdatesEnabled(True)

    # ---------- acciones ----------

    def ver_detalle_venta(self, venta_id):
        with get_session() as session:
            v = (
                session.query(Venta)
                .options(
                    joinedload(Venta.cliente),
                    joinedload(Venta.garante),
                    joinedload(Venta.producto),
                    joinedload(Venta.coordinador),
                    joinedload(Venta.vendedor),
                    joinedload(Venta.cobrador),
                    joinedload(Venta.creada_por),
                )
                .filter_by(id=venta_id)
                .first()
            )
            if not v:
                QMessageBox.warning(self, "Error", "Venta no encontrada.")
                return

            cliente = v.cliente
            garante = v.garante
            producto = v.producto

            msg_parts = []
            msg_parts.append(f"<b>ID:</b> {v.id}")
            msg_parts.append(f"<b>Fecha:</b> {v.fecha.strftime('%d/%m/%Y') if v.fecha else ''}")
            if cliente:
                doc_cli = formato_documento(cliente)
                cli_str = f"{cliente.apellidos}, {cliente.nombres}" + (f" ({doc_cli})" if doc_cli else "")
                msg_parts.append(f"<b>Cliente:</b> {cli_str}")
                if v.finalizada and cliente.calificacion:
                    msg_parts.append(f"<b>Calificación Cliente:</b> {cliente.calificacion}")

            if garante:
                doc_gar = formato_documento(garante)
                gar_str = f"{garante.apellidos}, {garante.nombres}" + (f" ({doc_gar})" if doc_gar else "")
                fila_garante = f"<b>Garante:</b> {gar_str}"
                if v.finalizada and garante.calificacion:
                    fila_garante += f"<br><b>Calificación Garante:</b> {garante.calificacion}"
                msg_parts.append(fila_garante)

            msg_parts.append(f"<b>Producto:</b> {producto.nombre if producto else ''}")
            msg_parts.append(f"<b>Plan de Pago:</b> {v.plan_pago.capitalize() if v.plan_pago else ''}")
            msg_parts.append(f"<b>Monto:</b> ${v.monto:,.2f}")
            msg_parts.append(f"<b>Cuotas:</b> {v.num_cuotas} x ${v.valor_cuota:,.2f}")
            msg_parts.append(
                f"<b>Personal:</b> Coordinador: {v.coordinador.nombres if v.coordinador else 'Sin asignar'} / "
                f"Vendedor: {v.vendedor.nombres if v.vendedor else ''} / "
                f"Cobrador: {v.cobrador.nombres if v.cobrador else 'Sin asignar'}"
            )

            if v.creada_por:
                msg_parts.append(f"<b>Creada por:</b> {v.creada_por.nombre}")

            ultimo_cobro = (
                session.query(Cobro)
                .filter_by(venta_id=v.id)
                .order_by(desc(Cobro.id))
                .first()
            )
            if ultimo_cobro and ultimo_cobro.registrado_por:
                msg_parts.append(f"<b>Último cobro cargado por:</b> {ultimo_cobro.registrado_por.nombre}")

            estado = "Anulada" if v.anulada else ("Finalizada" if v.finalizada else "Activa")
            msg_parts.append(f"<b>Estado:</b> {estado}")

        QMessageBox.information(self, "Detalle de Venta", "<br>".join(msg_parts))

    def editar_venta(self, venta_id):
        with get_session() as session:
            venta = session.query(Venta).get(venta_id)
            if not venta:
                QMessageBox.warning(self, "Error", "Venta no encontrada.")
                return
            anulada = venta.anulada
            finalizada = venta.finalizada

        if anulada:
            QMessageBox.warning(self, "No editable", "No se puede editar una venta anulada.")
            return
        if finalizada:
            if not confirmar(self, "Edición limitada",
                             "Solo podés cambiar calificaciones. ¿Continuar?"):
                return
        else:
            if not confirmar(self, "Edición limitada",
                             "Solo podés marcar anulada. ¿Continuar?"):
                return

        self.form = FormVenta(venta_id=venta_id)
        self.form.setWindowModality(Qt.ApplicationModal)
        self.form.setAttribute(Qt.WA_DeleteOnClose)
        self.form.showMaximized()
        self.form.closeEvent = self._refrescar_al_cerrar

    def abrir_documentos_venta(self, venta_id):
        with get_session() as session:
            venta = (
                session.query(Venta)
                .options(
                    joinedload(Venta.cliente),
                    joinedload(Venta.garante),
                    joinedload(Venta.producto),
                    joinedload(Venta.coordinador),
                    joinedload(Venta.vendedor),
                    joinedload(Venta.cobrador),
                    joinedload(Venta.cuotas),
                )
                .filter_by(id=venta_id)
                .first()
            )
        if not venta:
            QMessageBox.warning(self, "Error", "Venta no encontrada.")
            return

        # Diálogo de selección de formato
        dlg = QDialog(self)
        dlg.setWindowTitle("Seleccionar formato")
        vbox = QVBoxLayout(dlg)
        vbox.addWidget(QLabel("¿En qué formato querés generar y abrir los documentos?"))
        hbox = QHBoxLayout()
        btn_word = QPushButton("Word")
        btn_pdf = QPushButton("PDF")
        btn_style = f"""
            QPushButton {{ background-color: {PALETA['identidad']['primario']}; color: {PALETA['neutros']['texto_blanco']}; }}
            QPushButton:hover {{ background-color: {PALETA['identidad']['primario_hover']}; }}
        """
        btn_word.setStyleSheet(btn_style)
        btn_pdf.setStyleSheet(btn_style)
        hbox.addWidget(btn_word)
        hbox.addWidget(btn_pdf)
        vbox.addLayout(hbox)
        btn_cancel = QDialogButtonBox(QDialogButtonBox.Cancel)
        vbox.addWidget(btn_cancel)

        btn_cancel.rejected.connect(dlg.reject)

        def abrir_word():
            try:
                path_c, path_p = generar_docs_word(venta)
            except Exception as e:
                QMessageBox.critical(self, "Error al generar Word", str(e))
                return
            abiertos = sum(1 for p in (path_c, path_p) if self._open_file(p))
            if abiertos == 0:
                QMessageBox.warning(self, "Aviso", "Generados, pero no se pudieron abrir automáticamente.")
            dlg.accept()

        def abrir_pdf():
            try:
                pdf_c, pdf_p = generar_docs_pdf(venta)
            except Exception as e:
                QMessageBox.critical(self, "Error al generar PDF", str(e))
                return
            abiertos = sum(1 for p in (pdf_c, pdf_p) if self._open_file(p))
            if abiertos == 0:
                QMessageBox.warning(self, "Aviso", "PDF generados, pero no se pudieron abrir automáticamente.")
            dlg.accept()

        btn_word.clicked.connect(abrir_word)
        btn_pdf.clicked.connect(abrir_pdf)

        dlg.exec()

    def abrir_cobros(self, venta_id):
        # Import local para evitar ciclos si los hay
        from gui.form_cobro import FormCobro

        # Pasar el usuario actual si la clase lo tiene seteado
        usuario = getattr(self, "usuario_actual", None)

        # Instanciar el form de cobros con venta precargada y usuario actual
        self.form = FormCobro(venta_id=venta_id, usuario_actual=usuario)

        # Título con datos del cliente (si existen)
        with get_session() as session:
            venta = session.query(Venta).get(venta_id)
            if venta and venta.cliente:
                c = venta.cliente
                self.form.setWindowTitle(f"Gestión de Cobros – Venta #{venta.id} – {c.apellidos}, {c.nombres}")

        # 🔗 Conectar señales para refrescar listado automáticamente
        def _refrescar(_venta_id=None):
            # refresca todo el listado; si querés optimizamos luego solo esa fila
            self.cargar_datos()

        self.form.cobro_registrado.connect(_refrescar)
        self.form.cuotas_actualizadas.connect(_refrescar)
        self.form.venta_finalizada.connect(_refrescar)

        # Mostrar como ventana modal maximizada
        self.form.setWindowModality(Qt.ApplicationModal)
        self.form.setAttribute(Qt.WA_DeleteOnClose)
        self.form.showMaximized()

        # Fallback: si cierra sin emitir señal, refrescar igual
        self.form.closeEvent = self._refrescar_al_cerrar

    # ---------- filtro ----------

    def filtrar_ventas(self):
        texto = self.normalizar(self.buscador.text())

        def coincide(venta):
            cli = venta.cliente
            producto = venta.producto

            estado = "anulada" if venta.anulada else "finalizada" if venta.finalizada else "activa"
            con_mora = any(c.pagada and c.fecha_pago and c.fecha_pago > c.fecha_vencimiento for c in venta.cuotas)
            if con_mora:
                estado += " mora"

            return (
                (cli and (
                    texto in self.normalizar(cli.apellidos) or
                    texto in self.normalizar(cli.nombres) or
                    texto in self.normalizar(cli.nro_documento)
                )) or
                (producto and texto in self.normalizar(producto.nombre)) or
                (texto in self.normalizar(estado))
            )

        filtrados = [v for v in self.todas_las_ventas if coincide(v)]
        self.mostrar_ventas(filtrados)

    def normalizar(self, texto):
        if not texto:
            return ""
        return unicodedata.normalize('NFKD', texto.lower()).encode('ASCII', 'ignore').decode('utf-8')

    # ---------- refresh ----------

    def _refrescar_al_cerrar(self, event):
        self.cargar_datos()
        event.accept()

    def _load_after_paint(self):
        """Se ejecuta en el próximo ciclo del event loop: la UI ya está pintada."""
        self.setUpdatesEnabled(False)
        try:
            self.cargar_datos()
        finally:
            self.setUpdatesEnabled(True)
            self._hide_loading()

    def _show_loading(self, text="Cargando…"):
        from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
        # Reusar si ya existe
        if getattr(self, "_loading_overlay", None):
            self._loading_overlay.show()
            self._loading_label.setText(text)
            self._position_loading()
            return

        self._loading_overlay = QFrame(self)
        self._loading_overlay.setStyleSheet(
            "QFrame { background: rgba(255,255,255,220); border: 1px solid #ddd; border-radius: 8px; }"
        )
        self._loading_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        lay = QVBoxLayout(self._loading_overlay)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.addStretch()
        self._loading_label = QLabel(text, self._loading_overlay)
        self._loading_label.setAlignment(Qt.AlignCenter)
        self._loading_label.setStyleSheet("QLabel { font-size: 16px; color: #555; }")
        lay.addWidget(self._loading_label)
        lay.addStretch()

        self._position_loading()
        self._loading_overlay.show()

    def _position_loading(self):
        self._loading_overlay.setGeometry(self.rect())

    def _hide_loading(self):
        if getattr(self, "_loading_overlay", None):
            self._loading_overlay.hide()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if getattr(self, "_loading_overlay", None):
            self._position_loading()

