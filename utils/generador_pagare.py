from dateutil.relativedelta import relativedelta
from docx import Document
from openpyxl import load_workbook
from openpyxl.styles import numbers
from openpyxl.utils import get_column_letter
from pathlib import Path
from models import Venta
from decimal import Decimal, ROUND_HALF_UP

import tempfile
from datetime import datetime
import warnings
import shutil

# Silenciar el warning de openpyxl por encabezado/pie
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# ========= Helper: sanitizar plantilla Excel (no toca el original) =========
def _sanitizar_xlsx_origen(path_in: str) -> str:
    tmp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx").name
    shutil.copyfile(path_in, tmp_path)
    try:
        wb = load_workbook(tmp_path)
        ws = wb.active
        hf = getattr(ws, "header_footer", None)
        if hf:
            for attr in ("left_header", "center_header", "right_header",
                         "left_footer", "center_footer", "right_footer"):
                if hasattr(hf, attr):
                    setattr(hf, attr, "")
            for attr in ("differentFirst", "differentOddEven"):
                if hasattr(hf, attr):
                    setattr(hf, attr, False)
            for part in ("oddHeader", "oddFooter", "evenHeader", "evenFooter",
                         "firstHeader", "firstFooter"):
                obj = getattr(hf, part, None)
                if obj is not None:
                    for side in ("left", "center", "right"):
                        try:
                            setattr(obj, side, "")
                        except Exception:
                            pass
        wb.save(tmp_path)
    except Exception:
        pass
    return tmp_path

# ========= Fechas en español (sin locale) =========
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

def fecha_larga(dt):
    """Ej: 'miércoles 11 de octubre de 2025'."""
    return f"{DIAS[dt.weekday()]} {dt.day:02d} de {MESES[dt.month-1]} de {dt.year}"

def fecha_simple_es(dt):
    """Ej: '11 de octubre de 2025'."""
    return f"{dt.day:02d} de {MESES[dt.month-1]} de {dt.year}"

# ========= Números a letras =========
def numero_a_letras(n: int) -> str:
    if n == 0:
        return "cero"

    unidades = ("", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve")
    especiales = {
        10: "diez", 11: "once", 12: "doce", 13: "trece", 14: "catorce", 15: "quince",
        16: "dieciséis", 17: "diecisiete", 18: "dieciocho", 19: "diecinueve"
    }
    decenas = ("", "", "veinte", "treinta", "cuarenta", "cincuenta",
               "sesenta", "setenta", "ochenta", "noventa")
    centenas = ["", "ciento", "doscientos", "trescientos", "cuatrocientos",
                "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos"]

    def _lt100(x: int) -> str:
        if x in especiales:
            return especiales[x]
        d, u = divmod(x, 10)
        if d == 0:
            return unidades[u]
        if d == 2 and u != 0:
            if u == 1: return "veintiuno"
            if u == 2: return "veintidós"
            if u == 3: return "veintitrés"
            if u == 6: return "veintiséis"
            return "veinti" + unidades[u]
        return f"{decenas[d]} y {unidades[u]}" if u else decenas[d]

    if n < 100:
        return _lt100(n)

    if n < 1000:
        c, r = divmod(n, 100)
        if r == 0:
            return "cien" if c == 1 else centenas[c]
        return f"{centenas[c]} {_lt100(r)}".strip()

    if n < 1_000_000:
        m, r = divmod(n, 1000)
        miles = "mil" if m == 1 else f"{numero_a_letras(m)} mil"
        return miles if r == 0 else f"{miles} {numero_a_letras(r)}"

    if n < 1_000_000_000:
        mill, r = divmod(n, 1_000_000)
        millones = "un millón" if mill == 1 else f"{numero_a_letras(mill)} millones"
        return millones if r == 0 else f"{millones} {numero_a_letras(r)}"

    return str(n)

# ========= Montos =========
def monto_formateado(valor):
    return f"$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def monto_con_letras(valor) -> str:
    v = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    entero = int(v)
    centavos = int((v - Decimal(entero)) * 100)
    return f"{numero_a_letras(entero).capitalize()} pesos con {centavos:02d}/100"

# ========= Reemplazo en Word =========
def reemplazar_tags_pagare(doc: Document, datos: dict):
    for p in doc.paragraphs:
        for key, val in datos.items():
            token = f"{{{{{key}}}}}"
            if token in p.text:
                p.text = p.text.replace(token, str(val))

# ========= Armado de datos =========
def preparar_datos_pagare(venta: Venta) -> dict:
    cliente = venta.cliente
    garante = venta.garante

    fecha_pagare = venta.fecha
    fecha_inicio_pago = venta.fecha_inicio_pago

    # Última cuota como vencimiento del pagaré
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

        # Igual que en el contrato: número + letras
        "monto_letras": f"{monto_formateado(venta.ptf)} - {monto_con_letras(venta.ptf)}",

        "tem": f"{venta.tem:.2f}",
        # Fechas sin locale
        "fecha_pagare": fecha_larga(fecha_pagare),
        "fecha_vencimiento": fecha_simple_es(fecha_vencimiento),
        "ciudad": "Río Cuarto"
    }

# ========= Generadores =========
def generar_pagare_word(venta: Venta, plantilla_path: str) -> str:
    salida_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
    datos = preparar_datos_pagare(venta)
    doc = Document(plantilla_path)
    reemplazar_tags_pagare(doc, datos)
    doc.save(salida_path)
    return salida_path

def generar_pagare_excel(venta: Venta) -> str:
    plantilla_path = "plantillas/pagare_excel.xlsx"
    # Usar copia "sanitizada" para evitar header/footer raros
    plantilla_limpia = _sanitizar_xlsx_origen(plantilla_path)

    datos = preparar_datos_pagare(venta)
    wb = load_workbook(plantilla_limpia, data_only=False)
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
