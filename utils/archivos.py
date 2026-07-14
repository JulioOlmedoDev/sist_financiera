import os
import platform


def abrir_archivo(path: str) -> bool:
    """Abre un archivo con la app por defecto del sistema. Multiplataforma.
    Retorna True si se pudo lanzar la apertura, False si el archivo no existe o hubo error."""
    try:
        if not os.path.exists(path):
            return False
        system = platform.system().lower()
        if "windows" in system:
            os.startfile(path)  # type: ignore[attr-defined]
        elif "darwin" in system:  # macOS
            os.system(f"open '{path}'")
        else:  # Linux
            os.system(f"xdg-open '{path}'")
        return True
    except Exception:
        return False
