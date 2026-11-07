"""Compara dos salidas de ``tools/estado_extraccion.py`` (ANTES vs DESPUES).

Sirve para medir que aporta una corrida (pase IA, curacion de la taxonomia,
re-barrido...) sobre la EXTRACCION de codigo y sobre el matching:

    .\\.venv\\Scripts\\python.exe -X utf8 tools\\estado_extraccion.py antes antes.json
    # ... la corrida ...
    .\\.venv\\Scripts\\python.exe -X utf8 tools\\estado_extraccion.py despues despues.json
    .\\.venv\\Scripts\\python.exe -X utf8 tools\\comparar_extraccion.py antes.json despues.json

OJO al leer el resultado: que la cobertura de codigo se quede igual NO es
"no mejoro" si lo que se midio fue otra cosa (p.ej. la cobertura del CORPUS:
mas avisos con requisitos, mas campos estructurados).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SEP = "=" * 74


def _delta(a: float, b: float) -> str:
    d = b - a
    return ("%+d" % d) if d else "0"


def _bloque(titulo: str, filas: list[tuple[str, float, float, str]]) -> None:
    print(SEP)
    print(titulo)
    print(SEP)
    for etiqueta, a, b, sufijo in filas:
        print("  %-42s %10s -> %10s  %s%s" % (etiqueta, a, b, _delta(a, b), sufijo))


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    antes = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    despues = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

    print(SEP)
    print("COMPARACION DE LA EXTRACCION DE CODIGO  (%s -> %s)"
          % (antes["etiqueta"], despues["etiqueta"]))
    print(SEP)

    _bloque("1. REQUISITOS (lo que el motor VE)", [
        ("requisitos vigentes", antes["requisitos_vigentes"],
         despues["requisitos_vigentes"], ""),
        ("requisitos CON codigo_canonico", antes["requisitos_con_codigo"],
         despues["requisitos_con_codigo"], ""),
        ("requisitos SIN codigo (invisibles)", antes["requisitos_sin_codigo"],
         despues["requisitos_sin_codigo"], ""),
        ("cobertura de codigo (%)", antes["cobertura_codigo_pct"],
         despues["cobertura_codigo_pct"], "%"),
        ("variantes distintas con codigo", antes["variantes_distintas_con_codigo"],
         despues["variantes_distintas_con_codigo"], ""),
        ("codigos canonicos distintos usados", antes["codigos_distintos_usados"],
         despues["codigos_distintos_usados"], ""),
        ("avisos SIN ningun requisito", antes["avisos_sin_ningun_requisito"],
         despues["avisos_sin_ningun_requisito"], ""),
    ])

    _bloque("2. TAXONOMIA (variante -> codigo canonico)", [
        ("conceptos en la taxonomia", antes["conceptos_en_taxonomia"],
         despues["conceptos_en_taxonomia"], ""),
        ("cola concepto_no_normalizado", antes["cola_taxonomia"],
         despues["cola_taxonomia"], ""),
    ])

    print(SEP)
    print("3. REQUISITOS POR CATEGORIA (con codigo / total)")
    print(SEP)
    for cat in sorted(set(antes["por_categoria"]) | set(despues["por_categoria"])):
        a = antes["por_categoria"].get(cat, {"con_codigo": 0, "total": 0})
        b = despues["por_categoria"].get(cat, {"con_codigo": 0, "total": 0})
        print("  %-12s %5d/%-5d -> %5d/%-5d   (%+d requisitos, %+d sin codigo)"
              % (cat, a["con_codigo"], a["total"], b["con_codigo"], b["total"],
                 b["total"] - a["total"],
                 (b["total"] - b["con_codigo"]) - (a["total"] - a["con_codigo"])))

    print()
    print(SEP)
    print("4. REQUISITOS POR ORIGEN")
    print(SEP)
    for org in sorted(set(antes["por_origen"]) | set(despues["por_origen"])):
        a = antes["por_origen"].get(org, 0)
        b = despues["por_origen"].get(org, 0)
        print("  %-14s %5d -> %5d   (%+d)" % (org, a, b, b - a))

    print()
    print(SEP)
    print("5. CAMPOS ESTRUCTURADOS (los que produce la IA)")
    print(SEP)
    for campo in antes["campos"]:
        a = antes["campos"][campo]["llenos"]
        b = despues["campos"][campo]["llenos"]
        print("  %-18s %4d -> %4d   (%+d)   pendientes %d -> %d"
              % (campo, a, b, b - a,
                 antes["campos"][campo]["pendientes"],
                 despues["campos"][campo]["pendientes"]))

    print()
    print(SEP)
    print("6. MATCHING (Paso 5)")
    print(SEP)
    print("  corrida vigente: %s -> %s"
          % (antes["match_corrida"], despues["match_corrida"]))
    for est in sorted(set(antes["match_estados"]) | set(despues["match_estados"])):
        a = antes["match_estados"].get(est, 0)
        b = despues["match_estados"].get(est, 0)
        print("  %-22s %4d -> %4d   (%+d)" % (est, a, b, b - a))
    print("  %-22s %4d -> %4d   (%+d)   <-- solo lo firma una 2a persona"
          % ("educacion_no_confirmada", antes["educacion_no_confirmada"],
             despues["educacion_no_confirmada"],
             despues["educacion_no_confirmada"] - antes["educacion_no_confirmada"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
