# main.py
from PySide6.QtWidgets import QApplication, QMessageBox
from sqlalchemy.exc import OperationalError
from gui.dialog_crear_admin import DialogCrearAdmin
from gui.login_form import LoginForm
from gui.ventana_principal import VentanaPrincipal
from database import session
from models import Usuario, Base, engine
import sys

app = QApplication(sys.argv)
ventana_principal = None  # Para que no se destruya la ventana principal

def lanzar_ventana_principal(usuario):
    global ventana_principal
    ventana_principal = VentanaPrincipal(usuario)
    ventana_principal.show()

if __name__ == "__main__":
    # ❶ Crear todas las tablas si no existen aún
    try:
        Base.metadata.create_all(engine)
    except OperationalError as e:
        QMessageBox.critical(None, "Error de Base de Datos", f"No se pudieron crear las tablas:\n{e}")
        sys.exit(1)

    # ❷ Si no hay usuarios en la tabla, crear el super-usuario
    try:
        existe = session.query(Usuario).count() > 0
    except OperationalError as e:
        QMessageBox.critical(None, "Error de Base de Datos", f"No se puede acceder a la tabla usuarios:\n{e}")
        sys.exit(1)

    if not existe:
        dialog = DialogCrearAdmin()
        if dialog.exec() != DialogCrearAdmin.Accepted:
            QMessageBox.information(None, "Atención", "No se creó el super-usuario. Saliendo.")
            sys.exit(0)

    # ❸ Abrir el formulario de login
    login = LoginForm(on_login_success=lanzar_ventana_principal)
    login.show()

    # ❹ Iniciar el loop de la aplicación
    sys.exit(app.exec())

