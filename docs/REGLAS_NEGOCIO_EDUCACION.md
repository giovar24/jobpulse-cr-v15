# Reglas de NEGOCIO — el nivel educativo (Paso 5 · `educacion`)

> **Qué es esto**: las reglas de negocio que el motor del Paso 5 **no puede
> deducir del texto** y que, por lo tanto, decide una **segunda persona** (la
> firma vive en `job_match_decision`, se aplica en `docs/PASO5_FIRMA_EDUCACION.json`
> y se lee en `docs/PASO5_REVISION_PENDIENTES.md`).
>
> **Regla de oro**: una regla de negocio se escribe **con su fuente**. Si no hay
> fuente, el caso queda `dudoso` y abierto (no se decide "a criterio").

---

## 1. La escalera de niveles educativos

Orden **de mayor a menor** (decidido por el usuario el **2026-11-08**):

```
posgrado
  > título universitario
      > estudiante sin graduar pero con la mayoría de los créditos completados (80 % o más)
          > diploma técnico
              > bachillerato de secundaria
```

En el motor (`src/jobpulse_v15/matching.py`) esos escalones son los
`NIVEL_*`: `1` secundaria · `2` superior de ciclo corto · **`3` estudiante
avanzado** · `4` universitario · `5` posgrado (el escalón 3 es el punto de la
§4 y llegó con la migración **028**).

### Fuente de la escalera

| Fuente | Qué aporta | Enlace |
|---|---|---|
| **U.S. Department of State — InfoUSA, "Structure of U.S. Education"** | La estructura del sistema educativo de EE. UU.: *"a four-stage higher education degree system (associate, bachelor's, master's, doctorate) plus various non-degree certificates and diplomas"* y *"Completion of each level or stage is a prerequisite for access to the next"* | <https://usinfo.state.gov/infousa/education/overview/edlite-structure-us.html> (copia vigente: <https://usinfo.org/enus/education/overview/edlite-structure-us1.html>) |
| **ISCED 2011 (UNESCO), nivel 4 "partial level completion"** | Un avance parcial **no confiere título**: es una subcategoría de nivel, no una cualificación → por eso "80 % de un bachelor" NO es un título universitario | citado en el propio código (`matching.py`, comentario de `_PATRON_ESTUDIOS_PARCIALES`) |
| **CONESUP (Costa Rica)** | Entidad que acredita las instituciones de educación superior del país: un título de una entidad acreditada es una **titulación** de educación superior | criterio del usuario (2026-11-08); la fuente documental del CONESUP **no** se usó (no había ninguna a mano) |

### Por qué la referencia es el sistema de EE. UU. y no el de CONESUP

Decisión del usuario (**2026-11-08**): *"casi todo lo que hay en CR se basa en
políticas de EE. UU. […] lo cual sirve también para las empresas
multinacionales"*. En la práctica:

1. **Los avisos son de léxico estadounidense**: los portales que scrapea el repo
   (Workday, LinkedIn, Indeed) publican en inglés con la nomenclatura de EE. UU.
   ("Associate's degree", "Bachelor's degree", "Master's degree", "X % of
   completeness of a bachelor's degree program"). Sin una referencia de EE. UU.
   no hay forma de traducir "Associate's degree" a un nivel.
2. **Las empresas multinacionales** (Sysco, Abbott, Intel, Kimberly-Clark…)
   redactan y traducen sus avisos con esa misma nomenclatura.
3. La escalera de EE. UU. (associate < bachelor's < master's < doctorate) es
   **compatible** con la de CR: el "diploma técnico" CR equivale al *associate
   degree* (2 años, educación superior) y el "bachillerato de secundaria" CR
   equivale al *high school diploma*.

**Regla de acreditación (usuario, 2026-11-08)**: *"solo una titulación por una
entidad acreditada por el CONESUP cuenta como título académico superior"*. Es
un **criterio de curación del perfil** (qué hecho educativo merece qué código
canónico), no una comparación del matching: el motor compara **niveles**, y el
nivel de un hecho lo declara el código canónico curado.

### 1.1 Qué dice la tabla y qué NO dice (2026-11-10)

La tabla de EE. UU. es una escalera de **4 etapas de TÍTULO**
(associate < bachelor's < master's < doctorate) con la regla *"completion of
each level or stage is a prerequisite for access to the next"*. Leída al pie:

1. **El associate NO es un bachelor**: es el título de ciclo corto (2 años). El
   "diploma técnico" CR es su equivalente.
2. **El prerrequisito es una ETAPA COMPLETADA**: para entrar al bachelor hay
   que haber **completado** el associate. Quien está en el bachelor **ya tiene
   el associate** (de ahí que el escalón "estudiante avanzado" esté **por
   encima** del ciclo corto y no sea un ciclo corto disfrazado).
3. **La tabla no dice que el avance parcial equivalga a un título**: el
   avance parcial del bachelor no confiere título (ISCED 2011) → por eso el
   escalón 3 es propio.
4. **Lo que la tabla NO autoriza**: tratar "bachelor en curso" como
   "associate en curso". El `nominal − 1` que el motor usaba hasta el
   2026-11-10 **suponía** esa equivalencia sin que la fuente la dijera: un
   associate en curso **no** confiere el associate.

Efectivo de cada programa en curso (`matching.nivel_efectivo_fact`):

| Programa que se cursa | Títulos ya completados (por el prerrequisito) | Escalón efectivo |
|---|---|---|
| associate (ciclo corto) en curso | — | **1** (secundaria): no confiere el associate |
| bachelor (universitario) en curso | associate | **3** (estudiante avanzado) **solo con el 80 %+ documentado**; sin el dato, nada |
| master (posgrado) en curso | bachelor | **4** (universitario): el bachelor está terminado |

---

## 2. Qué significa cada escalón en la práctica

| Escalón | En los avisos (léxico de EE. UU.) | En CR | Dónde vive en el código |
|---|---|---|---|
| Posgrado | master's, MBA, doctorate, PhD | posgrado | `educacion-posgrado` |
| Título universitario | bachelor's degree, university degree, four-year college degree, "licenciatura" | bachillerato universitario / licenciatura | `educacion-universitaria` |
| Estudiante avanzado (80 %+) | "X % of completeness of a bachelor's degree program" | estudiante avanzado con la mayoría de los créditos | escalón `3` (`nivel_escala`); requiere un hecho `pursuing` **con el 80 %+ documentado** (§4, §4.1) |
| Diploma técnico | associate's degree, two-year college degree, technical degree, "técnico superior" | diploma técnico / técnico superior | `educacion-tecnica` |
| Bachillerato de secundaria | high school diploma, secondary education | bachillerato en educación media (MEP) | `educacion-secundaria` |

---

## 3. Reglas que se aplican

### R1 · Un requisito se cumple si el nivel del perfil ≥ el nivel del aviso

Es la comparación base del motor (`matching._evaluar_educacion`). Con la
escalera de la §1:

- aviso que pide *associate* (2) → cumple quien tiene diplomado técnico (2) o
  más;
- aviso que pide *bachelor* (3) → **no** cumple quien solo tiene diplomado
  técnico (2).

### R2 · El estudiante avanzado NO es un titulado

*"Hay empresas que permiten a estudiantes avanzados laborar, pero no les pegan
igual que a una persona titulada: lo hacen por conveniencia de la misma
empresa (menor pago), no porque el perfil califique"* (usuario, 2026-11-08).

Consecuencias:

1. Un aviso que exige **título universitario** NO lo cumple quien está en el
   escalón "estudiante avanzado" (aunque tenga el 99 % de los créditos): el
   aviso no dice "o estudios avanzados", dice "degree".
2. Un aviso que acepta explícitamente el avance parcial ("80 % of completeness
   of a bachelor's degree program") SÍ lo cumple el escalón "estudiante
   avanzado" — y solo ese escalón: un diplomado técnico está **por debajo**.

### R3 · "Preferred" no bloquea

Un requisito `preferred` nunca bloquea y no cuenta en el denominador (ya está
en el motor; regla dura del repo).

### R4 · El motor no decide lo que el texto no confirma

`descartada` solo si el texto **confirma** el título obligatorio **sin negación
y sin alternativa**; ante la duda → `revisar_a_mano / educacion_no_confirmada`
y lo decide una segunda persona (la firma). **Una firma nunca pisa un veredicto
del motor**: solo cierra los casos que el motor dejó abiertos.

### R5 · El campo del título importa (limitación conocida)

El motor **no** modela el *campo* del título ("in business, Finance" vs. un
diplomado en Electrónica). Cuando el nivel se cumple pero el campo no, el caso
lo cierra la **firma** de la segunda persona, no el motor.

---

## 4. El escalón "estudiante avanzado" en el motor — **HECHO (migración 028, 2026-11-10)**

La escalera del motor ya tiene **cinco** escalones:

| orden | escalón | `nivel_escala.codigo` |
|---|---|---|
| 1 | bachillerato de secundaria | `secundaria` |
| 2 | diploma técnico (ciclo corto) | `tecnico` |
| 3 | estudiante avanzado (80 %+) | `estudiante_avanzado` |
| 4 | título universitario | `universitaria` |
| 5 | posgrado | `posgrado` |

Cómo lo aplica el motor (`matching.py`):

1. **El estado cuenta**: un hecho `pursuing` no confiere el título que estudia
   → su nivel **efectivo** lo dice la tabla de EE. UU. (§1.1), no una resta:
   - `educacion-universitaria` (bachelor) en curso → **3** (estudiante
     avanzado) **solo si documenta el 80 %+ de los créditos**; sin el dato no
     se puede afirmar (nivel `None`).
   - `educacion-tecnica` (associate) en curso → **1** (secundaria): no
     confiere el associate.
   - `educacion-posgrado` (master) en curso → **4** (universitario): el
     bachelor es el prerrequisito y está terminado.
   - `completed` conserva el nivel nominal.
2. **El aviso con "X % de completitud"** declara el escalón 3 (si pide 80 % o
   más) o el escalón 2 (si pide menos), nunca el 4
   (`nivel_efectivo_requisito` + `porcentaje_estudios_parciales`).
3. **Las vías académicas** ("or coursework/studies toward a university
   degree") declaran el escalón 3: están disponibles para el estudiante
   avanzado, no solo para el titulado.
4. **Un requisito de estudiante activo** ("currently pursuing a Bachelor's
   degree") sigue comparando el nivel **nominal** del programa que se cursa
   (`estado_educacion_en_curso`): pregunta qué se estudia, no si el título
   está terminado.
5. **Posgrado en curso** (nivel 5) confiere el **título universitario** (4):
   el bachelor es el requisito de entrada del programa, y no depende del
   avance.

### 4.1 El 80 % es un UMBRAL EXIGIDO, no supuesto (2026-11-10)

Decisión del usuario, coherente con la referencia de EE. UU.: cuando un
puesto pide "estudiante avanzado", **se da por hecho que la persona tiene la
mayor parte de la carrera finalizada: 80 % o más de los créditos**. El motor
lo **exige en las dos direcciones**:

| Lado | Regla | Implementación |
|---|---|---|
| **El aviso** | "X % completeness of a bachelor's degree program" con X ≥ 80 → escalón 3 (estudiante avanzado); con X < 80 → escalón 2 (por debajo del avanzado) | `porcentaje_estudios_parciales` + `nivel_efectivo_requisito` |
| **El perfil** | Un hecho `pursuing` de nivel universitario **solo** alcanza el escalón 3 si declara el 80 %+; sin ese dato **no** se da por hecho (nivel `None`) | `porcentaje_avance_fact` + `nivel_efectivo_fact` |

Dónde se registra el avance del perfil (`porcentaje_avance_fact`): en el
texto libre del hecho (`qualifier`, `notes` o `value_text`, p. ej. "80 % de
créditos completados") **o** en `numeric_value` con `unit` de porcentaje
(`80` + `%`). En la UI v2 el campo **"Nivel / calificador"** de un dato de
categoría *Educación* sirve para anotarlo; en la UI clásica el campo
equivalente es **"Campo"** (queda en `notes`).

Sin ese dato, un `pursuing` **no** alcanza el escalón 3 y el perfil queda
**no verificable** en esa dimensión (nunca se descarta por falta de
información). Es la traducción literal de "no se da por hecho": el motor no
afirma lo que el perfil no dice.

Migración de datos: `src/jobpulse_v15/migrations/028_estudiante_avanzado.sql`
(inserta el escalón 3 y corre universitario 3→4 y posgrado 4→5). Esquema
**28**.

**Medición obligatoria en copia (2026-11-10, 735 avisos)** — código anterior
vs migración 028, mismo corpus:

| Dimensión | Cambios |
|---|---|
| Paso 5 (`job_match`): estado, motivo, puntaje, cobertura | **0** |
| Paso 5: conteos internos | **1** aviso (Abbott): `faltantes` 8→9, `nc` 2→1 (el requisito del 80 % pasa de `no_confirmado` a `faltante`, que es lo correcto: el perfil no tiene el hecho "en curso") |
| Viabilidad: bandas | **1** aviso (Abbott): `no_prioritario` → `revisar`, mismo ajuste (27,5). Es el **tope duro** documentado: ≥1 requisito `required` faltante ⇒ banda máxima `revisar` |
| Vetos | **0** nuevos |

Los dos cambios caen en el **mismo caso abierto** (Abbott) y son
consecuencia directa de la regla, no un efecto colateral: el aviso pide el
escalón 3, el perfil solo alcanza el 2, y por eso el requisito queda
`faltante` (no bloqueante, porque el texto ofrece la vía "or other
technical/scientific experience"). El caso sigue **abierto** (`dudoso`)
porque falta el dato del perfil (§5.2).

**Medición del umbral del 80 % (2026-11-10, copia, 735 avisos)** — regla del
§4.1 (avance exigido en aviso y perfil) contra el corpus real:

| Dimensión | Cambios |
|---|---|
| Paso 5: estado, motivo, puntaje, cobertura, conteos | **0** |
| Viabilidad: banda, ajuste, veto | **0** |

**0 cambios**, y es lo esperado: el perfil **no tiene** ningún hecho
`pursuing` (sus 2 hechos educativos son `completed`), así que el umbral
nuevo no tiene sobre qué actuar; y el único aviso con avance parcial
(Abbott) ya pedía 80 % → escalón 3, igual que antes. La regla queda
**sin efecto sobre el corpus actual** y solo gobierna los casos futuros en
que se registre un `pursuing` (que es exactamente el caso abierto de
Abbott: si se registra con 80 %+ de créditos, el motor lo cierra como
*cumple*).

**Medición de la corrección de la §1.1 (2026-11-10, copia, 735 avisos)** —
el `nominal − 1` (que suponía "associate en curso" para un bachelor en curso)
sustituido por la tabla de EE. UU.:

| Dimensión | Cambios |
|---|---|
| Paso 5: estado, motivo, puntaje, cobertura, conteos | **0** |
| Viabilidad: banda, ajuste, veto | **0** |

**0 cambios** otra vez, por el mismo motivo: sin hechos `pursuing` en el
perfil, ningún nivel efectivo cambia. La diferencia es de **principio**: el
nivel de un estudiante en curso ya no se deduce de una resta, sino de lo que
la tabla dice que el programa presupone.

Plan original (histórico): escalón nuevo por migración de datos + medición
en copia antes de tocar la BD real (ver `docs/PLAN_MEJORAS.md` §6.2).

---

## 5. Los dos casos queabraron esta regla (2026-11-08)

| Caso | Aviso (cita literal) | Escalón que pide | Perfil | Veredicto firmado | Efecto |
|---|---|---|---|---|---|
| `workday-Credit---Collections-Specialist--2_R232432` (Sysco) | «Required Associate’s or bachelor’s degree in business, Finance, or a related field» | `associate` (2) + `bachelor` (3) | diplomado técnico (2) **en Electrónica** (el aviso pide business/Finance) | **`bloqueo_real`** | `descartada` (R5: el nivel se cumple, el campo no) |
| `workday-Production-Supervisor-I_31163511` (Abbott) | «80% completeness of a bachelor’s degree program from a four-year college or university» | estudiante avanzado (3) | diplomado técnico (2), sin hechos "en curso" | **`bloqueo_real`** (re-firmado el 2026-11-11) | `descartada`: la regla ya estaba decidida y el motor ya la aplicó (el requisito del 80 % quedó `faltante`); la firma solo cerraba el caso |

Las dos firmas están en `docs/PASO5_FIRMA_EDUCACION.json`, ancladas al sha256
del texto exacto que se leyó (si el aviso se re-raspa y su texto cambia, la
firma deja de aplicar y el caso vuelve a la hoja).

> **Convención de citas**: en el `criterio` de cada firma, lo que va entre
> comillas angulares `«...»` es **siempre una cita literal del aviso**. Los
> nombres de escalones o de reglas van entre comillas simples (`'...'`).
> `decision sign` lo comprueba al firmar (rechaza la firma y avisa) y
> `verificar_evidencia.py` lo comprueba al verificar.

### 5.1 Aplicación en la BD real (2026-11-08)

| paso | resultado |
|---|---|
| backup | `data/backups/pre_regla_educacion_20261108_213631.db` |
| `decision sign --dry-run` | 29 decisiones · **texto_igual 29** · texto_cambiado 0 |
| `decision sign` | 29 aplicadas (upsert: Sysco y Abbott **actualizan** su fila; el mismo texto firmado dos veces → manda la segunda firma) |
| `run_paso5.py` | corrida **`20261108_214123`** (735 avisos evaluados) |
| `generar_evidencia_paso5.py` | 1689 líneas · descartada 100 · no_confirmada 1 |
| `verificar_evidencia.py` | **TODO CUADRA: 140 verificaciones con frase LITERAL** (29/29 firmas: cita literal + efecto) |
| `generar_revision_pendientes.py` | **1 caso abierto** (Abbott) |
| `db check` | esquema **27** · `integrity_check` ok · **0 violaciones FK** |

**El único cambio de estado en los 735 avisos** (diff de la corrida anterior
`20261108_175932` contra la vigente `20261108_214123`):

```
workday-Credit---Collections-Specialist--2_R232432
   antes: revisar_a_mano / educacion_no_confirmada
   ahora: descartada     / titulo_universitario_requerido
```

Abbott (`workday-Production-Supervisor-I_31163511`) sigue **abierto** en
`revisar_a_mano / educacion_no_confirmada`: la regla ya está decidida, lo que
falta es el **dato** del perfil.

### 5.2 Qué haría falta para cerrar Abbott (RESUELTO el 2026-11-11)

El aviso pide «80% completeness of a bachelor's degree program» → el escalón
"estudiante avanzado" (= 80 %+ de los créditos, §4.1). Para que el perfil lo
alcanzaba hacía falta **un hecho educativo en el perfil**:

- `education_status = 'pursuing'`,
- `codigo_canonico` de la licenciatura **en curso** (hoy el perfil no tiene
  ninguno: sus 2 hechos educativos son `completed`),
- y el avance (**80 %+ de los créditos**) registrado en el `qualifier` (o en
  las `notes`) del hecho, o en `numeric_value` + `unit = '%'`.

Con ese hecho, el motor lo cerraba como **cumple** (escalón 3 = escalón que
pide el aviso). Sin él, el perfil solo llegaba al escalón "diploma técnico" y
correspondía firmarlo `bloqueo_real` (la escalera de la §1 lo dice: el escalón
"estudiante avanzado" está **por encima** del diploma técnico).

> Nota: el motor ya tiene el escalón "estudiante avanzado" (migración 028,
> 2026-11-10) **y exige el 80 %**: un `pursuing` en `educacion-universitaria`
> cuenta como escalón 3 **solo** si documenta el avance → ver §4, §4.1 y
> `docs/PLAN_MEJORAS.md` §6.2.

**Cómo se cerró (2026-11-11)**: el perfil registra el escalón 2 (diploma
técnico / associate, completo) y **ningún** hecho `pursuing` → **no alcanza**
el escalón 3. El motor ya lo había dicho: el requisito del 80 % quedó
`faltante`. La regla estaba decidida y aplicada, así que lo que faltaba era el
**veredicto de la segunda persona**, no un dato: se re-firmó como
`bloqueo_real` (criterio con la cita literal del aviso + la escalera) y Abbott
pasó a `descartada`. La firma queda **anclada al sha256 del texto**: si el
perfil registra más adelante esa licenciatura en curso con su avance, la firma
deja de aplicar y el caso vuelve a abrirse solo.

---

## 6. Fuentes (todas)

| # | Fuente | Tipo | Qué sustenta |
|---|---|---|---|
| 1 | U.S. Department of State — InfoUSA, *Structure of U.S. Education* — <https://usinfo.state.gov/infousa/education/overview/edlite-structure-us.html> (copia: <https://usinfo.org/enus/education/overview/edlite-structure-us1.html>) | Documental, pública | La escalera de la §1 (associate < bachelor's < master's < doctorate; "completion of each level is a prerequisite for the next") y el mapeo de la terminología de los avisos |
| 2 | UNESCO, **ISCED 2011**, nivel *"partial level completion"* | Normativa internacional | Un avance parcial (X %) **no confiere título**: el escalón "estudiante avanzado" está por debajo del título universitario (R2) |
| 3 | **CONESUP** (Consejo Superior de Educación Superior, Costa Rica) | Entidad acreditadora | Criterio de curación: solo una titulación de una entidad acreditada es título académico superior (§1) — *fuente documental no aportada; el criterio quedó como regla del usuario* |
| 4 | **Usuario (Giovanni Vargas)**, 2026-11-08 | Decisión de negocio | La escalera (§1), el criterio de acreditación (§1), R2 ("el estudiante avanzado no es igual a un titulado"), la referencia de EE. UU. y el veredicto `bloqueo_real` del caso Sysco |
| 5 | `src/jobpulse_v15/matching.py` (comentarios de `_PATRON_ESTUDIOS_PARCIALES` y `_VIA_ACADEMICA_NIVEL`) | Código del repo | El precedente interno: el avance parcial es un nivel, no una cualificación; las vías alternativas declaran su nivel |
| 6 | `docs/PLAN_MEJORAS.md` §5.7 | Bitácora del repo | La decisión de separar el firmante del autor de la regla (el sesgo) |

> **Pendiente de fuente**: si alguna vez se quiere una fuente documental del
> CONESUP (p. ej. el registro de instituciones acreditadas y el catálogo de
> títulos), se añade aquí y se cita en las firmas afectadas.
