# insert_roles.py
from database import get_session
from models import Rol

with get_session() as session:
    if not session.query(Rol).filter_by(nombre="Administrador").first():
        session.add(Rol(nombre="Administrador"))
        session.commit()
        print("✅ Rol Administrador creado.")
    else:
        print("ℹ️ Rol Administrador ya existe.")
