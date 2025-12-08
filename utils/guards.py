# utils/guards.py
from typing import Iterable
from PySide6.QtWidgets import QMessageBox
from utils.permisos import tiene_permiso_match

def _close_widget(widget):
    """
    Cierra/rechaza el widget si es posible.
    Usado cuando el usuario no tiene permiso.
    """
    try:
        # Si es QDialog -> reject()
        if hasattr(widget, "reject") and callable(widget.reject):
            widget.reject()
            return
    except Exception:
        pass
    try:
        widget.close()
    except Exception:
        pass

def require_perm_or_close(widget, usuario, *tokens: Iterable[str], title="Acceso denegado", msg=None) -> bool:
    """
    Comprueba si `usuario` tiene alguno de los tokens (substrings) usando tiene_permiso_match.
    - Si tiene permiso: devuelve True.
    - Si NO lo tiene: muestra un QMessageBox apropiado y cierra/rechaza `widget`, devuelve False.

    Uso:
        if not require_perm_or_close(self, usuario, "0200", "crear_categoria"):
            return  # en __init__ del diálogo
    """
    if usuario is None:
        QMessageBox.critical(widget, title, msg or "No hay usuario autenticado.")
        _close_widget(widget)
        return False

    try:
        # tokens puede venir vacío -> tratar como deny por seguridad
        if not tokens:
            QMessageBox.warning(widget, title, msg or "No disponés de permisos para usar esta funcionalidad.")
            _close_widget(widget)
            return False

        if tiene_permiso_match(usuario, *tokens):
            return True

        default_msg = msg or "No tenés permisos para acceder a esta pantalla."
        QMessageBox.warning(widget, title, default_msg)
        _close_widget(widget)
        return False
    except Exception as e:
        # En caso de error inesperado, por seguridad cerramos la ventana
        QMessageBox.critical(widget, "Error", f"No se pudo verificar permisos: {e}")
        _close_widget(widget)
        return False
