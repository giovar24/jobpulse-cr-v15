# -*- coding: utf-8 -*-
"""Vuelca la ESTRUCTURA de la BD: tablas, columnas, índices, FK y recuentos.

Herramienta de solo lectura (abre la BD con ``mode=ro``; **no** aplica
migraciones). Sirve para **mantener al día** ``docs/ESTRUCTURA_BD.md``:
después de una migración nueva, comparar la salida contra §4/§2 del doc.

Uso:
  python tools/esquema_bd.py [--db RUTA] [--solo-tablas]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

BD_DEFECTO = Path(__file__).resolve().parent.parent / "data" / "jobpulse_v15.db"


def volcar(con: sqlite3.Connection, solo_tablas: bool) -> list[str]:
    lineas: list[str] = []

    version = con.execute("PRAGMA user_version").fetchone()[0]
    lineas.append(f"PRAGMA user_version (esquema) = {version}")

    tablas = [
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    vistas = [
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
        )
    ]
    disparadores = [
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name"
        )
    ]
    indices = [
        (r[0], r[1])
        for r in con.execute(
            "SELECT name, tbl_name FROM sqlite_master WHERE type='index' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY tbl_name, name"
        )
    ]

    lineas.append("")
    lineas.append(f"TABLAS ({len(tablas)}):")
    for tabla in tablas:
        n = con.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]
        lineas.append(f"  {tabla:<36} rows={n}")
    if vistas:
        lineas.append(f"VISTAS ({len(vistas)}): {', '.join(vistas)}")
    if disparadores:
        lineas.append(f"TRIGGERS ({len(disparadores)}): {', '.join(disparadores)}")
    lineas.append("")
    lineas.append(f"INDICES ({len(indices)}):")
    for nombre, tabla in indices:
        lineas.append(f"  {tabla:<30} {nombre}")

    if solo_tablas:
        return lineas

    lineas.append("")
    lineas.append("=" * 96)
    lineas.append("DETALLE POR TABLA")
    lineas.append("=" * 96)
    for tabla in tablas:
        columnas = con.execute(f'PRAGMA table_info("{tabla}")').fetchall()
        fks = con.execute(f'PRAGMA foreign_key_list("{tabla}")').fetchall()
        n = con.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]
        lineas.append("")
        lineas.append(
            f"### {tabla}  (rows={n}, columnas={len(columnas)}, fk={len(fks)})"
        )
        for col in columnas:
            flags = []
            if col["pk"]:
                flags.append(f"PK:{col['pk']}")
            if col["notnull"]:
                flags.append("NOT NULL")
            if col["dflt_value"] is not None:
                flags.append(f"DEFAULT={col['dflt_value']}")
            sufijo = ("  [" + ", ".join(flags) + "]") if flags else ""
            lineas.append(
                f"    {col['name']:<30} {col['type']:<14}{sufijo}"
            )
        for fk in fks:
            lineas.append(
                f"    FK -> {fk['table']}.{fk['from']}  (ref {fk['to']})  "
                f"on_delete={fk['on_delete']}"
            )
    return lineas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(BD_DEFECTO), help="Ruta de la BD")
    parser.add_argument(
        "--solo-tablas",
        action="store_true",
        help="Solo listado de tablas/columnas/índices (sin detalle por tabla)",
    )
    args = parser.parse_args()

    try:
        con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    except sqlite3.OperationalError as exc:
        print(
            f"ERROR: no se pudo abrir la BD en modo lectura: {args.db}\n"
            f"  ({exc})",
            file=sys.stderr,
        )
        return 2

    con.row_factory = sqlite3.Row
    lineas = volcar(con, args.solo_tablas)
    con.close()

    print("\n".join(lineas))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
