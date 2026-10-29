# -*- coding: utf-8 -*-
"""Verificacion de trazabilidad: valida por corrida + delta de estados."""
import sqlite3
import sys

conn = sqlite3.connect("data/jobpulse_v15.db")
conn.row_factory = sqlite3.Row

print("=== A) CORRIDAS: filas y valida ===")
for r in conn.execute(
    """SELECT corrida_id, COUNT(*) filas,
              SUM(CASE WHEN valida = 1 THEN 1 ELSE 0 END) vigentes
       FROM job_match GROUP BY corrida_id ORDER BY corrida_id"""
):
    print("  %-16s filas=%-4s valida=1 -> %s" % (r["corrida_id"], r["filas"], r["vigentes"]))

print()
print("=== B) DISTRIBUCION por corrida (estado x motivo) ===")
for cid in [r[0] for r in conn.execute("SELECT DISTINCT corrida_id FROM job_match ORDER BY corrida_id")]:
    print("  -- corrida %s" % cid)
    for r in conn.execute(
        """SELECT estado, motivo, COUNT(*) n FROM job_match
           WHERE corrida_id = ? GROUP BY estado, motivo ORDER BY estado, motivo""",
        (cid,),
    ):
        print("     %-22s | %-32s | %d" % (r["estado"], r["motivo"], r["n"]))

nueva = conn.execute(
    "SELECT corrida_id FROM job_match WHERE valida = 1 ORDER BY corrida_id DESC LIMIT 1"
).fetchone()[0]
anterior = conn.execute(
    """SELECT corrida_id FROM job_match WHERE valida = 0
       AND corrida_id < ? ORDER BY corrida_id DESC LIMIT 1""",
    (nueva,),
).fetchone()[0]

print()
print("=== C) DELTA %s -> %s ===" % (anterior, nueva))
prev = {r["job_id"]: r for r in conn.execute(
    "SELECT job_id, estado, motivo FROM job_match WHERE corrida_id = ?", (anterior,))}
nue = {r["job_id"]: r for r in conn.execute(
    "SELECT job_id, estado, motivo FROM job_match WHERE corrida_id = ?", (nueva,))}

cambios = [j for j in prev if j in nue and (prev[j]["estado"] != nue[j]["estado"]
                                            or prev[j]["motivo"] != nue[j]["motivo"])]
print("  jobs con cambio de estado/motivo: %d" % len(cambios))
for j in sorted(cambios):
    print("    %s" % j)
    print("       %-18s %-30s -> %-18s %s" % (
        prev[j]["estado"], prev[j]["motivo"], nue[j]["estado"], nue[j]["motivo"]))

print()
print("=== D) MOTIVOS de la nueva corrida: educacion_no_confirmada (18) ===")
for r in conn.execute(
    """SELECT job_id FROM job_match WHERE corrida_id = ?
       AND motivo = 'educacion_no_confirmada' ORDER BY job_id""",
    (nueva,),
):
    print("    %s" % r["job_id"])
conn.close()
