# -*- coding: utf-8 -*-
"""Idioma del aviso y REQUISITO de idioma del matching.

Regla de negocio (acordada 2026-10-31):

    **El requisito de idioma de un aviso es el idioma en que esta escrito**,
    salvo que el aviso **pida** uno o varios idiomas como requisito
    ("Fluent English required", "se requiere ingles intermedio", "bilingual
    English/Spanish"): en ese caso, los que pide el aviso son los requisitos.

Este modulo tiene las dos piezas:

* ``detectar_idioma_del_aviso``: deteccion **determinista** (sin IA) del
  idioma del texto de la oferta, para los tableros que no lo declaran
  (``posting_language='undetermined'``).
* ``CODIGO_IDIOMA``: mapeo del idioma del aviso al codigo canonico de
  ``concepto`` (categoria ``language``).
"""

from __future__ import annotations

import re
import unicodedata

# Codigo canonico de ``concepto`` por idioma del aviso.
CODIGO_IDIOMA = {
    "es": "espanol",
    "en": "ingles",
}

# Nombre legible del idioma (para los informes y la evidencia).
NOMBRE_IDIOMA = {
    "es": "espanol",
    "en": "ingles",
    "mixed": "mixto",
    "undetermined": "sin determinar",
}

# Palabras funcionales: son la senal mas estable del idioma de un texto
# (los terminos tecnicos y los nombres propios son iguales en ambos).
_MARCAS_ES = frozenset({
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por",
    "un", "para", "con", "no", "una", "su", "al", "lo", "como", "mas", "pero",
    "sus", "le", "ya", "o", "este", "si", "porque", "esta", "entre", "cuando",
    "muy", "sin", "sobre", "tambien", "hasta", "hay", "donde", "quien", "desde",
    "todo", "nos", "durante", "todos", "uno", "les", "ni", "contra", "otro",
    "ese", "eso", "ante", "ellos", "esto", "antes", "algunos", "unos", "otra",
    "el", "tan", "esta", "estos", "mucho", "quienes", "nada", "muchos",
    "cual", "poco", "ella", "estar", "estas", "algunas", "algo", "nosotros",
    "tu", "te", "ti", "mis", "mio", "mia", "tuyo", "tuya", "nuestro",
    "nuestra", "vosotros", "vosotras", "usted", "ustedes", "ser", "sido",
    "estar", "haber", "hace", "hacer", "puede", "pueden", "debe", "deben",
    "tendra", "tienen", "cada", "segun", "tambien", "mientras", "tambien",
    "trabajo", "puesto", "empresa", "experiencia", "requisitos", "habilidades",
    "conocimiento", "responsabilidades", "salario", "horario", "contrato",
})

_MARCAS_EN = frozenset({
    "the", "of", "and", "to", "in", "a", "is", "that", "for", "it", "with",
    "as", "was", "on", "be", "at", "by", "this", "have", "from", "or", "an",
    "are", "not", "but", "they", "you", "your", "we", "our", "their", "he",
    "she", "his", "her", "them", "us", "i", "me", "my", "all", "any", "some",
    "such", "no", "nor", "so", "if", "then", "else", "when", "while", "what",
    "which", "who", "whom", "how", "why", "can", "could", "should", "would",
    "may", "might", "must", "will", "shall", "do", "does", "did", "done",
    "been", "being", "more", "most", "other", "another", "own", "same", "too",
    "very", "just", "also", "into", "over", "under", "again", "here", "there",
    "both", "each", "few", "now", "has", "had", "having", "about", "after",
    "before", "between", "during", "through", "above", "below", "down", "up",
    "out", "off", "only", "own", "per", "role", "job", "team", "work",
    "experience", "skills", "requirements", "ability", "knowledge",
    "responsibilities", "salary", "schedule", "contract", "candidate",
    "candidate", "position", "company", "department", "looking", "join",
    "include", "includes", "required", "preferred", "must", "have", "years",
})

_TOKENO = re.compile(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+")
_MINIMO_MARCAS = 10


def _normalizar(texto: str) -> list[str]:
    """Palabras en minuscula y sin acentos (para comparar con las marcas)."""
    palabras = []
    for palabra in _TOKENO.findall(texto or ""):
        if len(palabra) < 2:
            continue
        plano = unicodedata.normalize("NFKD", palabra)
        palabras.append(
            "".join(c for c in plano if not unicodedata.combining(c)).casefold()
        )
    return palabras


def detectar_idioma_del_aviso(*textos: str | None) -> str:
    """Idioma del aviso: ``'es'``, ``'en'``, ``'mixed'`` o ``'undetermined'``.

    Es **determinista** (cuenta palabras funcionales, no usa IA) y conservadora:
    si el texto es demasiado corto o esta en un idioma que no se distingue,
    devuelve ``'undetermined'`` en vez de adivinar.
    """
    palabras = _normalizar(" ".join(t for t in textos if t))
    if not palabras:
        return "undetermined"
    marcas_es = sum(1 for palabra in palabras if palabra in _MARCAS_ES)
    marcas_en = sum(1 for palabra in palabras if palabra in _MARCAS_EN)
    total = marcas_es + marcas_en
    if total < _MINIMO_MARCAS:
        return "undetermined"
    proporcion_es = marcas_es / total
    if proporcion_es >= 0.75:
        return "es"
    if proporcion_es <= 0.25:
        return "en"
    return "mixed"


def codigo_canonico_del_idioma(idioma: str | None) -> str | None:
    """Codigo canonico de ``concepto`` para el idioma del aviso (``None`` si no)."""
    return CODIGO_IDIOMA.get((idioma or "").strip().casefold())
