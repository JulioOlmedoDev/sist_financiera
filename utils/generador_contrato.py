from dateutil.relativedelta import relativedelta
from docx import Document
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from decimal import Decimal, ROUND_HALF_UP

from pathlib import Path
from models import Venta
from datetime import timedelta
import tempfile
import os

# ========= Fechas en español sin locale =========
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

def fecha_larga(dt):
    """Devuelve: 'miércoles, 11 de octubre de 2025' sin usar locale."""
    return f"{DIAS[dt.weekday()]}, {dt.day:02d} de {MESES[dt.month-1]} de {dt.year}"


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
        if d == 2 and u != 0:  # 21-29
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


# ========= Formateo de montos =========
def monto_formateado(valor):
    return f"$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def monto_con_letras(valor) -> str:
    # Decimal para evitar errores de flotantes
    v = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    entero = int(v)
    centavos = int((v - Decimal(entero)) * 100)
    return f"{numero_a_letras(entero).capitalize()} pesos con {centavos:02d}/100"


# ========= Armado de datos para plantillas =========
def preparar_datos_contrato(venta: Venta):
    cliente = venta.cliente
    garante = venta.garante

    fecha_contrato = venta.fecha
    fecha_inicio_pago = venta.fecha_inicio_pago

    frecuencia = venta.plan_pago
    if frecuencia == "diaria":
        intervalo = relativedelta(days=1)
        texto_periodicidad = "diarias"
    elif frecuencia == "semanal":
        intervalo = relativedelta(weeks=1)
        texto_periodicidad = "semanales"
    else:
        intervalo = relativedelta(months=1)
        texto_periodicidad = "mensuales"

    vencs = [
        f"La cuota {i+1} vence el: {fecha_larga(fecha_inicio_pago + intervalo * i)}"
        for i in range(venta.num_cuotas)
    ]

    return {
        "cliente_nombre": f"{cliente.apellidos} {cliente.nombres}",
        "cliente_dni": cliente.dni,
        "cliente_domicilio": cliente.domicilio_personal or "________",
        "cliente_localidad": cliente.localidad or "________",
        "cliente_provincia": cliente.provincia or "________",
        "cuotas": venta.num_cuotas,
        "monto_letras": f"{monto_formateado(venta.monto)} - {monto_con_letras(venta.monto)}",
        "valor_cuota_letras": f"{monto_formateado(venta.valor_cuota)} - {monto_con_letras(venta.valor_cuota)}",
        "ptf_letras": f"{monto_formateado(venta.ptf)} - {monto_con_letras(venta.ptf)}",
        "tem": f"{venta.tem:.2f}",
        "tna": f"{venta.tna:.2f}",
        "tea": f"{venta.tea:.3f}",
        "vencimientos": "\n".join(vencs),
        "garante_nombre": f"{garante.apellidos} {garante.nombres}" if garante else "________",
        "garante_domicilio": garante.domicilio_personal if garante else "________",
        "garante_dni": garante.dni if garante else "________",
        "garante_localidad": garante.localidad if garante else "________",
        "dia": fecha_contrato.day,
        "mes": MESES[fecha_contrato.month - 1],  # sin locale
        "anio": fecha_contrato.year,
        "texto_periodicidad": texto_periodicidad,
        "fecha_inicio_pago": fecha_inicio_pago.strftime("%d/%m/%Y")
    }


# ========= Generadores =========
def reemplazar_tags_doc(doc: Document, datos: dict):
    for p in doc.paragraphs:
        for key, val in datos.items():
            tag = f"{{{{{key}}}}}"
            if tag in p.text:
                p.text = p.text.replace(tag, str(val))

def generar_contrato_word(venta: Venta, plantilla_path: str) -> str:
    salida_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
    datos = preparar_datos_contrato(venta)
    doc = Document(plantilla_path)
    reemplazar_tags_doc(doc, datos)
    doc.save(salida_path)
    return salida_path

def generar_contrato_excel(venta: Venta) -> str:
    plantilla_path = "plantillas/contrato_excel.xlsx"  # ruta fija
    salida_path = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx").name
    datos = preparar_datos_contrato(venta)
    wb = load_workbook(plantilla_path)
    ws = wb.active

    for row in ws.iter_rows():
        for cell in row:
            if cell.value and isinstance(cell.value, str):
                for key, val in datos.items():
                    cell.value = cell.value.replace(f"{{{{{key}}}}}", str(val))

    # Ajustar ancho de columnas al contenido
    for col in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max_length + 2

    wb.save(salida_path)
    return salida_path
