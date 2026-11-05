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

#: Escala de niveles de idioma (CEFR + "nativo"). Es la MISMA que la tabla
#: ``nivel_escala`` (categoria 'language'): A1..C2 y, encima, "nativo".
NIVEL_NATIVO = "nativo"
NIVELES_CEFR: dict[str, int] = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
ORDEN_NIVEL: dict[str, int] = {**NIVELES_CEFR, NIVEL_NATIVO: 7}

#: Palabras que describen un nivel sin escribir el codigo CEFR. El valor es
#: el codigo CEFR equivalente (o "nativo").
NIVEL_PALABRAS: dict[str, str] = {
    "nativo": NIVEL_NATIVO,
    "nativa": NIVEL_NATIVO,
    "native": NIVEL_NATIVO,
    "lengua materna": NIVEL_NATIVO,
    "lenguaje materno": NIVEL_NATIVO,
    "mother tongue": NIVEL_NATIVO,
    "fluent": "C1",
    "fluido": "C1",
    "fluida": "C1",
    "advanced": "C1",
    "avanzado": "C1",
    "avanzada": "C1",
    "intermediate": "B2",
    "intermedio": "B2",
    "intermedia": "B2",
    "conversational": "B2",
    "conversacional": "B2",
    "basic": "A2",
    "basico": "A2",
    "elemental": "A1",
    "principiante": "A1",
    "beginner": "A1",
}

_CEFR = re.compile(r"\b([ABCD][12])\b", re.IGNORECASE)


def normalizar_nivel(texto: str | None) -> str | None:
    """Nivel de idioma canonico: 'A1'..'C2', 'nativo' o ``None``.

    El corpus trae el nivel de muchas formas ("B2", "b2", "B2+", "C1-C2",
    "fluent", "intermedio", "avanzado/fluyente", "nativo"). Sin normalizar,
    la comparacion contra el perfil se ROMPE en silencio: ``IDIOMA_ORDEN`` solo
    tiene las claves en mayusculas, asi que un requisito con "b2" caia en
    "no_verificable" y el idioma no se comparaba (el gap real se escondia).

    Reglas:
    * "B2+" -> "B2" (el "+" significa "o superior": el minimo exigible es B2).
    * "C1-C2" -> "C1" (el rango exige el MINIMO).
    * "avanzado/fluyente" -> "C1"; "intermedio-avanzado" -> "B2" (se toma el
      nivel mas bajo del rango: el requisito mas suave que el aviso acepta).
    """
    if texto is None:
        return None
    limpio = str(texto).strip().lower()
    if not limpio:
        return None
    # El "+" no cambia el minimo exigible.
    limpio = limpio.replace("+", " ")
    match = _CEFR.search(limpio)
    if match:
        return match.group(1).upper()
    # Palabra: se toma la primera (la parte mas baja del rango).
    for parte in re.split(r"[/,;]| - ", limpio):
        clave = parte.strip()
        if clave in NIVEL_PALABRAS:
            return NIVEL_PALABRAS[clave]
    # "intermedio-avanzado" / "avanzado-fluyente": partir por guion.
    for parte in re.split(r"[-–]", limpio):
        clave = parte.strip()
        if clave in NIVEL_PALABRAS:
            return NIVEL_PALABRAS[clave]
    return None


def orden_nivel(nivel: str | None) -> int | None:
    """Posicion del nivel en la escala (None si no se sabe)."""
    if nivel is None:
        return None
    clave = str(nivel).strip().upper()
    if clave == NIVEL_NATIVO.upper():
        return ORDEN_NIVEL[NIVEL_NATIVO]
    return ORDEN_NIVEL.get(clave)


#: Nombre del idioma (como lo escribe la fuente) -> variante de la taxonomia
#: (``concepto``, categoria 'language'). Sin acentos y en minusculas.
NOMBRES_IDIOMA: dict[str, str] = {
    "english": "ingles",
    "ingles": "ingles",
    "en": "ingles",
    "spanish": "espanol",
    "espanol": "espanol",
    "castellano": "espanol",
    "es": "espanol",
    "french": "frances",
    "frances": "frances",
    "fr": "frances",
    "portuguese": "portugues",
    "portugues": "portugues",
    "pt": "portugues",
    "german": "aleman",
    "aleman": "aleman",
    "de": "aleman",
    "italian": "italiano",
    "italiano": "italiano",
    "it": "italiano",
    "chinese": "chino",
    "chino": "chino",
    "mandarin": "chino",
    "simplified chinese": "chino",
    "traditional chinese": "chino",
    "japanese": "japones",
    "japones": "japones",
    "korean": "coreano",
    "coreano": "coreano",
    "arabic": "arabe",
    "arabe": "arabe",
    "dutch": "neerlandes",
    "neerlandes": "neerlandes",
}


def _sin_acentos(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in plano if not unicodedata.combining(c)).lower()


def nombre_idioma_a_variante(nombre: str | None) -> str | None:
    """Variante de la taxonomia del nombre de idioma que trae la fuente.

    "Inglés" -> "ingles"; "Simplified Chinese (Singapore)" -> "chino";
    "portuguese" -> "portugues". ``None`` si no se reconoce el idioma.
    """
    if not nombre:
        return None
    texto = _sin_acentos(str(nombre)).strip()
    # Se quita lo que va entre parentesis ("chinese (Singapore)").
    texto = re.sub(r"\([^)]*\)", " ", texto)
    texto = " ".join(texto.split())
    if not texto:
        return None
    if texto in NOMBRES_IDIOMA:
        return NOMBRES_IDIOMA[texto]
    # "ingles (b2)" o "ingles b2": se prueba el primer token.
    partes = texto.split()
    if partes and partes[0] in NOMBRES_IDIOMA:
        return NOMBRES_IDIOMA[partes[0]]
    return None

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
