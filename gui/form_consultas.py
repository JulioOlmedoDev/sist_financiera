
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QHBoxLayout,
    QDateEdit, QLineEdit, QTableWidget, QTableWidgetItem, QGridLayout, QFileDialog
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

    def actualizar_filtros(self):
        while self.filtros_layout.count():
            item = self.filtros_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

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
            self.filtros_layout.addWidget(self.cliente_input, 1, 1, 1, 3)

        elif seleccion == "Ventas por producto":
            self.filtros_layout.addWidget(QLabel("Producto:"), 1, 0)
            self.producto_input = QLineEdit()
            self.filtros_layout.addWidget(self.producto_input, 1, 1, 1, 3)

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

    def actualizar_empleados_por_rol(self):
        rol = self.tipo_combo.currentText().lower()
        empleados = session.query(Personal).filter(Personal.tipo == rol).all()
        self.empleado_combo.clear()
        for e in empleados:
            self.empleado_combo.addItem(f"{e.apellidos}, {e.nombres} (DNI {e.dni})", userData=e.id)

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
            valor = self.cliente_input.text().lower()
            resultados = query.join(Cliente).filter(
                (Cliente.dni.ilike(f"%{valor}%")) |
                (Cliente.apellidos.ilike(f"%{valor}%"))
            ).all()
        elif seleccion == "Ventas por producto":
            valor = self.producto_input.text().lower()
            resultados = query.join(Producto).filter(Producto.nombre.ilike(f"%{valor}%")).all()
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

        if resultados:
            self.tabla.setColumnCount(8)
            self.tabla.setHorizontalHeaderLabels(["Fecha", "Cliente", "Producto", "Monto", "Cuotas", "PTF", "Estado", "Calif. Cliente"])
            self.tabla.setRowCount(len(resultados))

            for row, venta in enumerate(resultados):
                self.tabla.setItem(row, 0, QTableWidgetItem(str(venta.fecha)))
                self.tabla.setItem(row, 1, QTableWidgetItem(f"{venta.cliente.apellidos}, {venta.cliente.nombres}"))
                self.tabla.setItem(row, 2, QTableWidgetItem(venta.producto.nombre))
                self.tabla.setItem(row, 3, QTableWidgetItem(f"$ {venta.monto:,.2f}"))
                self.tabla.setItem(row, 4, QTableWidgetItem(str(venta.num_cuotas)))
                self.tabla.setItem(row, 5, QTableWidgetItem(f"$ {venta.ptf:,.2f}"))
                estado = "Anulada" if venta.anulada else "Finalizada" if venta.finalizada else "Activa"
                self.tabla.setItem(row, 6, QTableWidgetItem(estado))
                self.tabla.setItem(row, 7, QTableWidgetItem(venta.cliente.calificacion if venta.cliente else ""))

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

            fila = [
                str(venta.fecha),
                f"{venta.cliente.apellidos}, {venta.cliente.nombres}",
                venta.producto.nombre,
                f"$ {venta.monto:,.2f}",
                str(venta.num_cuotas),
                f"$ {venta.ptf:,.2f}",
                "Anulada" if venta.anulada else "Finalizada" if venta.finalizada else "Activa",
                venta.cliente.calificacion if venta.cliente else ""
            ]

            total_monto += venta.monto
            total_ptf += venta.ptf

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
        except:
            pass
