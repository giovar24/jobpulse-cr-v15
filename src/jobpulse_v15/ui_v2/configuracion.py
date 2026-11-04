# -*- coding: utf-8 -*-
"""Configuración persistente de la UI v2 (SIN Tk).

Comparte el archivo con la UI clásica: `~/.jobpulse_v15/ui_config.json`.
REGLA DE ORO: SIEMPRE cargar → update → guardar. El mismo archivo lo
escriben `ciclo_vida` (O8) y la ventana de configuración clásica:
sobrescribir el dict completo perdería sus claves (bug ya vivido en
`configuration_window._save_all`).

Claves que usa la UI v2:
- `paleta`   : nombre del esquema de color (ver `theme.PALETAS`).
- `densidad` : densidad de la interfaz (ver `theme.DENSIDADES`).
- `idioma`   : idioma de la interfaz (ver `i18n.IDIOMAS`).
- `csv_dir`  : directorio inicial de los diálogos "Exportar CSV"
               ("" = sin fijo → Tk usa su última carpeta).

El `.env` del proyecto (IA_PROVEEDOR/IA_BASE_URL/IA_MODEL/IA_API_KEY, los
límites opt-in IA_MAX_LLAMADAS/IA_RPM y la configuración del navegador
BRAVE_BIN/BRAVE_PERFIL/BRAVE_CDP_PORT) se escribe con `guardar_env`, que
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
CLAVE_DENSIDAD = "densidad"
CLAVE_IDIOMA = "idioma"

# Claves del .env que guardan la configuración del navegador (punto 2).
CLAVE_BRAVE_BIN = "BRAVE_BIN"
CLAVE_BRAVE_PERFIL = "BRAVE_PERFIL"
CLAVE_BRAVE_CDP_PORT = "BRAVE_CDP_PORT"

# Puerto CDP por defecto (el que trae el launcher del PC del usuario).
PUERTO_CDP_DEFECTO = 9222


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


def densidad_actual(ruta: Path | None = None) -> str:
    """Nombre de la densidad guardada ("" si nunca se eligió)."""
    return str(cargar(ruta).get(CLAVE_DENSIDAD) or "")


def idioma_actual(ruta: Path | None = None) -> str:
    """Código del idioma guardado ("" si nunca se eligió)."""
    return str(cargar(ruta).get(CLAVE_IDIOMA) or "")


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


def cargar_env() -> None:
    """Carga el .env del proyecto en ``os.environ`` (sin pisar lo existente).

    ``load_dotenv`` NO sobreescribe variables ya presentes: lo que el
    usuario exportó en la sesión manda sobre el archivo. Si python-dotenv no
    está instalado, no pasa nada (el `.env` se lee a mano con `leer_env`).
    """
    try:
        from dotenv import load_dotenv

        load_dotenv(ENV)
    except Exception:  # noqa: BLE001 - sin dotenv no hay .env que cargar
        pass


def leer_env(ruta: Path | None = None) -> dict[str, str]:
    """Valores del `.env` del proyecto como dict (NO toca ``os.environ``).

    Parser mínimo: `CLAVE=valor`, ignora comentarios y líneas vacías, y
    quita las comillas que envuelven el valor.
    """
    ruta = ruta or ENV
    valores: dict[str, str] = {}
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError:
        return valores
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        clave = clave.strip()
        if not clave or clave.startswith("export "):
            continue
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        valores[clave] = valor
    return valores


def valor_env(clave: str, defecto: str = "",
              ruta: Path | None = None) -> str:
    """Valor de una clave del entorno o del `.env` (el entorno gana)."""
    valor = os.getenv(clave)
    if valor is not None and valor.strip():
        return valor.strip()
    return str(leer_env(ruta).get(clave) or defecto).strip()


def puerto_cdp(ruta: Path | None = None) -> int:
    """Puerto CDP configurado (``BRAVE_CDP_PORT``) o 9222."""
    valor = valor_env(CLAVE_BRAVE_CDP_PORT, "", ruta)
    try:
        puerto = int(valor)
    except ValueError:
        return PUERTO_CDP_DEFECTO
    if not (1024 <= puerto <= 65535):
        return PUERTO_CDP_DEFECTO
    return puerto


def guardar_navegador(binario: str, perfil: str, puerto: int | str,
                       ruta: Path | None = None) -> dict[str, str]:
    """Guarda la configuración del navegador en el `.env` y la aplica YA.

    Escribe ``BRAVE_BIN`` / ``BRAVE_PERFIL`` / ``BRAVE_CDP_PORT`` y actualiza
    ``os.environ`` en el acto: el `.env`` no vuelve a mandar hasta el
    próximo arranque (``load_dotenv`` no pisa lo ya presente), así que sin
    esto el cambio no rigería en la sesión actual.
    """
    valores = {
        CLAVE_BRAVE_BIN: str(binario or "").strip(),
        CLAVE_BRAVE_PERFIL: str(perfil or "").strip(),
        CLAVE_BRAVE_CDP_PORT: str(puerto or "").strip(),
    }
    guardar_env(valores, ruta)
    for clave, valor in valores.items():
        if valor:
            os.environ[clave] = valor
        else:
            os.environ.pop(clave, None)
    return valores


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
