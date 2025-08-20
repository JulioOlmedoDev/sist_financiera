from dateutil.relativedelta import relativedelta
from docx import Document
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment
from decimal import Decimal, ROUND_HALF_UP

from pathlib import Path
from models import Venta
from datetime import timedelta
import tempfile
import os
import warnings
import shutil

# Silenciar el warning de openpyxl por encabezado/pie
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# ========= Helper: sanitizar plantilla Excel (no toca el original) =========
def _sanitizar_xlsx_origen(path_in: str) -> str:
    """
    Crea una copia temporal del XLSX, limpia encabezados/pies y devuelve la ruta a esa copia.
    No modifica la plantilla original.
    """
    tmp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx").name
    shutil.copyfile(path_in, tmp_path)
    try:
        wb = load_workbook(tmp_path)
        ws = wb.active
        hf = getattr(ws, "header_footer", None)
        if hf:
            # API clásica
            for attr in ("left_header", "center_header", "right_header",
                         "left_footer", "center_footer", "right_footer"):
                if hasattr(hf, attr):
                    setattr(hf, attr, "")
            for attr in ("differentFirst", "differentOddEven"):
                if hasattr(hf, attr):
                    setattr(hf, attr, False)
            # API alternativa (según versión)
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
        # Si algo falla, seguimos usando la copia (ya duplicada)
        pass
    return tmp_path

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
    plantilla_path = "plantillas/contrato_excel.xlsx"  # ← ruta fija
    # Usar copia "sanitizada" para evitar header/footer raros
    plantilla_limpia = _sanitizar_xlsx_origen(plantilla_path)

    salida_path = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx").name
    datos = preparar_datos_contrato(venta)
    wb = load_workbook(plantilla_limpia)
    ws = wb.active

    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str):
                text = cell.value
                es_celda_venc = False

                # Reemplazo token por token, detectando si esta celda tenía {{vencimientos}}
                for key, val in datos.items():
                    token = f"{{{{{key}}}}}"
                    if token in text:
                        if key == "vencimientos":
                            es_celda_venc = True
                            # normalizamos saltos de línea
                            val_str = str(val).replace("\r\n", "\n").replace("\r", "\n")
                            text = text.replace(token, val_str)
                        else:
                            text = text.replace(token, str(val))

                # Si hubo cambios, escribir y (si corresponde) aplicar formato especial
                if text != cell.value:
                    cell.value = text

                    if es_celda_venc:
                        # 1) Forzar multilínea y alineación
                        cell.alignment = Alignment(
                            wrap_text=True,
                            vertical="top",
                            horizontal="left"
                        )
                        # 2) Ajuste de alto de fila
                        orig_height = ws.row_dimensions[cell.row].height
                        lineas = text.count("\n") + 1
                        if orig_height is not None:  # venía fija → la ajustamos
                            base = 15.0  # aprox alto por línea en puntos
                            ws.row_dimensions[cell.row].height = max(orig_height, base * lineas * 1.15)
                        else:
                            ws.row_dimensions[cell.row].height = None  # auto

    # (opcional) autoajuste de columnas
    for col in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)
        for c in col:
            if c.value:
                max_length = max(max_length, len(str(c.value)))
        ws.column_dimensions[col_letter].width = max_length + 2

    wb.save(salida_path)
    return salida_path
