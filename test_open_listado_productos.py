# test_open_listado_productos.py
import sys, traceback
from PySide6.QtWidgets import QApplication
from database import get_session
from models import Usuario
from gui.form_listado_productos import FormListadoProductos

def run_for(username):
    try:
        app = QApplication(sys.argv)
        with get_session() as session:
            usuario = session.query(Usuario).filter_by(nombre=username).first()
        if not usuario:
            print("Usuario no encontrado:", username); return 1
        print("Usuario cargado:", usuario.nombre, "rol:", getattr(getattr(usuario,'rol',None),'nombre',None))
        dlg = FormListadoProductos(parent=None, usuario=usuario)
        print("Ejecutando dlg.exec() ...")
        res = dlg.exec()
        print("dlg.exec() ->", res)
        return 0
    except Exception:
        traceback.print_exc(); return 2

if __name__ == "__main__":
    usuario_a_probar = "lmarquez"
    sys.exit(run_for(usuario_a_probar))
