# test_open_producto.py
# Ejecutar desde la raíz del proyecto con el venv activado:
# (venv) C:\ruta\a\tu\proyecto> python test_open_producto.py

import sys
import traceback
from PySide6.QtWidgets import QApplication
from database import session
from models import Usuario, Producto
from gui.form_producto import FormProducto

def run_for(username, modo="crear", producto_id=None):
    """
    modo: "crear" -> abre diálogo en modo creación
          "editar" -> abre diálogo en modo edición (necesita producto_id)
    """
    try:
        app = QApplication(sys.argv)

        usuario = session.query(Usuario).filter_by(nombre=username).first()
        if not usuario:
            print("Usuario no encontrado:", username)
            return 1

        print("Usuario cargado:", usuario.nombre, "rol:", getattr(getattr(usuario, "rol", None), "nombre", None))

        if modo == "editar":
            if producto_id is None:
                # Intentar obtener un producto existente para editar
                prod = session.query(Producto).first()
                if not prod:
                    print("No hay productos en la DB para probar edición.")
                    return 3
                producto_id = prod.id
                print("Usando producto_id encontrado:", producto_id)

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
    finally:
        try:
            session.close()
        except Exception:
            pass

if __name__ == "__main__":
    # Cambiá por el usuario que querés probar: 'lmarquez' u otro admin
    usuario_a_probar = "admin"
    # Cambiá a "editar" si querés probar la edición y tenés productos en la BD
    modo = "crear"   # o "editar"
    sys.exit(run_for(usuario_a_probar, modo=modo))
