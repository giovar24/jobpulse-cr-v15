# -*- coding: utf-8 -*-
"""Verifica POR CONSULTA que el documento de evidencia contiene, con TEXTO
LITERAL, cada vacante de la corrida vigente.

ENVOLTORIO FINO: la logica vive en
``jobpulse_v15.evidencia.verificar_evidencia`` (O12 · Ola 1.4).

Para cada vacante `descartada` (y cada `educacion_no_confirmada`) comprueba:

1. que el `job_id` aparezca en el documento de evidencia de la corrida
   vigente (``docs/PASO5_EVIDENCIA_*.md``);
2. que la FRASE LITERAL que confirma el titulo aparezca en el documento;
3. que esa frase sea un substring LITERAL del texto de la oferta en la BD
   (``requirements_raw`` + ``description_raw``) -> no es un resumen.

Ademas comprueba que las 13 vacantes promovidas por la corrida anterior
siguen documentadas con frase literal.

Uso: .\\.venv\\Scripts\\python.exe -X utf8 verificar_evidencia.py [doc]
Salida: 0 si todo cuadra, 1 si hay discrepancias.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "src"))

from jobpulse_v15 import evidencia  # noqa: E402


def main() -> int:
    doc = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    resultado = evidencia.verificar_evidencia(
        db_path=REPO / "data" / "jobpulse_v15.db",
        docs_dir=REPO / "docs",
        doc=doc,
    )
    return 0 if resultado["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
