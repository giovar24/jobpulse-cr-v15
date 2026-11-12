# -*- coding: utf-8 -*-
"""Motor de VIABILIDAD = AJUSTE TECNICO del perfil con el aviso.

Distingue dos cosas que NO son lo mismo (regla del usuario, 2026-11-04):

* **Ajuste tecnico** (este modulo): el perfil cumple los requisitos que el
  aviso declara. Es deterministico y auditable.
* **Resultado del proceso** (`postulaciones.py`): lo que el reclutador humano
  decidio. **Ser rechazado NO significa que el perfil no califique** (hay
  presupuesto, timing, competencia, sesgos y azar). Por eso el resultado del
  proceso NUNCA entra en este score: solo sirve de contexto operativo.

Inspiracion (ATS modernos):
* Workday Skills Based Hiring: match de skills + *gaps*, con el desempate en
  los requisitos, no en la similitud de texto.
* Greenhouse/Lever: los requisitos (`required` / `preferred`) mandan; lo demas
  ordena.
* HireVue/Paradox: los *knockout* (requisitos que bloquean) son EXPLICITOS.
  Aqui el unico veto de negocio es el educativo (titulo universitario
  obligatorio confirmado por el texto) y el de area; el resto pondera.

Es un RANKING/INDICE propio: NO toca los umbrales congelados del Paso 5
(cobertura 0.60 / puntaje 0.80) ni los estados de `job_match`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from jobpulse_v15 import areas
from jobpulse_v15.matching import EvaluadorPaso5, Requisito

# ------------------------------------------------------------------ bandas --
BANDA_APLICAR = "aplicar"
BANDA_REVISAR = "revisar"
BANDA_NO_PRIORITARIO = "no_prioritario"
BANDA_VETO = "veto"
BANDA_SIN_DATOS = "sin_datos"

ORDEN_BANDAS: tuple[str, ...] = (
    BANDA_APLICAR,
    BANDA_REVISAR,
    BANDA_NO_PRIORITARIO,
    BANDA_SIN_DATOS,
    BANDA_VETO,
)

#: Umbrales de las bandas (fijos y documentados: se cambian aqui, no en las UIs).
UMBRAL_APLICAR = 85.0
UMBRAL_REVISAR = 80.0

#: Pesos por categoria de requisito (fijos: comparables entre avisos).
PESOS_CATEGORIA: dict[str, float] = {
    "skill": 0.40,
    "education": 0.25,
    "experience": 0.15,
    "language": 0.10,
    "license": 0.10,
}

#: Peso interno de cada nivel de requisito dentro de su categoria.
PESO_NIVEL: dict[str, float] = {
    "obligatorio": 2.0,
    "incierto": 1.0,
    "deseable": 0.5,
}

# --------------------------------------------------------- estados de req ---
ESTADO_CUMPLE = "cumple"
ESTADO_FALTA = "falta"
ESTADO_NO_VERIFICABLE = "no_verificable"
ESTADO_NO_CONFIRMADO = "no_confirmado"
ESTADO_BLOQUEANTE = "bloqueante"

#: Motivos (codigos estables para la UI y el CSV).
MOTIVO_VETO_AREA = "fuera_de_area"
MOTIVO_VETO_EDUCACION = "titulo_universitario_requerido"
MOTIVO_VETO_EN_CURSO = "titulo_universitario_en_curso_requerido"
MOTIVO_SIN_REQUISITOS = "sin_requisitos_mapeados"
MOTIVO_OBLIGATORIO_FALTANTE = "requisito_obligatorio_faltante"


@dataclass(frozen=True)
class DesgloseRequisito:
    """Un requisito del aviso y como queda frente al perfil."""

    category: str
    value_code: str
    value_text: str
    codigo_canonico: str
    nivel: str  # obligatorio | incierto | deseable
    estado: str  # cumple | falta | no_verificable | no_confirmado | bloqueante
    peso: float = 0.0
    motivo: str = ""

    @property
    def es_obligatorio(self) -> bool:
        return self.nivel == "obligatorio"

    @property
    def penaliza(self) -> bool:
        """True si este requisito baja el score (falta de verdad)."""
        return self.estado == ESTADO_FALTA

    @property
    def bloquea(self) -> bool:
        return self.estado == ESTADO_BLOQUEANTE


@dataclass
class Viabilidad:
    """Indice de ajuste tecnico de una vacante (0-100) y su lectura."""

    job_id: str
    ajuste: float | None = None
    banda: str = BANDA_SIN_DATOS
    veto: str = ""
    motivos: list[str] = field(default_factory=list)
    cobertura_obligatorios: float | None = None
    cobertura_deseables: float | None = None
    componentes: dict[str, float | None] = field(default_factory=dict)
    faltantes_obligatorios: list[str] = field(default_factory=list)
    desglose: list[DesgloseRequisito] = field(default_factory=list)
    total_requisitos: int = 0
    requisitos_evaluables: int = 0

    @property
    def aplicar(self) -> bool:
        return self.banda == BANDA_APLICAR

    @property
    def texto_banda(self) -> str:
        return {
            BANDA_APLICAR: "Aplicar",
            BANDA_REVISAR: "Revisar",
            BANDA_NO_PRIORITARIO: "No prioritario",
            BANDA_SIN_DATOS: "Sin datos",
            BANDA_VETO: "Descartado",
        }.get(self.banda, self.banda)

    @property
    def resumen(self) -> str:
        """Explicacion en una linea (para la tabla y el CSV)."""
        if self.veto:
            return self.veto
        partes: list[str] = []
        if self.cobertura_obligatorios is not None:
            partes.append(
                f"obligatorios {round(self.cobertura_obligatorios * 100)}%"
            )
        if self.cobertura_deseables is not None:
            partes.append(
                f"deseables {round(self.cobertura_deseables * 100)}%"
            )
        if self.faltantes_obligatorios:
            partes.append("falta: " + ", ".join(self.faltantes_obligatorios[:3]))
        return " | ".join(partes) if partes else "sin datos"


# ------------------------------------------------------------- helpers -----
def nivel_de_requisito(requisito: Requisito) -> str:
    """Nivel del requisito para el score.

    * `required` -> obligatorio.
    * `preferred` -> deseable ("Preferred" no bloquea).
    * `ambiguous` / `inferred` / sin nivel -> incierto: pesa como deseable y
      NO activa el tope de banda (el texto podria no exigirlo). La
      obligatoriedad DURO la decide el texto (ver `evaluar_educacion`).
    """
    nivel = (requisito.requirement_level or "").strip().lower()
    if nivel == "required":
        return "obligatorio"
    if nivel == "preferred":
        return "deseable"
    return "incierto"


def _redistribuir(
    componentes: Mapping[str, float | None],
    pesos: Mapping[str, float],
    extra: Mapping[str, float | None] | None = None,
) -> tuple[float, dict[str, float]]:
    """Score ponderado; los componentes SIN DATO se quitan y su peso se
    redistribuye entre los demas (nadie premia ni castiga la falta de dato).

    Devuelve (score 0-1, pesos efectivos usados).
    """
    todos: dict[str, float | None] = dict(componentes)
    if extra:
        todos.update(extra)
    pesos_vivos = {
        clave: peso
        for clave, peso in pesos.items()
        if todos.get(clave) is not None and peso > 0
    }
    total_peso = sum(pesos_vivos.values())
    if total_peso <= 0:
        return 0.0, {}
    score = 0.0
    for clave, peso in pesos_vivos.items():
        valor = todos.get(clave)
        if valor is None:
            continue
        score += (valor * peso) / total_peso
    return score, pesos_vivos


# ------------------------------------------------------------- evaluacion ---
def _evaluar_requisito(
    evaluador: EvaluadorPaso5,
    requisito: Requisito,
    texto: str,
    job_id: str | None = None,
) -> DesgloseRequisito:
    """Estado de UN requisito frente al perfil (reutiliza las reglas duras)."""
    nivel = nivel_de_requisito(requisito)
    categoria = requisito.category
    estado = ESTADO_FALTA
    motivo = ""

    if categoria == "skill":
        estado = ESTADO_CUMPLE if evaluador.cumple_skill(requisito.codigo_canonico) else ESTADO_FALTA
        motivo = "" if estado == ESTADO_CUMPLE else "skill_faltante"
    elif categoria == "language":
        if requisito.implicito:
            resultado = evaluador.cumple_idioma_del_aviso(requisito.codigo_canonico)
        else:
            resultado = evaluador.cumple_language(
                requisito.codigo_canonico, requisito.qualifier
            )
        if resultado is True:
            estado = ESTADO_CUMPLE
        elif resultado == "no_verificable":
            estado = ESTADO_NO_VERIFICABLE
            motivo = "idioma_no_comparable"
        else:
            estado = ESTADO_FALTA
            motivo = "idioma_no_comparable"
    elif categoria == "education":
        # ``job_id`` permite que el motor aplique la DECISION FIRMADA de la
        # dimension educativa (si el motor no pudo decidir).
        estado_educacion, _conf = evaluador.evaluar_educacion(
            requisito, texto, job_id
        )
        if estado_educacion == "cumple":
            estado = ESTADO_CUMPLE
        elif estado_educacion == "bloqueante":
            estado = ESTADO_BLOQUEANTE
            motivo = (
                MOTIVO_VETO_EN_CURSO
                if (_conf is not None and _conf.en_curso)
                else MOTIVO_VETO_EDUCACION
            )
        elif estado_educacion == "no_confirmado":
            estado = ESTADO_NO_CONFIRMADO
            motivo = "educacion_no_confirmada"
        elif estado_educacion == "no_verificable":
            estado = ESTADO_NO_VERIFICABLE
            motivo = "educacion_no_verificable"
        else:
            estado = ESTADO_FALTA
            motivo = "educacion_no_cumple"
    elif categoria == "experience":
        resultado = evaluador.cumple_experience(requisito.minimum)
        if resultado is True:
            estado = ESTADO_CUMPLE
        elif resultado == "no_verificable":
            estado = ESTADO_NO_VERIFICABLE
            motivo = "experiencia_no_verificable"
        else:
            estado = ESTADO_FALTA
            motivo = "experiencia_no_cumple"
    elif categoria == "license":
        # Licencia: misma regla que los idiomas. Si el perfil no registra
        # ninguna licencia, NO se puede afirmar que no la tenga -> queda
        # pendiente (no penaliza). Si registra otras, y no esa -> falta de
        # verdad.
        resultado = evaluador.cumple_license(requisito.codigo_canonico)
        if resultado is True:
            estado = ESTADO_CUMPLE
        elif resultado == "no_verificable":
            estado = ESTADO_NO_VERIFICABLE
            motivo = "licencia_no_comparable"
        else:
            estado = ESTADO_FALTA
            motivo = "licencia_no_cumple"

    return DesgloseRequisito(
        category=categoria,
        value_code=requisito.value_code,
        value_text=requisito.value_text,
        codigo_canonico=requisito.codigo_canonico,
        nivel=nivel,
        estado=estado,
        peso=PESO_NIVEL.get(nivel, 1.0),
        motivo=motivo,
    )


def _componentes_de(
    evaluables: Sequence[DesgloseRequisito],
) -> dict[str, float | None]:
    """Componente por categoria (0-1): fraccion cubierta, ponderada por nivel.

    `None` = la categoria no tiene requisitos evaluables (NO hay dato).
    """
    componentes: dict[str, float | None] = {}
    for categoria in PESOS_CATEGORIA:
        items = [d for d in evaluables if d.category == categoria]
        if not items:
            componentes[categoria] = None
            continue
        peso_total = sum(d.peso for d in items)
        cubierto = sum(d.peso for d in items if d.estado == ESTADO_CUMPLE)
        componentes[categoria] = (cubierto / peso_total) if peso_total else None
    return componentes


def puntuar_componentes(
    componentes: Mapping[str, float | None],
    *,
    pesos_categoria: Mapping[str, float] | None = None,
    imputacion: Mapping[str, float] | None = None,
) -> tuple[float, dict[str, float]]:
    """Puntaje 0-100 de los componentes de una vacante.

    DOS MODOS (misma idea que el ranking ATS, gotcha 26):

    * **con `imputacion`** (modo corpus): los componentes SIN DATO toman el
      promedio del corpus y los pesos son FIJOS -> las vacantes son
      comparables entre si. Sin esto, una vacante con un solo requisito
      cubierto sacaria 100 y subiria sola en el ranking.
    * **sin `imputacion`** (modo vacante suelta): los componentes sin dato
      se quitan y su peso se redistribuye (nadie premia ni castiga la falta
      de dato, pero el score no es comparable con otras vacantes).
    """
    pesos = dict(pesos_categoria or PESOS_CATEGORIA)
    valores: dict[str, float | None] = dict(componentes)

    if imputacion is not None:
        for clave, valor in list(valores.items()):
            if valor is not None:
                continue
            promedio = imputacion.get(clave)
            if promedio is None:
                # Sin promedio del corpus para ese componente: se excluye
                # (no se inventa un 0, que castigaria al que no tiene dato).
                continue
            valores[clave] = float(promedio)
        return _redistribuir(valores, pesos)

    return _redistribuir(valores, pesos)


def promedios_componentes(
    componentes: Sequence[Mapping[str, float | None]],
) -> dict[str, float]:
    """Promedio del corpus por componente (para la imputacion).

    Solo promedia los avisos que SI tienen dato de ese componente: el
    promedio de "quien no tiene datos" no debe entrar.
    """
    promedios: dict[str, float] = {}
    for clave in PESOS_CATEGORIA:
        valores = [
            float(componentes[clave])
            for componentes in componentes
            if componentes.get(clave) is not None
        ]
        if valores:
            promedios[clave] = sum(valores) / len(valores)
    return promedios


def evaluar_viabilidad(
    evaluador: EvaluadorPaso5,
    job_id: str,
    *,
    pesos_categoria: Mapping[str, float] | None = None,
    umbral_aplicar: float = UMBRAL_APLICAR,
    umbral_revisar: float = UMBRAL_REVISAR,
    imputacion: Mapping[str, float] | None = None,
) -> Viabilidad:
    """Indice de ajuste tecnico de una vacante (0-100) + su banda.

    `imputacion`: promedios del corpus (modo comparable, ver
    `puntuar_componentes`).
    """
    pesos_categoria = dict(pesos_categoria or PESOS_CATEGORIA)
    resultado = Viabilidad(job_id=job_id)

    # -- veto de AREA (el perfil no marco esa area) -------------------------
    # Se reutiliza `areas.es_fuera_de_area`: las ofertas `otros` o sin
    # clasificar NUNCA se vetan (una clasificacion dudosa no tapa ofertas).
    if evaluador.aplicar_filtro_areas and areas.es_fuera_de_area(
        evaluador.area_por_job.get(job_id), evaluador.areas_perfil
    ):
        resultado.banda = BANDA_VETO
        resultado.veto = MOTIVO_VETO_AREA
        resultado.motivos.append(MOTIVO_VETO_AREA)
        return resultado

    requisitos = evaluador.requisitos_efectivos(job_id)
    if not requisitos:
        resultado.banda = BANDA_SIN_DATOS
        resultado.motivos.append(MOTIVO_SIN_REQUISITOS)
        return resultado

    texto = evaluador.textos_por_job.get(job_id, "")
    desglose = [
        _evaluar_requisito(evaluador, requisito, texto, job_id)
        for requisito in requisitos
    ]
    resultado.desglose = desglose
    resultado.total_requisitos = len(desglose)

    # -- veto EDUCATIVO (titulo universitario obligatorio, texto confirmado) -
    for item in desglose:
        if item.bloquea:
            resultado.banda = BANDA_VETO
            resultado.veto = item.motivo or MOTIVO_VETO_EDUCACION
            resultado.motivos.append(resultado.veto)
            return resultado

    evaluables = [d for d in desglose if d.estado != ESTADO_NO_VERIFICABLE]
    resultado.requisitos_evaluables = len(evaluables)
    if not evaluables:
        resultado.banda = BANDA_SIN_DATOS
        resultado.motivos.append("perfil_sin_datos_comparables")
        return resultado

    # -- cobertura por nivel (para leerlo de un vistazo) --------------------
    obligatorios = [d for d in evaluables if d.nivel == "obligatorio"]
    deseables = [d for d in evaluables if d.nivel in ("deseable", "incierto")]
    if obligatorios:
        resultado.cobertura_obligatorios = (
            sum(1 for d in obligatorios if d.estado == ESTADO_CUMPLE)
            / len(obligatorios)
        )
    if deseables:
        resultado.cobertura_deseables = (
            sum(1 for d in deseables if d.estado == ESTADO_CUMPLE) / len(deseables)
        )

    # -- componentes por categoria (ponderados por nivel dentro de la cat.) --
    componentes = _componentes_de(evaluables)
    resultado.componentes = componentes

    # -- score ponderado ---------------------------------------------------
    score, _efectivos = puntuar_componentes(
        componentes,
        pesos_categoria=pesos_categoria,
        imputacion=imputacion,
    )
    resultado.ajuste = round(score * 100.0, 1)

    # -- faltantes obligatorios: tope de banda (nunca "aplicar") -----------
    faltantes = [
        f"{d.category}:{d.value_code}"
        for d in evaluables
        if d.nivel == "obligatorio" and d.estado == ESTADO_FALTA
    ]
    resultado.faltantes_obligatorios = faltantes

    # -- banda -------------------------------------------------------------
    if faltantes:
        resultado.banda = BANDA_REVISAR
        resultado.motivos.append(MOTIVO_OBLIGATORIO_FALTANTE)
    elif resultado.ajuste >= umbral_aplicar:
        resultado.banda = BANDA_APLICAR
    elif resultado.ajuste >= umbral_revisar:
        resultado.banda = BANDA_REVISAR
    else:
        resultado.banda = BANDA_NO_PRIORITARIO

    return resultado


def evaluar_viabilidades(
    evaluador: EvaluadorPaso5,
    job_ids: Iterable[str],
    *,
    pesos_categoria: Mapping[str, float] | None = None,
    imputacion: Mapping[str, float] | None = None,
) -> list[Viabilidad]:
    """Evalua varias vacantes y las devuelve ordenadas: mejor ajuste primero.

    Orden: por banda (aplicar > revisar > no prioritario > sin datos > veto),
    luego por ajuste descendente.
    """
    resultados = [
        evaluar_viabilidad(
            evaluador,
            job_id,
            pesos_categoria=pesos_categoria,
            imputacion=imputacion,
        )
        for job_id in job_ids
    ]
    return sorted(
        resultados,
        key=lambda v: (
            ORDEN_BANDAS.index(v.banda) if v.banda in ORDEN_BANDAS else 99,
            -(v.ajuste if v.ajuste is not None else -1),
        ),
    )


def resumen_bandas(viabilidades: Sequence[Viabilidad]) -> dict[str, int]:
    """Conteo por banda (para los tiles de la UI)."""
    conteo = {banda: 0 for banda in ORDEN_BANDAS}
    for viabilidad in viabilidades:
        conteo[viabilidad.banda] = conteo.get(viabilidad.banda, 0) + 1
    return conteo


def a_fila(v: Viabilidad) -> dict[str, Any]:
    """Fila plana (UI / CSV)."""
    return {
        "job_id": v.job_id,
        "ajuste": v.ajuste,
        "banda": v.banda,
        "banda_texto": v.texto_banda,
        "veto": v.veto,
        "motivos": list(v.motivos),
        "cobertura_obligatorios": v.cobertura_obligatorios,
        "cobertura_deseables": v.cobertura_deseables,
        "faltantes_obligatorios": list(v.faltantes_obligatorios),
        "total_requisitos": v.total_requisitos,
        "requisitos_evaluables": v.requisitos_evaluables,
        "componentes": dict(v.componentes),
        "resumen": v.resumen,
    }


def calcular_viabilidades(
    repository: Any,
    job_ids: Iterable[str],
    *,
    pesos_categoria: Mapping[str, float] | None = None,
    evaluar_todo: bool = False,
) -> list[Viabilidad]:
    """Evalua un conjunto de vacantes contra el perfil guardado (2 pasadas).

    Es el punto de entrada compartido por la CLI y la UI (una sola
    implementacion, misma respuesta). `evaluar_todo=True` ignora el filtro
    por areas del perfil (igual que el Paso 5 con `--evaluar-todo`).

    **DOS PASADAS** (igual que el ranking ATS): la primera calcula los
    componentes de cada vacante y el promedio del corpus; la segunda puntua
    con pesos FIJOS e imputacion, para que las vacantes sean COMPARABLES
    entre si (si no, una vacante con un solo requisito covered sacaria 100
    y subiria sola en el ranking).
    """
    lista_ids = list(job_ids)
    with repository.database.connection() as connection:
        evaluador = EvaluadorPaso5(
            connection, aplicar_filtro_areas=not evaluar_todo
        )
        # -- PASADA 1: componentes crudos (sin puntuar) --------------------
        crudos: dict[str, dict[str, float | None]] = {}
        for job_id in lista_ids:
            componentes = _componentes_crudos(evaluador, job_id)
            if componentes is not None:
                crudos[job_id] = componentes
        promedios = promedios_componentes(list(crudos.values()))
        # -- PASADA 2: puntaje comparable ----------------------------------
        resultados = [
            evaluar_viabilidad(
                evaluador,
                job_id,
                pesos_categoria=pesos_categoria,
                imputacion=promedios,
            )
            for job_id in lista_ids
        ]
    return sorted(
        resultados,
        key=lambda v: (
            ORDEN_BANDAS.index(v.banda) if v.banda in ORDEN_BANDAS else 99,
            -(v.ajuste if v.ajuste is not None else -1),
        ),
    )


def _componentes_crudos(
    evaluador: EvaluadorPaso5, job_id: str
) -> dict[str, float | None] | None:
    """Componentes de UNA vacante (sin puntuar); None si no hay requisitos."""
    requisitos = evaluador.requisitos_efectivos(job_id)
    if not requisitos:
        return None
    texto = evaluador.textos_por_job.get(job_id, "")
    desglose = [
        _evaluar_requisito(evaluador, requisito, texto, job_id)
        for requisito in requisitos
    ]
    evaluables = [d for d in desglose if d.estado != ESTADO_NO_VERIFICABLE]
    if not evaluables:
        return None
    return _componentes_de(evaluables)
