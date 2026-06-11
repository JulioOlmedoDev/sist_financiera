# test_open_categoria.py
# Ejecutar desde la raíz del proyecto con el venv activado:
# (venv) $ python test_open_categoria.py

import sys
import traceback
from PySide6.QtWidgets import QApplication
from database import get_session
from models import Usuario
from gui.form_categoria import FormCategoria

def run_for(username):
    try:
        app = QApplication(sys.argv)
        with get_session() as session:
            usuario = session.query(Usuario).filter_by(nombre=username).first()
        if not usuario:
            print("Usuario no encontrado:", username)
            return 1
        print("Usuario cargado:", usuario.nombre, "rol:", getattr(getattr(usuario, "rol", None), "nombre", None))
        dlg = FormCategoria(parent=None, usuario=usuario)
        print("Ejecutando dlg.exec() ... (cierra al aprobar/cancelar o si la guard lo rechazó)")
        res = dlg.exec()
        print("dlg.exec() ->", res)
        return 0
    except Exception:
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    usuario_a_probar = "lmarquez"
    sys.exit(run_for(usuario_a_probar))
