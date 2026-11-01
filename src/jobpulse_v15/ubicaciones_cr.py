# -*- coding: utf-8 -*-
"""Division territorial de Costa Rica: pais -> provincia -> canton -> distrito.

La busqueda va **siempre de MAYOR a MENOR**: se comprueba el pais (tiene que
ser Costa Rica), luego la provincia, el canton y por ultimo el distrito. Como la
cadena es fija, un canton o un distrito nombrados bastan para deducir la
provincia; pero un nombre **ambiguo** (el mismo distrito en dos provincias)
NUNCA se usa para deducirla: no se adivina.

La regla aplica **solo a Costa Rica** y **no a los avisos puramente remotos**
(la modalidad remota se descarta: no hay sede que resolver). Si aplica a los
**hibridos**, que si tienen sede declarada.

Datos (semillas versionadas, editables sin tocar codigo):

- ``seeds/division_territorial_cr.csv``: 490 distritos, 84 cantones y 7
  provincias (columnas ``Distrito,Cantón,Provincia,País``).
- ``seeds/lugares_cr.csv``: **tabla de lugares** (parques, zonas francas y
  sedes: Ultra Park I/II, AFZ, Coyol Free Zone, Peninsula Papagayo, Control
  Fronterizo Peñas Blancas) con columnas ``Lugar,Alias,Ciudad,Provincia,Pais``.
  Es el ULTIMO recurso: se usa solo cuando el nombre del lugar (en la
  ubicacion o en el TEXTO del aviso) resuelve un campo de ciudad que la tabla
  territorial por si sola no puede. Un lugar declarado **tiene prioridad**
  sobre el nombre homonimo de la division territorial ("Peñas Blancas" es un
  distrito en Alajuela, pero el control fronterizo con ese nombre esta en
  Guanacaste).
"""
from __future__ import annotations

import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

SEEDS = Path(__file__).resolve().parent / "seeds"
DIVISION_CSV = SEEDS / "division_territorial_cr.csv"
LUGARES_CSV = SEEDS / "lugares_cr.csv"

PAIS = "Costa Rica"

# Niveles de la jerarquia, de MAYOR a MENOR.
NIVEL_PROVINCIA = 1
NIVEL_CANTON = 2
NIVEL_DISTRITO = 3

# Separadores de una direccion: coma, guion, barra, barra vertical
# ("Control Fronterizo | Peñas Blancas"), guion bajo ("GCG_Costa Rica_San
# Jose") y parentesis ("Lagunilla (Heredia)").
_SEPARADORES = re.compile(r"[,\-/–_|()\[\]]")
# Codigo postal al final ("Merced 10102", "Tres Ríos 30301").
_CODIGO_POSTAL = re.compile(r"\s+\d{3,5}$")
# "Provincia de X" -> X
_PROVINCIA_DE = re.compile(r"^provincia\s+de\s+", re.IGNORECASE)

# Lo que NO es un lugar: el pais, la modalidad y las agrupaciones regionales.
# Los limites NO usan \b porque el guion bajo cuenta como caracter de palabra:
# en "GCG_Costa Rica_San Jose" el pais va pegado ("_Costa") y \b no casaria.
_RUIDO = re.compile(
    r"(?<![A-Za-z0-9])(?:costa\s*rica|remote|remoto|remota|virtual"
    r"|home\s*office|hybrid|h[ií]brid[oa]|teletrabajo|presencial"
    r"|on[- ]?site|latin\s*america|latam|global\s*service\s*center"
    r"|multi-?loc)(?![A-Za-z0-9])",
    re.IGNORECASE,
)

# Fragmentos que acompanan a una direccion real pero NO son la ciudad: la
# planta, la zona franca o la sede ("Wet Plant", "BSC", "Local Office").
_PALABRAS_NO_CIUDAD = frozenset({
    "plant", "wet plant", "dry plant", "bsc", "local office", "office",
    "headquarters", "hq", "site", "afz", "gcg", "zona franca", "free zone",
})

# Palabras que delatan un descriptor corporativo y no un lugar: "Central",
# "Ciudad del Este", "Global Service Center"... Un nombre que las contiene no
# se guarda como ciudad.
_PALABRAS_DESCRIPTORAS = frozenset({
    "central", "corporate", "corporacion", "group", "grupo", "global",
    "international", "internacional", "regional", "operations", "operaciones",
    "services", "servicios", "solutions", "soluciones", "technologies",
    "tecnologias", "industries", "industrias", "manufacturing", "company",
    "team", "equipo", "department", "departamento", "division", "location",
    "ubicacion", "planta", "plantas", "oficina", "sede", "campus", "center",
    "centre", "laboratories", "laboratorios", "labs", "logistics", "logistica",
    "engineering", "ingenieria", "administration", "administracion", "city",
    "ciudad", "area", "area", "zone", "zona", "park", "parque", "barrio",
    "sucursal", "tienda", "bodega", "local", "agencia",
})


def clave(valor: str) -> str:
    """Clave de comparacion (sin acentos, minusculas, sin espacios sobrantes)."""
    normalizado = unicodedata.normalize("NFKD", valor or "")
    return "".join(
        caracter for caracter in normalizado if not unicodedata.combining(caracter)
    ).casefold().strip()


# Nombre historico del helper (lo usaba el normalizador de Workday).
province_key = clave


def partir(texto: str) -> list[str]:
    """Partes de una direccion (por separadores, no por espacios).

    Conserva los nombres de varias palabras y quita el "Provincia de" y el
    codigo postal del final: ``"Merced 10102"`` -> ``"Merced"``.
    """
    if not texto:
        return []
    partes = []
    for bruto in _SEPARADORES.split(texto):
        parte = _CODIGO_POSTAL.sub("", bruto.strip(" .;:"))
        parte = _PROVINCIA_DE.sub("", parte).strip(" .;:")
        if len(parte) > 1:
            partes.append(parte)
    return partes


def es_ciudad_plausible(parte: str, provincia: str | None = None) -> bool:
    """True si ``parte`` puede ser el nombre de un lugar concreto.

    Descarta el ruido que se colaba como ciudad: abreviaturas de relleno
    ("GCG", "-H"), plantas y sedes ("Wet Plant", "BSC", "Local Office"),
    descriptores corporativos ("Central", "Ciudad del Este") y
    "Provincia + zona" ("Alajuela Coyol").
    """
    nombre = clave(parte)
    if len(nombre) < 4 or any(caracter.isdigit() for caracter in nombre):
        return False
    if parte.isupper() and len(nombre) <= 5:
        return False
    if nombre in _PALABRAS_NO_CIUDAD:
        return False
    if any(clave(palabra) in _PALABRAS_DESCRIPTORAS for palabra in parte.split()):
        return False
    if provincia is not None and nombre.startswith(clave(provincia)):
        return False
    return True


def ciudad_es_basura(
    ciudad: str | None, region: str | None = None
) -> bool:
    """True si lo GUARDADO como ciudad no puede ser un lugar.

    Firma del parser viejo, que metia la cadena entera de la ubicacion en
    ``city`` ("GCG_Costa Rica_San Jose"), y los artefactos del normalizador
    legacy ("BSC", "Alajuela Coyol" = provincia + zona). Sirve para corregir
    datos ya guardados: si no se corrigieran, el ``COALESCE`` de ``save_job``
    los conservaria para siempre.
    """
    if not ciudad:
        return False
    nombre = clave(ciudad)
    if (
        "costa rica" in nombre
        or "_" in ciudad
        or any(caracter.isdigit() for caracter in nombre)
        or nombre in _PALABRAS_NO_CIUDAD
    ):
        return True
    if region and len(nombre) > len(clave(region)) and nombre.startswith(
        clave(region)
    ):
        # "Alajuela Coyol": la provincia repetida + zona no es una ciudad.
        # (Si la ciudad ES la provincia, no es basura: es un dato valido.)
        return True
    # "Gravilias Tres Rios" no es una ciudad sino DOS (un distrito de San Jose
    # y otro de Cartago): un nombre compuesto de lugares de provincias
    # distintas nunca es un lugar unico. Ojo: "San Jose" SI es un lugar (la
    # capital) aunque tenga distritos homonimos en otras provincias.
    if resolver(ciudad) is None and len(_provincias_de_un_lugar(ciudad)) > 1:
        return True
    return False


def nombre_canonico(nombre: str) -> str | None:
    """Nombre oficial de un lugar, si el catalogo lo reconoce.

    ``None`` si el nombre no esta en la division territorial ni en la tabla
    de lugares. Si el texto trae una forma distinta, se devuelve la oficial
    ("CSI Escazu" -> "Escazú").
    """
    if not nombre:
        return None
    opciones = candidatos(nombre) or _resolver_en_palabras(nombre)
    if not opciones:
        clave_nombre = clave(nombre)
        for _, canonico, ciudad, _ in _lugares():
            if clave(canonico) == clave_nombre or clave(ciudad) == clave_nombre:
                return canonico if clave(canonico) == clave_nombre else ciudad
        return None
    # Un nombre homonimo en varias provincias ("Belén") sigue siendo un
    # lugar: se devuelve su nombre oficial, sin decidir la provincia.
    return max(opciones, key=lambda opcion: opcion[0])[3]


def es_lugar_conocido(nombre: str) -> bool:
    """True si el catalogo reconoce ese nombre como un lugar."""
    return nombre_canonico(nombre) is not None


def es_costa_rica(country_code: str, country_query: str) -> bool:
    """True si el aviso es de Costa Rica (la jerarquia solo aplica ahi)."""
    return (
        (country_code or "").strip().casefold() in {"cr", "cri"}
        and (country_query or "").strip().casefold() == "costa rica"
    )


@lru_cache(maxsize=1)
def _division() -> tuple[dict, dict, dict]:
    """(provincias, cantones, distritos) con TODAS las combinaciones crudas.

    ``cantones`` y ``distritos`` mapean clave -> set de
    (nombre_oficial, canton, provincia). El nombre oficial se devuelve al
    resolver, para no guardar en la BD el texto tal como lo escribio el
    tablero ("SARDINAL", "Tres Rios").
    """
    provincias: dict[str, str] = {}
    cantones: dict[str, set[tuple[str, str, str]]] = {}
    distritos: dict[str, set[tuple[str, str, str]]] = {}
    if DIVISION_CSV.exists():
        with DIVISION_CSV.open(encoding="utf-8", newline="") as fh:
            for fila in csv.DictReader(fh):
                if clave(fila.get("País", "")) != clave(PAIS):
                    continue
                provincia = (fila.get("Provincia") or "").strip()
                canton = (fila.get("Cantón") or "").strip()
                distrito = (fila.get("Distrito") or "").strip()
                if not provincia:
                    continue
                provincias[clave(provincia)] = provincia
                if canton:
                    cantones.setdefault(clave(canton), set()).add(
                        (canton, canton, provincia)
                    )
                if distrito:
                    distritos.setdefault(clave(distrito), set()).add(
                        (distrito, canton, provincia)
                    )
    return provincias, cantones, distritos


def provincias() -> dict[str, str]:
    return _division()[0]


@lru_cache(maxsize=1)
def cantones_unicos() -> dict[str, tuple[str, str]]:
    """Cantones cuyo nombre aparece en UNA sola provincia (84 de 84)."""
    return {
        nombre: (oficial, provincia)
        for nombre, valor in _division()[1].items()
        if len({provincia for _, _, provincia in valor}) == 1
        for oficial, _, provincia in sorted(valor)
    }


@lru_cache(maxsize=1)
def distritos_unicos() -> dict[str, tuple[str, str]]:
    """Distritos cuya PROVINCIA es unica (no dependen del contexto)."""
    unicos: dict[str, tuple[str, str]] = {}
    for nombre, valor in _division()[2].items():
        if len({provincia for _, _, provincia in valor}) == 1:
            oficial, canton, provincia = sorted(valor)[0]
            unicos[nombre] = (canton, provincia)
    return unicos


def distritos_de_canton(canton: str) -> set[str]:
    """Nombres de distrito del canton (clave sin acentos)."""
    canton_clave = clave(canton)
    return {
        clave(nombre)
        for nombre, valor in _division()[2].items()
        if any(clave(c) == canton_clave for _, c, _ in valor)
    }


def candidatos(parte: str) -> list[tuple[int, str, str | None, str]]:
    """Todos los lugares que puede nombrar un texto: ``(nivel, provincia,
    canton, nombre oficial)``.

    Un mismo nombre puede ser CANTON en una provincia y DISTRITO en otra
    ("Santo Domingo": canton de Heredia y distrito de San Jose; "Belén":
    canton de Heredia y distrito de Guanacaste). Por eso se devuelven TODOS
    los candidatos y es el contexto (la provincia que nombra el texto) el que
    decide.
    """
    nombre = clave(parte)
    if not nombre:
        return []
    found: list[tuple[int, str, str | None, str]] = []
    provincias_, cantones, distritos = _division()
    if nombre in provincias_:
        found.append(
            (NIVEL_PROVINCIA, provincias_[nombre], None, provincias_[nombre])
        )
    for oficial, canton, provincia in sorted(cantones.get(nombre, ())):
        found.append((NIVEL_CANTON, provincia, canton, oficial))
    for oficial, canton, provincia in sorted(distritos.get(nombre, ())):
        found.append((NIVEL_DISTRITO, provincia, canton, oficial))
    return found


def resolver(parte: str) -> tuple[int, str, str | None, str] | None:
    """Nivel, provincia, canton y nombre oficial de un lugar.

    La busqueda va de MAYOR a MENOR: provincia, luego canton y al final
    distrito. Devuelve ``None`` si el nombre existe en VARIAS provincias
    (es ambiguo y no se usa para deducir nada).
    """
    opciones = candidatos(parte)
    if not opciones:
        return None
    # La provincia manda: "San José" es la provincia (aunque tambien sea el
    # nombre de un distrito en Alajuela y en Heredia).
    for opcion in opciones:
        if opcion[0] == NIVEL_PROVINCIA:
            return opcion
    if len({opcion[1] for opcion in opciones}) > 1:
        return None
    for nivel in (NIVEL_CANTON, NIVEL_DISTRITO):
        for opcion in opciones:
            if opcion[0] == nivel:
                return opcion
    return None


def _resolver_en_palabras(parte: str) -> list[tuple[int, str, str | None, str]]:
    """Busca lugares DENTRO de un nombre compuesto ("San Antonio de Belen").

    Se prueban palabras sueltas y pares contiguos ("Santa Ana"), y se
    devuelven los candidatos mas especificos.
    """
    palabras = parte.split()
    textos: list[str] = list(palabras)
    textos += [
        f"{palabras[indice]} {palabras[indice + 1]}"
        for indice in range(len(palabras) - 1)
    ]
    mejor_nivel = 0
    mejores: list[tuple[int, str, str | None, str]] = []
    for texto in textos:
        if len(texto) < 4:
            continue
        for opcion in candidatos(texto):
            if opcion[0] > mejor_nivel:
                mejor_nivel = opcion[0]
                mejores = [opcion]
            elif opcion[0] == mejor_nivel and opcion not in mejores:
                mejores.append(opcion)
    return mejores


def _es_nombre_de_provincia(nombre: str) -> bool:
    return clave(nombre) in provincias()


def _provincias_en_texto(parte: str) -> list[str]:
    """Provincias que nombra ``parte``, aunque vengan pegadas a otra palabra.

    Un tablero escribe "HCLTech, Belen Heredia" (sin coma entre el canton y la
    provincia): el ``partir`` no puede separarlo, pero la PROVINCIA sigue
    siendo un dato cierto porque el texto la nombra. Se buscan n-gramas de
    hasta tres palabras (para "San Jose", "Perez Zeledon"... solo cuando el
    nombre es de provincia).
    """
    palabras = (parte or "").split()
    mapa = provincias()
    halladas: list[str] = []
    for tam in (3, 2, 1):
        for inicio in range(len(palabras) - tam + 1):
            nombre = mapa.get(clave(" ".join(palabras[inicio : inicio + tam])))
            if nombre and nombre not in halladas:
                halladas.append(nombre)
    return halladas


def _provincias_de_un_lugar(nombre: str) -> set[str]:
    """Provincias en las que podria estar ``nombre`` segun el catalogo."""
    return {opcion[1] for opcion in _resolver_en_palabras(nombre)}


def resolver_direccion(
    texto: str, *, descripcion: str | None = None, work_mode: str | None = None
) -> dict[str, str | None]:
    """Ciudad y provincia de una ubicacion de Costa Rica.

    Jerarquia **pais -> provincia -> canton -> distrito**:

    - La **provincia** es un dato cierto cuando el texto la nombra, aunque su
      nombre tambien sea el de una ciudad ("San Jose, Costa Rica" -> region San
      Jose, ciudad nula): la ambiguedad afecta a la CIUDAD, no a la provincia.
      Basta con que el texto la nombre, aunque venga pegada a otra palabra sin
      separador ("HCLTech, Belen Heredia" -> region Heredia).
    - La **ciudad** se toma del lugar mas especifico que el texto nombre y que
      sea inequivoco; si es solo la provincia no se repite como ciudad. La
      EXCEPCION es la repeticion "ciudad, canton, pais" ("Heredia, Heredia,
      Costa Rica" -> ciudad Heredia): ahi la repeticion es el contexto.
    - Un **distrito ambiguo** se desambigua con el canton que lo acompania
      ("San Antonio, Belen, Heredia" -> San Antonio, Heredia).
    - Un nombre compuesto por lugares de provincias distintas ("Gravilias Tres
      Rios") no es una ciudad: no se guarda.
    - ``descripcion``: ULTIMO recurso para los campos de CIUDAD que la
      ubicacion no resuelve. Se busca un lugar conocido de
      ``seeds/lugares_cr.csv`` en el texto del aviso ("hybrid position based in
      Ultra Park II, Lagunilla (Heredia)"). No se aplica a los avisos
      **remotos**: ahi no hay sede que resolver (si a los hibridos).
    """
    partes = partir(_RUIDO.sub(" ", texto or ""))
    provincias_nombradas: list[str] = []
    hallazgos: list[tuple[int, str, str, str | None]] = []
    desconocidos: list[str] = []

    # Primera pasada: las provincias que nombra el texto. Se necesitan antes
    # de resolver el resto, porque un nombre homonimo ("Belén") solo se
    # desambigua con la provincia que lo acompania.
    opciones_por_parte: list[tuple[str, list]] = []
    for parte in partes:
        opciones = candidatos(parte) or _resolver_en_palabras(parte)
        opciones_por_parte.append((parte, opciones))
        for opcion in opciones:
            if opcion[0] != NIVEL_PROVINCIA:
                continue
            if opcion[1] not in provincias_nombradas:
                provincias_nombradas.append(opcion[1])
        # La provincia puede venir PEGADA a otra palabra ("Belen Heredia"):
        # el texto la nombra y por tanto es un dato cierto.
        for provincia in _provincias_en_texto(parte):
            if provincia not in provincias_nombradas:
                provincias_nombradas.append(provincia)

    # Segunda pasada: canton y distrito.
    for parte, opciones in opciones_por_parte:
        if not opciones:
            if es_ciudad_plausible(parte):
                desconocidos.append(parte)
            continue
        if any(opcion[0] == NIVEL_PROVINCIA for opcion in opciones):
            continue
        # Un nombre con varias provincias posibles ("Belén": canton de
        # Heredia y distrito de Guanacaste) se desambigua con la provincia
        # que nombra el texto o con un distrito que el texto nombra y que
        # pertenece a uno de los cantones candidatos ("San Antonio de
        # Belen"). Si no hay contexto, se descarta (no se adivina).
        provincias_posibles = {opcion[1] for opcion in opciones}
        if len(provincias_posibles) > 1:
            elegida = [
                opcion for opcion in opciones if opcion[1] in provincias_nombradas
            ]
            if not elegida:
                resolucion = _candidato_por_distrito(parte, opciones)
                if resolucion is None:
                    if es_ciudad_plausible(parte):
                        desconocidos.append(parte)
                    continue
                distrito, opcion = resolucion
                hallazgos.append((NIVEL_DISTRITO, distrito, opcion[1], opcion[2]))
                continue
            opciones = elegida
        nivel, provincia, canton, nombre = max(
            opciones,
            # A igual nivel se prefiere el nombre que NO es el de la provincia:
            # "Lagar San Ramon de Alajuela" -> San Ramon (la provincia no
            # aporta ciudad, solo confirma la region).
            key=lambda item: (item[0], not _es_nombre_de_provincia(item[3])),
        )
        candidato = (nivel, nombre, provincia, canton)
        if candidato not in hallazgos:
            hallazgos.append(candidato)

    region = provincias_nombradas[0] if provincias_nombradas else None
    city: str | None = None

    # De mas especifico a menos: distrito, luego canton.
    hallazgos.sort(key=lambda candidato: -candidato[0])
    if hallazgos:
        nivel, nombre, provincia, canton = hallazgos[0]
        if nivel == NIVEL_CANTON and desconocidos:
            # "San Antonio, Belen": el distrito desambigua con su canton.
            distritos_del_canton = distritos_de_canton(canton)
            for desconocido in desconocidos:
                if clave(desconocido) in distritos_del_canton:
                    city = desconocido
                    break
        if city is None and not _es_nombre_de_provincia(nombre):
            city = nombre
        if region is None:
            region = provincia
    elif desconocidos:
        # Solo se nombro la provincia (o nada): se usa el lugar concreto si la
        # tabla lo reconoce en una unica provincia.
        for desconocido in desconocidos:
            provincia_unica = _provincia_de_distrito(clave(desconocido))
            if provincia_unica is None:
                continue
            if region is None or clave(region) == clave(provincia_unica):
                city = desconocido
                break
        if city is None and len(desconocidos) == 1:
            # Un unico lugar nombrado que no es la provincia: es la ciudad
            # ("Alajuela - Coyol", "Four Seasons Costa Rica"). Salvo que sea
            # una ENSALADA de lugares ("Gravilias Tres Rios" = un distrito de
            # San Jose + otro de Cartago, "Sucursal Toyota Zapote"): ahi no hay
            # una ciudad, hay dos, y no se guarda basura.
            if len(_provincias_de_un_lugar(desconocidos[0])) <= 1:
                city = desconocidos[0]

    # "Heredia, Heredia, Costa Rica" es el idioma universal "ciudad, canton,
    # pais": la REPETICION es el contexto que desambigua el nombre homonimo de
    # la provincia. Sin repetir ("Heredia, Costa Rica") no se adivina: la
    # ubicacion solo dice la provincia.
    if city is None and provincias_nombradas:
        claves_partes = [clave(parte) for parte in partes]
        for nombre_provincia in provincias_nombradas:
            if claves_partes.count(clave(nombre_provincia)) >= 2:
                city = nombre_provincia
                break

    # La tabla de LUGARES tambien se consulta en la propia ubicacion: un
    # tablero puede escribir "HCLTech, AFZ" o "Control Fronterizo | Peñas
    # Blancas" y ahi el lugar es el unico dato de ubicacion. Un lugar declarado
    # TIENE PRIORIDAD sobre el nombre homonimo de la division territorial
    # ("Peñas Blancas" existe como distrito en Alajuela, pero el control
    # fronterizo con ese nombre esta en Guanacaste).
    lugar_ubicacion = resolver_lugar(texto or "")
    if lugar_ubicacion is not None:
        _, ciudad_lugar, provincia_lugar = lugar_ubicacion
        region = provincia_lugar
        if city is None or resolver(city) is None:
            city = ciudad_lugar

    # ULTIMO recurso para los campos que la ubicacion NO pudo resolver: el
    # TEXTO del aviso nombra un lugar conocido ("hybrid position based in
    # Ultra Park II, Lagunilla (Heredia)"). Solo rellena lo que falta y nunca
    # contradice una provincia ya resuelta. No se usa en avisos remotos: ahi
    # no hay sede que resolver (si en los hibridos).
    if (city is None or region is None) and descripcion and not _es_remoto(
        work_mode, texto, descripcion
    ):
        lugar = resolver_lugar(descripcion)
        if lugar is not None:
            nombre_lugar, ciudad_lugar, provincia_lugar = lugar
            if region is None or clave(region) == clave(provincia_lugar):
                if city is None:
                    city = ciudad_lugar
                elif resolver(city) is None:
                    # La ciudad de la ubicacion no esta en la tabla
                    # ("Four Seasons"), pero el texto si da el lugar.
                    city = ciudad_lugar
                if region is None:
                    region = provincia_lugar
    return {"city": city, "region": region}


def _candidato_por_distrito(
    parte: str, opciones: list[tuple[int, str, str | None, str]]
) -> tuple[str, tuple[int, str, str | None, str]] | None:
    """Desambigua un nombre usando el canton o distrito que el texto nombra.

    ``"San Antonio de Belen"``: "San Antonio" es un distrito del canton
    Belen, asi que el canton es el de Heredia (no el distrito homonimo de
    Guanacaste). Devuelve ``(distrito, opcion del canton)``.
    """
    texto = clave(parte)
    encontrados: list[tuple[tuple[int, str, str | None, str], str]] = []
    for opcion in opciones:
        canton = opcion[2]
        if not canton:
            continue
        nombres = {clave(canton)} | distritos_de_canton(canton)
        # El nombre del propio candidato no sirve para desambiguar.
        nombres.discard(clave(opcion[3]))
        for nombre in nombres:
            patron = r"\s+".join(
                re.escape(palabra) for palabra in nombre.split()
            )
            if re.search(rf"(?<![a-z0-9]){patron}(?![a-z0-9])", texto):
                encontrados.append((opcion, opcion[3]))
                break
    if not encontrados:
        return None
    if len({opcion[1] for opcion, _ in encontrados}) > 1:
        return None
    opcion, distrito = max(encontrados, key=lambda par: len(par[1]))
    return distrito, opcion


def _provincia_de_distrito(nombre_clave: str) -> str | None:
    """Provincia del distrito si TODAS sus apariciones son de la misma."""
    valor = _division()[2].get(nombre_clave)
    if not valor:
        return None
    provincias_distintas = {provincia for _, _, provincia in valor}
    if len(provincias_distintas) != 1:
        return None
    return provincias_distintas.pop()


def _es_remoto(
    work_mode: str | None, texto: str | None = None, descripcion: str | None = None
) -> bool:
    """True si el aviso es REMOTO (no hay sede que resolver).

    Se mira la modalidad (``work_mode``) y, si aun no se sabe, el texto de la
    ubicacion ("Costa Rica Remote") y las marcas inequivocas del anuncio
    ("fully remote", "remote position"). Un aviso **hibrido** NO es remoto: si
    tiene sede, la sede se resuelve.
    """
    if clave(work_mode or "") == "remote":
        return True
    if texto:
        marca = re.search(
            r"\b(?:remote|remoto|remota|virtual|teletrabajo|work\s*from\s*home)"
            r"(?!\s*(?:/|,)?\s*hybrid)",
            texto or "",
            re.IGNORECASE,
        )
        if marca:
            return True
    if descripcion:
        marca = re.search(
            r"(?:fully|100%|completely|totalmente|full)\s+remote"
            r"|remote\s+(?:position|role|work|job)"
            r"|position\s+(?:is\s+)?remote"
            r"|trabajo\s+remoto"
            r"|teletrabajo",
            descripcion,
            re.IGNORECASE,
        )
        if marca:
            return True
    return False


@lru_cache(maxsize=1)
def _lugares() -> list[tuple[re.Pattern[str], str, str, str]]:
    """[(patron, lugar canonico, ciudad, provincia)] desde la tabla de lugares.

    El patron exige el nombre completo con limites de palabra para no confundir
    "AFZ" con una subcadena cualquiera. El nombre canonico es el de la columna
    ``Lugar`` (no el alias): si el texto dice "Zona Franca Coyol", el lugar se
    llama "Coyol Free Zone". La columna ``Ciudad`` es lo que se guarda en el
    campo ``city`` (la localidad donde esta el lugar).
    """
    lugares: list[tuple[re.Pattern[str], str, str, str]] = []
    if not LUGARES_CSV.exists():
        return lugares
    with LUGARES_CSV.open(encoding="utf-8", newline="") as fh:
        for fila in csv.DictReader(fh):
            if clave(fila.get("Pais", "")) != clave(PAIS):
                continue
            provincia = (fila.get("Provincia") or "").strip()
            canonico = (fila.get("Lugar") or "").strip()
            if not provincia or not canonico:
                continue
            ciudad = (fila.get("Ciudad") or "").strip()
            for nombre in (canonico, (fila.get("Alias") or "").strip()):
                if not nombre:
                    continue
                # Se escapa CADA palabra y se unen con \\s+: escapar el nombre
                # entero dejaria los espacios como "\\ " y el patron no
                # casaria con "Ultra  Park" (dos espacios).
                cuerpo = r"\s+".join(
                    re.escape(palabra) for palabra in nombre.split()
                )
                patron = re.compile(
                    r"(?<![\w])" + cuerpo + r"(?![\w])", re.IGNORECASE
                )
                lugares.append((patron, canonico, ciudad or canonico, provincia))
    return lugares


def resolver_lugar(texto: str) -> tuple[str, str, str] | None:
    """Lugar conocido (parque/zona/sede) en el texto, si es INEQUIVOCO.

    Devuelve ``(lugar, ciudad, provincia)`` o ``None``. Si el texto nombra
    lugares de provincias distintas no se elige ninguno (no se adivina).
    """
    if not texto:
        return None
    hallados: list[tuple[str, str, str]] = []
    for patron, canonico, ciudad, provincia in _lugares():
        if patron.search(texto):
            candidato = (canonico, ciudad, provincia)
            if candidato not in hallados:
                hallados.append(candidato)
    if not hallados:
        return None
    if len({provincia for _, _, provincia in hallados}) > 1:
        return None
    # Gana el nombre mas especifico ("Ultra Park II" antes que "Ultra Park").
    hallados.sort(key=lambda candidato: -len(candidato[0]))
    return hallados[0]
