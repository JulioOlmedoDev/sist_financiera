# insert_roles.py
from database import session
from models import Rol

if not session.query(Rol).filter_by(nombre="Administrador").first():
    session.add(Rol(nombre="Administrador"))
    session.commit()
    print("✅ Rol Administrador creado.")
else:
    print("ℹ️ Rol Administrador ya existe.")
