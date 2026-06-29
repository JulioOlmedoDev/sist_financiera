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
