"""
Configuración central de la API CREDANZA.

Variables nuevas requeridas en .env:
    API_SECRET_KEY=<cadena aleatoria larga>

Variables opcionales:
    API_ACCESS_TOKEN_MINUTES=480   # token de sesión (default 8 hs)
    API_PREAUTH_TOKEN_MINUTES=5    # tokens intermedios (2FA, cambio de clave)
    API_SETUP_2FA_TOKEN_MINUTES=10 # token de configuración de 2FA (lleva el secret)
"""

import os

from dotenv import load_dotenv

load_dotenv()

API_SECRET_KEY = os.environ.get("API_SECRET_KEY", "")
ACCESS_TOKEN_MINUTES = int(os.environ.get("API_ACCESS_TOKEN_MINUTES", "480"))
PREAUTH_TOKEN_MINUTES = int(os.environ.get("API_PREAUTH_TOKEN_MINUTES", "5"))
SETUP_2FA_TOKEN_MINUTES = int(os.environ.get("API_SETUP_2FA_TOKEN_MINUTES", "10"))
JWT_ALGORITHM = "HS256"


def validar_config() -> None:
    """Falla rápido y con mensaje claro si falta configuración crítica."""
    if not API_SECRET_KEY:
        raise RuntimeError(
            "Falta API_SECRET_KEY en el archivo .env. "
            "Generala con: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
