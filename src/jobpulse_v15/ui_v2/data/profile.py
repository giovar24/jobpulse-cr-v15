# -*- coding: utf-8 -*-
"""Capa de datos del PERFIL del candidato para la UI v2 (SIN Tkinter).

Igual que :mod:`jobpulse_v15.ui_v2.data.jobs`, la pestaña no habla con
SQLite: habla con :class:`ProfileStore`, que envuelve el ``Repository`` y
devuelve dataclasses planas. Así la lógica se testea sin abrir ventana.

El perfil es un SINGLETON (no hay ``candidate_id``): todos los hechos viven
en ``candidate_profile_facts`` y se identifican por ``(category, value_code)``.

IMPORTANTE (vínculo con el matching)
------------------------------------
``Repository.save_candidate_profile_facts`` **no** escribe
``codigo_canonico``; el motor del Paso 5 exige ``codigo_canonico IS NOT NULL``
para skill/idioma/educación. Por eso un hecho guardado aquí puede ser
invisible para el motor mientras siga pendiente la capa B (ver AGENTS.md,
migración 017). La UI lo muestra sin ocultarlo (columna "Canónico").
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jobpulse_v15 import candidate_profile
from jobpulse_v15.candidate_profile import CandidateProfileImport
from jobpulse_v15.repository import Repository

# --- categorías (espejo de repository.PROFILE_FACT_CATEGORIES) ---
CATEGORIAS: tuple[str, ...] = (
    "contact",
    "summary",
    "education",
    "experience",
    "project",
    "skill",
    "certification",
    "language",
    "license",
    "work_authorization",
    "schedule",
    "availability",
    "other",
    "area",
)

ETIQUETAS_CATEGORIA: dict[str, str] = {
    "contact": "Datos personales",
    "summary": "Resumen",
    "education": "Educación",
    "experience": "Experiencia",
    "project": "Proyectos",
    "skill": "Habilidad",
    "certification": "Certificación",
    "language": "Idioma",
    "license": "Licencia",
    "work_authorization": "Autorización de trabajo",
    "schedule": "Horario",
    "availability": "Disponibilidad",
    "other": "Otro",
    "area": "Área de empleo",
}

ESTADOS_EDUCACION: tuple[str, ...] = ("", "completed", "pursuing", "unspecified")
ETIQUETAS_ESTADO_EDUCACION: dict[str, str] = {
    "": "—",
    "completed": "Completado",
    "pursuing": "En curso",
    "unspecified": "Sin especificar",
}

NIVELES_CEFR: tuple[str, ...] = ("", "A1", "A2", "B1", "B2", "C1", "C2", "nativo")

CATEGORIAS_CON_ESTADO: frozenset[str] = frozenset({"education"})
CATEGORIAS_CON_NUMERO: frozenset[str] = frozenset({"experience"})


def etiqueta_categoria(categoria: str) -> str:
    """Nombre legible de una categoría de perfil."""
    return ETIQUETAS_CATEGORIA.get(categoria, categoria or "—")


def etiqueta_estado_educacion(estado: str) -> str:
    return ETIQUETAS_ESTADO_EDUCACION.get(estado or "", estado or "—")


def origen_texto(origen: str) -> str:
    return {"manual": "Manual", "imported": "Importado"}.get(origen or "", origen or "—")


@dataclass(frozen=True)
class ProfileQuery:
    """Filtros de la pestaña de perfil."""

    texto: str = ""
    categoria: str = ""


@dataclass(frozen=True)
class ProfileFact:
    """Un dato del perfil tal como está en la base."""

    fact_id: int
    category: str
    value_code: str
    value_text: str
    qualifier: str
    education_status: str
    numeric_value: float | None
    unit: str
    notes: str
    origin: str
    codigo_canonico: str
    updated_at: str
    import_source_name: str

    @property
    def categoria_legible(self) -> str:
        return etiqueta_categoria(self.category)

    @property
    def nivel_legible(self) -> str:
        if self.category in CATEGORIAS_CON_ESTADO and self.education_status:
            return etiqueta_estado_educacion(self.education_status)
        if self.qualifier:
            return self.qualifier
        if self.numeric_value is not None:
            numero = f"{self.numeric_value:g}"
            return f"{numero} {self.unit}".strip()
        return "—"

    @property
    def origen_legible(self) -> str:
        return origen_texto(self.origin)


@dataclass(frozen=True)
class ProfileResumen:
    """Cifras para la franja de resumen."""

    total: int = 0
    importados: int = 0
    manuales: int = 0
    con_canonico: int = 0
    por_categoria: Mapping[str, int] = field(default_factory=dict)

    @property
    def categorias_cubiertas(self) -> int:
        return len(self.por_categoria)


def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, str):
        return valor.strip()
    return str(valor).strip()


def _entero(valor: Any) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return 0


def _numero(valor: Any) -> float | None:
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def recortar(texto: str, largo: int = 80) -> str:
    """Texto de una línea, cortado con puntos suspensivos."""
    limpio = " ".join((texto or "").split())
    if len(limpio) <= largo:
        return limpio
    return limpio[: largo - 1].rstrip() + "…"


class ProfileStore:
    """Acceso al perfil del candidato para la UI v2."""

    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    # -- lectura --
    def load(self, query: ProfileQuery | None = None) -> list[ProfileFact]:
        """Hechos del perfil que cumplen el filtro (búsqueda en memoria)."""
        consulta = query or ProfileQuery()
        termino = consulta.texto.casefold().strip()
        hechos = [self._to_fact(fila) for fila in self.repository.list_candidate_profile_facts()]
        resultado: list[ProfileFact] = []
        for hecho in hechos:
            if consulta.categoria and hecho.category != consulta.categoria:
                continue
            if termino:
                campo = " ".join(
                    (hecho.value_code, hecho.value_text, hecho.qualifier, hecho.notes)
                ).casefold()
                if termino not in campo:
                    continue
            resultado.append(hecho)
        return resultado

    def resumen(self, hechos: Iterable[ProfileFact]) -> ProfileResumen:
        hechos = list(hechos)
        por_categoria: dict[str, int] = {}
        for hecho in hechos:
            por_categoria[hecho.category] = por_categoria.get(hecho.category, 0) + 1
        return ProfileResumen(
            total=len(hechos),
            importados=sum(1 for h in hechos if h.origin == "imported"),
            manuales=sum(1 for h in hechos if h.origin != "imported"),
            con_canonico=sum(1 for h in hechos if h.codigo_canonico),
            por_categoria=por_categoria,
        )

    # -- escritura --
    def save(
        self,
        category: str,
        value_code: str,
        value_text: str,
        *,
        qualifier: str = "",
        education_status: str = "",
        numeric_value: str | float | None = None,
        unit: str = "",
        notes: str = "",
        fact_id_viejo: int | None = None,
    ) -> None:
        """Crea o actualiza un hecho. Valida según las reglas del repositorio.

        Si ``fact_id_viejo`` apunta a otro ``value_code`` (el usuario editó el
        código), el hecho anterior se elimina para no dejar un duplicado.
        """
        categoria = _texto(category)
        codigo = _texto(value_code)
        texto = _texto(value_text)
        estado = _texto(education_status) if categoria in CATEGORIAS_CON_ESTADO else None
        numero = _numero(numeric_value) if categoria in CATEGORIAS_CON_NUMERO else None
        hecho = {
            "category": categoria,
            "value_code": codigo,
            "value_text": texto,
            "qualifier": _texto(qualifier) or None,
            "education_status": estado or None,
            "numeric_value": numero,
            "unit": _texto(unit) or None,
            "notes": _texto(notes) or None,
        }
        if fact_id_viejo is not None:
            anterior = self._fact_por_id(fact_id_viejo)
            if anterior is not None and (
                anterior.category != categoria
                or anterior.value_code.casefold() != codigo.casefold()
            ):
                self.repository.delete_candidate_profile_fact(fact_id_viejo)
        self.repository.save_candidate_profile_facts([hecho])

    def delete(self, fact_id: int) -> bool:
        return self.repository.delete_candidate_profile_fact(fact_id)

    # -- importación desde CV --
    def import_from_cv(self, path: str | Path, *, texto: str | None = None) -> CandidateProfileImport:
        """Lee un CV local y propone hechos (no guarda nada todavía)."""
        return candidate_profile.extract_candidate_profile(path, texto=texto)

    def import_facts(self, source_name: str, facts: Sequence[Mapping[str, Any]]) -> int:
        """Guarda un lote importado (con snapshot para poder revertirlo)."""
        self.repository.import_candidate_profile_facts(source_name, list(facts))
        return len(facts)

    def importaciones(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return self.repository.list_candidate_profile_imports(limit=limit)

    def revertir_ultima(self) -> dict[str, Any] | None:
        return self.repository.revert_last_candidate_profile_import()

    # -- apoyo --
    def _fact_por_id(self, fact_id: int) -> ProfileFact | None:
        for fila in self.repository.list_candidate_profile_facts():
            if _entero(fila.get("profile_fact_id")) == fact_id:
                return self._to_fact(fila)
        return None

    @staticmethod
    def _to_fact(fila: Mapping[str, Any]) -> ProfileFact:
        return ProfileFact(
            fact_id=_entero(fila.get("profile_fact_id")),
            category=_texto(fila.get("category")),
            value_code=_texto(fila.get("value_code")),
            value_text=_texto(fila.get("value_text")),
            qualifier=_texto(fila.get("qualifier")),
            education_status=_texto(fila.get("education_status")),
            numeric_value=_numero(fila.get("numeric_value")),
            unit=_texto(fila.get("unit")),
            notes=_texto(fila.get("notes")),
            origin=_texto(fila.get("origin")),
            codigo_canonico=_texto(fila.get("codigo_canonico")),
            updated_at=_texto(fila.get("updated_at")),
            import_source_name=_texto(fila.get("import_source_name")),
        )


# -- conversión de sugerencias de CV a hechos --
def fact_desde_sugerencia(sugerencia) -> dict[str, Any]:
    """Convierte una ``CandidateProfileSuggestion`` en un Mapping guardable."""
    categoria = _texto(sugerencia.category)
    return {
        "category": categoria,
        "value_code": _texto(sugerencia.value_code),
        "value_text": _texto(sugerencia.value_text),
        "qualifier": _texto(sugerencia.qualifier) or None,
        "education_status": (
            _texto(sugerencia.education_status) or None
            if categoria in CATEGORIAS_CON_ESTADO
            else None
        ),
        "numeric_value": (
            _numero(sugerencia.numeric_value)
            if categoria in CATEGORIAS_CON_NUMERO
            else None
        ),
        "unit": _texto(sugerencia.unit) or None,
    }


# -- exportación --
CAMPOS_CSV: tuple[str, ...] = (
    "fact_id",
    "category",
    "value_code",
    "value_text",
    "qualifier",
    "education_status",
    "numeric_value",
    "unit",
    "notes",
    "origin",
    "codigo_canonico",
)


def exportar_csv(hechos: Sequence[ProfileFact], ruta: str | Path) -> int:
    """Escribe los hechos del perfil en CSV; devuelve cuántos escribió."""
    destino = Path(ruta)
    with destino.open("w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(CAMPOS_CSV))
        escritor.writeheader()
        for hecho in hechos:
            escritor.writerow(
                {
                    "fact_id": hecho.fact_id,
                    "category": hecho.category,
                    "value_code": hecho.value_code,
                    "value_text": hecho.value_text,
                    "qualifier": hecho.qualifier,
                    "education_status": hecho.education_status,
                    "numeric_value": hecho.numeric_value if hecho.numeric_value is not None else "",
                    "unit": hecho.unit,
                    "notes": hecho.notes,
                    "origin": hecho.origin,
                    "codigo_canonico": hecho.codigo_canonico,
                }
            )
    return len(hechos)
