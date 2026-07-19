# Paleta semántica — tema violeta (base)
#
# Sub-dict "identidad": cambia según el tema activo (violeta → crema → naranja…)
# Resto de sub-dicts: fijos en todos los temas
PALETA = {
    "identidad": {
        "primario":         "#9c27b0",
        "primario_hover":   "#7b1fa2",
        "primario_pressed": "#6a1b9a",
        "primario_oscuro":  "#4a148c",
        "menu_texto_header": "#6b21a8",
        "menu_borde_item":   "#ede7f6",
        "menu_hover_fondo":  "#f3e8ff",
        "menu_hover_borde":  "#d6c3ff",
        "menu_pressed_fondo": "#efe6ff",
        "pastilla_borde": "#d9c6ef",
    },
    "acciones": {
        "guardar":          "#4caf50",
        "guardar_hover":    "#388e3c",
        "eliminar":         "#e53935",
        "eliminar_hover":   "#c62828",
        "cancelar":         "#757575",
        "cancelar_hover":   "#616161",
    },
    "neutros": {
        "fondo_app":        "#f5f5f5",
        "fondo_base":       "#fdfdfd",
        "borde":            "#cccccc",
        "texto":            "#333333",
        "texto_secundario": "#666666",
        "texto_blanco":     "#ffffff",
    },
    "feedback": {
        "error_fondo":      "#ffebee",
        "error_borde":      "#e53935",
    },
    "especial": {
        "atencion":         "#FFEB3B",  # botón mora — caso único de cobros
        "atencion_hover":   "#FDD835",
    },
}


# --- Temas alternativos (misma estructura de "identidad", para reventa) ---
IDENTIDAD_VIOLETA = dict(PALETA["identidad"])  # copia del tema original

IDENTIDAD_CREMA = {
    "primario":         "#b8860b",
    "primario_hover":   "#996f09",
    "primario_pressed": "#7d5a07",
    "primario_oscuro":  "#5c4305",
    "menu_texto_header": "#7a5c00",
    "menu_borde_item":   "#f3ecd9",
    "menu_hover_fondo":  "#faf3dd",
    "menu_hover_borde":  "#e6d4a3",
    "menu_pressed_fondo": "#f5e9c8",
    "pastilla_borde": "#e6d9a8",
}

IDENTIDAD_NARANJA = {
    "primario":         "#f57c00",
    "primario_hover":   "#ef6c00",
    "primario_pressed": "#e65100",
    "primario_oscuro":  "#bf360c",
    "menu_texto_header": "#b34700",
    "menu_borde_item":   "#ffe0cc",
    "menu_hover_fondo":  "#fff0e0",
    "menu_hover_borde":  "#ffcda3",
    "menu_pressed_fondo": "#ffe6cc",
    "pastilla_borde": "#ffd0a3",
}

IDENTIDAD_CELESTE = {
    "primario":         "#0288d1",
    "primario_hover":   "#0277bd",
    "primario_pressed": "#01579b",
    "primario_oscuro":  "#014a7f",
    "menu_texto_header": "#01579b",
    "menu_borde_item":   "#d6ecfb",
    "menu_hover_fondo":  "#e6f4fd",
    "menu_hover_borde":  "#a9d9f5",
    "menu_pressed_fondo": "#d0ecfb",
    "pastilla_borde": "#a9d9f5",
}

TEMAS_DISPONIBLES = {
    "violeta": IDENTIDAD_VIOLETA,
    "crema":   IDENTIDAD_CREMA,
    "naranja": IDENTIDAD_NARANJA,
    "celeste": IDENTIDAD_CELESTE,
}

NOMBRES_TEMAS = {
    "violeta": "Violeta (predeterminado)",
    "crema":   "Crema",
    "naranja": "Naranja",
    "celeste": "Celeste",
}


def aplicar_tema(nombre_tema: str) -> None:
    """
    Muta PALETA['identidad'] IN PLACE (no reemplaza el dict PALETA en si),
    para que cualquier modulo que ya haya hecho
    'from utils.estilos import PALETA' vea el cambio de tema sin
    necesidad de volver a importar nada.

    Los formularios que referencian PALETA['identidad'][...] de forma
    dinamica (no cacheada en una constante propia) se re-temizan solos.
    Los que tienen colores hardcodeados en su propio QSS (ej. "#9c27b0"
    escrito a mano) NO se ven afectados por esto: quedan pendientes de
    una refactorizacion aparte para referenciar PALETA en vez de un
    valor fijo.
    """
    nueva_identidad = TEMAS_DISPONIBLES.get(nombre_tema, IDENTIDAD_VIOLETA)
    PALETA["identidad"].clear()
    PALETA["identidad"].update(nueva_identidad)


def generar_qss(paleta: dict) -> str:
    i = paleta["identidad"]
    a = paleta["acciones"]
    e = paleta["especial"]

    return f"""
    /* QPushButton base — identidad, cambia con el tema */
    QPushButton {{
        background-color: {i['primario']};
        color: #ffffff;
        padding: 10px 20px;
        border-radius: 4px;
        font-weight: bold;
        border: none;
    }}
    QPushButton:hover    {{ background-color: {i['primario_hover']}; }}
    QPushButton:pressed  {{ background-color: {i['primario_pressed']}; }}
    QPushButton:disabled {{ background-color: #b0bec5; color: #ffffff; }}

    /* Semánticos por objectName — fijos en todos los temas */
    QPushButton#btnGuardar        {{ background-color: {a['guardar']}; }}
    QPushButton#btnGuardar:hover  {{ background-color: {a['guardar_hover']}; }}

    QPushButton#btnEliminar       {{ background-color: {a['eliminar']}; }}
    QPushButton#btnEliminar:hover {{ background-color: {a['eliminar_hover']}; }}

    QPushButton#btnCancelar       {{ background-color: {a['cancelar']}; }}
    QPushButton#btnCancelar:hover {{ background-color: {a['cancelar_hover']}; }}

    QPushButton#btnAtencion       {{ background-color: {e['atencion']}; color: #333333; }}
    QPushButton#btnAtencion:hover {{ background-color: {e['atencion_hover']}; }}

    /* QComboBox dropdown — preservado del main.py original */
    QComboBox QAbstractItemView {{
        background-color: white;
        border: 1px solid #bdbdbd;
        selection-background-color: #ffe0b2;
        selection-color: #424242;
        padding: 4px;
    }}
    """


def qss_boton_dialogo(paleta: dict) -> str:
    """QSS para botones de confirmar(). Se aplica directo sobre el QPushButton."""
    i = paleta["identidad"]
    return f"""
        QPushButton {{
            background-color: {i['primario']};
            color: #ffffff;
            padding: 8px 20px;
            border-radius: 4px;
            font-weight: bold;
            border: none;
            min-width: 64px;
        }}
        QPushButton:hover {{
            background-color: {i['primario_hover']};
        }}
        QPushButton:pressed {{
            background-color: {i['primario_pressed']};
        }}
    """
