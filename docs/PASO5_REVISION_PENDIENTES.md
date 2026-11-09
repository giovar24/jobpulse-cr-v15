# Paso 5 — HOJA DE REVISIÓN PENDIENTE (corrida `20261108_175932`)

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
| 2 | 2 | 2 | 0 |

### Decisiones de NEGOCIO que siguen pendientes

Estos casos tienen firma, pero el veredicto es **"dudoso"**: dependen
de una decisión de negocio que todavía NO está tomada (hay que
decidirla **con una fuente**, no por impulso).

- `workday-Credit---Collections-Specialist--2_R232432` — Credit & Collections Specialist: El aviso pide «Required Associate’s or bachelor’s degree in business, Finance, or a related field». Sigue SIN decidir la REGLA DE NEGOCIO #2 (si 2 anos de educacion superior en CR - fuente CONESUP - cuentan como universitario): el veredicto queda DUDOSO y el caso ABIERTO.
- `workday-Production-Supervisor-I_31163511` — Production Supervisor I: El aviso pide «80% completeness of a bachelor’s degree program from a four-year college or university». Sigue SIN decidir la REGLA DE NEGOCIO #3 (si un bachillerato PARCIAL del 80 % cuenta como requisito universitario cumplido): el veredicto queda DUDOSO y el caso ABIERTO.

## Casos a revisar (2)

Columnas de la tabla de firmas: `veredicto` (bloqueo real / no bloqueo /
dudoso), `criterio que lo justifica`, `revisor`, `fecha`.

### 1. `workday-Credit---Collections-Specialist--2_R232432` — Credit & Collections Specialist

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
| dudoso | El aviso pide «Required Associate’s or bachelor’s degree in business, Finance, or a related field». Sigue SIN decidir la REGLA DE NEGOCIO #2 (si 2 anos de educacion superior en CR - fuente CONESUP - cuentan como universitario): el veredicto queda DUDOSO y el caso ABIERTO. | Giovanni Vargas | 2026-11-08 |

**Texto 1 (verbatim):**

> o resolve past-due balances and communicate account status changes Maintain accurate documentation of all collection and credit activities in the system Research and resolve discrepancies such as short pays, deductions, overpayments, and unapplied cash Support credit memo requests and payment arrangements with appropriate approvals Ensure customer master data is accurate and up to date Deliver excellent customer service to both internal and external partners Participate in special projects and additional duties as assigned Required Associate’s or bachelor’s degree in business, Finance, or a related field 1–2 years of experience in B2B credit, collections, or accounts receivable Excellent communication skills in English (B2+ or higher) and ability to collaborate across functions and geographies. Strong attention to detail and analytical skills Excellent verbal and written communication skills Intermediate pr

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='bachelor'` · `requirement_level='required'` · evidencia: > Responsibilities Manage and collect accounts receivable for an assigned portfolio of B2B customers Monitor customer aging and enforce credit terms and limits using ERP and A/R systems (SAP, Esker or similar) Review credit applications and evaluate customer creditworthiness using credit bureaus and references Approve new customer credit limits within assigned authority and prepare recommendations for higher limits Place accounts on credit hold , issue final notices, and recommend escalation to third-party collections when necessary Collaborate closely with Sales Representatives to resolve past-due balances and communicate account status changes Maintain accurate documentation of all collection and credit activities in the system Research and resolve discrepancies such as short pays, deductions, overpayments, and unapplied cash Support credit memo requests and payment arrangements with appropriate approvals Ensure customer master data is accurate and up to date Deliver excellent customer service to both internal and external partners Participate in special projects and additional duties as assigned Required Associate’s or bachelor’s degree in business, Finance, or a related field 1–2 years of experience in B2B credit, collections, or accounts receivable Excellent communication skills in English (B2+ or higher) and ability to collaborate across functions and geographies.

---

### 2. `workday-Production-Supervisor-I_31163511` — Production Supervisor I

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
| dudoso | El aviso pide «80% completeness of a bachelor’s degree program from a four-year college or university». Sigue SIN decidir la REGLA DE NEGOCIO #3 (si un bachillerato PARCIAL del 80 % cuenta como requisito universitario cumplido): el veredicto queda DUDOSO y el caso ABIERTO. | Giovanni Vargas | 2026-11-08 |

**Texto 1 (verbatim):**

> lated information. Build positive, outgoing relations with the other production supervisors in sharing of product, process or equipment related information. Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience. 0-2 years supervisory experience. Preferably in a medical device, pharmaceutical, or electronic industry. Computer skills. . Demonstrated proficiency on manufacturing systems used to collect data and control/monitor processes. , For example SFA, SAP, Kronos, or simil

**Texto 2 (verbatim):**

> d or applicable to medical industry. For example CQE, 6Sigma black belt, lean coach, problem solving techniques, etc. Flexibility to work on different shifts schedule and areas is preferred. Demonstrated capacity to effectively lead/influence peers and other functions towards organizational goals. Basic Command of English. Preferred Qualifications Bachelor’s degree in business administration, Engineering or similar field. Experience leading teams. Knowledge of Costa Rica laws applicable to direct labor operators is a plus. Apply Now Follow your career aspirations to Abbott for diverse opportunities with a company that can help you build your future and live your best life. Abbott is an Equal Opportunity Empl

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='preferred'` · evidencia: > Preferred Qualifications Bachelor’s degree in business administration, Engineering or similar field.
- `value_text='bachelor'` · `requirement_level='required'` · evidencia: > Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience.

---
