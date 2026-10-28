# -*- coding: utf-8 -*-
"""ciclo_vida — O8: republicaciones heredan el estado manual del original.

Mecanismo portado del proyecto v1.x (core/dedupe.py + core/database.py,
SOLO lectura) adaptado al modelo de v1.5: la republicacion (ID de
origen nuevo) que coincide con un puesto que el usuario ya marco como
`reviewed`/`applied` nace OCULTA (user_job_state + skip_automatic=1) con
nota de herencia, y queda marcada `dup_of` -> al original. Nunca se borra
ni se funde nada.

Criterio de matching (decision del usuario 27-10): compania igual +
huella de descripcion EXACTA o ratio >= 0.92. El titulo NO es criterio
primario (O5.4 lo desmonto con ANE "Confidencial": 13 coincidencias
solo-titulo no eran republicaciones).

Ventana temporal: la copia solo hereda si el estado manual del original
tiene MENOS de `ventana_republicaciones_meses` de antiguedad (ancla =
user_job_state.updated_at; default 3 meses). Fuera de la ventana la copia
entra como vacante NUEVA (nuevo ciclo, re-aplicable).

Solo stdlib. Sin dependencia de repositorio en import-time (guard
TYPE_CHECKING para no crear ciclo con repository.py).
"""

from __future__ import annotations

import difflib
import json
import logging
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:  # pragma: no cover - solo tipado
    from jobpulse_v15.repository import Repository

logger = logging.getLogger("jobpulse_v15.ciclo_vida")

CONFIG_FILE = os.path.join(
    os.path.expanduser("~"), ".jobpulse_v15", "ui_config.json"
)

# Ventana permitida para republicaciones y retencion (selector de la pestaña
# Vacantes en Configuracion). Defaults decididos por el usuario (27-10):
# republicaciones 3 meses; retencion de puestos 6 meses (aun por confirmar).
MESES_PERMITIDOS = (1, 2, 3, 6, 12)
DEFAULT_VENTANA_REPUBLICACIONES = 3
DEFAULT_RETENCION_PUESTOS = 6

CLAVE_VENTANA_REPUBLICACIONES = "ventana_republicaciones_meses"
CLAVE_RETENCION_PUESTOS = "retencion_puestos_meses"

# Ratio minimo (SequenceMatcher sobre huella de descripcion) para considerar
# republicacion SIN huella exacta. Duda media sigue siendo revision manual
# via `quality duplicates` (regla de dedupe conservador).
UMBRAL_RATIO = 0.92

# Estados manuales que hereda una republicacion. dismissed/archived NO
# heredan: al republicarse el puesto, el usuario vuelve a verlo.
ESTADOS_HEREDABLES = ("reviewed", "applied")

# Formato CURRENT_TIMESTAMP de SQLite (UTC) para comparar updated_at.
_FORMATO_SQL_TS = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------------------
# Normalizacion (port de core/dedupe.py de v1.x, tokens ASCII orden-insensibles)
# ---------------------------------------------------------------------------

def _ascii_tokens(texto: Any) -> list[str]:
    """Tokens ASCII lowercase; borra todo lo no alfanumerico."""
    text = unicodedata.normalize("NFKD", str(texto or ""))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = text.replace("+", " ").replace("&", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return [tok for tok in text.split() if tok]


def norm_empresa(company: Any) -> str:
    """Clave conservadora de empresa (sin quitar sufijos ni ruido)."""
    return " ".join(sorted(_ascii_tokens(company)))


def norm_lugar_exacto(location: Any) -> str:
    return " ".join(sorted(_ascii_tokens(location)))


def clave_exacta(
    company: Any, title: Any, location: Any | None
) -> tuple[str, str, str] | None:
    """Clave empresa|titulo|ubicacion exacta (v1.x `clave_duplicado_exacto`).

    None si falta alguno de los tres: sin ubicacion no se puede afirmar que
    dos filas son el mismo puesto.
    """
    empresa = norm_empresa(company)
    titulo = " ".join(sorted(_ascii_tokens(title)))
    lugar = norm_lugar_exacto(location)
    if not empresa or not titulo or not lugar:
        return None
    return (empresa, titulo, lugar)


def huella_descripcion(description: Any) -> str:
    """Huella de descripcion: lowercase + solo alfanumericos (normalizacion O5.4).

    Es el criterio primario de republicacion en ANE, donde la compania se
    publica como "Confidencial" y los titulos se reutilizan entre plazas.
    """
    text = unicodedata.normalize("NFKD", str(description or ""))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def ratio_descripcion(huella_a: str, huella_b: str) -> float:
    """Similitud ([0..1]) de dos huellas; 1.0 si alguna es la cadena vacia."""
    if not huella_a or not huella_b:
        return 0.0
    matcher = difflib.SequenceMatcher(None, huella_a, huella_b)
    return matcher.ratio()


# ---------------------------------------------------------------------------
# Preferencias (ui_config.json, pestaña Vacantes de Configuracion)
# ---------------------------------------------------------------------------

def _mes_valido(valor: Any, defecto: int) -> int:
    try:
        meses = int(valor)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return defecto
    return meses if meses in MESES_PERMITIDOS else defecto


def preferencias(config_file: str | None = None) -> dict[str, int]:
    """Lee (ventana_republicaciones_meses, retencion_puestos_meses).

    TODO elsewhere uses this via the UI tab; valores invalidos o ausentes
    -> defaults. `config_file` existe para tests (parchear `CONFIG_FILE`
    tambien funciona)."""
    ruta = config_file or CONFIG_FILE
    cfg: dict[str, Any] = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                cfg = json.load(f) or {}
        except (OSError, ValueError):
            cfg = {}
    return {
        CLAVE_VENTANA_REPUBLICACIONES: _mes_valido(
            cfg.get(CLAVE_VENTANA_REPUBLICACIONES),
            DEFAULT_VENTANA_REPUBLICACIONES,
        ),
        CLAVE_RETENCION_PUESTOS: _mes_valido(
            cfg.get(CLAVE_RETENCION_PUESTOS),
            DEFAULT_RETENCION_PUESTOS,
        ),
    }


def guardar_preferencias(
    ventana_republicaciones_meses: int,
    retencion_puestos_meses: int,
    config_file: str | None = None,
) -> None:
    """Merge-update-save: lee el JSON actual, cambia SOLO las 2 claves O8 y
    reescribe. Es el patron load-merge-update-save (la escritura previa de la
    UI sobreescribia el dict entero y perdia claves -- gotcha del handoff)."""
    ruta = config_file or CONFIG_FILE
    if ventana_republicaciones_meses not in MESES_PERMITIDOS:
        raise ValueError("ventana_republicaciones_meses no es un mes permitido.")
    if retencion_puestos_meses not in MESES_PERMITIDOS:
        raise ValueError("retencion_puestos_meses no es un mes permitido.")
    cfg: dict[str, Any] = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                cfg = json.load(f) or {}
        except (OSError, ValueError):
            cfg = {}
    cfg[CLAVE_VENTANA_REPUBLICACIONES] = int(ventana_republicaciones_meses)
    cfg[CLAVE_RETENCION_PUESTOS] = int(retencion_puestos_meses)
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Ventana temporal
# ---------------------------------------------------------------------------

def corte_de_ventana(meses: int) -> str:
    """Frontera (UTC, formato CURRENT_TIMESTAMP de SQLite) de hace N meses.

    Ancla de herencia: user_job_state.updated_at >= corte. Fuera del corte el
    estado 'caduco' y la republicacion entra como vacante nueva."""
    if meses not in MESES_PERMITIDOS:
        raise ValueError("La ventana debe ser uno de: 1, 2, 3, 6, 12 meses.")
    ahora = datetime.now(timezone.utc)
    corte = ahora - timedelta(days=30 * meses)
    # 30*meses es la granularidad que v1.x usaba para ventanas; un margen de
    # dias en una ventana de meses es irrelevante y evita aritmetica de
    # calendario por un efecto de borde de 1-2 dias.
    return corte.strftime(_FORMATO_SQL_TS)


def corte_de_retencion(meses: int) -> str:
    """Frontera ISO (fecha) para vigencia de puestos: hoy - N meses."""
    if meses not in MESES_PERMITIDOS:
        raise ValueError("La retencion debe ser uno de: 1, 2, 3, 6, 12 meses.")
    hoy = datetime.now(timezone.utc).date()
    dias = 30 * meses
    return (hoy - timedelta(days=dias)).isoformat()


# ---------------------------------------------------------------------------
# Herencia al ingest
# ---------------------------------------------------------------------------

NOTA_HERENCIA = (
    "Republicacion de {original}: heredado estado '{estado}' automaticamente "
    "(O8; compania + huella de descripcion)."
)


def evaluar_herencia(
    repository: Repository, job: Mapping[str, Any]
) -> str | None:
    """Hereda el estado manual del original a una republicacion nueva.

    `job` es el mapping recien guardado (keys de save_job: job_id, title,
    company, location_raw, description_raw...). Devuelve el job_id del
    original si herdó; None si no es republicacion reconocida.

    En ingest se invoca best-effort (try/except): un fallo aqui NO puede
    romper la corrida.
    """
    job_id = str(job.get("job_id") or "").strip()
    if not job_id:
        return None

    # Guard: si la fila nueva ya tiene estado manual, no la tocamos.
    if repository.get_user_job_state(job_id) is not None:
        return None

    empresa_nueva = norm_empresa(job.get("company"))
    huella_nueva = huella_descripcion(job.get("description_raw"))
    if not empresa_nueva or not huella_nueva:
        return None

    estados = repository.estados_para_herencia(
        corte_de_ventana(preferencias()[CLAVE_VENTANA_REPUBLICACIONES])
    )
    for estado in estados:
        if norm_empresa(estado.get("company_snapshot")) != empresa_nueva:
            continue
        estado_herencia = estado.get("estado_herencia")
        # Defensivo: el query ya filtra por ESTADOS_HEREDABLES.
        if estado_herencia not in ESTADOS_HEREDABLES:
            continue
        huella_original = huella_descripcion(
            estado.get("description_original")
        )
        if not huella_original:
            continue
        if huella_original != huella_nueva and (
            ratio_descripcion(huella_original, huella_nueva) < UMBRAL_RATIO
        ):
            continue

        # Coincidencia: heredar el estado manual del original.
        repository.marcar_dup_of(job_id, str(estado["original_job_id"]))
        repository.set_user_job_state(
            job_id,
            str(estado_herencia),
            skip_automatic=True,
            notes=NOTA_HERENCIA.format(
                original=estado["original_job_id"], estado=estado_herencia
            ),
        )
        logger.info(
            "Republicacion %s hereda estado '%s' de %s.",
            job_id,
            estado_herencia,
            estado["original_job_id"],
        )
        return str(estado["original_job_id"])

    return None
