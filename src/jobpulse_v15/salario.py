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
Un aviso declara salario si en la MISMA frase (a menos de 80 caracteres, sin
cruzar un punto) hay

1. una MARCA literal de compensacion ("compensation", "salary", "salario",
   "remuneracion", "wage", "hourly rate", "pay range", "base pay",
   "stipend", "honorarios", "sueldo"), y
2. una CIFRA con moneda ("$20,000", "₡ 625000", "420,000 colones",
   "USD 1,400").

Las tres condiciones juntas (marca + cifra + moneda) evitan los falsos
positivos que la version anterior (marca + moneda, en cualquier punto del
aviso) dejaba pasar:

- "Compensation: Paid in USD" / "Compensation & Benefits USD" (sin cifra),
- "your proposed ... hourly rate in USD" (le pide la tarifa al CANDIDATO),
- "raised $26 million in Series B financing" junto a un "salary" lejano
  (cifra de funding, no del puesto).

Cual de las cifras es el salario lo juzga el modelo; aqui solo se decide si
el aviso MERECE pasar por el prompt.
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
# Una CIFRA con moneda pegada ("$20,000", "₡ 625000", "420,000 colones",
# "USD 1,400"). Un numero suelto no cuenta: "20,000 restaurant owners" o
# "we've raised $26 million" no son el salario del puesto.
_RE_MONTO = re.compile(
    r"(?:["
    + re.escape("".join(m for m in MARCAS_MONEDA if not m.isalpha()))
    + r"]\s*\d[\d.,]*"
    r"|\d[\d.,]*\s*(?:" + "|".join(_patron_tolerante(m) for m in MARCAS_MONEDA if m.isalpha()) + r")\b"
    r"|\b(?:" + "|".join(_patron_tolerante(m) for m in ("usd", "crc")) + r")\b\s*\d[\d.,]*)",
    re.IGNORECASE,
)

# Distancia maxima entre la marca de salario y la cifra: la misma frase.
# "estimated base salary for this role is $19,984,600 CRC annually" = 40
# chars; "Salary: ₡ 625000" = 8. Cruzar un punto (o 80 chars) separa dos
# frases distintas ("Competitive salary. We raised $200 million.").
VENTANA_MONTO = 80

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
_PATRON_SALARIO_Y_MONTO = (
    r"(?:" + _RE_SALARIO.pattern + r")[^.]{0," + str(VENTANA_MONTO) + r"}?(?:"
    + _RE_MONTO.pattern + r")"
    r"|(?:" + _RE_MONTO.pattern + r")[^.]{0," + str(VENTANA_MONTO) + r"}?(?:"
    + _RE_SALARIO.pattern + r")"
)
# Nombre historico (lo usaban los tests y el predicado SQL): mismo patron.
_PATRON_SALARIO_Y_MONEDA = _PATRON_SALARIO_Y_MONTO

_RE_SALARIO_Y_MONTO = re.compile(_PATRON_SALARIO_Y_MONTO, re.IGNORECASE)


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
    """True si el aviso DECLARA su compensacion (marca + cifra + moneda).

    Acepta varios textos (descripcion, requisitos) y basta con que uno de
    ellos declare el salario.
    """
    for texto in textos:
        if not texto:
            continue
        if _RE_SALARIO_Y_MONTO.search(texto):
            return True
    return False


def _cifras_declaradas(texto: str):
    """Cifras monetarias cuya frase SI declara salario (yield del match)."""
    for cifra in _RE_MONTO.finditer(texto):
        inicio = max(0, cifra.start() - VENTANA_MONTO)
        fin = min(len(texto), cifra.end() + VENTANA_MONTO)
        if _RE_SALARIO_Y_MONTO.search(texto[inicio:fin]) is None:
            continue
        yield cifra


def contexto_salario(
    *textos: Optional[str], ventana: int = 700, max_fragmentos: int = 2
) -> Optional[str]:
    """Fragmento(s) del texto alrededor de la CIFRA del salario.

    El modelo local ve una ventana corta: si la seccion de compensacion
    esta al final de un aviso largo (caso tipico: va despues de "What You
    Will Do"), mandarle solo los primeros 2000 caracteres perderia el
    dato. Aqui se recorta el texto alrededor de la CIFRA (no de la palabra
    "salary"): una marca sin cifra cercana no es un dato y no debe gastar
    uno de los dos fragmentos.

    Antes se centraba en la palabra: en un aviso con "salary" en una frase
    de relleno los dos fragmentos se gastaban ahi y el modelo nunca veia la
    cifra real ("The estimated base salary for this role is $19,984,600 CRC
    annually" se quedo sin extraer en la corrida del 2026-11-01).
    """
    fragmentos: list[str] = []
    for texto in textos:
        if not texto:
            continue
        for cifra in _cifras_declaradas(texto):
            inicio = max(0, cifra.start() - ventana // 2)
            fin = min(len(texto), cifra.end() + ventana)
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
