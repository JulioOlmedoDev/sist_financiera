"""
migrate_drop_dni.py — Elimina la columna 'dni' de las tablas clientes, garantes y personal.

Idempotente: si la columna ya no existe en una tabla, informa y continúa sin error.
Requiere confirmación explícita en bases que no sean credanzadb_test.

Uso:
    python migrate_drop_dni.py                        # base en .env
    DB_NAME=credanzadb python migrate_drop_dni.py     # producción explícita
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv()

import sqlalchemy as sa
from database import engine

DB_NAME = os.getenv("DB_NAME", "")
DB_TEST = "credanzadb_test"

TABLAS = ["clientes", "garantes", "personal"]


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
    print("    • Eliminar la columna 'dni' de las tablas clientes, garantes y personal")
    print()
    print("  DROP COLUMN es IRREVERSIBLE. Los datos de la columna 'dni'")
    print("  se pierden definitivamente. Asegurate de tener un backup completo.")
    print("  Ejemplo:  mysqldump -u root -p credanzadb > backup_pre_drop_dni.sql")
    print()
    respuesta = input("  Para confirmar, escribí exactamente CONFIRMAR: ").strip()
    if respuesta != "CONFIRMAR":
        print("\n  Operación cancelada. No se aplicó ningún cambio.")
        sys.exit(0)
    print()


# ── Migración por tabla ────────────────────────────────────────────────────────

def drop_dni_si_existe(conn, tabla):
    print(f"── Tabla: {tabla}")
    if columna_existe(conn, tabla, "dni"):
        conn.execute(sa.text(f"ALTER TABLE `{tabla}` DROP COLUMN `dni`"))
        print(f"   ✓ columna 'dni' eliminada")
    else:
        print(f"   · columna 'dni' ya no existe, sin acción")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print()
    print("═══════════════════════════════════════════════════")
    print("  MIGRACIÓN: eliminación de la columna dni")
    print("═══════════════════════════════════════════════════")
    print()

    confirmar_si_produccion()

    with engine.connect() as conn:
        for tabla in TABLAS:
            drop_dni_si_existe(conn, tabla)
        conn.commit()

    print()
    print("✅ Migración completada.")
    print()
    print("Podés verificar con:")
    print("  DESCRIBE clientes;")
    print("  DESCRIBE garantes;")
    print("  DESCRIBE personal;")
    print()


if __name__ == "__main__":
    main()
