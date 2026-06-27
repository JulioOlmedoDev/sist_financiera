"""
migrate_totp_set_by_admin.py — Agrega la columna 'totp_set_by_admin' a la tabla usuarios.

Indica si el token 2FA fue impuesto por un administrador (True) o activado por
el propio usuario (False). Permite controlar quién puede desactivarlo.

Idempotente: si la columna ya existe, informa y no hace nada.
Requiere confirmación explícita en bases que no sean credanzadb_test.

Uso:
    python migrate_totp_set_by_admin.py               # base apuntada en .env
    DB_NAME=credanzadb python migrate_totp_set_by_admin.py   # producción explícita
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv()

import sqlalchemy as sa
from database import engine

DB_NAME = os.getenv("DB_NAME", "")
DB_TEST = "credanzadb_test"


# ── Helpers ────────────────────────────────────────────────────────────────────

def columna_existe(conn, tabla, col):
    r = conn.execute(sa.text("""
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = :t
          AND COLUMN_NAME  = :c
    """), {"t": tabla, "c": col})
    return r.scalar() > 0


# ── Confirmación para producción ───────────────────────────────────────────────

def confirmar_si_produccion():
    if DB_NAME == DB_TEST:
        print(f"ℹ  Base de datos de test detectada ({DB_TEST}). Continuando sin confirmación.\n")
        return

    print()
    print("=" * 60)
    print("  ⚠️  ATENCIÓN: BASE DE DATOS DE PRODUCCIÓN")
    print("=" * 60)
    print(f"  Base apuntada: {DB_NAME}")
    print()
    print("  Esta operación va a:")
    print("    • Agregar la columna 'totp_set_by_admin' a la tabla usuarios")
    print("      (TINYINT(1) NOT NULL DEFAULT 0 — ningún registro existente se modifica)")
    print()
    print("  ASEGURATE de tener un dump completo de la base antes de continuar.")
    print("  Ejemplo:  mysqldump -u root -p credanzadb > backup_pre_totp_admin.sql")
    print()
    respuesta = input("  Para confirmar, escribí exactamente CONFIRMAR: ").strip()
    if respuesta != "CONFIRMAR":
        print("\n  Operación cancelada. No se aplicó ningún cambio.")
        sys.exit(0)
    print()


# ── Migración ─────────────────────────────────────────────────────────────────

def migrar_usuarios(conn):
    print("── Tabla: usuarios")
    if not columna_existe(conn, "usuarios", "totp_set_by_admin"):
        conn.execute(sa.text(
            "ALTER TABLE `usuarios` ADD COLUMN `totp_set_by_admin` TINYINT(1) NOT NULL DEFAULT 0"
        ))
        print("   + totp_set_by_admin agregado (default 0)")
    else:
        print("   · totp_set_by_admin ya existe, sin acción")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print()
    print("═══════════════════════════════════════════════════")
    print("  MIGRACIÓN: totp_set_by_admin en usuarios")
    print("═══════════════════════════════════════════════════")
    print()

    confirmar_si_produccion()

    with engine.connect() as conn:
        migrar_usuarios(conn)
        conn.commit()

    print()
    print("✅ Migración completada.")
    print()
    print("Podés verificar con:")
    print("  DESCRIBE usuarios;")
    print()


if __name__ == "__main__":
    main()
