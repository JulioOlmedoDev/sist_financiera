# test_open_categoria.py
# Ejecutar desde la raíz del proyecto con el venv activado:
# (venv) C:\ruta\a\tu\proyecto> python test_open_categoria.py

import sys
import traceback
from PySide6.QtWidgets import QApplication
from database import session
from models import Usuario
from gui.form_categoria import FormCategoria

def run_for(username):
    try:
        app = QApplication(sys.argv)

        usuario = session.query(Usuario).filter_by(nombre=username).first()
        if not usuario:
            print("Usuario no encontrado:", username)
            return 1

        print("Usuario cargado:", usuario.nombre, "rol:", getattr(getattr(usuario, "rol", None), "nombre", None))
        # Instanciamos el diálogo PASANDO explícitamente el usuario
        dlg = FormCategoria(parent=None, usuario=usuario)

        # Si el diálogo fue cerrado inmediatamente por la guard, dlg.exec() devolverá 0/Rejected.
        print("Ejecutando dlg.exec() ... (cierra al aprobar/cancelar o si la guard lo rechazó)")
        res = dlg.exec()
        print("dlg.exec() ->", res)
        return 0
    except Exception:
        traceback.print_exc()
        return 2
    finally:
        try:
            session.close()
        except Exception:
            pass

if __name__ == "__main__":
    # Cambiá el nombre por 'lmarquez' o por uno admin para comparar
    usuario_a_probar = "lmarquez"
    sys.exit(run_for(usuario_a_probar))
