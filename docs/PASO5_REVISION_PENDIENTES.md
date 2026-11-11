# Paso 5 — HOJA DE REVISIÓN PENDIENTE (corrida `20261111_074200`)

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
| 0 | 0 | 0 | 0 |

## Casos a revisar (0)

Columnas de la tabla de firmas: `veredicto` (bloqueo real / no bloqueo /
dudoso), `criterio que lo justifica`, `revisor`, `fecha`.
