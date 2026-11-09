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
`NIVEL_*` (`1` secundaria · `2` superior de ciclo corto · `3` universitario ·
`4` posgrado; el escalón "estudiante avanzado" es el que falta y es el punto
de la §4).

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

---

## 2. Qué significa cada escalón en la práctica

| Escalón | En los avisos (léxico de EE. UU.) | En CR | Dónde vive en el código |
|---|---|---|---|
| Posgrado | master's, MBA, doctorate, PhD | posgrado | `educacion-posgrado` |
| Título universitario | bachelor's degree, university degree, four-year college degree, "licenciatura" | bachillerato universitario / licenciatura | `educacion-universitaria` |
| Estudiante avanzado (80 %+) | "X % of completeness of a bachelor's degree program" | estudiante avanzado con la mayoría de los créditos | **falta el escalón** (§4) |
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

## 4. Lo que falta en el motor (pendiente, con su plan)

El motor tiene la escalera de 4 escalones (`1` secundaria, `2` superior de
ciclo corto, `3` universitario, `4` posgrado) y **no tiene el escalón
"estudiante avanzado"**. Efecto actual: un hecho de perfil
`educacion-universitaria` con `education_status='pursuing'` cuenta como
universitario completo → un estudiante avanzado "cumple" un aviso que exige
título (esto contradice **R2**).

Plan (Ola 6 · R1, en `docs/PLAN_MEJORAS.md`):

1. **Escalón nuevo** en `nivel_escala` y en `concepto.nivel_orden`
   (migración de datos nueva, nunca `UPDATE` a mano): `avanzado` entre
   `tecnico` y `universitaria`.
2. **El estado cuenta**: un hecho `pursuing` no confiere título → su nivel
   efectivo es el escalón inferior (un `pursuing` en `educacion-universitaria`
   = escalón "estudiante avanzado"; con el `qualifier` en "% de créditos" se
   puede exigir el 80 % que fija R2).
3. **El aviso con "X % de completitud"** declara el escalón "estudiante
   avanzado", no el universitario (ISCED 2011: el avance parcial no confiere
   título).
4. **Medición obligatoria en copia** antes de tocar la BD real: el cambio no
   debe mover ninguna banda ni ningún estado del corpus; si mueve alguno, se
   revisa caso por caso antes de aplicar la migración.

---

## 5. Los dos casos queabraron esta regla (2026-11-08)

| Caso | Aviso (cita literal) | Escalón que pide | Perfil | Veredicto firmado | Efecto |
|---|---|---|---|---|---|
| `workday-Credit---Collections-Specialist--2_R232432` (Sysco) | «Required Associate’s or bachelor’s degree in business, Finance, or a related field» | `associate` (2) + `bachelor` (3) | diplomado técnico (2) **en Electrónica** (el aviso pide business/Finance) | **`bloqueo_real`** | `descartada` (R5: el nivel se cumple, el campo no) |
| `workday-Production-Supervisor-I_31163511` (Abbott) | «80% completeness of a bachelor’s degree program from a four-year college or university» | estudiante avanzado (3) | diplomado técnico (2), sin hechos "en curso" | **`dudoso`** (sigue abierto) | Falta el **dato** del perfil, no la regla: si se registra "cursando, 80 %+ de los créditos", el motor lo cierra como cumplido; si no, corresponde firmarlo `bloqueo_real` |

Las dos firmas están en `docs/PASO5_FIRMA_EDUCACION.json`, ancladas al sha256
del texto exacto que se leyó (si el aviso se re-raspa y su texto cambia, la
firma deja de aplicar y el caso vuelve a la hoja).

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

### 5.2 Qué haría falta para cerrar Abbott

El aviso pide «80% completeness of a bachelor's degree program» → el escalón
"estudiante avanzado". Para que el perfil lo alcance hace falta **un hecho
educativo en el perfil**:

- `education_status = 'pursuing'`,
- `codigo_canonico` de la licenciatura **en curso** (hoy el perfil no tiene
  ninguno: sus 2 hechos educativos son `completed`),
- y el avance (80 %+ de los créditos) registrado en el `qualifier` del hecho.

Con ese hecho, el motor lo cierra como **cumple**. Sin él, el perfil solo
llega al escalón "diploma técnico" y corresponde firmarlo `bloqueo_real`
(la escalera de la §1 lo dice: el escalón "estudiante avanzado" está **por
encima** del diploma técnico).

> Nota: el motor **todavía no tiene** el escalón "estudiante avanzado" (hoy un
> `pursuing` cuenta como universitario completo) → ver §4 y el plan de
> medición en `docs/PLAN_MEJORAS.md` §6.2.

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
