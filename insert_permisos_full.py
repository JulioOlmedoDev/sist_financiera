# insert_permisos_full.py
from database import session
from models import Permiso

# === Definición de permisos con código y nombre ===
# Guardamos el código como prefijo para que sea único/estable y fácil de consultar.
# Formato sugerido: "XXXX Nombre legible"
PERM_DEFS = {
    "0000 Módulo Ventas": [],
    "0001 Módulo Consultas": [],
    "0002 Módulo Productos": [],
    "0003 Módulo Personal": [],
    "0004 Módulo Configurar tasas": [],
    "0005 Módulo Cobros": [],

    # Ventas
    "0010 (crear) clientes": [],
    "0020 (crear) garantes": [],
    "0030 (ver/editar) listado de clientes": [],
    "0040 (ver/editar) listado de garantes": [],
    "0050 (ver) listado de ventas": [],
    "0051 a) Detalle de venta": [],
    "0052 b) Editar venta": [],
    "0053 c) Abrir documentos": [],
    "0054 d) Registrar cobros desde venta": [],
    "0060 (crear) nueva venta": [],

    # Consultas
    "0100 Consultas: selector general": [],
    "0101 a) ventas por fecha": [],
    "0102 b) ventas por cliente": [],
    "0103 c) ventas por producto": [],
    "0104 d) ventas por calificación de cliente": [],
    "0105 e) ventas por personal": [],
    "0106 f) ventas anuladas": [],
    "0107 g) cobros por fecha": [],

    # Productos
    "0200 (crear) categorías": [],
    "0210 (crear) productos": [],
    "0220 (ver/editar) listado categorías y productos": [],

    # Personal
    "0300 (ver) mi perfil": [],
    "0310 (crear) personal": [],
    "0320 (ver/editar) listado de personal": [],
    "0330 (crear) usuario": [],
    "0340 (ver/editar) listado de usuarios": [],
    "0350 Recuperar acceso (blanqueo contraseña)": [],
    "0360 (otorgar) permisos": [],

    # Configurar tasas
    "0400 Configurar tasas": [],

    # Cobros
    "0500 Gestión de cobros": [],
}

def ensure_perm(nombre):
    existe = session.query(Permiso).filter_by(nombre=nombre).first()
    if not existe:
        p = Permiso(nombre=nombre)
        session.add(p)

def main():
    for n in PERM_DEFS.keys():
        ensure_perm(n)
    session.commit()
    print("✅ Permisos (con códigos) verificados/creados.")

if __name__ == "__main__":
    main()
