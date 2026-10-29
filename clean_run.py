#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Limpieza completa para corrida limpia: borra todo lo de scraping,
mantiene perfil de usuario y configuración.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("data/jobpulse_v15.db")

TABLES_TO_CLEAR = [
    # Datos de scraping
    "jobs",
    "job_analysis",
    "job_requirements",
    "job_field_status",
    "job_manual_overrides",
    "job_source_records",
    "source_run_sites",
    "source_runs",
    "source_job_memory",
    # IA/enriquecimiento
    "candidate_profile_import_snapshots",
]

TABLES_TO_KEEP = [
    # Perfil de usuario
    "candidate_profile_facts",
    "candidate_profile_imports",
    # Configuración
    "source_platforms",
    "source_sites",
    "source_sites_review_log",
    "user_job_state",
    "applications",
]

def main() -> int:
    import sys
    if not DB_PATH.exists():
        print(f"BD no existe: {DB_PATH}")
        return 1

    # Confirmar via arg
    if len(sys.argv) < 2 or sys.argv[1].upper() != "SI":
        print("⚠️  Uso: python clean_run.py SI")
        print("   Esto borrará TODOS los jobs, análisis, runs, source_records.")
        print("   Se MANTIENEN: perfil usuario, sitios, plataformas, credenciales, estado manual.")
        return 0

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")

    try:
        # Verificar tablas existentes
        existing = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        cleared = []
        for table in TABLES_TO_CLEAR:
            if table in existing:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                conn.execute(f"DELETE FROM {table}")
                # Reset autoincrement si existe
                conn.execute(f"DELETE FROM sqlite_sequence WHERE name = '{table}'")
                cleared.append(f"{table} ({count} filas)")
                print(f"  🗑️  {table}: {count} filas borradas")

        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()

        # Vacuum para liberar espacio
        conn.execute("VACUUM")
        conn.close()

        print(f"\n✅ Limpieza completada. Tablas borradas: {len(cleared)}")
        for c in cleared:
            print(f"   - {c}")
        print("\n✅ Mantenidas intactas: perfil usuario, sitios, plataformas, credenciales")

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())