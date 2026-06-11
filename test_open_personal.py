from PySide6.QtWidgets import QApplication
from gui.form_personal import FormPersonal
from database import get_session
from models import Usuario
import sys

"""
Probá esto con la app cerrada:
python test_open_personal.py
"""

def get_user(username):
    with get_session() as session:
        return session.query(Usuario).filter_by(nombre=username).first()

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
        user = get_user("empleado")

    print("Usuario elegido:", user.nombre if user else "Usuario no encontrado")

    form = FormPersonal(usuario=user)
    form.show()

    sys.exit(app.exec())
