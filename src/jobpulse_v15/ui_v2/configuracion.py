# -*- coding: utf-8 -*-
"""Configuración persistente de la UI v2 (SIN Tk).

Comparte el archivo con la UI clásica: `~/.jobpulse_v15/ui_config.json`.
REGLA DE ORO: SIEMPRE cargar → update → guardar. El mismo archivo lo
escriben `ciclo_vida` (O8) y la ventana de configuración clásica:
sobrescribir el dict completo perdería sus claves (bug ya vivido en
`configuration_window._save_all`).

Claves que usa la UI v2:
- `paleta`  : nombre del esquema de color (ver `theme.PALETAS`).
- `csv_dir` : directorio inicial de los diálogos "Exportar CSV"
              ("" = sin fijo → Tk usa su última carpeta).

El `.env` del proyecto (IA_PROVEEDOR/IA_BASE_URL/IA_MODEL/IA_API_KEY y los
límites opt-in IA_MAX_LLAMADAS/IA_RPM) se escribe con `guardar_env`, que
actualiza solo las claves pedidas y preserva el resto de líneas/comentarios.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Archivo compartido con la UI clásica y ciclo_vida (¡no pisar claves ajenas!).
ARCHIVO = Path(os.path.expanduser("~")) / ".jobpulse_v15" / "ui_config.json"

# .env del proyecto (gitignored): raíz = src/jobpulse_v15/ui_v2/ → 3 arriba.
ENV = Path(__file__).resolve().parents[3] / ".env"

CLAVE_PALETA = "paleta"
CLAVE_CSV_DIR = "csv_dir"


def cargar(ruta: Path | None = None) -> dict[str, Any]:
    """Lee el JSON de configuración; {} si no existe o está ilegible."""
    ruta = ruta or ARCHIVO
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def guardar(claves: dict[str, Any], ruta: Path | None = None) -> dict[str, Any]:
    """Carga → update → guarda: NUNCA se pierden claves escritas por otros."""
    ruta = ruta or ARCHIVO
    cfg = cargar(ruta)
    cfg.update(claves)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return cfg


def paleta_actual(ruta: Path | None = None) -> str:
    """Nombre de la paleta guardada ("" si nunca se eligió)."""
    return str(cargar(ruta).get(CLAVE_PALETA) or "")


def directorio_csv(ruta: Path | None = None) -> str | None:
    """Directorio configurado para exportar CSV.

    None si está vacío o si ya no existe en disco (el diálogo entonces
    cae al comportamiento por defecto de Tk en vez de fallar).
    """
    valor = str(cargar(ruta).get(CLAVE_CSV_DIR) or "").strip()
    if valor and Path(valor).is_dir():
        return valor
    return None


def ruta_env() -> Path:
    """Ruta del .env del proyecto (para load_dotenv con ruta explícita)."""
    return ENV


def guardar_env(valores: dict[str, str], ruta: Path | None = None) -> None:
    """Actualiza claves del .env preservando el resto de líneas y comentarios.

    Si una clave no existe se agrega al final. Los valores se sanean
    (sin CR ni LF): una clave con salto de línea rompería el archivo.
    """
    ruta = ruta or ENV
    lineas: list[str] = []
    if ruta.exists():
        try:
            lineas = ruta.read_text(encoding="utf-8").splitlines()
        except OSError:
            lineas = []
    for clave, valor in valores.items():
        valor = str(valor).replace("\r", " ").replace("\n", " ").strip()
        for i, linea in enumerate(lineas):
            if linea.strip() == clave or linea.strip().startswith(f"{clave}="):
                lineas[i] = f"{clave}={valor}"
                break
        else:
            if lineas and lineas[-1].strip():
                lineas.append("")
            lineas.append(f"{clave}={valor}")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
