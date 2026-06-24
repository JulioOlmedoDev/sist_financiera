def formato_documento(obj) -> str:
    """Devuelve 'TIPO número' para un objeto con tipo_documento y nro_documento; '' si no hay número."""
    nro = getattr(obj, "nro_documento", None) or ""
    if not nro:
        return ""
    tipo = getattr(obj, "tipo_documento", None) or ""
    return f"{tipo} {nro}".strip()
