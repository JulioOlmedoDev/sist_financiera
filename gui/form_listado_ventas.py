from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox,
    QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt
from database import session
from models import Venta, Cliente
from gui.form_venta import FormVenta
from utils.generador_contrato import generar_contrato_word, generar_contrato_excel
from utils.generador_pagare import generar_pagare_word, generar_pagare_excel
from gui.form_cobro import FormCobro
import os
import platform
import unicodedata

class FormVentas(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestión de Ventas")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        titulo = QLabel("Listado de Ventas")
        titulo.setObjectName("titulo")
        layout.addWidget(titulo)

        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("Buscar por apellido, nombre, DNI, producto o estado (activa, finalizada, anulada, mora)")
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

        self.cargar_datos()

        self.setStyleSheet("""
            QLabel#titulo {
                font-size: 22px;
                font-weight: bold;
                color: #6a1b9a;
            }
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #dddddd;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #9c27b0;
                color: white;
                padding: 4px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7b1fa2;
            }
        """)

    # ---------- util ----------

    def _open_file(self, path: str):
        """Abrir archivo con la app por defecto en Windows/macOS/Linux."""
        try:
            if not os.path.exists(path):
                return False
            system = platform.system().lower()
            if "windows" in system:
                os.startfile(path)  # type: ignore[attr-defined]
            elif "darwin" in system:  # macOS
                os.system(f"open '{path}'")
            else:  # Linux
                os.system(f"xdg-open '{path}'")
            return True
        except Exception:
            return False

    # ---------- datos ----------

    def cargar_datos(self):
        self.todas_las_ventas = session.query(Venta).all()
        self.mostrar_ventas(self.todas_las_ventas)

    def mostrar_ventas(self, lista):
        self.tabla.setRowCount(0)
        for row_index, venta in enumerate(lista):
            self.tabla.insertRow(row_index)
            self.tabla.setItem(row_index, 0, QTableWidgetItem(str(venta.id)))
            fecha_str = venta.fecha.strftime("%d/%m/%Y") if venta.fecha else ""
            self.tabla.setItem(row_index, 1, QTableWidgetItem(fecha_str))
            cliente = venta.cliente
            cliente_str = f"{cliente.apellidos}, {cliente.nombres} (DNI {cliente.dni})" if cliente else ""
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

            # Botones
            btn_ver = QPushButton("Detalle")
            btn_ver.clicked.connect(lambda checked=False, vid=venta.id: self.ver_detalle_venta(vid))
            self.tabla.setCellWidget(row_index, 6, btn_ver)

            btn_editar = QPushButton("Editar")
            btn_editar.clicked.connect(lambda checked=False, vid=venta.id: self.editar_venta(vid))
            self.tabla.setCellWidget(row_index, 7, btn_editar)

            btn_doc = QPushButton("Abrir Docs")
            btn_doc.clicked.connect(lambda checked=False, vid=venta.id: self.abrir_documentos_venta(vid))
            self.tabla.setCellWidget(row_index, 8, btn_doc)

            btn_cobros = QPushButton("Cobros")
            btn_cobros.clicked.connect(lambda checked=False, vid=venta.id: self.abrir_cobros(vid))
            self.tabla.setCellWidget(row_index, 9, btn_cobros)

    # ---------- acciones ----------

    def ver_detalle_venta(self, venta_id):
        v = session.query(Venta).get(venta_id)
        if not v:
            QMessageBox.warning(self, "Error", "Venta no encontrada.")
            return
        cliente = v.cliente
        garante = v.garante
        producto = v.producto
        msg = f"<b>ID:</b> {v.id}<br><b>Fecha:</b> {v.fecha.strftime('%d/%m/%Y') if v.fecha else ''}<br>" \
              f"<b>Cliente:</b> {cliente.apellidos}, {cliente.nombres} (DNI {cliente.dni})<br>"
        if v.finalizada and cliente.calificacion:
            msg += f"<b>Calificación Cliente:</b> {cliente.calificacion}<br>"
        if garante:
            msg += f"<b>Garante:</b> {garante.apellidos}, {garante.nombres} (DNI {garante.dni})<br>" \
                   + (f"<b>Calificación Garante:</b> {garante.calificacion}<br>" if v.finalizada and garante.calificacion else "")
        msg += f"<b>Producto:</b> {producto.nombre if producto else ''}<br>" \
               f"<b>Plan de Pago:</b> {v.plan_pago.capitalize() if v.plan_pago else ''}<br>" \
               f"<b>Monto:</b> ${v.monto:,.2f}<br>" \
               f"<b>Cuotas:</b> {v.num_cuotas} x ${v.valor_cuota:,.2f}<br>" \
               f"<b>Personal:</b> Coordinador: {v.coordinador.nombres if v.coordinador else ''} / " \
               f"Vendedor: {v.vendedor.nombres if v.vendedor else ''} / " \
               f"Cobrador: {v.cobrador.nombres if v.cobrador else ''}<br>" \
               f"<b>Estado:</b> {'Anulada' if v.anulada else ('Finalizada' if v.finalizada else 'Activa')}"
        QMessageBox.information(self, "Detalle de Venta", msg)

    def editar_venta(self, venta_id):
        venta = session.query(Venta).get(venta_id)
        if not venta:
            QMessageBox.warning(self, "Error", "Venta no encontrada.")
            return
        if venta.anulada:
            QMessageBox.warning(self, "No editable", "No se puede editar una venta anulada.")
            return
        if venta.finalizada:
            if QMessageBox.question(self, "Edición limitada", "Solo podés cambiar calificaciones. ¿Continuar?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                return
        else:
            if QMessageBox.question(self, "Edición limitado", "Solo podés marcar anulada. ¿Continuar?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                return
        self.form = FormVenta(venta_id=venta_id)
        self.form.setWindowModality(Qt.ApplicationModal)
        self.form.setAttribute(Qt.WA_DeleteOnClose)
        self.form.showMaximized()
        self.form.closeEvent = self._refrescar_al_cerrar

    def abrir_documentos_venta(self, venta_id):
        venta = session.query(Venta).get(venta_id)
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
        btn_excel = QPushButton("Excel")
        hbox.addWidget(btn_word)
        hbox.addWidget(btn_excel)
        vbox.addLayout(hbox)
        btn_cancel = QDialogButtonBox(QDialogButtonBox.Cancel)
        vbox.addWidget(btn_cancel)

        btn_cancel.rejected.connect(dlg.reject)

        def abrir_word():
            plantilla_c = "plantillas/plantilla_contrato_mutuo.docx"
            plantilla_p = "plantillas/plantilla_pagare_con_garante.docx"

            # Validar plantillas
            faltan = [p for p in (plantilla_c, plantilla_p) if not os.path.exists(p)]
            if faltan:
                QMessageBox.critical(self, "Plantillas faltantes",
                                     "No se encontraron estas plantillas:\n- " + "\n- ".join(faltan))
                return

            try:
                path_c = generar_contrato_word(venta, plantilla_c)
                path_p = generar_pagare_word(venta, plantilla_p)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudieron generar los documentos Word:\n{e}")
                return

            abiertos = 0
            for p in (path_c, path_p):
                if self._open_file(p):
                    abiertos += 1
            if abiertos == 0:
                QMessageBox.warning(self, "Aviso", "Se generaron los documentos, pero no se pudieron abrir automáticamente.")
            dlg.accept()

        def abrir_excel():
            try:
                path_c = generar_contrato_excel(venta)
                path_p = generar_pagare_excel(venta)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudieron generar los documentos Excel:\n{e}")
                return

            abiertos = 0
            for p in (path_c, path_p):
                if self._open_file(p):
                    abiertos += 1
            if abiertos == 0:
                QMessageBox.warning(self, "Aviso", "Se generaron los documentos, pero no se pudieron abrir automáticamente.")
            dlg.accept()

        btn_word.clicked.connect(abrir_word)
        btn_excel.clicked.connect(abrir_excel)

        dlg.exec()

    def abrir_cobros(self, venta_id):
        self.form = FormCobro(venta_id=venta_id)
        venta = session.query(Venta).get(venta_id)
        if venta and venta.cliente:
            cliente = venta.cliente
            self.form.setWindowTitle(f"Gestión de Cobros – Venta #{venta.id} – {cliente.apellidos}, {cliente.nombres}")
        self.form.setWindowModality(Qt.ApplicationModal)
        self.form.setAttribute(Qt.WA_DeleteOnClose)
        self.form.showMaximized()
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
                    texto in self.normalizar(cli.dni)
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
