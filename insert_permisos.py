from database import get_session
from models import Permiso

permisos_base = [
    "admin_total",
    "crear_venta",
    "ver_ventas",
    "cargar_cliente",
    "cargar_personal",
    "asignar_usuario",
    "asignar_permisos",
    "crear_producto",
    "crear_categoria",
    "consultar_morosos",
    "realizar_cobro"
]

with get_session() as session:
    for nombre in permisos_base:
        existe = session.query(Permiso).filter_by(nombre=nombre).first()
        if not existe:
            nuevo = Permiso(nombre=nombre)
            session.add(nuevo)
    session.commit()
print("✅ Permisos cargados correctamente.")
