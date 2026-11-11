# -*- coding: utf-8 -*-
"""DECISIONES FIRMADAS del Paso 5 (Paso 7 · "tabla de decisiones").

Por que existe: el motor NO puede decidir, por si solo, si un requisito
educativo universitario BLOQUEA o no. La regla es deliberadamente
conservadora ("descartada" solo si el texto confirma el titulo obligatorio
SIN negacion y SIN alternativa), asi que cuando el texto ofrece una via
alternativa ("or equivalent experience") el caso queda en
``revisar_a_mano / educacion_no_confirmada`` esperando un VEREDICTO HUMANO.

Ese veredicto lo firma una **segunda persona** (la revision previa la hizo
el autor de la regla -> se descarta por sesgo). Hasta ahora la firma vivia
solo en un documento: el motor no la podia leer, asi que los casos firmados
seguian contando como "pendientes" para siempre.

Este modulo es la FUENTE UNICA de:

* las dimensiones y veredictos validos (``job_match_decision`` los exige);
* el **ancla** de cada decision: el ``sha256`` del TEXTO del aviso que se
  reviso. Si el aviso se re-scrapea y su texto cambia, la decision deja de
  aplicar (el caso vuelve a ``educacion_no_confirmada`` y hay que volver a
  firmarlo): una firma vieja no puede aplicarse a un texto que nadie leyo.

El texto que se ancla es EXACTAMENTE el que leen el motor
(``matching._cargar_textos``) y la hoja de revision
(``generar_revision_pendientes.py``): ``requirements_raw`` + ``description_raw``
unidos con un salto de linea.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from typing import Any, Mapping

#: Dimension del matching que hoy admite decisiones firmadas.
DIMENSION_EDUCACION = "educacion"

#: La dimension educativa sigue ABIERTA: es la que el motor no puede cerrar.
DIMENSIONES = (DIMENSION_EDUCACION,)

#: Veredicto "el titulo universitario BLOQUEA" -> la vacante se descarta.
VEREDICTO_BLOQUEO_REAL = "bloqueo_real"

#: Veredicto "el titulo universitario NO bloquea" -> el requisito queda como
#: faltante y la vacante a revision manual (nunca se descarta).
VEREDICTO_NO_BLOQUEO = "no_bloqueo"

#: Veredicto "no se puede decidir todavia" (falta una decision de negocio):
#: el caso sigue ABIERTO, igual que si nadie lo hubiera revisado.
VEREDICTO_DUDOSO = "dudoso"

VEREDICTOS = (
    VEREDICTO_BLOQUEO_REAL,
    VEREDICTO_NO_BLOQUEO,
    VEREDICTO_DUDOSO,
)


def texto_aviso(requirements_raw: Any, description_raw: Any) -> str:
    """Texto del aviso que leen el motor y la hoja de revision.

    Es el MISMO texto en ambos sitios a proposito: la decision se ancla a
    este texto, asi que tiene que ser el que la persona leyo.
    """
    partes = [requirements_raw or "", description_raw or ""]
    return "\n".join(parte for parte in partes if parte)


def hash_texto(texto: str) -> str:
    """sha256 del texto del aviso (ancla de la decision)."""
    return hashlib.sha256((texto or "").encode("utf-8")).hexdigest()


def hash_aviso(requirements_raw: Any, description_raw: Any) -> str:
    """sha256 del texto del aviso, tal como lo lee el motor."""
    return hash_texto(texto_aviso(requirements_raw, description_raw))


#: Las comillas angulares «...» del criterio son la CONVENCION de "cita
#: LITERAL del aviso": lo que va entre ellas tiene que ser un fragmento
#: exacto del texto del aviso (lo comprueba ``verificar_evidencia.py``).
#: Los nombres de escalones o de reglas van entre comillas simples ('...'):
#: si no, la firma se acepta pero la evidencia falla al verificarse.
CITA_ANGULAR = re.compile(r"«([^»]+)»")


def citas_del_criterio(criterio: str) -> list[str]:
    """Citas literales del aviso que el criterio afirma (``«...»``)."""
    return [c.strip() for c in CITA_ANGULAR.findall(criterio or "") if c.strip()]


def validar_citas(criterio: str, texto_aviso_actual: str) -> list[str]:
    """Citas del criterio que NO son literales del texto del aviso.

    Devuelve la lista de citas problematicas (vacia = todo bien). No lanza:
    el llamador decide si es un error (firma) o un aviso (revision).
    """
    texto = texto_aviso_actual or ""
    problematicas: list[str] = []
    for cita in citas_del_criterio(criterio):
        if cita not in texto:
            problematicas.append(cita)
    return problematicas


def validar_dimension(dimension: Any) -> str:
    """Dimension valida (o ``ValueError``)."""
    valor = str(dimension or "").strip()
    if valor not in DIMENSIONES:
        raise ValueError(
            "dimension no valida: %r (validas: %s)."
            % (dimension, ", ".join(DIMENSIONES))
        )
    return valor


def validar_veredicto(veredicto: Any) -> str:
    """Veredicto valido (o ``ValueError``)."""
    valor = str(veredicto or "").strip()
    if valor not in VEREDICTOS:
        raise ValueError(
            "veredicto no valido: %r (validos: %s)."
            % (veredicto, ", ".join(VEREDICTOS))
        )
    return valor


def decision_aplica(decision: Mapping[str, Any] | None) -> bool:
    """True si la decision cambia el veredicto del motor.

    ``dudoso`` NO cambia nada: el caso sigue abierto (falta una decision de
    negocio), igual que si nadie lo hubiera revisado.
    """
    if not decision:
        return False
    return str(decision.get("veredicto") or "") in (
        VEREDICTO_BLOQUEO_REAL,
        VEREDICTO_NO_BLOQUEO,
    )


# --------------------------------------------------------------------------
# Persistencia (tabla ``job_match_decision``, migracion 027)
# --------------------------------------------------------------------------


def hash_aviso_en_base(
    connection: sqlite3.Connection, job_id: str
) -> str | None:
    """sha256 del texto ACTUAL del aviso en la base (o ``None`` si no existe).

    Es el ancla de la decision: si el aviso se re-scrapea y el texto cambia,
    la firma deja de aplicar.
    """
    fila = connection.execute(
        "SELECT requirements_raw, description_raw FROM jobs WHERE job_id = ?",
        (job_id,),
    ).fetchone()
    if fila is None:
        return None
    return hash_aviso(fila["requirements_raw"], fila["description_raw"])


def texto_aviso_en_base(
    connection: sqlite3.Connection, job_id: str
) -> str | None:
    """Texto ACTUAL del aviso en la base (o ``None`` si no existe).

    Es el mismo texto que se ancla en ``text_hash``: sirve para comprobar
    que las citas del criterio (``«...»``) son literales de ESTE aviso.
    """
    fila = connection.execute(
        "SELECT requirements_raw, description_raw FROM jobs WHERE job_id = ?",
        (job_id,),
    ).fetchone()
    if fila is None:
        return None
    return texto_aviso(fila["requirements_raw"], fila["description_raw"])


def guardar_decision(
    connection: sqlite3.Connection,
    *,
    job_id: str,
    dimension: str,
    veredicto: str,
    criterio: str,
    revisor: str,
    fecha: str,
    text_hash: str,
    corrida_id: str | None = None,
) -> int:
    """Registra (o re-firma) la decision de un aviso.

    Firmar dos veces el MISMO texto es un UPDATE (manda la segunda firma);
    un texto distinto es una fila nueva (historico).
    """
    dimension = validar_dimension(dimension)
    veredicto = validar_veredicto(veredicto)
    job_id = str(job_id or "").strip()
    if not job_id:
        raise ValueError("job_id no puede ir vacio.")
    criterio = str(criterio or "").strip()
    if not criterio:
        raise ValueError("criterio no puede ir vacio: dice POR QUE se firma.")
    revisor = str(revisor or "").strip()
    if not revisor:
        raise ValueError("revisor no puede ir vacio.")
    fecha = str(fecha or "").strip()
    if not fecha:
        raise ValueError("fecha no puede ir vacia.")
    text_hash = str(text_hash or "").strip()
    if not text_hash:
        raise ValueError("text_hash no puede ir vacio.")

    connection.execute(
        """
        INSERT INTO job_match_decision (
            job_id, dimension, veredicto, criterio, revisor, fecha,
            text_hash, corrida_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (job_id, dimension, text_hash) DO UPDATE SET
            veredicto = excluded.veredicto,
            criterio = excluded.criterio,
            revisor = excluded.revisor,
            fecha = excluded.fecha,
            corrida_id = excluded.corrida_id
        """,
        (
            job_id,
            dimension,
            veredicto,
            criterio,
            revisor,
            fecha,
            text_hash,
            corrida_id,
        ),
    )
    fila = connection.execute(
        """
        SELECT id FROM job_match_decision
        WHERE job_id = ? AND dimension = ? AND text_hash = ?
        """,
        (job_id, dimension, text_hash),
    ).fetchone()
    return int(fila["id"]) if fila else 0


def listar_decisiones(
    connection: sqlite3.Connection,
    *,
    dimension: str | None = None,
    job_id: str | None = None,
) -> list[dict[str, Any]]:
    """Decisiones registradas (con el veredicto vigente de cada aviso)."""
    sql = [
        """
        SELECT d.id, d.job_id, d.dimension, d.veredicto, d.criterio,
               d.revisor, d.fecha, d.text_hash, d.corrida_id,
               j.title AS job_title
        FROM job_match_decision d
        JOIN jobs j ON j.job_id = d.job_id
        WHERE 1 = 1
        """
    ]
    params: list[Any] = []
    if dimension:
        sql.append("AND d.dimension = ?")
        params.append(validar_dimension(dimension))
    if job_id:
        sql.append("AND d.job_id = ?")
        params.append(job_id)
    sql.append("ORDER BY d.job_id, d.fecha DESC, d.id DESC")
    filas = connection.execute(" ".join(sql), params).fetchall()
    return [dict(fila) for fila in filas]


def decision_vigente(
    connection: sqlite3.Connection, job_id: str, dimension: str
) -> dict[str, Any] | None:
    """Decision vigente de un aviso: la del texto ACTUAL (o ``None``)."""
    dimension = validar_dimension(dimension)
    text_hash = hash_aviso_en_base(connection, job_id)
    if not text_hash:
        return None
    fila = connection.execute(
        """
        SELECT id, job_id, dimension, veredicto, criterio, revisor, fecha,
               text_hash, corrida_id
        FROM job_match_decision
        WHERE job_id = ? AND dimension = ? AND text_hash = ?
        """,
        (job_id, dimension, text_hash),
    ).fetchone()
    return dict(fila) if fila else None


# --------------------------------------------------------------------------
# Hoja de firma (JSON) -> tabla de decisiones
# --------------------------------------------------------------------------

#: Formato del JSON de la firma (una hoja por dimension).
FORMATO_FIRMA = 1


def cargar_firma(path: str) -> dict[str, Any]:
    """Lee y valida el JSON de la firma.

    Formato::

        {
          "formato": 1,
          "dimension": "educacion",
          "revisor": "Nombre de quien firma",
          "fecha": "AAAA-MM-DD",
          "decisiones": [
            {"job_id": "...", "veredicto": "no_bloqueo",
             "criterio": "por que", "text_hash": "sha256..."}
          ]
        }
    """
    import json
    from pathlib import Path

    datos = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(datos, Mapping):
        raise ValueError("El JSON de la firma debe ser un objeto.")
    formato = datos.get("formato", FORMATO_FIRMA)
    if formato != FORMATO_FIRMA:
        raise ValueError("formato de firma no soportado: %r." % (formato,))
    dimension = validar_dimension(datos.get("dimension"))
    revisor = str(datos.get("revisor") or "").strip()
    if not revisor:
        raise ValueError("El JSON de la firma necesita 'revisor'.")
    fecha = str(datos.get("fecha") or "").strip()
    if not fecha:
        raise ValueError("El JSON de la firma necesita 'fecha'.")
    lista = datos.get("decisiones")
    if not isinstance(lista, list) or not lista:
        raise ValueError("El JSON de la firma necesita la lista 'decisiones'.")
    for item in lista:
        if not isinstance(item, Mapping):
            raise ValueError("Cada decision de la firma debe ser un objeto.")
        validar_veredicto(item.get("veredicto"))
        if not str(item.get("job_id") or "").strip():
            raise ValueError("Cada decision necesita 'job_id'.")
        if not str(item.get("criterio") or "").strip():
            raise ValueError("Cada decision necesita 'criterio'.")
        if not str(item.get("text_hash") or "").strip():
            raise ValueError("Cada decision necesita 'text_hash'.")
    return {
        "formato": formato,
        "dimension": dimension,
        "revisor": revisor,
        "fecha": fecha,
        "decisiones": [dict(item) for item in lista],
    }


def aplicar_firma(
    connection: sqlite3.Connection, firma: Mapping[str, Any]
) -> dict[str, Any]:
    """Aplica la hoja de firma a la tabla de decisiones.

    Solo se aplica una decision si el aviso existe y su texto ACTUAL sigue
    siendo EXACTAMENTE el que se reviso (``text_hash``). Si el texto cambio,
    la decision NO se aplica (queda pendiente de una firma nueva): una firma
    vieja no puede aplicarse a un texto que nadie leyo.

    Ademas, lo que el criterio cita entre comillas angulares «...» tiene que
    ser LITERAL del texto del aviso: si no, la firma se RECHAZA (no se
    escribe). Es la misma comprobacion que hace ``verificar_evidencia.py``,
    pero aqui falla al firmar y no tres etapas despues.
    """
    dimension = validar_dimension(firma.get("dimension"))
    revisor = str(firma.get("revisor") or "").strip()
    fecha = str(firma.get("fecha") or "").strip()
    aplicadas: list[str] = []
    texto_cambiado: list[str] = []
    desconocidas: list[str] = []
    citas_no_literal: list[dict[str, str]] = []
    for item in firma.get("decisiones") or []:
        job_id = str(item.get("job_id") or "").strip()
        text_hash = str(item.get("text_hash") or "").strip()
        actual = hash_aviso_en_base(connection, job_id)
        if actual is None:
            desconocidas.append(job_id)
            continue
        if actual != text_hash:
            texto_cambiado.append(job_id)
            continue
        criterio = str(item.get("criterio"))
        texto_actual = texto_aviso_en_base(connection, job_id)
        problematicas = validar_citas(criterio, texto_actual)
        if problematicas:
            citas_no_literal.append(
                {"job_id": job_id, "citas": " | ".join(problematicas)}
            )
            continue
        guardar_decision(
            connection,
            job_id=job_id,
            dimension=dimension,
            veredicto=str(item.get("veredicto")),
            criterio=criterio,
            revisor=revisor,
            fecha=fecha,
            text_hash=text_hash,
            corrida_id=item.get("corrida_id"),
        )
        aplicadas.append(job_id)
    return {
        "dimension": dimension,
        "revisor": revisor,
        "fecha": fecha,
        "aplicadas": aplicadas,
        "texto_cambiado": texto_cambiado,
        "desconocidas": desconocidas,
        "citas_no_literal": citas_no_literal,
    }
