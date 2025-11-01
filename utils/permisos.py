# utils/permisos.py
from typing import Optional
from database import session as dbsession
from models import Permiso, Usuario

# Modo compatibilidad: si aún no migraste permisos, no bloquear la UI.
try:
    _PERM_COUNT = dbsession.query(Permiso).count()
    _SAFE_MODE = (_PERM_COUNT == 0)
except Exception:
    _SAFE_MODE = True  # si falla la DB al importar, no bloquear

# 🔑 Roles que consideramos "admin total" por política de negocio
ADMIN_ROLES = {"Administrador", "Gerente"}
ADMIN_WILDCARD_PERMISSION = "admin_total"

def es_admin(usuario: Usuario) -> bool:
    """
    Es admin si:
      - su rol.nombre está en ADMIN_ROLES (Administrador o Gerente), o
      - posee el permiso 'admin_total'.
    """
    try:
        if not usuario:
            return False
        rol = getattr(usuario, "rol", None)
        if rol and (rol.nombre or "").strip() in ADMIN_ROLES:
            return True
        return any((p.nombre == ADMIN_WILDCARD_PERMISSION) for p in getattr(usuario, "permisos", []) or [])
    except Exception:
        return False

def tiene_permiso(usuario: Usuario, nombre_permiso: str) -> bool:
    """
    - Admin => True siempre.
    - Compatibilidad: si no hay permisos en DB, True (no romper UI).
    - Caso normal: True si el usuario posee el permiso exacto.
    """
    if es_admin(usuario):
        return True
    if _SAFE_MODE:
        return True
    try:
        return any((p.nombre == nombre_permiso) for p in getattr(usuario, "permisos", []) or [])
    except Exception:
        return False

def contar_admins_activos(db) -> int:
    """
    Cuenta admins activos: usuarios con activo=True y (rol en ADMIN_ROLES o permiso 'admin_total').
    """
    from sqlalchemy.orm import aliased
    from models import Usuario, Rol, UsuarioPermiso, Permiso

    r = aliased(Rol)
    up = aliased(UsuarioPermiso)
    pe = aliased(Permiso)

    # Admin por rol (Administrador o Gerente)
    q_rol = db.query(Usuario.id).join(r, Usuario.rol_id == r.id, isouter=True)\
        .filter(Usuario.activo == True, r.nombre.in_(list(ADMIN_ROLES)))

    # Admin por permiso comodín
    q_perm = db.query(Usuario.id).join(up, up.usuario_id == Usuario.id)\
        .join(pe, pe.id == up.permiso_id)\
        .filter(Usuario.activo == True, pe.nombre == ADMIN_WILDCARD_PERMISSION)

    admin_ids = set([uid for (uid,) in q_rol.all()] + [uid for (uid,) in q_perm.all()])
    return len(admin_ids)

def tiene_permiso_match(usuario: Usuario, *tokens: str) -> bool:
    """
    Igual que tiene_permiso pero tolerante:
    - Matchea si ALGUNO de los tokens aparece como substring en el nombre del permiso.
    - Ejemplo: tokens ("cargar_cliente", "0010") => True si el permiso se llama
      "0010 (crear) clientes" o "cargar_cliente" o "ventas.cargar_cliente", etc.
    """
    if es_admin(usuario):
        return True
    if _SAFE_MODE:
        return True
    try:
        user_perms = [(p.nombre or "").lower() for p in getattr(usuario, "permisos", []) or []]
        want = [t.lower() for t in tokens if t]
        for up in user_perms:
            for t in want:
                if t in up:
                    return True
        return False
    except Exception:
        return False

