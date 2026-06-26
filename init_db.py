"""
init_db.py — Inicialización completa de la base de datos desde cero.

Uso:
    python init_db.py

Idempotente: se puede ejecutar sobre una base ya inicializada sin perder datos.
"""
import getpass
import sys

from dotenv import load_dotenv

load_dotenv()

from database import engine, get_session
from models import Base, Permiso, Rol, Usuario
from utils.security import hash_password

# ── Datos canónicos ────────────────────────────────────────────────────────────

ROLES = ["Administrador", "Gerente", "Coordinador", "Administrativo"]

PERMISOS = [
    "admin_total",  # wildcard — requerido por permisos.py
    # Módulos
    "0000 Módulo Ventas",
    "0001 Módulo Consultas",
    "0002 Módulo Productos",
    "0003 Módulo Personal",
    "0004 Módulo Configurar tasas",
    "0005 Módulo Cobros",
    # Ventas
    "0010 (crear) clientes",
    "0020 (crear) garantes",
    "0030 (ver/editar) listado de clientes",
    "0040 (ver/editar) listado de garantes",
    "0050 (ver) listado de ventas",
    "0051 a) Detalle de venta",
    "0052 b) Editar venta",
    "0053 c) Abrir documentos",
    "0054 d) Registrar cobros desde venta",
    "0060 (crear) nueva venta",
    # Consultas
    "0100 Consultas: selector general",
    "0101 a) ventas por fecha",
    "0102 b) ventas por cliente",
    "0103 c) ventas por producto",
    "0104 d) ventas por calificación de cliente",
    "0105 e) ventas por personal",
    "0106 f) ventas anuladas",
    "0107 g) cobros por fecha",
    # Productos
    "0200 (crear) categorías",
    "0210 (crear) productos",
    "0220 (ver/editar) listado categorías y productos",
    # Personal
    "0300 (ver) mi perfil",
    "0310 (crear) personal",
    "0320 (ver/editar) listado de personal",
    "0330 (crear) usuario",
    "0340 (ver/editar) listado de usuarios",
    "0350 Recuperar acceso (blanqueo contraseña)",
    "0360 (otorgar) permisos",
    # Tasas / Cobros
    "0400 Configurar tasas",
    "0500 Gestión de cobros",
]


# ── Pasos ──────────────────────────────────────────────────────────────────────

def paso_crear_tablas() -> None:
    print("── [1/5] Creando tablas...")
    Base.metadata.create_all(engine)
    print("   ✓ Tablas verificadas/creadas.")


def paso_seed_roles(session) -> None:
    print("── [2/5] Verificando roles...")
    creados = []
    for nombre in ROLES:
        if not session.query(Rol).filter_by(nombre=nombre).first():
            session.add(Rol(nombre=nombre))
            creados.append(nombre)
    session.flush()
    if creados:
        print(f"   ✓ Roles nuevos: {', '.join(creados)}")
    else:
        print("   · Todos los roles ya existían.")


def paso_seed_permisos(session) -> None:
    print("── [3/5] Verificando permisos...")
    creados = 0
    for nombre in PERMISOS:
        if not session.query(Permiso).filter_by(nombre=nombre).first():
            session.add(Permiso(nombre=nombre))
            creados += 1
    session.flush()
    total = session.query(Permiso).count()
    if creados:
        print(f"   ✓ {creados} permiso(s) nuevo(s). Total en DB: {total}.")
    else:
        print(f"   · Todos los permisos ya existían ({total} en DB).")


def paso_crear_admin(session) -> bool:
    """
    Devuelve True si se creó un admin nuevo, False si se saltó.
    """
    print("── [4/5] Administrador...")

    count = session.query(Usuario).count()
    if count > 0:
        print(f"   · Ya hay {count} usuario(s) en la base.")
        resp = input("   ¿Crear un nuevo admin de todas formas? [s/N]: ").strip().lower()
        if resp != "s":
            print("   · Se omite la creación del admin.")
            return False

    print()
    print("   Ingresá los datos del administrador:")

    while True:
        nombre = input("   Usuario: ").strip()
        if not nombre:
            print("   El nombre de usuario no puede estar vacío.")
            continue
        if session.query(Usuario).filter_by(nombre=nombre).first():
            print(f"   El usuario «{nombre}» ya existe. Elegí otro.")
            continue
        break

    while True:
        email = input("   Email:   ").strip()
        if not email or "@" not in email or "." not in email:
            print("   Ingresá un email válido.")
            continue
        if session.query(Usuario).filter_by(email=email).first():
            print(f"   El email «{email}» ya está en uso.")
            continue
        break

    while True:
        pwd1 = getpass.getpass("   Contraseña:         ")
        if len(pwd1) < 6:
            print("   La contraseña debe tener al menos 6 caracteres.")
            continue
        pwd2 = getpass.getpass("   Confirmar contraseña: ")
        if pwd1 != pwd2:
            print("   Las contraseñas no coinciden.")
            continue
        break

    pwd_hash = hash_password(pwd1)

    rol_admin = session.query(Rol).filter_by(nombre="Administrador").first()
    todos_los_permisos = session.query(Permiso).all()

    admin = Usuario(
        nombre=nombre,
        email=email,
        password=pwd_hash,
        rol_id=rol_admin.id if rol_admin else None,
        personal_id=None,
        activo=True,
        must_change_password=False,
    )
    admin.permisos.extend(todos_los_permisos)
    session.add(admin)
    session.flush()

    print(f"\n   ✓ Admin «{nombre}» creado con rol «Administrador» y {len(todos_los_permisos)} permiso(s).")
    return True


def paso_informe(session) -> None:
    print("── [5/5] Resumen:")
    print(f"   Roles:    {session.query(Rol).count()}")
    print(f"   Permisos: {session.query(Permiso).count()}")
    print(f"   Usuarios: {session.query(Usuario).count()}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print()
    print("═══════════════════════════════════════════")
    print("  INICIALIZACIÓN DE BASE DE DATOS")
    print("═══════════════════════════════════════════")
    print()

    try:
        paso_crear_tablas()

        with get_session() as session:
            paso_seed_roles(session)
            paso_seed_permisos(session)
            session.commit()

            paso_crear_admin(session)
            session.commit()

            print()
            paso_informe(session)

    except Exception as exc:
        print(f"\n❌ Error durante la inicialización: {exc}", file=sys.stderr)
        sys.exit(1)

    print()
    print("✅ Base de datos inicializada correctamente.")
    print()


if __name__ == "__main__":
    main()
