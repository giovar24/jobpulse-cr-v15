# -*- coding: utf-8 -*-
"""Señal de SALARIO declarada en el texto de un aviso.

FUENTE ÚNICA de la regla "este aviso declara su compensacion": la usan

- el extractor con IA (:mod:`jobpulse_v15.ia_enrichment`) para decidir si
  dispara el prompt de salario, y
- el contador de huecos (:mod:`jobpulse_v15.ia_estado`) para saber si el
  salario sigue pendiente.

Ambas usan EXACTAMENTE la misma regla: si no, el panel diria "pendiente"
mientras el extractor no trabaja, o al reves.

POR QUE EXISTE (bug corregido el 2026-11-01)
--------------------------------------------
El prompt de salario solo se disparaba si el aviso traia el campo
``salary_raw`` de la FUENTE. Las APIs de empleo casi nunca lo traen: en la
corrida por la UI del 2026-11-01, **0 de 354** avisos lo traian, y por eso
``salary_min`` quedo en 0 % ... aunque 14 avisos SI declaran la
compensacion en el texto ("Estimated base salary: $19,984,600 CRC annually",
"Compensation is of 420,000 colones per month", "Hourly Rate: $10 to $23
USD per hour"). La puerta era el bug: no faltaba el dato.

LA REGLA
--------
Un aviso declara salario si en su texto hay

1. una MARCA literal de compensacion ("compensation", "salary", "salario",
   "remuneracion", "wage", "hourly rate", "pay range", "base pay",
   "stipend", "honorarios", "sueldo"), y
2. una MONEDA ("$", "₡", "€", "USD", "CRC", "colones", "dolares").

Las dos condiciones juntas evitan los falsos positivos: "compensation" en
una frase generica ("great compensation package") sin cifra no es un dato,
y una cifra sin marca ("raised $200 million in funding") no es un salario.
La cifra y la moneda las juzga el modelo; aqui solo se decide si el aviso
MERECE pasar por el prompt.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from typing import Optional

# ─── La lista (fuente unica) ───

PALABRAS_SALARIO = (
    "compensation",
    "compensacion",
    "salary",
    "salaries",
    "salario",
    "remuneración",
    "earn",
    "wage",
    "wages",
    "hourly rate",
    "pay rate",
    "pay range",
    "salary range",
    "base pay",
    "stipend",
    "honorarios",
    "sueldo",
)

MARCAS_MONEDA = (
    "$",
    "₡",
    "€",
    "usd",
    "crc",
    "colones",
    "dólares",
)

# Variantes acentuadas admitidas al comparar (tolerancia a como lo escribe
# cada tablero: "remuneracion" / "remuneración", "dolares" / "dólares").
_VARIANTES = {
    "a": "aáäâà",
    "e": "eéëêè",
    "i": "iíïîì",
    "o": "oóöôò",
    "u": "uúüûù",
    "n": "nñ",
}


def _patron_tolerante(palabra: str) -> str:
    """Regex que acepta la palabra con o sin acento ("dolares"/"dólares")."""
    partes: list[str] = []
    for caracter in palabra.casefold():
        descompuesto = unicodedata.normalize("NFKD", caracter)
        if len(descompuesto) > 1:
            # letra acentuada: se admiten TODAS sus variantes ("o", "ó", ...)
            base = descompuesto[0]
            partes.append(f"[{_VARIANTES.get(base, base)}]")
        elif caracter in _VARIANTES:
            partes.append(f"[{_VARIANTES[caracter]}]")
        else:
            partes.append(re.escape(caracter))
    return "".join(partes)


def _prefijo_ascii(palabra: str, minimo: int = 4) -> str:
    """Prefijo sin acento de la palabra ("remuneración" -> "remuneraci").

    El SQL no puede normalizar acentos: el fragmento se corta ANTES de la
    letra acentuada para que '%remuneraci%' cubra las dos escrituras. Si
    el prefijo queda muy corto ("dólares" -> "d") se usa la palabra entera
    sin acento y el fragmento extra "%lares%" cubre la version acentuada.
    """
    salida: list[str] = []
    for caracter in palabra.casefold():
        if len(unicodedata.normalize("NFKD", caracter)) > 1:
            break
        salida.append(caracter)
    prefijo = "".join(salida)
    if len(prefijo) < minimo:
        descompuesto = unicodedata.normalize("NFKD", palabra)
        return "".join(
            caracter for caracter in descompuesto if not unicodedata.combining(caracter)
        ).casefold()
    return prefijo


_RE_SALARIO = re.compile(
    r"\b(?:" + "|".join(_patron_tolerante(p) for p in PALABRAS_SALARIO) + r")\b",
    re.IGNORECASE,
)
_RE_MONEDA = re.compile(
    r"(?:["
    + re.escape("".join(m for m in MARCAS_MONEDA if not m.isalpha()))
    + r"]|\b(?:"
    + "|".join(_patron_tolerante(m) for m in MARCAS_MONEDA if m.isalpha())
    + r")\b)",
    re.IGNORECASE,
)

# Fragmentos SQL equivalentes a las listas de arriba.
_FRAGMENTOS_SALARIO_SQL = tuple(
    f"%{_prefijo_ascii(palabra)}%" for palabra in PALABRAS_SALARIO
)
# Fragmentos SQL equivalentes a las listas de arriba. OJO: no se anade un
# fragmento "lares" (suena a "dolares" acentuado) porque tambien aparece
# dentro de "salaries" y de "salary certificates": dos avisos sin cifra
# (el de Abbott con "base pay is N/A" y una licitacion de consultoria con
# "honorarios") contaban como si declararan salario.

# El MISMO regex de Python, usado por la funcion RE() que se registra en la
# conexion SQLite (ver ``registrar_funciones``): asi el panel de la UI y el
# extractor NO pueden discrepar. Con LIKE habia diferencias ("%earn%"
# encuentra "learning", "%pay%" encuentra "payroll").
_PATRON_SALARIO_Y_MONEDA = (
    "(?:" + _RE_SALARIO.pattern + ")[\\s\\S]*?(?:" + _RE_MONEDA.pattern + ")"
    "|(?:" + _RE_MONEDA.pattern + ")[\\s\\S]*?(?:" + _RE_SALARIO.pattern + ")"
)
_RE_SALARIO_Y_MONEDA = re.compile(_PATRON_SALARIO_Y_MONEDA, re.IGNORECASE)


def _re_sql(patron: str | None, valor: str | None) -> int:
    """Implementacion de la funcion SQLite RE(patron, texto)."""
    if not patron or valor is None:
        return 0
    try:
        return 1 if re.search(patron, str(valor), re.IGNORECASE) else 0
    except re.error:
        return 0


def registrar_funciones(con: sqlite3.Connection) -> None:
    """Registra RE(patron, texto) en la conexion SQLite.

    Sin esta funcion, el predicado SQL del panel no se puede ejecutar. La
    registra ``ia_estado`` en su conexion.
    """
    con.create_function("RE", 2, _re_sql, deterministic=True)


def declara_salario(*textos: Optional[str]) -> bool:
    """True si el aviso DECLARA su compensacion (marca de salario + moneda).

    Acepta varios textos (descripcion, requisitos) y basta con que uno de
    ellos declare el salario.
    """
    for texto in textos:
        if not texto:
            continue
        if _RE_SALARIO_Y_MONEDA.search(texto):
            return True
    return False


def contexto_salario(
    *textos: Optional[str], ventana: int = 700, max_fragmentos: int = 2
) -> Optional[str]:
    """Fragmento(s) del texto alrededor de la marca de salario.

    El modelo local ve una ventana corta: si la seccion de compensacion
    esta al final de un aviso largo (caso tipico: va despues de "What You
    Will Do"), mandarle solo los primeros 2000 caracteres perderia el
    dato. Aqui se recorta el texto alrededor de la marca, que es lo que el
    modelo tiene que leer.
    """
    fragmentos: list[str] = []
    for texto in textos:
        if not texto:
            continue
        for match in _RE_SALARIO.finditer(texto):
            inicio = max(0, match.start() - ventana // 2)
            fin = min(len(texto), match.end() + ventana)
            fragmento = " ".join(texto[inicio:fin].split())
            if fragmento and fragmento not in fragmentos:
                fragmentos.append(fragmento)
            if len(fragmentos) >= max_fragmentos:
                return "\n...\n".join(fragmentos)
    return "\n...\n".join(fragmentos) if fragmentos else None


def predicado_sql_hueco() -> str:
    """SQL: el aviso TODAVIA no tiene salario y su texto declara uno.

    Es la condicion de "hueco pendiente" que usa ``ia_estado`` (el panel
    de la UI) y la del extractor: misma regla, mismo regex (la funcion RE
    la registra ``ia_estado`` en su conexion SQLite).
    """
    return (
        "salary_min IS NULL AND ("
        "TRIM(COALESCE(salary_raw,'')) <> ''"
        f" OR RE('{_PATRON_SALARIO_Y_MONEDA}', "
        "COALESCE(description_raw,'') || ' ' || COALESCE(requirements_raw,''))"
        ")"
    )
