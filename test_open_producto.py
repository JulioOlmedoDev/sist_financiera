# test_open_producto.py
# Ejecutar desde la raíz del proyecto con el venv activado:
# (venv) $ python test_open_producto.py

import sys
import traceback
from PySide6.QtWidgets import QApplication
from database import get_session
from models import Usuario, Producto
from gui.form_producto import FormProducto

def run_for(username, modo="crear", producto_id=None):
    try:
        app = QApplication(sys.argv)
        with get_session() as session:
            usuario = session.query(Usuario).filter_by(nombre=username).first()
            if not usuario:
                print("Usuario no encontrado:", username)
                return 1
            print("Usuario cargado:", usuario.nombre, "rol:", getattr(getattr(usuario, "rol", None), "nombre", None))
            if modo == "editar" and producto_id is None:
                prod = session.query(Producto).first()
                if not prod:
                    print("No hay productos en la DB para probar edición.")
                    return 3
                producto_id = prod.id
                print("Usando producto_id encontrado:", producto_id)

        if modo == "editar":
            dlg = FormProducto(producto_id=producto_id, parent=None, usuario=usuario)
        else:
            dlg = FormProducto(parent=None, usuario=usuario)

        print("Ejecutando dlg.exec() ... (se cerrará si la guard niega acceso)")
        res = dlg.exec()
        print("dlg.exec() ->", res)
        return 0
    except Exception:
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    usuario_a_probar = "admin"
    modo = "crear"   # o "editar"
    sys.exit(run_for(usuario_a_probar, modo=modo))
