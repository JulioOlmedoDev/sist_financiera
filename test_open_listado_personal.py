from PySide6.QtWidgets import QApplication
from gui.form_listado_personal import FormListadoPersonal
from database import session
from models import Usuario
import sys

"""
Probalo con:
python test_open_listado_personal.py
"""

def get_user(username):
    return session.query(Usuario).filter_by(usuario=username).first()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    print("Seleccioná el usuario para la prueba:")
    print("1) owner_root")
    print("2) admin")
    print("3) usuario_sin_permiso")

    opcion = input("Ingrese opción: ")

    if opcion == "1":
        user = get_user("owner_root")
    elif opcion == "2":
        user = get_user("admin")
    else:
        user = get_user("empleado")  # ajustá si tu usuario sin permiso es otro

    print("Usuario elegido:", user.usuario if user else "Usuario no encontrado")

    form = FormListadoPersonal(usuario=user)
    form.show()

    sys.exit(app.exec())
