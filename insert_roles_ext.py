# insert_roles_ext.py
from database import get_session
from models import Rol

NEEDED = ["Administrador", "Gerente", "Coordinador", "Administrativo"]

with get_session() as session:
    for nombre in NEEDED:
        if not session.query(Rol).filter_by(nombre=nombre).first():
            session.add(Rol(nombre=nombre))
    session.commit()
print("✅ Roles verificados/creados:", ", ".join(NEEDED))
