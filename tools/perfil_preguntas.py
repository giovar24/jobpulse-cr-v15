# -*- coding: utf-8 -*-
"""Cuestionario generico de perfil (envoltorio de verificacion).

La implementacion UNICA vive en ``jobpulse_v15.perfil_huecos`` (la misma que
usa la pestaña Perfil de la UI v2). Este tool solo la imprime en formato
legible/JSON para sesiones y scripts; **no** duplica la logica.

Deriva las preguntas de la BD cargada: compara lo que el CORPUS pide
(requisitos evaluables con ``codigo_canonico``) contra lo que el PERFIL
registra. No asume NADA del titular.

SOLO LECTURA (abre la BD con ``mode=ro``; no aplica migraciones).

Uso:
  python tools/perfil_preguntas.py [--db RUTA] [--top 30] [--json]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from jobpulse_v15 import perfil_huecos
from jobpulse_v15.perfil_huecos import HuecosPerfil

BD_DEFECTO = Path(__file__).resolve().parent.parent / "data" / "jobpulse_v15.db"


def a_json(huecos: HuecosPerfil, top: int) -> dict:
    """El cuestionario como dict (para consumirlo desde otro script)."""
    por_categoria = huecos.por_categoria()
    salida: dict = {}
    for categoria, lista in por_categoria.items():
        bloque: dict = {
            "total_fuera": len(lista),
            "faltan": [
                {
                    "codigo": h.codigo,
                    "avisos": h.avisos,
                    "niveles": list(h.niveles),
                    "calificadores": list(h.calificadores),
                }
                for h in lista[:top]
            ],
        }
        if categoria in perfil_huecos.CATEGORIAS_CERRADAS:
            bloque["tipo"] = "cerrada"
            bloque["opciones"] = [
                o.codigo for o in huecos.opciones if o.categoria == categoria
            ]
        salida[categoria] = bloque

    if huecos.areas_catalogo and not huecos.areas_marcadas:
        salida["area"] = {
            "tipo": "lista",
            "pregunta": (
                "Sin areas marcadas se evalua TODO el corpus. "
                "¿Que areas le interesan a la persona? (1 o mas)"
            ),
            "marcadas": list(huecos.areas_marcadas),
            "catalogo": [
                {"codigo": c, "nombre": n} for c, n in huecos.areas_catalogo
            ],
        }
    if huecos.sin_canonico:
        salida["_sin_codigo_canonico"] = {
            "tipo": "aviso",
            "mensaje": (
                "Hechos de categorias motor SIN codigo_canonico: el motor "
                "los ignora. Resolver con `enrich profile-canonico --apply` "
                "o re-registrarlos."
            ),
            "hechos": [
                {"category": h.categoria, "value_code": h.value_code,
                 "value_text": h.value_text}
                for h in huecos.sin_canonico
            ],
        }
    return salida


def imprimir(huecos: HuecosPerfil, top: int) -> None:
    if huecos.vacios:
        print("El perfil ya cubre todo lo que el corpus pide: nada que preguntar.")
        return
    print(f"Avisos evaluables: {huecos.avisos_evaluables} · "
          f"datos de perfil: {huecos.avisos_con_perfil}")
    for categoria, lista in huecos.por_categoria().items():
        cerrada = categoria in perfil_huecos.CATEGORIAS_CERRADAS
        print(f"\n===== {categoria.upper()} ({len(lista)} fuera) =====")
        if cerrada:
            print("  Categoria CERRADA: el titular elige entre las opciones.")
        for hueco in lista[:top]:
            extra = f" niveles={list(hueco.niveles)}" if hueco.niveles else ""
            print(f"    [ ] {hueco.codigo:<32} avisos={hueco.avisos:<4}{extra}")
        if len(lista) > top:
            print(f"    … y {len(lista) - top} mas (usa --top N)")
        if cerrada:
            opciones = [o.codigo for o in huecos.opciones
                        if o.categoria == categoria]
            print(f"    Opciones: {', '.join(opciones)}")

    if huecos.areas_catalogo and not huecos.areas_marcadas:
        print("\n===== AREA (ninguna marcada) =====")
        print("  Sin areas marcadas se evalua TODO el corpus.")
        for codigo, nombre in huecos.areas_catalogo:
            print(f"    [ ] {codigo:<22} {nombre}")
    elif huecos.areas_marcadas:
        print(f"\n===== AREA =====\n  Marcadas: {', '.join(huecos.areas_marcadas)}")

    if huecos.sin_canonico:
        print("\n===== SIN CODIGO CANONICO (el motor los ignora) =====")
        for h in huecos.sin_canonico:
            print(f"    - [{h.categoria}] {h.value_code} = {h.value_text}")

    print("\n(Respuestas -> UI v2 pestana Perfil → «Completar perfil».)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(BD_DEFECTO), help="Ruta de la BD")
    parser.add_argument("--top", type=int, default=30,
                        help="Items a mostrar por categoria (30)")
    parser.add_argument("--json", action="store_true",
                        help="Salida JSON (para consumirla desde otra sesion)")
    args = parser.parse_args()

    try:
        con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    except sqlite3.OperationalError as exc:
        print(f"ERROR: no se pudo abrir la BD en modo lectura: {args.db}\n"
              f"  ({exc})", file=sys.stderr)
        return 2

    huecos = perfil_huecos.calcular_huecos(con)
    con.close()

    if args.json:
        print(json.dumps(a_json(huecos, args.top), ensure_ascii=False, indent=2))
        return 0
    imprimir(huecos, args.top)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
