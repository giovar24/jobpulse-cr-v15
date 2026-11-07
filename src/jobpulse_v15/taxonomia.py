# -*- coding: utf-8 -*-
"""Curacion de la taxonomia de conceptos (Ola 4.2).

Por que existe: la tabla `concepto` (variante de texto -> codigo canonico) es
el "idioma" que comparan el requisito del aviso y el hecho del perfil. El
motor (matching) SOLO compara los requisitos CON `codigo_canonico`
(`AND codigo_canonico IS NOT NULL`): los que no lo tienen se IGNORAN en
silencio y la vacante parece mas compatible de lo que es.

La cola `concepto_no_normalizado` es la LISTA DE TRABAJO de esa taxonomia:
"estas variantes del corpus todavia no tienen codigo". Para que sirva:

1. **No debe llenarse de basura**: `conceptos.es_variante_encolable` descarta
   lo que no es una competencia (una actividad, una palabra vacia, un
   sector). Sin ese filtro, la cola del corpus real tenia 1988 filas de las
   que 1976 no resolvian a nada.
2. **Debe reflejar la DEMANDA REAL**: cuantas variantes pide cada aviso. La
   cola se reconstruye desde `jobs.skills` / `jobs.languages` (la MISMA
   fuente que usa el pipeline), no desde un contador de encolados que
   acumula historia y entradas que ya no existen en el corpus.

Este modulo NO decide que es una competencia: eso es curacion (datos, por
tandas, en las migraciones `02x_taxonomia_*`). Aqui solo se audita y se
mantiene la cola al dia.
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from typing import Any

from jobpulse_v15 import conceptos, idiomas, skills_fuente

#: Clave de la demanda: ``(categoria, variante)``.
Clave = tuple[str, str]


def _filas_corpus(connection: sqlite3.Connection) -> list[tuple]:
    """Avisos con campos estructurados (skills / languages) informados.

    Se devuelven tuplas (no filas con nombre) para no depender del
    ``row_factory`` de quien abre la conexion.
    """
    return connection.execute(
        """
        SELECT job_id, skills, languages
        FROM jobs
        WHERE (COALESCE(TRIM(skills), '') NOT IN ('', '[]', '{}', 'null')
            OR COALESCE(TRIM(languages), '') NOT IN ('', '[]', '{}', 'null'))
        """
    ).fetchall()


def demanda_corpus(connection: sqlite3.Connection) -> dict[str, Counter]:
    """Audita el corpus frente a la taxonomia.

    Devuelve tres contadores ``(categoria, variante) -> menciones`` (una
    mencion = un aviso que pide esa etiqueta):

    * ``resueltas``: ya tienen codigo canonico (comparables con el perfil);
    * ``ruido``: NO son competencias (actividad, palabra vacia, sector);
    * ``pendientes``: son competencias que la taxonomia todavia no cubre
      (esta es la lista de trabajo de la curacion).
    """
    mapa = skills_fuente.mapa_normalizado(connection)
    resueltas: Counter[Clave] = Counter()
    ruido: Counter[Clave] = Counter()
    pendientes: Counter[Clave] = Counter()

    def _demanda_de_idioma(variante: str) -> None:
        """Cuenta una peticion de idioma en su lado (idioma), no en skills.

        El idioma se compara contra los hechos de IDIOMA del perfil
        (``cumple_language``): un concepto skill con "espanol c1" haria un
        falso "faltante" incluso con el perfil diciendo que el espanol es
        su lengua nativa.
        """
        clave = skills_fuente.normalizar(variante)
        if not clave:
            return
        if ("language", clave) in mapa:
            resueltas[("language", clave)] += 1
        elif conceptos.es_variante_encolable("language", clave):
            pendientes[("language", clave)] += 1
        else:
            ruido[("language", clave)] += 1

    for _job_id, skills, languages in _filas_corpus(connection):
        for etiqueta in skills_fuente.parsear_skills(skills):
            clave = skills_fuente.normalizar(etiqueta)
            if not clave:
                continue
            # Idioma disfrazado de skill ("Inglés - C1" entre las skills de
            # ANE): el extractor nunca lo convierte en requisito skill, asi
            # que la cola no debe pedir curarlo como tal. Va al lado idioma.
            variante_idioma = idiomas.idioma_en_skill(etiqueta)
            if variante_idioma is not None:
                _demanda_de_idioma(variante_idioma)
                continue
            if skills_fuente.clasificar(connection, clave, mapa):
                resueltas[("skill", clave)] += 1
            elif conceptos.es_variante_encolable("skill", clave):
                pendientes[("skill", clave)] += 1
            else:
                ruido[("skill", clave)] += 1

        for nombre in skills_fuente.parsear_languages(languages):
            clave = skills_fuente.normalizar(nombre)
            if not clave:
                continue
            if skills_fuente.clasificar(connection, clave, mapa):
                resueltas[("language", clave)] += 1
            elif conceptos.es_variante_encolable("language", clave):
                pendientes[("language", clave)] += 1
            else:
                ruido[("language", clave)] += 1

    return {
        "resueltas": resueltas,
        "ruido": ruido,
        "pendientes": pendientes,
    }


def _cola_actual(connection: sqlite3.Connection) -> list[tuple]:
    """Filas de la cola como tuplas ``(categoria, texto, origen, veces)``."""
    return connection.execute(
        """
        SELECT categoria, texto, origen, veces
        FROM concepto_no_normalizado
        ORDER BY categoria, texto, origen
        """
    ).fetchall()


def curar(
    connection: sqlite3.Connection,
    *,
    aplicar: bool = False,
    limite: int = 50,
) -> dict[str, Any]:
    """Audita la cola y (opcionalmente) la reconstruye desde el corpus.

    ``aplicar=False`` (por defecto): solo informa; no escribe nada.

    ``aplicar=True``: deja la cola de las OFERTAS con lo que el corpus pide
    de verdad y sigue sin concepto:

    * se BORRAN las filas que ya resolvieron (la taxonomia las cubrio) y las
      que son ruido (no son competencias);
    * se BORRAN las filas que el corpus ya no pide (entradas historicas);
    * se reescribe ``veces`` con el numero de AVISOS que piden cada variante
      (antes contaba encolados: un valor que se inflationaba con cada
      re-analisis y no decia cuanto la pedia el corpus).

    Las filas de origen ``cv`` (hechos del perfil) NO se tocan: la curacion
    de la taxonomia es la misma para los dos lados.

    No borra avisos, analisis ni requisitos: solo la lista de trabajo de la
    taxonomia (que es un estado derivado).
    """
    demanda = demanda_corpus(connection)
    pendientes: Counter[Clave] = demanda["pendientes"]
    cola = _cola_actual(connection)

    oferta_actual = {
        (categoria, texto): (origen, veces)
        for categoria, texto, origen, veces in cola
        if origen != "cv"
    }
    # El corpus es la verdad: lo pendiente es lo que pide y no resuelve.
    objetivo: dict[Clave, int] = dict(pendientes)

    a_borrar = [clave for clave in oferta_actual if clave not in objetivo]
    a_agregar = [clave for clave in objetivo if clave not in oferta_actual]
    a_actualizar = [
        clave
        for clave in objetivo
        if clave in oferta_actual
        and int(oferta_actual[clave][1]) != objetivo[clave]
    ]
    # Las filas del perfil (origen 'cv') no se tocan: cuentan aparte.
    filas_cv = len(cola) - len(oferta_actual)

    informe: dict[str, Any] = {
        "modo": "apply" if aplicar else "dry_run",
        "cola_antes": len(cola),
        "filas_oferta_antes": len(oferta_actual),
        "filas_cv_antes": filas_cv,
        "demanda": {
            "resueltas": len(demanda["resueltas"]),
            "resueltas_menciones": sum(demanda["resueltas"].values()),
            "ruido": len(demanda["ruido"]),
            "ruido_menciones": sum(demanda["ruido"].values()),
            "pendientes": len(pendientes),
            "pendientes_menciones": sum(pendientes.values()),
        },
        "a_borrar": len(a_borrar),
        "a_agregar": len(a_agregar),
        "a_actualizar": len(a_actualizar),
        # Las filas del perfil no se tocan: siguen en la cola.
        "cola_despues": filas_cv + len(oferta_actual) - len(a_borrar) + len(a_agregar),
        "top_pendientes": [
            {"categoria": categoria, "variante": variante, "menciones": n}
            for (categoria, variante), n in sorted(
                pendientes.items(), key=lambda par: (-par[1], par[0])
            )[:limite if limite > 0 else None]
        ],
    }

    if aplicar:
        for categoria, texto in a_borrar:
            connection.execute(
                """
                DELETE FROM concepto_no_normalizado
                WHERE categoria = ? AND texto = ? AND origen <> 'cv'
                """,
                (categoria, texto),
            )
        for (categoria, texto), n in objetivo.items():
            # Se reescribe la fila desde cero: si existia con otro origen
            # ('ambos'), queda una sola, la de las ofertas (el corpus).
            connection.execute(
                """
                DELETE FROM concepto_no_normalizado
                WHERE categoria = ? AND texto = ? AND origen <> 'cv'
                """,
                (categoria, texto),
            )
            connection.execute(
                """
                INSERT INTO concepto_no_normalizado (categoria, texto, origen, veces)
                VALUES (?, ?, 'oferta', ?)
                ON CONFLICT (categoria, texto, origen)
                DO UPDATE SET veces = excluded.veces
                """,
                (categoria, texto, n),
            )
    return informe
