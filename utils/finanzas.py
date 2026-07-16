"""
utils/finanzas.py

Funciones puras para el manejo de tasas de interes y calculo de cuotas
bajo el sistema frances (cuota fija).

Todas las tasas se manejan como decimales (0.10 = 10%), nunca como
porcentajes enteros. La conversion a/desde porcentaje para mostrar en
la UI es responsabilidad de quien llama a estas funciones.
"""

DIAS_MES = 30
DIAS_SEMANA = 7
DIAS_DIA = 1


def tna_desde_tem(tem: float) -> float:
    """TNA nominal anual (simple) a partir de la TEM."""
    return tem * 12


def tea_desde_tem(tem: float) -> float:
    """TEA efectiva anual (compuesta) a partir de la TEM."""
    return (1 + tem) ** 12 - 1


def tem_desde_tna(tna: float) -> float:
    """TEM a partir de la TNA nominal (division simple)."""
    return tna / 12


def tem_desde_tea(tea: float) -> float:
    """TEM a partir de la TEA efectiva (raiz 12)."""
    return (1 + tea) ** (1 / 12) - 1


def tasa_efectiva_periodo(tem: float, dias_periodo: int, dias_mes: int = DIAS_MES) -> float:
    """
    Tasa efectiva para un periodo de 'dias_periodo' dias, derivada de
    la TEM (tasa efectiva mensual), asumiendo un mes de 'dias_mes' dias.

    Ejemplos:
        tasa_efectiva_periodo(tem, DIAS_SEMANA)  -> tasa efectiva semanal
        tasa_efectiva_periodo(tem, DIAS_DIA)     -> tasa efectiva diaria
        tasa_efectiva_periodo(tem, DIAS_MES)     -> devuelve la TEM sin cambios
    """
    if dias_periodo == dias_mes:
        return tem
    return (1 + tem) ** (dias_periodo / dias_mes) - 1


def tasa_efectiva_por_plan(tem: float, plan: str) -> float:
    """
    Tasa efectiva del periodo segun el plan de pago ('mensual',
    'semanal', 'diaria'), derivada de la TEM base del producto.
    """
    dias = {
        "mensual": DIAS_MES,
        "semanal": DIAS_SEMANA,
        "diaria": DIAS_DIA,
    }.get(plan)
    if dias is None:
        raise ValueError(f"Plan de pago desconocido: {plan!r}")
    return tasa_efectiva_periodo(tem, dias)


def calcular_cuota_frances(monto: float, tasa_periodo: float, n_cuotas: int) -> float:
    """
    Calcula la cuota fija (sistema frances) para un prestamo de 'monto',
    a 'n_cuotas' cuotas, con 'tasa_periodo' = tasa efectiva por cuota
    (ya expresada en la frecuencia correspondiente: mensual/semanal/diaria).

    Formula: cuota = monto * i / (1 - (1 + i) ** -n)

    Caso especial: si tasa_periodo == 0, la cuota es simplemente el
    monto dividido en partes iguales (sin interes).
    """
    if monto <= 0:
        raise ValueError("El monto debe ser mayor que 0.")
    if n_cuotas <= 0:
        raise ValueError("La cantidad de cuotas debe ser mayor que 0.")
    if tasa_periodo == 0:
        return monto / n_cuotas
    i = tasa_periodo
    n = n_cuotas
    return monto * i / (1 - (1 + i) ** -n)


def calcular_ptf_frances(monto: float, tasa_periodo: float, n_cuotas: int) -> float:
    """Precio Total Financiado = cuota_frances * n_cuotas."""
    cuota = calcular_cuota_frances(monto, tasa_periodo, n_cuotas)
    return cuota * n_cuotas
