"""
Configuración central de la API CREDANZA.

Todas las variables sensibles se leen del .env de la raíz del proyecto
(el mismo que ya usa la app de escritorio).

Variables nuevas requeridas en .env:
    API_SECRET_KEY=<cadena aleatoria larga>   # generar con: python -c "import secrets; print(secrets.token_hex(32))"

Variables opcionales:
    API_ACCESS_TOKEN_MINUTES=480   # duración del token de sesión (default 8 hs)
    API_PREAUTH_TOKEN_MINUTES=5    # duración del token intermedio de 2FA
"""

import os

from dotenv import load_dotenv

load_dotenv()

API_SECRET_KEY = os.environ.get("API_SECRET_KEY", "")
ACCESS_TOKEN_MINUTES = int(os.environ.get("API_ACCESS_TOKEN_MINUTES", "480"))
PREAUTH_TOKEN_MINUTES = int(os.environ.get("API_PREAUTH_TOKEN_MINUTES", "5"))
JWT_ALGORITHM = "HS256"


def validar_config() -> None:
    """Falla rápido y con mensaje claro si falta configuración crítica."""
    if not API_SECRET_KEY:
        raise RuntimeError(
            "Falta API_SECRET_KEY en el archivo .env. "
            "Generala con: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
