# Paso 5 — HOJA DE REVISIÓN PENDIENTE (corrida `20261110_210220`)

> Documento GENERADO por `generar_revision_pendientes.py` — los textos
> son **literales de la BD**; el veredicto es el de la **segunda
> persona** que firmó la tabla de decisiones del Paso 7
> (`job_match_decision`).
> Estado de estos casos: **ABIERTOS** (el motor no pudo decidirlos).

## Para quién es este documento

Esta hoja lista los casos que el MOTOR no pudo decidir (quedan en
`revisar_a_mano / educacion_no_confirmada`). La revisión previa de estos
casos la hizo **el autor de la regla**, por eso su veredicto ("ninguna
bloquea") se **descarta**: no es una segunda opinión.

Quien firma lo registra en la tabla `job_match_decision` (Paso 7), que
queda anclada al **sha256 del texto exacto que leyó**: si el aviso se vuelve
a raspar y su texto cambia, la firma deja de aplicar y el caso vuelve a
esta hoja. Un veredicto "dudoso" NO cierra el caso: sigue abierto hasta
que se decida la cuestión de NEGOCIO que lo bloquea (con una fuente).

## Estado de la revisión

| casos abiertos | con firma | firmados "dudoso" (siguen abiertos) | sin firma |
|---|---|---|---|
| 1 | 1 | 1 | 0 |

### Decisiones de NEGOCIO que siguen pendientes

Estos casos tienen firma, pero el veredicto es **"dudoso"**: dependen
de una decisión de negocio que todavía NO está tomada (hay que
decidirla **con una fuente**, no por impulso).

- `workday-Production-Supervisor-I_31163511` — Production Supervisor I: El aviso pide «80% completeness of a bachelor’s degree program from a four-year college or university». REGLA DE NEGOCIO YA DECIDIDA (2026-11-08; ver docs/REGLAS_NEGOCIO_EDUCACION.md): «80%» es el escalon 'estudiante sin graduar con la mayoria de los creditos completados (80% o mas)', que va POR DEBAJO del titulo universitario y por encima del diploma tecnico (fuente: U.S. Department of State - InfoUSA, Structure of U.S. Education). Lo que falta ya no es la regla sino el DATO del perfil: no hay ningun hecho educativo 'en curso' registrado, asi que no se puede afirmar que el perfil alcance ese escalon. El veredicto queda DUDOSO y el caso ABIERTO: si se registra ese hecho, el motor lo cierra como cumplido; si no, corresponde firmarlo como bloqueo real.

## Casos a revisar (1)

Columnas de la tabla de firmas: `veredicto` (bloqueo real / no bloqueo /
dudoso), `criterio que lo justifica`, `revisor`, `fecha`.

### 1. `workday-Production-Supervisor-I_31163511` — Production Supervisor I

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
| dudoso | El aviso pide «80% completeness of a bachelor’s degree program from a four-year college or university». REGLA DE NEGOCIO YA DECIDIDA (2026-11-08; ver docs/REGLAS_NEGOCIO_EDUCACION.md): «80%» es el escalon 'estudiante sin graduar con la mayoria de los creditos completados (80% o mas)', que va POR DEBAJO del titulo universitario y por encima del diploma tecnico (fuente: U.S. Department of State - InfoUSA, Structure of U.S. Education). Lo que falta ya no es la regla sino el DATO del perfil: no hay ningun hecho educativo 'en curso' registrado, asi que no se puede afirmar que el perfil alcance ese escalon. El veredicto queda DUDOSO y el caso ABIERTO: si se registra ese hecho, el motor lo cierra como cumplido; si no, corresponde firmarlo como bloqueo real. | Giovanni Vargas | 2026-11-08 |

**Texto 1 (verbatim):**

> lated information. Build positive, outgoing relations with the other production supervisors in sharing of product, process or equipment related information. Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience. 0-2 years supervisory experience. Preferably in a medical device, pharmaceutical, or electronic industry. Computer skills. . Demonstrated proficiency on manufacturing systems used to collect data and control/monitor processes. , For example SFA, SAP, Kronos, or simil

**Texto 2 (verbatim):**

> d or applicable to medical industry. For example CQE, 6Sigma black belt, lean coach, problem solving techniques, etc. Flexibility to work on different shifts schedule and areas is preferred. Demonstrated capacity to effectively lead/influence peers and other functions towards organizational goals. Basic Command of English. Preferred Qualifications Bachelor’s degree in business administration, Engineering or similar field. Experience leading teams. Knowledge of Costa Rica laws applicable to direct labor operators is a plus. Apply Now Follow your career aspirations to Abbott for diverse opportunities with a company that can help you build your future and live your best life. Abbott is an Equal Opportunity Empl

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='preferred'` · evidencia: > Preferred Qualifications Bachelor’s degree in business administration, Engineering or similar field.
- `value_text='bachelor'` · `requirement_level='required'` · evidencia: > Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience.

---
