from dateutil.relativedelta import relativedelta
from docx import Document
from openpyxl import load_workbook
from openpyxl.styles import numbers
from openpyxl.utils import get_column_letter
from pathlib import Path
from models import Venta
import locale
import pandas as pd

import tempfile
from datetime import datetime

# Español
try:
    locale.setlocale(locale.LC_TIME, 'es_AR.utf8')
except:
    locale.setlocale(locale.LC_TIME, 'es_ES.utf8')


def numero_a_letras(n):
    unidades = (
        "", "uno", "dos", "tres", "cuatro", "cinco", "seis",
        "siete", "ocho", "nueve"
    )
    especiales = {10: "diez", 11: "once", 12: "doce", 13: "trece", 14: "catorce", 15: "quince"}
    decenas = (
        "", "", "veinte", "treinta", "cuarenta", "cincuenta",
        "sesenta", "setenta", "ochenta", "noventa"
    )
    centenas = [
        "", "ciento", "doscientos", "trescientos", "cuatrocientos",
        "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos"
    ]

    if n in especiales:
        return especiales[n]
    elif n < 10:
        return unidades[n]
    elif n < 100:
        d, u = divmod(n, 10)
        return f"{decenas[d]} y {unidades[u]}" if u else decenas[d]
    elif n < 1000:
        c, r = divmod(n, 100)
        return f"{centenas[c]} {numero_a_letras(r)}".strip() if r else "cien"
    elif n < 1_000_000:
        m, r = divmod(n, 1000)
        miles = "mil" if m == 1 else f"{numero_a_letras(m)} mil"
        return f"{miles} {numero_a_letras(r)}".strip()
    return str(n)


def monto_formateado(valor):
    return f"$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def monto_con_letras(valor):
    return f"{numero_a_letras(int(valor)).capitalize()} pesos con {int(round((valor - int(valor)) * 100)):02d}/100"


def reemplazar_tags_pagare(doc: Document, datos: dict):
    for p in doc.paragraphs:
        for key, val in datos.items():
            token = f"{{{{{key}}}}}"
            if token in p.text:
                p.text = p.text.replace(token, str(val))


def preparar_datos_pagare(venta: Venta) -> dict:
    cliente = venta.cliente
    garante = venta.garante

    fecha_pagare = venta.fecha
    fecha_inicio_pago = venta.fecha_inicio_pago

    # Calcular vencimiento real: fecha de la última cuota
    if venta.plan_pago == "diaria":
        intervalo = relativedelta(days=1)
    elif venta.plan_pago == "semanal":
        intervalo = relativedelta(weeks=1)
    else:
        intervalo = relativedelta(months=1)

    fecha_vencimiento = fecha_inicio_pago + intervalo * (venta.num_cuotas - 1)

    return {
        "cliente_nombre": f"{cliente.apellidos} {cliente.nombres}",
        "cliente_dni": cliente.dni,
        "cliente_domicilio": cliente.domicilio_personal or "________",
        "cliente_localidad": cliente.localidad or "________",
        "cliente_provincia": cliente.provincia or "________",
        "garante_nombre": f"{garante.apellidos} {garante.nombres}" if garante else "________",
        "garante_dni": garante.dni if garante else "________",
        "garante_domicilio": garante.domicilio_personal if garante else "________",
        "monto_letras": f"{monto_formateado(venta.ptf)} - {monto_con_letras(venta.ptf)}",
        "tem": f"{venta.tem:.2f}",
        "fecha_pagare": fecha_pagare.strftime("%A %d de %B de %Y").capitalize(),
        "fecha_vencimiento": fecha_vencimiento.strftime("%d de %B de %Y").capitalize(),
        "ciudad": "Río Cuarto"
    }


def generar_pagare_word(venta: Venta, plantilla_path: str) -> str:
    salida_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
    datos = preparar_datos_pagare(venta)
    doc = Document(plantilla_path)
    reemplazar_tags_pagare(doc, datos)
    doc.save(salida_path)
    return salida_path


def generar_pagare_excel(venta: Venta) -> str:
    plantilla_path = "plantillas/pagare_excel.xlsx"
    datos = preparar_datos_pagare(venta)

    wb = load_workbook(plantilla_path, data_only=False)
    ws = wb.active

    for row in ws.iter_rows():
        for cell in row:
            val = cell.value
            if isinstance(val, str):
                for key, v in datos.items():
                    token = f"{{{{{key}}}}}"
                    if token in val:
                        cell.value = val.replace(token, str(v))
                        break

    for col in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max_length + 2

    salida_path = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx").name
    wb.save(salida_path)
    return salida_path
