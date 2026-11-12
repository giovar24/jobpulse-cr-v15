# -*- coding: utf-8 -*-
"""Cachés del sistema: inspección y limpieza (SIN Tk).

Hay UNA caché en disco: la **caché de la IA** (`ia_api.CACHE_DIR`, por
defecto `data/usuario/ia_cache/`): un archivo JSON por petición, con el
nombre = hash SHA-256 de 32 hex de la petición. Sirve para NO volver a pagar
(ni volver a esperar) una llamada al LLM. Borrarla obliga a repetir las
llamadas: por eso la UI pide confirmación y avisa del coste.

REGLA DE SEGURIDAD: en la caché de la IA **solo** se borran archivos que
cumplen el patrón del sistema (`[0-9a-f]{32}.json`): cualquier otro archivo
que el usuario haya metido ahí se respeta.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Nombre de archivo de la caché IA: hash de 32 hex + .json
PATRON_CACHE_IA = re.compile(r"^[0-9a-f]{32}\.json$")

CLAVE_IA = "ia"

TITULO_IA = "Caché de la IA"


def _tamano_legible(bytes_: int) -> str:
    """Bytes en texto legible (KB/MB/GB)."""
    valor = float(max(0, bytes_))
    for unidad in ("B", "KB", "MB", "GB"):
        if valor < 1024 or unidad == "GB":
            if unidad == "B":
                return f"{int(valor)} B"
            return f"{valor:.1f} {unidad}"
        valor /= 1024
    return f"{valor:.1f} GB"


@dataclass(frozen=True)
class InfoArchivo:
    """Un archivo de caché y su estado en disco."""

    nombre: str
    ruta: str
    existe: bool
    bytes: int

    @property
    def tamano(self) -> str:
        return _tamano_legible(self.bytes)


@dataclass(frozen=True)
class EstadoCache:
    """Estado de una caché (qué hay, cuánto ocupa)."""

    clave: str
    titulo: str
    ruta: str
    archivos: tuple[InfoArchivo, ...] = ()
    archivos_totales: int = 0
    bytes_totales: int = 0
    nota: str = ""

    @property
    def tamano(self) -> str:
        return _tamano_legible(self.bytes_totales)

    @property
    def texto_resumen(self) -> str:
        """Resumen de una línea para la tarjeta de la UI."""
        if not self.archivos_totales:
            return "Vacía (0 respuestas guardadas)"
        return f"{self.archivos_totales} respuestas · {self.tamano}"


@dataclass(frozen=True)
class ResultadoLimpieza:
    """Qué pasó al limpiar una caché."""

    clave: str
    archivos_borrados: int
    bytes_liberados: int
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error

    @property
    def tamano_liberado(self) -> str:
        return _tamano_legible(self.bytes_liberados)


def _info_archivo(ruta: Path) -> InfoArchivo:
    existe = ruta.is_file()
    bytes_ = ruta.stat().st_size if existe else 0
    return InfoArchivo(nombre=ruta.name, ruta=str(ruta), existe=existe,
                       bytes=bytes_)


def _ruta_ia() -> Path:
    """Carpeta de la caché IA (la MISMA que usa `ia_api`)."""
    from jobpulse_v15 import ia_api

    return Path(ia_api.CACHE_DIR)


def _archivos_ia(ruta: Path) -> list[Path]:
    """Archivos de la caché IA que cumplen el patrón del sistema."""
    if not ruta.is_dir():
        return []
    return sorted(p for p in ruta.iterdir()
                  if p.is_file() and PATRON_CACHE_IA.match(p.name))


def estado_ia() -> EstadoCache:
    """Estado de la caché de la IA (archivos, tamaño, ruta)."""
    ruta = _ruta_ia()
    archivos = _archivos_ia(ruta)
    total = sum(p.stat().st_size for p in archivos)
    return EstadoCache(
        clave=CLAVE_IA,
        titulo=TITULO_IA,
        ruta=str(ruta),
        archivos_totales=len(archivos),
        bytes_totales=total,
        nota=("Borrarla hace que el enriquecimiento IA vuelva a llamar "
              "al modelo (cuesta tiempo y, con IA externa, dinero)."),
    )


def estado_caches() -> dict[str, EstadoCache]:
    """Todas las cachés del sistema (para la tarjeta de Configuración)."""
    return {
        CLAVE_IA: estado_ia(),
    }


def limpiar_ia() -> ResultadoLimpieza:
    """Borra SOLO los archivos `[0-9a-f]{32}.json` de la caché IA."""
    ruta = _ruta_ia()
    borrados = 0
    bytes_ = 0
    try:
        for archivo in _archivos_ia(ruta):
            try:
                bytes_ += archivo.stat().st_size
                archivo.unlink()
                borrados += 1
            except OSError:
                continue
    except OSError as exc:
        return ResultadoLimpieza(CLAVE_IA, borrados, bytes_, str(exc))
    return ResultadoLimpieza(CLAVE_IA, borrados, bytes_)


def limpiar(clave: str) -> ResultadoLimpieza:
    """Limpia la caché indicada por clave."""
    if clave == CLAVE_IA:
        return limpiar_ia()
    return ResultadoLimpieza(clave, 0, 0, f"Caché desconocida: {clave}")


def archivos_huerfanos_ia(ruta: Path | None = None) -> Iterable[Path]:
    """Archivos de la carpeta IA que NO son del sistema (no se borran)."""
    carpeta = Path(ruta) if ruta is not None else _ruta_ia()
    if not carpeta.is_dir():
        return []
    return [p for p in carpeta.iterdir()
            if p.is_file() and not PATRON_CACHE_IA.match(p.name)]
