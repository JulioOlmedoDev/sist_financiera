from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QHBoxLayout,
    QDateEdit, QLineEdit, QTableWidget, QTableWidgetItem, QGridLayout, QFileDialog,
    QDialog, QDialogButtonBox, QCompleter
)
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QIcon
from database import session
from models import Venta, Cliente, Producto, Categoria, Personal
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


class FormConsultas(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Consultas")

        layout = QVBoxLayout()

        self.combo_consulta = QComboBox()
        self.combo_consulta.addItems([
            "Ventas por fecha",
            "Ventas por cliente",
            "Ventas por producto",
            "Ventas por calificación de cliente",
            "Ventas por personal",
            "Ventas anuladas"
        ])
        self.combo_consulta.currentIndexChanged.connect(self.actualizar_filtros)
        layout.addWidget(QLabel("Seleccione el tipo de consulta:"))
        layout.addWidget(self.combo_consulta)

        self.filtros = QWidget()
        self.filtros_layout = QGridLayout()
        self.filtros.setLayout(self.filtros_layout)
        layout.addWidget(self.filtros)

        self.tabla = QTableWidget()
        layout.addWidget(self.tabla)

        boton_layout = QHBoxLayout()
        self.btn_buscar = QPushButton("Buscar")
        self.btn_buscar.clicked.connect(self.ejecutar_consulta)

        self.btn_exportar = QPushButton("Exportar a PDF")
        self.btn_exportar.setIcon(QIcon("static/pdf_icon.png"))
        self.btn_exportar.clicked.connect(self.exportar_pdf)

        boton_layout.addWidget(self.btn_buscar)
        boton_layout.addWidget(self.btn_exportar)
        layout.addLayout(boton_layout)

        self.setLayout(layout)
        self.actualizar_filtros()

    # ---------------------------
    # UI: armado de filtros
    # ---------------------------
    def actualizar_filtros(self):
        # limpiar layout
        while self.filtros_layout.count():
            item = self.filtros_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        # rango de fechas estándar
        self.filtros_layout.addWidget(QLabel("Desde:"), 0, 0, Qt.AlignRight)
        self.fecha_inicio = QDateEdit()
        self.fecha_inicio.setCalendarPopup(True)
        self.fecha_inicio.setDate(QDate.currentDate().addMonths(-1))
        self.filtros_layout.addWidget(self.fecha_inicio, 0, 1)

        self.filtros_layout.addWidget(QLabel("Hasta:"), 0, 2, Qt.AlignRight)
        self.fecha_fin = QDateEdit()
        self.fecha_fin.setCalendarPopup(True)
        self.fecha_fin.setDate(QDate.currentDate())
        self.filtros_layout.addWidget(self.fecha_fin, 0, 3)

        seleccion = self.combo_consulta.currentText()

        if seleccion == "Ventas por cliente":
            self.filtros_layout.addWidget(QLabel("DNI o Apellido:"), 1, 0)
            self.cliente_input = QLineEdit()
            self.cliente_input.setPlaceholderText("Ej.: 30123456  ó  Miranda  ó  Miranda Juan")
            self.filtros_layout.addWidget(self.cliente_input, 1, 1, 1, 3)

        elif seleccion == "Ventas por producto":
            # Combo editable con autocompletado
            self.filtros_layout.addWidget(QLabel("Producto:"), 1, 0)
            self.producto_combo = QComboBox()
            self.producto_combo.setEditable(True)
            self.producto_combo.setInsertPolicy(QComboBox.NoInsert)  # que no agregue ítems nuevos
            self.producto_combo.setPlaceholderText("Elegí un producto o escribí para buscar…")
            self.cargar_productos_en_combo()
            # Autocompleter (ignora mayúsculas/minúsculas)
            completer = QCompleter([self.producto_combo.itemText(i) for i in range(self.producto_combo.count())])
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            # (opcional) que matchee por contiene, no solo por prefijo:
            # completer.setFilterMode(Qt.MatchContains)
            self.producto_combo.setCompleter(completer)
            self.filtros_layout.addWidget(self.producto_combo, 1, 1)

        elif seleccion == "Ventas por calificación de cliente":
            self.filtros_layout.addWidget(QLabel("Calificación:"), 1, 0)
            self.calificacion_combo = QComboBox()
            self.calificacion_combo.addItems(["Todas", "Excelente", "Bueno", "Riesgoso", "Incobrable", "Sin Calificación"])
            self.filtros_layout.addWidget(self.calificacion_combo, 1, 1)

        elif seleccion == "Ventas por personal":
            self.filtros_layout.addWidget(QLabel("Tipo (Coordinador/Vendedor/Cobrador):"), 1, 0)
            self.tipo_combo = QComboBox()
            self.tipo_combo.addItems(["Coordinador", "Vendedor", "Cobrador"])
            self.tipo_combo.currentIndexChanged.connect(self.actualizar_empleados_por_rol)
            self.filtros_layout.addWidget(self.tipo_combo, 1, 1)

            self.filtros_layout.addWidget(QLabel("Empleado:"), 2, 0)
            self.empleado_combo = QComboBox()
            self.filtros_layout.addWidget(self.empleado_combo, 2, 1, 1, 1)
            # inicializar lista
            self.actualizar_empleados_por_rol()

    def cargar_productos_en_combo(self):
        """Carga productos en el combo con userData=producto_id. Deja un ítem vacío al inicio."""
        self.producto_combo.clear()
        self.producto_combo.addItem("— Seleccionar —", userData=None)
        productos = session.query(Producto).order_by(Producto.nombre.asc()).all()
        for p in productos:
            self.producto_combo.addItem(p.nombre or "", userData=p.id)

    def actualizar_empleados_por_rol(self):
        if not hasattr(self, "tipo_combo"):
            return
        rol = self.tipo_combo.currentText().lower()
        empleados = session.query(Personal).filter(Personal.tipo == rol).all()
        self.empleado_combo.clear()
        for e in empleados:
            self.empleado_combo.addItem(f"{e.apellidos}, {e.nombres} (DNI {e.dni})", userData=e.id)

    # ---------------------------
    # Lógica: ejecutar consulta
    # ---------------------------
    def ejecutar_consulta(self):
        self.tabla.setRowCount(0)
        self.tabla.setColumnCount(0)

        seleccion = self.combo_consulta.currentText()
        inicio = self.fecha_inicio.date().toPython()
        fin = self.fecha_fin.date().toPython()

        query = session.query(Venta).filter(Venta.fecha >= inicio, Venta.fecha <= fin)

        if seleccion == "Ventas por fecha":
            resultados = query.all()

        elif seleccion == "Ventas por cliente":
            valor = (getattr(self, "cliente_input", QLineEdit()).text() or "").strip()

            if not valor:
                resultados = []
            else:
                if valor.isdigit():
                    clientes = session.query(Cliente).filter(Cliente.dni == valor).all()
                else:
                    patron = f"%{valor.lower()}%"
                    clientes = session.query(Cliente).filter(
                        (Cliente.apellidos.ilike(patron)) |
                        ((Cliente.apellidos + " " + Cliente.nombres).ilike(patron))
                    ).all()

                if len(clientes) == 0:
                    resultados = []
                elif len(clientes) == 1:
                    cliente_id = clientes[0].id
                    resultados = query.filter(Venta.cliente_id == cliente_id).all()
                else:
                    seleccionado = self.seleccionar_cliente(clientes)
                    if seleccionado is None:
                        resultados = []
                    else:
                        resultados = query.filter(Venta.cliente_id == seleccionado.id).all()

        elif seleccion == "Ventas por producto":
            # 1) Si el usuario eligió un ítem del combo => filtro por producto_id exacto
            producto_id = None
            if hasattr(self, "producto_combo"):
                producto_id = self.producto_combo.currentData()

            if producto_id:
                resultados = query.filter(Venta.producto_id == producto_id).all()
            else:
                # 2) Si escribió texto libre en el combo (editable) y no seleccionó nada => ilike
                texto = ""
                if hasattr(self, "producto_combo"):
                    texto = (self.producto_combo.currentText() or "").strip().lower()
                if texto:
                    resultados = query.join(Producto).filter(Producto.nombre.ilike(f"%{texto}%")).all()
                else:
                    resultados = []

        elif seleccion == "Ventas por calificación de cliente":
            texto = self.calificacion_combo.currentText()
            if texto == "Todas":
                resultados = query.all()
            elif texto == "Sin Calificación":
                resultados = query.filter(Venta.cliente.has(Cliente.calificacion == None)).all()
            else:
                resultados = query.filter(Venta.cliente.has(Cliente.calificacion == texto)).all()

        elif seleccion == "Ventas por personal":
            tipo = self.tipo_combo.currentText()
            empleado_id = self.empleado_combo.currentData()
            campo = {
                "Coordinador": Venta.coordinador_id,
                "Vendedor": Venta.vendedor_id,
                "Cobrador": Venta.cobrador_id
            }[tipo]
            resultados = query.filter(campo == empleado_id).all()

        elif seleccion == "Ventas anuladas":
            resultados = query.filter(Venta.anulada == True).all()

        else:
            resultados = []

        self.resultados_actuales = resultados
        self.poblar_tabla(resultados)

    # ---------------------------
    # Diálogo de selección de cliente
    # ---------------------------
    def seleccionar_cliente(self, clientes):
        """
        Abre un cuadro de diálogo con una tabla de coincidencias para elegir un cliente exacto.
        Retorna el objeto Cliente seleccionado o None si se cancela.
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("Seleccionar cliente")
        dlg.resize(700, 400)

        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Se encontraron varios clientes. Seleccione uno:"))

        tabla = QTableWidget()
        tabla.setColumnCount(4)
        tabla.setHorizontalHeaderLabels(["Apellidos", "Nombres", "DNI", "Calificación"])
        tabla.setRowCount(len(clientes))
        tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tabla.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        tabla.horizontalHeader().setStretchLastSection(True)
        tabla.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)

        for r, cte in enumerate(clientes):
            tabla.setItem(r, 0, QTableWidgetItem(cte.apellidos or ""))
            tabla.setItem(r, 1, QTableWidgetItem(cte.nombres or ""))
            tabla.setItem(r, 2, QTableWidgetItem(str(cte.dni) if cte.dni is not None else ""))
            tabla.setItem(r, 3, QTableWidgetItem(cte.calificacion or ""))

        v.addWidget(tabla)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        v.addWidget(botones)
        botones.accepted.connect(dlg.accept)
        botones.rejected.connect(dlg.reject)

        if dlg.exec() == QDialog.Accepted:
            fila = tabla.currentRow()
            if fila >= 0:
                return clientes[fila]
        return None

    # ---------------------------
    # Render de tabla resultados
    # ---------------------------
    def poblar_tabla(self, resultados):
        self.tabla.setRowCount(0)
        self.tabla.setColumnCount(0)
        if not resultados:
            return

        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels(["Fecha", "Cliente", "Producto", "Monto", "Cuotas", "PTF", "Estado", "Calif. Cliente"])
        self.tabla.setRowCount(len(resultados))

        for row, venta in enumerate(resultados):
            self.tabla.setItem(row, 0, QTableWidgetItem(str(venta.fecha)))
            cliente_txt = f"{venta.cliente.apellidos}, {venta.cliente.nombres}" if venta.cliente else ""
            self.tabla.setItem(row, 1, QTableWidgetItem(cliente_txt))
            self.tabla.setItem(row, 2, QTableWidgetItem(venta.producto.nombre if venta.producto else ""))
            self.tabla.setItem(row, 3, QTableWidgetItem(f"$ {venta.monto:,.2f}"))
            self.tabla.setItem(row, 4, QTableWidgetItem(str(venta.num_cuotas)))
            self.tabla.setItem(row, 5, QTableWidgetItem(f"$ {venta.ptf:,.2f}"))
            estado = "Anulada" if venta.anulada else "Finalizada" if venta.finalizada else "Activa"
            self.tabla.setItem(row, 6, QTableWidgetItem(estado))
            self.tabla.setItem(row, 7, QTableWidgetItem(venta.cliente.calificacion if venta.cliente else ""))

        self.tabla.resizeColumnsToContents()

    # ---------------------------
    # Exportar PDF
    # ---------------------------
    def exportar_pdf(self):
        if not hasattr(self, "resultados_actuales") or not self.resultados_actuales:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Guardar como PDF", "reporte_ventas.pdf", "PDF Files (*.pdf)")
        if not path:
            return

        c = canvas.Canvas(path, pagesize=letter)
        width, height = letter
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 50, "Reporte de Ventas")
        c.setFont("Helvetica", 7)
        y = height - 70

        headers = ["Fecha", "Cliente", "Producto", "Monto", "Cuotas", "PTF", "Estado", "Calif. Cliente"]
        col_positions = [40, 90, 200, 270, 330, 390, 470, 530]

        for i, header in enumerate(headers):
            c.drawString(col_positions[i], y, header)
        y -= 12

        total_monto = 0
        total_ptf = 0

        for venta in self.resultados_actuales:
            if y < 40:
                c.showPage()
                c.setFont("Helvetica", 7)
                y = height - 50
                # reimprimir headers por nueva página
                for i, header in enumerate(headers):
                    c.drawString(col_positions[i], y, header)
                y -= 12

            fila = [
                str(venta.fecha),
                f"{venta.cliente.apellidos}, {venta.cliente.nombres}" if venta.cliente else "",
                venta.producto.nombre if venta.producto else "",
                f"$ {venta.monto:,.2f}",
                str(venta.num_cuotas),
                f"$ {venta.ptf:,.2f}",
                "Anulada" if venta.anulada else "Finalizada" if venta.finalizada else "Activa",
                venta.cliente.calificacion if venta.cliente else ""
            ]

            total_monto += venta.monto or 0
            total_ptf += venta.ptf or 0

            for i, texto in enumerate(fila):
                c.drawString(col_positions[i], y, str(texto))
            y -= 12

        # Totales
        y -= 10
        c.setFont("Helvetica-Bold", 8)
        c.drawString(col_positions[3], y, "TOTALES:")
        c.drawString(col_positions[3] + 50, y, f"$ {total_monto:,.2f}")
        c.drawString(col_positions[5], y, f"$ {total_ptf:,.2f}")

        c.save()

        try:
            import os
            os.startfile(path)
        except Exception:
            pass
