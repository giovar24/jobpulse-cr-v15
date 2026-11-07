# -*- coding: utf-8 -*-
"""Normalizacion de requisitos al codigo canonico de la tabla ``concepto``.

La tabla ``concepto`` (migracion 009) mapea variantes de texto a codigos
canonicos. La migracion 010 relleno ``job_requirements.codigo_canonico`` como
backfill ONE-TIME: en ningun punto del codigo se rellenaba al INSERTAR, asi
que todo requisito nuevo queda en NULL y el Paso 5 lo descarta
(``matching`` filtra ``AND codigo_canonico IS NOT NULL``) -> la vacante se
evalua con 0 requisitos y cae en ``sin_requisitos``.

Este modulo cierra el hueco: resuelve el codigo AL GUARDAR el analisis y
encola las variantes sin concepto en ``concepto_no_normalizado`` para que la
taxonomia crezca con datos reales (la cola solo la llenaba la migracion 010).

Regla de resolucion (identica a la del backfill de la migracion 010):
``concepto.variante = LOWER(TRIM(value_code))`` y ``categoria = category``.
Solo se usan conceptos activos (``activa = 1``).
"""
from __future__ import annotations

import sqlite3
from typing import Any, Mapping, Sequence

# Categorias que la tabla `concepto` puede cubrir (CHECK de la migracion 009).
CATEGORIAS_CONCEPTO = ("skill", "language", "license", "education", "experience")

#: Categorias cuyo `value_code` del perfil es un CONCEPTO (una skill, un
#: idioma, una licencia, un nivel de estudio). Las demas (titulo de puesto,
#: area, contacto) NO son conceptos: encolarlas ensuciaria la taxonomia.
CATEGORIAS_PERFIL_CONCEPTO = ("skill", "language", "license", "education")

# ---------------------------------------------------------------------------
# Filtro de la cola (Ola 4.2)
# ---------------------------------------------------------------------------
#
# La cola `concepto_no_normalizado` es la LISTA DE TRABAJO de la taxonomia:
# "estas variantes del corpus todavia no tienen codigo canonico". Para que
# sirva, solo debe contener lo que de verdad falta.
#
# Audit del corpus real (2026-11-06, 3397 skills distintas / 5199 menciones):
# solo 241 resolvian a un concepto; 1180 eran frases de tarea y 1976 NO
# resolvian. De esas 1976, la mayoria NO eran competencias sino:
#
#   * ACTIVIDADES  ("despachar", "empacar", "revisar equipos"): lo que hace el
#     puesto, no lo que sabe el perfil;
#   * PALABRAS VACIAS ("analysis", "planning", "control"): no distinguen nada;
#   * SECTORES ("construccion", "ventas"): nombran el sector, no la skill.
#
# El criterio NO es nuevo: la migracion 021 ya lo aplico a mano ("se deja
# fuera lo que es una funcion ('ventas'), un sector ('construccion'), una
# palabra vacia ('analysis', 'planning') o una tarea ('despachar',
# 'empacar')"). Aqui se automatiza para que la cola no vuelva a llenarse de
# basura, y la curacion de lo que SI falta se hace por tandas (datos, no
# codigo).
#
# El filtro es CONSERVADOR: solo descarta lo que es inequivocamente una
# actividad, una palabra vacia o un sector. Lo que no entra en estas listas
# se queda en la cola (a la espera de curacion), nunca se borra en silencio.

#: Palabras que describen una ACTIVIDAD: un verbo de tarea (o su
#: nominalizacion) en espanol o ingles. "Despachar" no es una competencia.
PALABRAS_DE_ACTIVIDAD = frozenset({
    # -- espanol: verbos de tarea --
    "acomodar", "ajustar", "alinear", "alistar", "aprobar", "armar", "archivar",
    "asesorar", "atender", "auditar", "balancear", "barrer", "calibrar",
    "cambiar", "capturar", "clasificar", "colectar", "colocar", "completar",
    "componer", "conectar", "configurar", "contar", "controlar", "cortar",
    "cotizar", "crear", "cuantificar", "desarmar", "despachar", "digitar",
    "dirigir", "distribuir", "ejecutar", "elaborar", "empacar", "entregar",
    "envolver", "escalar", "escanear", "esmerillar", "establecer", "estimar",
    "evaluar", "examinar", "expedir", "fabricar", "fregar", "generar",
    "gestionar", "guardar", "identificar", "implementar", "imprimir",
    "inspeccionar", "instalar", "instruir", "inventariar", "limpiar",
    "llenar", "mantener", "medir", "mezclar", "moler", "monitorear",
    "monitorizar", "notificar", "operar", "ordenar", "organizar", "pagar",
    "pelar", "pesar", "planificar", "preparar", "presentar", "presenciar",
    "prestar", "probar", "producir", "programar", "proteger", "proyectar",
    "publicar", "pulir", "recepcionar", "recibir", "recabar", "recolectar",
    "recomendar", "redactar", "registrar", "reparar", "rellenar", "reportar",
    "revisar", "rotular", "seleccionar", "separar", "servir", "soportar",
    "supervisar", "tapar", "tomar", "transportar", "trasladar", "vender",
    "verificar", "vigilar", "realizar", "retirar", "buscar", "almacenar",
    "investigar", "modificar", "analizar", "comparar", "cargar", "descargar",
    "sincronizar", "migrar", "gestionar", "surtir", "reponer", "revisar",
    # -- espanol: nominalizaciones de una actividad --
    "acomodacion", "acomodar", "acomodo", "ajuste", "alisto", "aprobacion",
    "armado", "archivo", "asesoramiento", "atencion", "auditoria", "barrido",
    "calibracion", "cambio", "clasificacion", "colecta", "colocacion",
    "completado", "composicion", "conexion", "configuracion", "conteo",
    "control", "correccion", "corte", "cotizacion", "creacion", "desarmado",
    "despacho", "digito", "distribucion", "ejecucion", "elaboracion",
    "empacado", "empaque", "ensamblaje", "entrega", "envoltura", "escaneo",
    "esmerilado", "estimacion", "evaluacion", "examen", "expedicion",
    "fabricacion", "fregado", "generacion", "gestion", "impresion",
    "inspeccion", "instalacion", "implementacion", "limpieza", "llenado",
    "medicion", "mezcla", "molienda", "monitoreo", "notificacion",
    "operacion", "ordenamiento", "pago", "pesaje", "planificacion",
    "preparacion", "presentacion", "produccion", "programacion", "proyeccion",
    "publicacion", "pulido", "prueba", "pruebas", "recepcion", "recoleccion",
    "recomendacion", "recopilacion", "registro", "reparacion",
    "reparaciones", "reporte", "revision", "rotulacion", "seguimiento",
    "separacion", "supervision", "tapeado", "toma", "tomas", "transporte",
    "traslado", "verificacion", "vigilancia",
    # -- ingles: verbos de tarea --
    "activate", "adjust", "align", "apply", "assemble", "automate", "calculate",
    "calibrate", "carry", "check", "clean", "close", "collect", "complete",
    "configure", "connect", "control", "cook", "cut", "debug", "deliver",
    "deploy", "design", "develop", "diagnose", "dispatch", "drive", "execute",
    "fill", "finish", "fix", "handle", "implement", "install", "inspect",
    "load", "maintain", "make", "manage", "mix", "monitor", "operate", "pack",
    "perform", "pick", "prepare", "process", "produce", "program", "provide",
    "receive", "record", "register", "repair", "remove", "replace", "report",
    "review", "run", "schedule", "seal", "select", "ship", "sort", "stack",
    "stock", "support", "take", "test", "track", "troubleshoot", "upgrade",
    "validate", "wash", "weigh", "weld", "wrap",
    # -- ingles: gerundio de tarea --
    "analyzing", "assembling", "auditing", "billing", "booking", "cleaning",
    "coding", "configuring", "controlling", "counting", "cutting",
    "delivering", "designing", "developing", "dispatching", "driving",
    "editing", "evaluating", "executing", "handling", "inspecting",
    "installing", "inventorying", "labeling", "loading", "maintaining",
    "managing", "measuring", "monitoring", "operating", "ordering",
    "packaging", "painting", "patching", "picking", "preparing", "processing",
    "producing", "programming", "receiving", "reconciling", "recording",
    "repairing", "reporting", "researching", "resolving", "restoring",
    "reviewing", "running", "scheduling", "sealing", "setting", "shipping",
    "sorting", "stocking", "supporting", "testing", "tracking",
    "troubleshooting", "upgrading", "validating", "weighing", "wrapping",
})

#: Palabras demasiado GENERICAS: no distinguen una competencia ("analysis",
#: "planning", "control"). Solo se aplican a variantes de UNA palabra: en
#: una frase ("control de calidad") la palabra puede ser legitima y la
#: curacion la decide la tanda, no el filtro automatico.
PALABRAS_GENERICAS = frozenset({
    "activities", "actividad", "actividades", "analysis", "analisis",
    "applications", "aprendizaje", "area", "areas", "business", "capacidad",
    "capacidades", "computer", "computers", "computador", "conocimiento",
    "conocimientos", "data", "datos", "delivery", "desarrollo", "development",
    "document", "documents", "documentos", "entrega", "equipo", "equipment",
    "execution", "ejecucion", "engineering", "experiencia", "experience",
    "herramientas", "information", "informacion", "ingenieria", "knowledge",
    "logistica", "management", "materials", "materiales", "metodo", "metodos",
    "objetivos", "operations", "operaciones", "performance", "planning",
    "planificacion", "process",
    "processes", "proceso", "procesos", "procedure", "procedures",
    "procedimiento", "project", "projects", "proyecto", "proyectos",
    "recursos", "resources", "service", "services", "servicio", "servicios",
    "software", "soporte", "support", "sistema", "sistemas", "skills",
    "habilidades", "solucion", "soluciones", "solution", "solutions", "team",
    "teams", "technology", "tecnologia", "trabajo", "work", "workplace",
})

#: SECTORES / areas de negocio: nombran el sector, no la competencia
#: ("construccion", "ventas" son los ejemplos que la migracion 021 excluyo
#: a mano).
SECTORES = frozenset({
    "administracion", "agroforesteria", "automotriz", "banca", "comercio",
    "construccion", "construcciones", "contabilidad", "culinary", "electrica",
    "electronica", "financiera", "finanzas", "gastronomia", "hoteleria",
    "hospitality", "informatica", "ingenieria", "inmobiliaria", "logistica",
    "logistics", "manufactura", "manufacturing", "marketing", "medicina",
    "metalmecanica", "operations", "panaderia", "pasteleria", "publicidad",
    "quimica", "reposteria", "restauracion", "retail", "salud", "silvicultura",
    "telecomunicaciones", "textil", "transportes", "turismo", "ventas",
    "sales", "accounting",
})

#: Maximo de palabras de una variante encolable (mismo criterio que el
#: ranking ATS: "account and inventory reconciliation activities" es una
#: frase, no una competencia).
MAX_PALABRAS_VARIANTE = 3


def _variante(value_code: str | None) -> str:
    return (value_code or "").strip().lower()


def _variantes_alternas(variante: str) -> tuple[str, ...]:
    """Variantes equivalentes a la dada (para tolerar slugs).

    El importador de CV produce SLUGS ('active-directory', 'excel-avanzado')
    y la taxonomia esta escrita en texto natural ('active directory'). Son la
    MISMA variante: se prueban las dos formas (y la de guiones bajos).
    """
    if not variante:
        return ()
    alternas: list[str] = []
    con_espacios = variante.replace("-", " ").replace("_", " ").strip()
    if con_espacios and con_espacios != variante:
        alternas.append(con_espacios)
    con_guiones = variante.replace(" ", "-").replace("_", "-").strip()
    if con_guiones and con_guiones != variante:
        alternas.append(con_guiones)
    return tuple(alternas)


def mapa_conceptos(connection: sqlite3.Connection) -> dict[tuple[str, str], str]:
    """Carga ``(categoria, variante) -> codigo_canonico`` de los conceptos activos.

    Publica: la usan tambien ``skills_fuente`` (para clasificar las skills que
    trae la fuente) y los backfills, que necesitan el mismo mapa.
    """
    try:
        rows = connection.execute(
            """
            SELECT categoria, variante, codigo_canonico
            FROM concepto
            WHERE activa = 1
            """
        ).fetchall()
    except sqlite3.OperationalError:
        # Sin la tabla `concepto` (esquema viejo o BD minima en tests):
        # se deja el requisito sin codigo, igual que hacia la migracion 010.
        return {}
    return {
        (row[0], row[1]): row[2]
        for row in rows
    }


#: Alias interno (compatibilidad con las llamadas previas).
_mapa_conceptos = mapa_conceptos


def es_variante_encolable(categoria: str, variante: str) -> bool:
    """True si la variante merece entrar en la cola de la taxonomia.

    La cola `concepto_no_normalizado` es la lista de trabajo de la
    taxonomia: lo que el corpus pide y todavia no tiene codigo canonico.
    Para que sirva, no debe llenarse de basura.

    Se descarta (NO se encola):

    * lo que no es una categoria de concepto;
    * lo que tiene mas de ``MAX_PALABRAS_VARIANTE`` palabras (es una frase);
    * lo que el ranking ATS ya identifica como frase de tarea
      (``ats.es_frase_de_tarea``);
    * lo que contiene un VERBO DE TAREA ("despachar", "revisar equipos"):
      describe la ACTIVIDAD del puesto, no la competencia del perfil;
    * lo que es una PALABRA VACIA ("analysis", "planning") o un SECTOR
      ("construccion", "ventas").

    El filtro es conservador: lo que no cae en estas reglas se queda en la
    cola, a la espera de curacion. Nunca se descarta una variante en
    silencio (la cola es informacion, no un error).
    """
    if categoria not in CATEGORIAS_CONCEPTO:
        return False
    texto = _variante(variante)
    if not texto:
        return False
    palabras = texto.split()
    if len(palabras) > MAX_PALABRAS_VARIANTE:
        return False
    # El filtro de frases de tarea vive en el modulo del ranking ATS: es la
    # MISMA regla que ya se aplica a `jobs.skills` (una sola implementacion).
    from jobpulse_v15 import ats

    if ats.es_frase_de_tarea(texto):
        return False
    if any(palabra in PALABRAS_DE_ACTIVIDAD for palabra in palabras):
        return False
    if len(palabras) == 1:
        if texto in PALABRAS_GENERICAS or texto in SECTORES:
            return False
    return True


def resolver(
    connection: sqlite3.Connection,
    requirements: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    """Resuelve el codigo canonico de cada requisito.

    Devuelve ``(requisitos, sin_concepto)``:
    - requisitos: copias con la clave ``codigo_canonico`` (``None`` si no hay
      concepto para esa variante);
    - sin_concepto: pares ``(categoria, variante)`` que no tienen concepto y
      deben encolarse en ``concepto_no_normalizado``.
    """
    mapa = _mapa_conceptos(connection)
    resueltos: list[dict[str, Any]] = []
    sin_concepto: list[tuple[str, str]] = []
    vistas: set[tuple[str, str]] = set()
    for requirement in requirements:
        copia = dict(requirement)
        category = copia.get("category")
        # La variante es el `value_code`; si el requisito no trae (las
        # licencias que el extractor guardaba como "Driver's license" sin
        # clase), se usa su `value_text`: sin este fallback el requisito
        # queda SIN codigo y el motor lo IGNORA en silencio.
        variante = _variante(copia.get("value_code")) or _variante(
            copia.get("value_text")
        )
        codigo = None
        if category in CATEGORIAS_CONCEPTO and variante:
            codigo = mapa.get((category, variante))
            if codigo is None:
                # Slug del CV ('active-directory') vs texto de la taxonomia
                # ('active directory'): son la misma variante.
                for alterna in _variantes_alternas(variante):
                    codigo = mapa.get((category, alterna))
                    if codigo is not None:
                        break
        copia["codigo_canonico"] = codigo
        resueltos.append(copia)
        if codigo is None and category in CATEGORIAS_CONCEPTO and variante:
            clave = (category, variante)
            if clave not in vistas:
                vistas.add(clave)
                sin_concepto.append(clave)
    return resueltos, sin_concepto


def encolar_sin_concepto(
    connection: sqlite3.Connection,
    sin_concepto: Sequence[tuple[str, str]],
    *,
    origen: str = "oferta",
) -> int:
    """Suma las variantes sin concepto a la cola ``concepto_no_normalizado``.

    `origen`: 'oferta' (requisito del aviso), 'cv' (hecho del perfil) o
    'ambos'. La cola usa la variante como texto.

    **Filtro (Ola 4.2)**: solo entran las variantes ENCOLABLES
    (``es_variante_encolable``): las actividades ("despachar"), las palabras
    vacias ("analysis") y los sectores ("construccion") no son competencias
    que la taxonomia deba cubrir, y llenaban la cola de basura (1988 filas
    en la BD real, 1976 de ellas sin concepto). Es el UNICO punto de
    entrada de la cola, asi que el filtro se aplica a todos los origenes.

    Devuelve cuantas filas se encolaron de verdad (0 si todo se descarto).
    """
    if origen not in ("oferta", "cv", "ambos"):
        raise ValueError("origen debe ser 'oferta', 'cv' o 'ambos'.")
    encoladas = 0
    for category, variante in sin_concepto:
        if not es_variante_encolable(category, variante):
            continue
        connection.execute(
            """
            INSERT INTO concepto_no_normalizado (categoria, texto, origen, veces)
            VALUES (?, ?, ?, 1)
            ON CONFLICT (categoria, texto, origen)
            DO UPDATE SET veces = veces + 1
            """,
            (category, variante, origen),
        )
        encoladas += 1
    return encoladas
