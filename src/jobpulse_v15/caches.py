# -*- coding: utf-8 -*-
"""Cachés del sistema: inspección y limpieza (SIN Tk).

Hay dos cachés en disco, de naturaleza distinta:

1. **Caché de la IA** (`ia_api.CACHE_DIR`, por defecto
   `data/usuario/ia_cache/`): un archivo JSON por petición, con el nombre
   = hash SHA-256 de 32 hex de la petición. Sirve para NO volver a pagar
   (ni volver a esperar) una llamada al LLM. Borrarla obliga a repetir las
   llamadas: por eso la UI pide confirmación y avisa del coste.

2. **Caché de embeddings** (`search_engine`): cuatro archivos
   (`embeddings_cache.npy` + `embeddings_meta.json` y los equivalentes de
   TÍTULOS). Guardan los vectores de los avisos para que el ranking ATS no
   re-vectorice 535 avisos en cada arranque (77 s). Borrarla NO cuesta
   dinero: solo tiempo de cómputo la próxima vez.

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
CLAVE_EMBEDDINGS = "embeddings"

TITULO_IA = "Caché de la IA"
TITULO_EMBEDDINGS = "Caché de embeddings (ranking ATS)"


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
            if self.clave == CLAVE_IA:
                return "Vacía (0 respuestas guardadas)"
            return "Vacía (se re-vectoriza en el próximo ranking)"
        if self.clave == CLAVE_IA:
            return f"{self.archivos_totales} respuestas · {self.tamano}"
        return f"{self.archivos_totales} archivos · {self.tamano}"


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


def _rutas_embeddings() -> tuple[Path, ...]:
    """Los cuatro archivos de la caché de embeddings."""
    from jobpulse_v15 import search_engine

    return (
        Path(search_engine.EMB_CACHE_FILE),
        Path(search_engine.EMB_META_FILE),
        Path(search_engine.EMB_TIT_CACHE_FILE),
        Path(search_engine.EMB_TIT_META_FILE),
    )


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


def estado_embeddings() -> EstadoCache:
    """Estado de la caché de embeddings (4 archivos)."""
    rutas = _rutas_embeddings()
    infos = tuple(_info_archivo(p) for p in rutas)
    total = sum(i.bytes for i in infos)
    return EstadoCache(
        clave=CLAVE_EMBEDDINGS,
        titulo=TITULO_EMBEDDINGS,
        ruta=str(rutas[0].parent) if rutas else "",
        archivos=infos,
        archivos_totales=sum(1 for i in infos if i.existe),
        bytes_totales=total,
        nota=("Borrarla no cuesta dinero: el próximo ranking ATS vuelve a "
              "vectorizar los avisos (tarda ~1-2 min la primera vez)."),
    )


def estado_caches() -> dict[str, EstadoCache]:
    """Todas las cachés del sistema (para la tarjeta de Configuración)."""
    return {
        CLAVE_IA: estado_ia(),
        CLAVE_EMBEDDINGS: estado_embeddings(),
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


def limpiar_embeddings() -> ResultadoLimpieza:
    """Borra los cuatro archivos de la caché de embeddings."""
    borrados = 0
    bytes_ = 0
    try:
        for ruta in _rutas_embeddings():
            if ruta.is_file():
                bytes_ += ruta.stat().st_size
                ruta.unlink()
                borrados += 1
    except OSError as exc:
        return ResultadoLimpieza(CLAVE_EMBEDDINGS, borrados, bytes_, str(exc))
    return ResultadoLimpieza(CLAVE_EMBEDDINGS, borrados, bytes_)


def limpiar(clave: str) -> ResultadoLimpieza:
    """Limpia la caché indicada por clave."""
    if clave == CLAVE_IA:
        return limpiar_ia()
    if clave == CLAVE_EMBEDDINGS:
        return limpiar_embeddings()
    return ResultadoLimpieza(clave, 0, 0, f"Caché desconocida: {clave}")


def archivos_huerfanos_ia(ruta: Path | None = None) -> Iterable[Path]:
    """Archivos de la carpeta IA que NO son del sistema (no se borran)."""
    carpeta = Path(ruta) if ruta is not None else _ruta_ia()
    if not carpeta.is_dir():
        return []
    return [p for p in carpeta.iterdir()
            if p.is_file() and not PATRON_CACHE_IA.match(p.name)]
