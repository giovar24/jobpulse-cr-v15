# -*- coding: utf-8 -*-
"""Genera el documento de evidencia de la corrida VIGENTE del Paso 5.

ENVOLTORIO FINO: la logica vive en ``jobpulse_v15.evidencia.generar_evidencia``
(O12 · Ola 1.4), para que la UI pueda generar y verificar la evidencia **sin
subprocess** y mostrar "evidencia: al dia / desactualizada" tras cada corrida.

Por omision escribe ``docs/PASO5_EVIDENCIA_<fecha de la corrida>.md`` (p. ej.
``PASO5_EVIDENCIA_2026-11-04.md``); el nombre lo decide la corrida vigente, no
una fecha fija, para que una corrida nueva no pise el documento de otro dia.
Se puede indicar otro archivo como argumento.

Uso: .\\.venv\\Scripts\\python.exe -X utf8 generar_evidencia_paso5.py [salida]
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "src"))

from jobpulse_v15 import evidencia  # noqa: E402


def main() -> int:
    salida = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    resultado = evidencia.generar_evidencia(
        db_path=REPO / "data" / "jobpulse_v15.db",
        docs_dir=REPO / "docs",
        salida=salida,
        log=lambda _texto: None,  # el envoltorio imprime UNA linea de resumen
    )
    print(
        "escrito %s (%d lineas) | corrida=%s | descartada=%d | no_confirmada=%d"
        % (
            resultado["ruta"],
            resultado["lineas"],
            resultado["corrida"],
            resultado["descartadas"],
            resultado["no_confirmadas"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
