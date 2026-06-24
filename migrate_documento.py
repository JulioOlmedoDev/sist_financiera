"""
migrate_documento.py — Migración: desdobla 'dni' en 'tipo_documento' + 'nro_documento'.

Aplica sobre: clientes, garantes, personal.

Pasos por tabla:
  1. Agrega columna tipo_documento VARCHAR(20) NULL  (si no existe)
  2. Agrega columna nro_documento  VARCHAR(50) NULL  (si no existe)
  3. Migra registros existentes: tipo_documento='DNI', nro_documento=dni
  4. Elimina el/los índice/s UNIQUE sobre 'dni' (busca el nombre real en
     information_schema; no asume ningún nombre concreto)
  5. Agrega restricción UNIQUE compuesta (tipo_documento, nro_documento)

Idempotente: cada paso verifica antes de actuar. Seguro de correr varias veces.

Uso:
    python migrate_documento.py               # apunta a la base en .env
    DB_NAME=credanzadb python migrate_documento.py   # apunta a producción
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv()

import sqlalchemy as sa
from database import engine

DB_NAME = os.getenv("DB_NAME", "")
DB_TEST = "credanzadb_test"

TABLAS = [
    ("clientes", "uq_clientes_tipo_nro"),
    ("garantes", "uq_garantes_tipo_nro"),
    ("personal", "uq_personal_tipo_nro"),
]


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


def indice_existe(conn, tabla, nombre):
    r = conn.execute(sa.text("""
        SELECT COUNT(*)
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = :t
          AND INDEX_NAME   = :i
    """), {"t": tabla, "i": nombre})
    return r.scalar() > 0


def obtener_indices_unique_sobre_dni(conn, tabla):
    """Devuelve los nombres de todos los índices UNIQUE cuya columna sea 'dni'."""
    r = conn.execute(sa.text("""
        SELECT INDEX_NAME
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = :t
          AND COLUMN_NAME  = 'dni'
          AND NON_UNIQUE   = 0
    """), {"t": tabla})
    return [row[0] for row in r]


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
    print("    • Agregar columnas a las tablas clientes, garantes y personal")
    print("    • Modificar datos existentes (migración tipo/nro_documento)")
    print("    • Eliminar índices UNIQUE sobre 'dni'")
    print("    • Crear nuevas restricciones UNIQUE compuestas")
    print()
    print("  ASEGURATE de tener un dump completo de la base antes de continuar.")
    print("  Ejemplo:  mysqldump -u root -p credanzadb > backup_pre_migra.sql")
    print()
    respuesta = input("  Para confirmar, escribí exactamente CONFIRMAR: ").strip()
    if respuesta != "CONFIRMAR":
        print("\n  Operación cancelada. No se aplicó ningún cambio.")
        sys.exit(0)
    print()


# ── Migración por tabla ────────────────────────────────────────────────────────

def migrar_tabla(conn, tabla, nombre_uq):
    print(f"── Tabla: {tabla}")
    acciones = 0

    # 1. Agregar tipo_documento
    if not columna_existe(conn, tabla, "tipo_documento"):
        conn.execute(sa.text(
            f"ALTER TABLE `{tabla}` ADD COLUMN `tipo_documento` VARCHAR(20) NULL"
        ))
        print(f"   + tipo_documento agregado")
        acciones += 1
    else:
        print(f"   · tipo_documento ya existe")

    # 2. Agregar nro_documento
    if not columna_existe(conn, tabla, "nro_documento"):
        conn.execute(sa.text(
            f"ALTER TABLE `{tabla}` ADD COLUMN `nro_documento` VARCHAR(50) NULL"
        ))
        print(f"   + nro_documento agregado")
        acciones += 1
    else:
        print(f"   · nro_documento ya existe")

    # 3. Migrar datos existentes
    r = conn.execute(sa.text(f"""
        UPDATE `{tabla}`
        SET tipo_documento = 'DNI',
            nro_documento  = dni
        WHERE dni IS NOT NULL
          AND (tipo_documento IS NULL OR nro_documento IS NULL)
    """))
    if r.rowcount > 0:
        print(f"   ✓ {r.rowcount} registro(s) migrado(s): tipo_documento='DNI', nro_documento=dni")
        acciones += 1
    else:
        print(f"   · Datos ya migrados (0 filas actualizadas)")

    # 4. Eliminar índice(s) UNIQUE sobre 'dni' (nombre real desde information_schema)
    indices = obtener_indices_unique_sobre_dni(conn, tabla)
    if indices:
        for nombre_idx in indices:
            conn.execute(sa.text(
                f"ALTER TABLE `{tabla}` DROP INDEX `{nombre_idx}`"
            ))
            print(f"   - Índice UNIQUE '{nombre_idx}' sobre 'dni' eliminado")
            acciones += 1
    else:
        print(f"   · No se encontró índice UNIQUE sobre 'dni' (ya eliminado o no existía)")

    # 5. Agregar UNIQUE compuesto
    if not indice_existe(conn, tabla, nombre_uq):
        conn.execute(sa.text(
            f"ALTER TABLE `{tabla}` ADD CONSTRAINT `{nombre_uq}` "
            f"UNIQUE (`tipo_documento`, `nro_documento`)"
        ))
        print(f"   + UNIQUE({nombre_uq}) creado sobre (tipo_documento, nro_documento)")
        acciones += 1
    else:
        print(f"   · UNIQUE({nombre_uq}) ya existe")

    estado = f"{acciones} acción(es)" if acciones else "nada que hacer"
    print(f"   → {estado}\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print()
    print("═══════════════════════════════════════════════════")
    print("  MIGRACIÓN: desdoblamiento dni → tipo + nro")
    print("═══════════════════════════════════════════════════")
    print()

    confirmar_si_produccion()

    with engine.connect() as conn:
        for tabla, nombre_uq in TABLAS:
            migrar_tabla(conn, tabla, nombre_uq)
        conn.commit()

    print("✅ Migración completada.")
    print()
    print("Podés verificar con:")
    print("  SHOW INDEX FROM clientes;")
    print("  SHOW INDEX FROM garantes;")
    print("  SHOW INDEX FROM personal;")
    print()


if __name__ == "__main__":
    main()
