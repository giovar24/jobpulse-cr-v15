# Paso 5 — Evidencia del bloqueante educativo (corrida `20261108_214123`)

> Documento GENERADO por `generar_evidencia_paso5.py` (no editado a mano).
> Todo el texto citado es **literal** de `jobs.requirements_raw` +
> `jobs.description_raw`. Regla: `descartada` solo si el TEXTO confirma un
> título universitario **obligatorio**, **sin negación y sin alternativa**;
> si el texto no lo confirma → `revisar_a_mano` (`educacion_no_confirmada`).

## 1. Criterio aplicado

- **La obligatoriedad la decide el TEXTO**, no solo `requirement_level`:
  si la cláusula exige el título ("Required Qualifications", "Minimum
  Qualifications", "Basic Qualifications", "must have", "degree or
  above", "Requisitos", "Job Requirements:", "Role Requirements",
  "Further requirements", "What you need to bring", "Education &
  Experience", "Formación:") bloquea aunque el extractor lo marque
  `ambiguous`/`inferred`. Si el texto solo lo prefiere ("Preferred") NO
  bloquea.
- **Negación** → no se descarta ("No university degree required.").
- **Alternativa** → no se descarta ("or equivalent experience", "Associate's
  or bachelor's degree", "or advanced university studies", "alternatively,
  3+ years of relevant professional experience").
- **Excepción**: "or equivalent field of study / discipline / degree" NO es
  una vía alternativa: sigue exigiendo un título universitario.
- **Alcance por grupo**: la negación, el suavizador y la obligatoriedad se
  aplican al **grupo** de títulos unidos por enumeración, no a la cláusula
  completa. Así "Bachelor's/University degree, Master's degree preferred"
  EXIGE el bachelor's (la coma corta el alcance del "preferred") pero
  "Bachelor's or Master's degree preferred" NO exige ninguno de los dos.
- **Estudiante activo** ("currently pursuing", "must be enrolled", "active
  university student") es un criterio DISTINTO del título completado →
  motivo `titulo_universitario_en_curso_requerido`.
- **Semántica de la AUSENCIA del fact `pursuing`** (decidida 2026-10-29):
  - el perfil registra hechos educativos y NINGUNO dice `pursuing` → se
    sabe que la persona NO está registrada como estudiante activo →
    **no cumple** → la vacante se descarta con el motivo
    `titulo_universitario_en_curso_requerido`;
  - el perfil NO registra NINGÚN hecho educativo → la dimensión educativa
    **no es verificable** → nunca se descarta por falta de información: la
    vacante va a `revisar_a_mano` con el motivo
    `educacion_no_verificable`.

### 1.1. Mecánicas GENERALES (decididas 2026-10-30)

Las reglas son **generales**: el nivel lo declara el TEXTO de la oferta y
el perfil se compara contra ese nivel. Nada depende de quién sea la
persona: si cambia el perfil (sus hechos educativos), cambian los
resultados sin tocar el código.

- **M1 — El nivel lo declara el TEXTO, no el código canónico.** La escalera
  es general (tipo ISCED): 1 secundaria · 2 superior de ciclo corto ·
  3 universitario · 4 posgrado. El ancla es la evidencia literal del
  requisito (`job_requirements.evidence`) y gana la frase más larga que
  cubre al término: "Two year college degree" → 2 (aunque dentro diga
  "college degree"), "Bachelor's degree" → 3, "Master's degree" → 4,
  "Associate's degree" → 2, "High School Diploma" → 1. Un aviso del
  extranjero se lee con SU vocabulario (no hay equivalencias por país).
- **M2 — Una vía alternativa ACADÉMICA está o no DISPONIBLE** para el
  perfil: se compara el nivel que declara la vía con el nivel de estudios
  del perfil. "or advanced university studies" → posgrado (4);
  "or advanced/university coursework" → universitario (3);
  "or technical degree" / "or associate's degree" → ciclo corto (2).
  Si hay una vía disponible → no bloquea; si TODAS las vías son de nivel
  superior al del perfil → la vía no rescata y el título principal sigue
  exigiéndose → `descartada`. Las vías por **experiencia** ("or
  equivalent experience") NO son evaluables → nunca confirman un
  descarte (conservador).
- **M3 — Estudios universitarios PARCIALES** ("80% completeness of a
  bachelor's degree program") = nivel 3 **sin título**: lo cumplen el
  título universitario o los estudios universitarios en curso. Un
  porcentaje de completitud no confiere título (ISCED 2011:
  "partial level completion" es subcategoría de nivel, no cualificación).
- **M4 — Sin lógica por país:** el perfil y las vacantes se comparan en la
  misma escalera; el nivel vive en `candidate_profile_facts` + `concepto`
  (datos), nunca en el código.

**Fuentes de las 3 decisiones de negocio** (generales, no de Costa Rica):

1. `"or advanced university studies"` (posgrado) solo desbloquea a quien
   tiene estudios universitarios: ISCED 2011/OECD — los programas de
   posgrado *require at least two years at ISCED level 6 prior to
   entrance (although most require a four-year Bachelor's degree)*; la
   UCR/SEP exige títulos previos para admitir en posgrado.
2. `"two year college degree"` / `"associate degree"` = nivel 2: ISCED
   2011/OECD — *Programmes classified at ISCED level 5 may be referred to
   in many ways: higher technical education, community college education,
   technician or advanced/higher vocational training, **associate degree**,
   bac+2*; el bachelor es el nivel 6.
3. `"X % de un bachelor's degree program"` = estudios parciales: ISCED
   2011 — *individual credits awarded for successful completion of
   individual courses are not considered as qualifications*.

## 2. Trazabilidad de corridas (`job_match`)

```
corrida          filas  valida=1
20261107_225916  735    0
20261108_131343  735    0
20261108_175932  735    0
20261108_213837  735    0
20261108_214123  735    735
```

## 3. Conteo por estado y motivo (corrida vigente `20261108_214123`)

```
calificada             | cumple_umbral                          | 202
datos_insuficientes    | cobertura_insuficiente                 | 30
datos_insuficientes    | educacion_no_cumple                    | 2
datos_insuficientes    | skill_faltante                         | 4
descartada             | titulo_universitario_en_curso_requerido | 23
descartada             | titulo_universitario_requerido         | 77
revisar_a_mano         | educacion_no_confirmada                | 1
revisar_a_mano         | educacion_no_cumple                    | 79
revisar_a_mano         | experiencia_no_verificable             | 3
revisar_a_mano         | idioma_no_comparable                   | 1
revisar_a_mano         | skill_faltante                         | 302
sin_requisitos         | sin_requisitos_mapeados                | 11
```

## 4. Las 100 `descartada` — evidencia literal

### 1. `ane-122048` — Ingeniero Civil

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Nivel académico: Licenciatura (Requerido).

> Nivel académico: Licenciatura (Requerido).
>
> contexto: ...torio nacional.. Habilidades importantes a tener en cuenta: Adaptabilidad, Disposición, Enfoque a resultados, Liderazgo, Orientación a la calidad, Profesionalismo, Trabajo en equipo. Nivel académico: Licenciatura (Requerido). Experiencia laboral: De 1 a menos de 12 meses (Requerido) Inspección de obras civiles en concreto y acero. Inspección de obras de infraestructura habitacional y comercial. Mantenimiento...

### 2. `ane-122056` — Gestor/a en Soporte Tecnológico

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Nivel académico: Licenciatura (Requerido).

> Nivel académico: Licenciatura (Requerido).
>
> contexto: ...ogramas de cómputo: SQL Server - MEDIO (Requerido), Visual Basic/Visual Basic.net - MEDIO (Requerido), C/C++ V.3/Borlan C++ V.5/C#.net - MEDIO (Requerido). Licencias de conducir: B1. Nivel académico: Licenciatura (Requerido). Experiencia laboral: De 2 a menos de 5 años (Requerido) Ejecutar labores estratégicas y especializadas de diseño, arquitectura, administración, optimización, seguridad, continuidad opera...

### 3. `ane-122063` — Coordinador Servicio Ciudadano

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Nivel académico: Licenciatura (Requerido).

> Nivel académico: Licenciatura (Requerido).
>
> contexto: ...9-1-1 Cualquier consulta comunicarse mediante correo electrónico gfajardo@911.go.cr o vía telefónica al 2225-2723 con la funcionaria Gidget Fajardo Vargas. Licencias de conducir: B1. Nivel académico: Licenciatura (Requerido). Experiencia laboral: De 5 a menos de 10 años (Requerido). Estudio técnico: Técnico universitario Coordinar tácticamente la operación del Proceso de Servicio Ciudadano mediante la supervi...

### 4. `ane-122085` — Contador Auxiliar

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Nivel académico: Licenciatura (Requerido).

> Nivel académico: Licenciatura (Requerido).
>
> contexto: ...r en cuenta: Adaptabilidad, Aprendizaje permanente, Comunicación asertiva, Disposición, Enfoque a resultados, Liderazgo, Orientación a la calidad, Profesionalismo, Trabajo en equipo. Nivel académico: Licenciatura (Requerido). Experiencia laboral: De 2 a menos de 5 años (Requerido). Estudio técnico: Diplomado universitario Funciones principales • Controlar cuentas por cobrar y dar seguimiento a facturas y cobr...

### 5. `ashby-greenlight-workforce-solutions-204564b1-633d-4e73-845e-ba9cc0a7d9f1` — Senior Accountant

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Qualifications Bachelor’s degree in Accounting.

> Qualifications Bachelor’s degree in Accounting.
>
> contexto: ...ssigned control activities. Identify opportunities to improve, standardize, and automate close procedures. Assist with special projects and other accounting responsibilities as needed. Qualifications Bachelor’s degree in Accounting. 3–5 years of progressive accounting experience, preferably including significant general ledger and month-end close responsibilities. Strong knowledge of U.S. GAAP and accountin...

### 6. `cinde-4887` — Engineering Consultant Apprentice- TMV execution - Medical Device #2612

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachillerato universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachillerato universitario'` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Formación: Bachillerato universitario incompleto.

> Formación: Bachillerato universitario incompleto.
>
> contexto: ...Categoría: Calidad. Nivel: Profesional Jr.. Experiencia: de 1 a 2 años. Formación: Bachillerato universitario incompleto. Idiomas: Inglés-B2+. Modalidad: Presencial What you'll do Support Stack Analysis Support the design of plastic parts in SolidWorks. Support the development of Test Methods: Protocols gene...

### 7. `cinde-4888` — IT Software Developer II

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachillerato universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachillerato universitario'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Formación: Bachillerato universitario completo.
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What We're Looking For Required Qualifications Bachelor's degree in Computer Science, Software Engineering, Information Technology, or a related field, or equivalent practical experience.

> Formación: Bachillerato universitario completo.
>
> contexto: ...Categoría: Desarrollo Web. Nivel: Profesional. Experiencia: de 3 a 5 años. Formación: Bachillerato universitario completo. Idiomas: Inglés-B2. Modalidad: 100% virtual Software Engineer – Platform Automation & Integrations Location: San José, Costa Rica (Hybrid) About the Role We are looking for a highly motivat...

### 8. `cinde-4889` — IT Systems Engineer II

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachillerato universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Education: Bachelor’s degree in Computer Science, Information Technology, or a related field.
  - `value_text='Bachillerato universitario'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Formación: Bachillerato universitario completo.

> Formación: Bachillerato universitario completo.
>
> contexto: ...Categoría: Soporte Técnico. Nivel: Profesional. Experiencia: de 3 a 5 años. Formación: Bachillerato universitario completo. Idiomas: Inglés-B2. Modalidad: 100% virtual IT SYSTEMS ENGINEER II JOB DESCRIPTION – APPSTERS World Fuel is a global energy management and solutions provider delivering fuel, logistics, and...

### 9. `cinde-4890` — Cloud Engineer III

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachillerato universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachillerato universitario'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Formación: Bachillerato universitario completo.

> Formación: Bachillerato universitario completo.
>
> contexto: ...Categoría: Soporte Técnico. Nivel: Profesional Sr.. Experiencia: de 5 a 8 años. Formación: Bachillerato universitario completo. Idiomas: Inglés-B2. Modalidad: 100% virtual AWS FinOps Engineer III Job Description At World Fuel Services, our employees are key to our global success. We are industry leaders because of t...

### 10. `cinde-4892` — AI Finance Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachillerato universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Currently pursuing a Bachelor’s degree in one of the following (or related fields): o	Computer Science o	Software Engineering o	Data Science o	Data Analytics o	Computer Engineering o	Artificial Intelligence o	Information Systems o	Industrial Engineering (with strong analytics focus) Intermediate to Advanced English Strong analytical and problem-solving skills.
  - `value_text='Bachillerato universitario'` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Formación: Bachillerato universitario incompleto.

> Formación: Bachillerato universitario incompleto.
>
> contexto: ...Categoría: Finanzas / Análisis Financiero. Nivel: Otro. Experiencia: sin experiencia. Formación: Bachillerato universitario incompleto. Idiomas: Inglés-B2+. Modalidad: 100% virtual We are looking for highly motivated university students in Costa Rica who are passionate about Artificial Intelligence, Data Analytics, and pr...

### 11. `cinde-4896` — Lead Data Engineer

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachillerato universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachillerato universitario'` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Formación: Bachillerato universitario incompleto.

> Formación: Bachillerato universitario incompleto.
>
> contexto: ...Categoría: Informática / Sistemas. Nivel: Profesional. Experiencia: de 3 a 5 años. Formación: Bachillerato universitario incompleto. Idiomas: Inglés-B2. Modalidad: Híbrido. Vacantes: 3 We are looking for a Lead Data Engineer who will be responsible for defining data engineering standards, building reusable patterns, me...

### 12. `cinde-4897` — Full Stack Lead Engineer

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachillerato universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachillerato universitario'` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Formación: Bachillerato universitario incompleto.

> Formación: Bachillerato universitario incompleto.
>
> contexto: ...Categoría: Informática / Sistemas. Nivel: Profesional. Experiencia: de 3 a 5 años. Formación: Bachillerato universitario incompleto. Idiomas: Inglés-B2. Modalidad: Híbrido. Vacantes: 5 We are seeking an experienced Full Stack Lead Engineer to drive engineering excellence, mentor technical talent, and support the delive...

### 13. `cinde-4898` — Lead Software Engineer

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Formación: Licenciatura.

> Formación: Licenciatura.
>
> contexto: ...Categoría: Diseño de Software. Nivel: Supervisores/Líderes de Equipo. Experiencia: de 5 a 8 años. Formación: Licenciatura. Idiomas: Inglés-C1;Español-C2. Modalidad: Híbrido We are looking for an experienced Lead Software Engineer / Chapter Lead who combines strong hands-on technical expertise with engineering leadership...

### 14. `cinde-4901` — Regulatory Affairs Specialist

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachillerato universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Perform other duties as assigned ESSENCIAL QUALIFICATIONS Bachelor's degree in Engineering (e.g., Industrial, Biomedical, or Chemical), Biotechnology, Chemistry, or a related scientific or technical discipline.
  - `value_text='Bachillerato universitario'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Formación: Bachillerato universitario completo.

> Formación: Bachillerato universitario completo.
>
> contexto: ...Categoría: Calidad. Nivel: Profesional. Experiencia: de 1 a 2 años. Formación: Bachillerato universitario completo. Idiomas: Inglés-B2+. Modalidad: Presencial POSITION SUMMARY: The Regulatory Affairs Specialist I is an entry-level member of LifeSync's Global Quality & Regulatory Affairs organization, bas...

### 15. `elempleo-879447` — Gestor de riesgos (unidad modelos matematicos y metodologias de riesgo)

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Requisitos: -Licenciatura Universitaria (Incorporado al Colegio Profesional respectivo) o Bachillerato Universitario con Maestría e incorporado al Colegio de Profesionales respectivo.

> Requisitos: -Licenciatura Universitaria (Incorporado al Colegio Profesional respectivo) o Bachillerato Universitario con Maestría e incorporado al Colegio de Profesionales respectivo.
>
> contexto: ...elos, metodologías, técnicas y herramientas relacionadas a la gestión del riesgo, con el fin de apoyar al área en el fortalecimiento del Sistema de Gestión Integral del Riesgo del CFBCR. Requisitos: -Licenciatura Universitaria (Incorporado al Colegio Profesional respectivo) o Bachillerato Universitario con Maestría e incorporado al Colegio de Profesionales respectivo. -Experiencia en puestos profesionales. Ma...

### 16. `elempleo-880226` — Desarrollador(a) fullstack (react / java quarkus)

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachillerato universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachillerato universitario'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Requisitos: Bachillerato universitario en Ingeniería en Sistemas, Informática, Ingeniería de Software o carrera afín.

> Requisitos: Bachillerato universitario en Ingeniería en Sistemas, Informática, Ingeniería de Software o carrera afín.
>
> contexto: ...ítico, iniciativa y pasión por la tecnología, interesada en desarrollar aplicaciones web e integraciones que conecten nuestros sistemas con entidades bancarias y plataformas de servicios. Requisitos: Bachillerato universitario en Ingeniería en Sistemas, Informática, Ingeniería de Software o carrera afín. Al menos 2 años de experiencia en desarrollo de software, preferiblemente Fullstack. Conocimientos en React, Java, JavaS...

### 17. `elempleo-880266` — Analista de proveeduría - interno

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Misión del Puesto: Gestionar los procesos operativos asociados a las diversas contrataciones que se realizan, con el propósito de brindar un servicio eficiente y de calidad a los clientes internos y externos de INS Servicios SA Requisitos Indispensables: Título de Bachillerato en Administración de empresas, carrera afín a las ciencias económicas o Licenciatura en Derecho.

> Misión del Puesto: Gestionar los procesos operativos asociados a las diversas contrataciones que se realizan, con el propósito de brindar un servicio eficiente y de calidad a los clientes internos y externos de INS Servicios SA Requisitos Indispensables: Título de Bachillerato en Administración de empresas, carrera afín a las ciencias económicas o Licenciatura en Derecho.
>
> contexto: ...eficiente y de calidad a los clientes internos y externos de INS Servicios SA Requisitos Indispensables: Título de Bachillerato en Administración de empresas, carrera afín a las ciencias económicas o Licenciatura en Derecho. Conocimiento intermedio en la aplicación de paquetes office (Word y Excel) Incorporado al Colegio Profesional respectivo De 2 a 3 años de experiencia en Contratación Pública. (LGCP y su R...

### 18. `elempleo-880270` — System design engineer

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > - Provide technical leadership on a cross-functional engineering team - Define and analyze system requirements, clinical workflows, and input/output processes by using systems engineering methods and techniques - Apply critical thinking to solve systems integration problems and make recommendations - Utilize architecture design tools to develop and document system-level interactions - Create design documentation such as requirements rationale, requirements tracing, system change analysis within our quality system - Writing reports for and working with internal regulatory team to satisfy the requirements for external regulatory agencies - Apply project management principles to plan, track, execute, and report status of projects within a range of team sizes - Support system risk management activities, such as FMEA’s and risk/hazard analysis -Requirements- Education: Bachelor’s degree or higher in Electrical Engineering, Computer Engineering, Electromechanical Engineering, Systems Engineering, Computer Science, or related field.

> ...ples to plan, track, execute, and report status of projects within a range of team sizes - Support system risk management activities, such as FMEA’s and risk/hazard analysis -Requirements- Education: Bachelor’s degree or higher in Electrical Engineering, Computer Engineering, Electromechanical Engineering, Systems Engineering, Computer Science, or related field....
>
> contexto: ...ples to plan, track, execute, and report status of projects within a range of team sizes - Support system risk management activities, such as FMEA’s and risk/hazard analysis -Requirements- Education: Bachelor’s degree or higher in Electrical Engineering, Computer Engineering, Electromechanical Engineering, Systems Engineering, Computer Science, or related field. Experience: 3+ years of experience in similar...

### 19. `elempleo-880274` — Senior recruiter

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Requirements: Education: *Bachelor's degree in Business Administration with an emphasis in Human Resources or similar Experience: *Minimum of 5 years of experience in senior-level recruitment positions.

> Requirements: Education: *Bachelor's degree in Business Administration with an emphasis in Human Resources or similar Experience: *Minimum of 5 years of experience in senior-level recruitment positions.
>
> contexto: ...have strong sourcing, interviewing, and stakeholder management skills, with a proven ability to fill positions efficiently while ensuring an excellent candidate experience. Requirements: Education: *Bachelor's degree in Business Administration with an emphasis in Human Resources or similar Experience: *Minimum of 5 years of experience in senior-level recruitment positions. *Previous experience recruiting a...

### 20. `greenhouse-smartsheet-8273999` — Content Designer II (Remote Eligible - Costa Rica)

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Education: Bachelor’s degree in a related field Support other duties as assigned Perks & Benefits: Fully paid Health & Life insurance for full-time employees and family members Monthly stipend to support your work and productivity 12 days paid Vacation + Flexible Time Away Program 20 weeks fully paid Maternity Leave 12 weeks fully paid Paternity/Adoption Leave Personal paid Volunteer Day to support our community Opportunities for professional growth and development including access to LinkedIn Learning online courses Company Funded Perks including a counseling membership and your own personal Smartsheet account Teleworking options from any registered location in Costa Rica (role specific) Get to Know Us: At Smartsheet, your ideas are heard, your potential is supported, and your contributions have real impact.

> ...Education: Bachelor’s degree in a related field Support other duties as assigned Perks & Benefits: Fully paid Health & Life insurance for full-time employees and family members Monthly stipend to support your wo...
>
> contexto: ...a track record of using research to inform content decisions. Communication: Excellent collaboration skills and the ability to champion the "why" behind content decisions to stakeholders. Education: Bachelor’s degree in a related field Support other duties as assigned Perks & Benefits: Fully paid Health & Life insurance for full-time employees and family members Monthly stipend to support your work and pro...

### 21. `harvie-4463` — Líder de Iniciativas Comerciales de Repuestos Automotrices

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Requisitos Indispensables: Licenciatura en Administración de Empresas o Ingeniería Industrial.

> Requisitos Indispensables: Licenciatura en Administración de Empresas o Ingeniería Industrial.
>
> contexto: ...iniciativas Impulsar la mejora continua de los procesos comerciales del negocio de repuestos, promoviendo mejores prácticas, innovación y el uso de herramientas analíticas. Requisitos Indispensables: Licenciatura en Administración de Empresas o Ingeniería Industrial. Conocimiento certificado en SQL, VBA y Power BI. Nivel de inglés 85% . Experiencia: Al menos 2 años en áreas comerciales. Al menos 2 años en neg...

### 22. `harvie-5872` — Ingeniero (a) de Procesos Jr

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Requisitos Indispensables: Licenciatura en Ingeniería Industrial.

> Requisitos Indispensables: Licenciatura en Ingeniería Industrial.
>
> contexto: ...ilizando metodologías de uso ingenieril y filosofía Toyota , apoyándose en el uso de software como Microsoft visio o power BI para el manejo y extracción de la información. Requisitos Indispensables: Licenciatura en Ingeniería Industrial. Certificación Scrum Master. Inglés Intermedio. Licencia de conducir B1. Certificación en Administración de Proyectos: CAPM, PMP, o afines (deseable). Experiencia: 1+ años en...

### 23. `harvie-6147` — Product Manager Digital

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachillerato Universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachillerato Universitario'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Requisitos indispensables: Bachillerato Universitario en Contaduría Pública, Finanzas, Administración de Empresas, Administración de Proyectos, Ingenierías, Logística, o áreas afines.

> Requisitos indispensables: Bachillerato Universitario en Contaduría Pública, Finanzas, Administración de Empresas, Administración de Proyectos, Ingenierías, Logística, o áreas afines.
>
> contexto: ...mejora del ERP: Liderar la planificación, ejecución y adopción de nuevas capacidades del ERP, coordinando implementadores, socios tecnológicos y usuarios clave (key users). Requisitos indispensables: Bachillerato Universitario en Contaduría Pública, Finanzas, Administración de Empresas, Administración de Proyectos, Ingenierías, Logística, o áreas afines. Se valorará formación complementaria en finanzas, contabilidad, caden...

### 24. `harvie-6476` — C-077 Negociador Comercial IV (Gerente Administrativo Centro de Control Fronterizo Peñas Blancas)

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Requisitos 🎓Formación Académica Licenciatura universitaria en Derecho, Economía, Administración de Empresas, Aduanera, Comercio Internacional, Relaciones Internacionales, Agronomía, Economía Agrícola, Ciencias Políticas, Ingenierías o carrera afín.

> Requisitos 🎓Formación Académica Licenciatura universitaria en Derecho, Economía, Administración de Empresas, Aduanera, Comercio Internacional, Relaciones Internacionales, Agronomía, Economía Agrícola, Ciencias Políticas, Ingenierías o carrera afín.
>
> contexto: ...e iniciativas de alto impacto. 👤Perfil que buscamos Visión estratégica y capacidad de liderazgo para gestionar negociaciones comerciales internacionales de alto nivel. Requisitos 🎓Formación Académica Licenciatura universitaria en Derecho, Economía, Administración de Empresas, Aduanera, Comercio Internacional, Relaciones Internacionales, Agronomía, Economía Agrícola, Ciencias Políticas, Ingenierías o carrera a...

### 25. `harvie-6508` — Analista Operativo de Carrocería

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Requisitos indispensables: Licenciatura en Ingeniería Industrial, Administración de Empresas, Contaduría o carreras afines Conocimientos avanzados de Excel y manejo de Bases de Datos, Power BI.

> Requisitos indispensables: Licenciatura en Ingeniería Industrial, Administración de Empresas, Contaduría o carreras afines Conocimientos avanzados de Excel y manejo de Bases de Datos, Power BI.
>
> contexto: ...ientales significativos pertinentes a su área de trabajo, implementando los ajustes, mejoras y disposiciones según corresponda. Ejecutar otras funciones propias del puesto. Requisitos indispensables: Licenciatura en Ingeniería Industrial, Administración de Empresas, Contaduría o carreras afines Conocimientos avanzados de Excel y manejo de Bases de Datos, Power BI. Con buenas bases sobre procesos analíticos y...

### 26. `indeed-25f9df220ed96621` — Soporte Técnico de Sitio (Presencial - Coyol)

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'bachillerato universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='bachillerato universitario'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Formación: Certificado de colegio técnico profesional o bachillerato universitario avanzado en tecnologías de la información o carreras afines.

> Formación: Certificado de colegio técnico profesional o bachillerato universitario avanzado en tecnologías de la información o carreras afines.
>
> contexto: ...en soporte técnico en campo. Experiencia en manejo y control de inventarios TI. Experiencia en servicio al cliente y atención a usuario final. Formación: Certificado de colegio técnico profesional o bachillerato universitario avanzado en tecnologías de la información o carreras afines. Requisito indispensable: Licencia de Conducir B1 con 2 años de emisión. Maneja de herramientas ITSM y metodología ITIL para la gestión de...

### 27. `recruitee-primeworks-2683696` — Hospitality/Hotel Sales Representative

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor degree'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Bachelor degree Previous experience in hospitality or hotel-related sales is required.

> Bachelor degree Previous experience in hospitality or hotel-related sales is required.
>
> contexto: ...service and meet client expectations. Maintain accurate customer records and follow up on sales opportunities. Identify opportunities to improve the customer experience and increase client retention. Bachelor degree Previous experience in hospitality or hotel-related sales is required. Proven experience in customer support or customer service. Fluent English (spoken and written). Strong communication, int...

### 28. `recruitee-transperfect-2786154` — Freelance Long-Term EN > Traditional Chinese (TW) Life Science translator

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'college degree'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 2 years of translation experience and a college degree;
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 5 years of translation experience and no college degree;

> 2 years of translation experience and a college degree
>
> contexto: ...on, Linguistics, or Language Studies or an equivalent degree that includes significant translation training, from a recognized institution of higher education; 2 years of translation experience and a college degree; 5 years of translation experience and no college degree; or A certificate of competence in translation awarded by an appropriate government body....

### 29. `recruitee-transperfect-2794764` — Freelance Full-Time English into Simplified Chinese (China) CTD Module Language Lead

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'college degree'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Have 2 years of professional translation experience plus a college degree;
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Have 5 years of professional translation experience without a college degree;
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 2 years of translation experience and a college degree;
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 5 years of translation experience and no college degree;

> 2 years of translation experience and a college degree
>
> contexto: ...in Translation, Linguistics, Language Studies, or an equivalent program with significant translation training from a recognized university; Have 2 years of professional translation experience plus a college degree; Have 5 years of professional translation experience without a college degree; OR Possess a translation competence certificate issued by an appropriate government authority. Preferred Experience Acad...

### 30. `recruitee-transperfect-2798207` — Freelance English into Simplified Chinese (Singapore) Legal and Insurance Translator

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'college degree'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 2 years of translation experience and a college degree;
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 5 years of translation experience and no college degree;

> 2 years of translation experience and a college degree
>
> contexto: ...on, Linguistics, or Language Studies or an equivalent degree that includes significant translation training, from a recognized institution of higher education; 2 years of translation experience and a college degree; 5 years of translation experience and no college degree; or A certificate of competence in translation awarded by an appropriate government body....

### 31. `recruitee-transperfect-2801676` — Freelance English into Simplified Chinese (Singapore) Legal and Insurance Translator

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'college degree'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 2 years of translation experience and a college degree;
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 5 years of translation experience and no college degree;

> 2 years of translation experience and a college degree
>
> contexto: ...on, Linguistics, or Language Studies or an equivalent degree that includes significant translation training, from a recognized institution of higher education; 2 years of translation experience and a college degree; 5 years of translation experience and no college degree; or A certificate of competence in translation awarded by an appropriate government body....

### 32. `recruitee-transperfect-2803321` — Freelance English into Traditional Chinese (Taiwan) Clinical Legal Translator

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'college degree'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 2 years of translation experience and a college degree;
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 5 years of translation experience and no college degree;

> 2 years of translation experience and a college degree
>
> contexto: ...on, Linguistics, or Language Studies or an equivalent degree that includes significant translation training, from a recognized institution of higher education; 2 years of translation experience and a college degree; 5 years of translation experience and no college degree; or A certificate of competence in translation awarded by an appropriate government body....

### 33. `recruitee-transperfect-2815962` — Freelance English into Traditional Chinese (Taiwan) Investment Banking Translator

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'college degree'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 2 years of translation experience and a college degree;
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 5 years of translation experience and no college degree;

> 2 years of translation experience and a college degree
>
> contexto: ...on, Linguistics, or Language Studies or an equivalent degree that includes significant translation training, from a recognized institution of higher education; 2 years of translation experience and a college degree; 5 years of translation experience and no college degree; or A certificate of competence in translation awarded by an appropriate government body....

### 34. `recruitee-transperfect-2815963` — Freelance Traditional Chinese (Taiwan) into English Investment Banking Translator

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'college degree'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 2 years of translation experience and a college degree;
  - `value_text='college degree'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 5 years of translation experience and no college degree;

> 2 years of translation experience and a college degree
>
> contexto: ...on, Linguistics, or Language Studies or an equivalent degree that includes significant translation training, from a recognized institution of higher education; 2 years of translation experience and a college degree; 5 years of translation experience and no college degree; or A certificate of competence in translation awarded by an appropriate government body....

### 35. `workday-Accounting-Analyst---Temporary_J-020392` — Accounting Analyst – Temporary

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `alternativa` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications Bachelor’s degree in Accounting, Finance, or a related field , or advanced university studies in Accounting.

> Minimum Qualifications Bachelor’s degree in Accounting, Finance, or a related field , or advanced university studies in Accounting.
>
> contexto: ...ork at our office in AFZ, Heredia, on Mondays, Wednesdays, and Thursdays. Please note that additional office days may occasionally be required based on specific business needs. Minimum Qualifications Bachelor’s degree in Accounting, Finance, or a related field , or advanced university studies in Accounting. Minimum of 2 years of professional accounting experience. Practical knowledge of core accounting prin...

### 36. `workday-Accounting-Team-Lead_J-020415` — Accounting Team Lead

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications Bachelor Accounting Degree required 7+ years of accounting experience 2+ years of supervisory or people leadership experience Advanced English Skills and knowledge Strong analytical skills Proficient with MS Excel.

> Minimum Qualifications Bachelor Accounting Degree required 7+ years of accounting experience 2+ years of supervisory or people leadership experience Advanced English Skills and knowledge Strong analytical skills Proficient with MS Excel.
>
> contexto: ...ur office in AFZ, Heredia on Mondays, Wednesdays, and Thursdays. Please note that there may be occasions where additional office days are required, due specific business needs. Minimum Qualifications Bachelor Accounting Degree required 7+ years of accounting experience 2+ years of supervisory or people leadership experience Advanced English Skills and knowledge Strong analytical skills Proficient with MS...

### 37. `workday-Analyst--Compensation_Req-51280` — Analyst, Compensation

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What You'll Need (Required): Bachelor's degree in human resources, Business Administration, Finance, Economics, or a related field and minimum 3 years of experience in Compensation, Human Resources, or related roles.

> What You'll Need (Required): Bachelor's degree in human resources, Business Administration, Finance, Economics, or a related field and minimum 3 years of experience in Compensation, Human Resources, or related roles.
>
> contexto: ...tion. Support continuous improvement initiatives that enhance compensation programs, tools, and operational effectiveness. Perform other duties as assigned by management. What You'll Need (Required): Bachelor's degree in human resources, Business Administration, Finance, Economics, or a related field and minimum 3 years of experience in Compensation, Human Resources, or related roles. What Else We Look For...

### 38. `workday-Associate-Manager--Technical-Training_R576351` — Associate Manager, Technical Training

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What You Will Need Bachelor’s degree in Business, Education, Human Resources, or related discipline.

> What You Will Need Bachelor’s degree in Business, Education, Human Resources, or related discipline.
>
> contexto: ...g records and qualification evidence as needed. Provide support for NC/CAPAs related to training outcomes or training processes. Perform additional duties and projects as assigned. What You Will Need Bachelor’s degree in Business, Education, Human Resources, or related discipline. Minimum of 5 years of experience in medical device, supporting quality, compliance, manufacturing, operations, or technical trai...

### 39. `workday-Associate-Manager-Technical-Services_R567836` — Associate Manager Technical Services

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.

> What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.
>
> contexto: ...as the operational backup for the Technical Services leader, ensuring continuity of decision-making, prioritization, and execution across the organization. What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field. Minimum 7 years of experience in Quality Engineering, Technical Services, Microbiology, Sterilization, Calibrations, Receiving Inspection, or relat...

### 40. `workday-Business-Analyst--Contract-Pricing-and-Accuracy_R265403` — Business Analyst, Contract Pricing and Accuracy

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > QUALIFICATIONS AND SKILLS: Bachelor’s degree in Industrial Engineering, Business Administration, or a related field.

> QUALIFICATIONS AND SKILLS: Bachelor’s degree in Industrial Engineering, Business Administration, or a related field.
>
> contexto: ...em. Create and maintain user guides, and conduct workshops as needed. Generate reports and dashboards to provide insights into contract status, compliance, and performance. QUALIFICATIONS AND SKILLS: Bachelor’s degree in Industrial Engineering, Business Administration, or a related field. 3 years of experience as a Business Analyst or similar role with emphasis on areas such as contract management, pricing...

### 41. `workday-Business-Operations---Customer-Delivery-Intern_3170188-1` — Business Operations & Customer Delivery Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text="bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university.

> Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university.
>
> contexto: ...hnology journey to drive business outcomes, enhance employee experiences, and accelerate innovation. Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university. Preferred Majors/Programs: Business Administration Finance Economics Industrial Engineering Business Analytics Data Ana...

### 42. `workday-Business-Process-Automation---Data-Analytics-Intern_3170183-1` — Business Process Automation & Data Analytics Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text="bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university.

> Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university.
>
> contexto: ...hnology journey to drive business outcomes, enhance employee experiences, and accelerate innovation. Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university. Preferred Majors/Programs: Computer Science Data Engineering / Data Analytics Industrial Engineering Process Engineerin...

### 43. `workday-Buyer-GPC_R571353` — Buyer GPC

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Required Qualifications Bachelor’s degree in Supply Chain Management, Business Administration, Industrial Engineering, Operations Management, or a related field.

> Required Qualifications Bachelor’s degree in Supply Chain Management, Business Administration, Industrial Engineering, Operations Management, or a related field.
>
> contexto: ...oject progress, and operational results. Support strategic initiatives, including product lifecycle management, cost reduction projects, and supply chain optimization efforts. Required Qualifications Bachelor’s degree in Supply Chain Management, Business Administration, Industrial Engineering, Operations Management, or a related field. Minimum 3 years of experience in purchasing, supply planning, materials...

### 44. `workday-Buyer-Procurement-Operations_J-020161` — Buyer Procurement Operations

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications Bachelor's degree in Logistics, Supply Chain, Engineering, Business Administration, or a related field.

> Minimum Qualifications Bachelor's degree in Logistics, Supply Chain, Engineering, Business Administration, or a related field.
>
> contexto: ...ur office in AFZ, Heredia on Mondays, Wednesdays, and Thursdays. Please note that there may be occasions where additional office days are required, due specific business needs. Minimum Qualifications Bachelor's degree in Logistics, Supply Chain, Engineering, Business Administration, or a related field. Experience/educational requirements may be waived for internal candidates. 1+ years of direct experience i...

### 45. `workday-Continuous-Improvement-Intern_J-020427` — Continuous Improvement Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications Currently pursuing a Bachelor's or Licentiate degree in Industrial Engineering, with more than 75% of the degree program completed.

> Minimum Qualifications Currently pursuing a Bachelor's or Licentiate degree in Industrial Engineering, with more than 75% of the degree program completed.
>
> contexto: ...when additional office days are required due to specific business needs. The candidate must have an unrestricted right to work for Huntsman in Costa Rica. Minimum Qualifications Currently pursuing a Bachelor's or Licentiate degree in Industrial Engineering, with more than 75% of the degree program completed. Demonstrated interest in Continuous Improvement, problem-solving, and process optimization. Written...

### 46. `workday-Contract-Administrator--Internship-_1213007` — Contract Administrator (Internship)

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Job Description: Job Family Definition: Students pursuing a Bachelor's degree in Business Administration, Industrial Engineering, Finance, Accounting or related fields.
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Responsibilities: Supports sales processing activities for assigned areas and processes Learns requirements and develops capability in all areas of sales processing Collects, consolidates, and charts data from sales and process results for assigned portions of operations areas to identify trends and issues learns and practices basic analysis Implements specified changes to processes and tools to improve performance, efficiency and customer satisfaction Develops understanding of internal and external relationships with stakeholders for performance expectations and needs Education and Experience Required: Bachelor's degree in Business Administration, Industrial Engineering, Finance, Accounting or related fields.
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Impact/Scope: University students actively enrolled in a university/college/institution pursuing a Bachelor's degree in a non-technical area of study, and who typically works during school breaks and then returns to their university.

> Job Description: Job Family Definition: Students pursuing a Bachelor's degree in Business Administration, Industrial Engineering, Finance, Accounting or related fields.
>
> contexto: ...and are a force for good. If you are looking to stretch and grow your career our culture will embrace you. Open up opportunities with HPE. Job Description: Job Family Definition: Students pursuing a Bachelor's degree in Business Administration, Industrial Engineering, Finance, Accounting or related fields. Assists in various tasks aligned with their field of study, including research, collaboration on team...

### 47. `workday-Contract-Pricing-Team-Lead_R265399` — Contract Pricing Team Lead

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Qualifications and Skills Bachelor's degree in Business Administration or a related field required.

> Qualifications and Skills Bachelor's degree in Business Administration or a related field required.
>
> contexto: ...ghts clearly and effectively. Support change management efforts tied to process or system enhancements. Provide training and support to end-users on new tools and workflows. Qualifications and Skills Bachelor's degree in Business Administration or a related field required. Excellent communication skills in English (B2+ or higher) and ability to collaborate across functions and geographies. Minimum 5 years o...

### 48. `workday-Controls-Application-Engineer-II_WD30284064` — Controls Application Engineer II

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Qualifications Bachelor’s degree in Electronics, Mechatronics, Electrical, or Electromechanical Engineering.

> Qualifications Bachelor’s degree in Electronics, Mechatronics, Electrical, or Electromechanical Engineering.
>
> contexto: ...n packages, and by using feedback to strengthen future work. Win as one team by collaborating with diverse perspectives and supporting both internal partners and external stakeholders. Qualifications Bachelor’s degree in Electronics, Mechatronics, Electrical, or Electromechanical Engineering. 2 to 3 years of experience in engineering-related activities. Ability to meet deadlines while maintaining a positive...

### 49. `workday-Credit---Collections-Specialist--2_R232432` — Credit & Collections Specialist

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `alternativa` (término: `'bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- **decisión firmada** (2ª persona, `educacion`): veredicto `bloqueo_real` · revisor `Giovanni Vargas` · fecha `2026-11-08`
  - criterio: El aviso pide «Required Associate’s or bachelor’s degree in business, Finance, or a related field». REGLA DE NEGOCIO (decidida el 2026-11-08; escalera de niveles y fuentes en docs/REGLAS_NEGOCIO_EDUCACION.md): el aviso ofrece DOS vias alternativas y la permisiva es «Associate’s» = titulo academico superior de ciclo corto (escalera: posgrado > titulo universitario > estudiante sin graduar con 80% o mas de creditos > diploma tecnico > bachillerato de secundaria; fuente: U.S. Department of State - InfoUSA, Structure of U.S. Education, usinfo.state.gov/infousa/education/overview/edlite-structure-us.html). El perfil SI tiene ese nivel (Diplomado en Electronica, INTEC) pero NO en el campo que pide el aviso (Electronica, no business/Finance): el NIVEL se cumple, el CAMPO no -> el requisito no se cumple -> BLOQUEO REAL -> la vacante se descarta.
- requisitos `education` extraídos:
  - `value_text='bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Responsibilities Manage and collect accounts receivable for an assigned portfolio of B2B customers Monitor customer aging and enforce credit terms and limits using ERP and A/R systems (SAP, Esker or similar) Review credit applications and evaluate customer creditworthiness using credit bureaus and references Approve new customer credit limits within assigned authority and prepare recommendations for higher limits Place accounts on credit hold , issue final notices, and recommend escalation to third-party collections when necessary Collaborate closely with Sales Representatives to resolve past-due balances and communicate account status changes Maintain accurate documentation of all collection and credit activities in the system Research and resolve discrepancies such as short pays, deductions, overpayments, and unapplied cash Support credit memo requests and payment arrangements with appropriate approvals Ensure customer master data is accurate and up to date Deliver excellent customer service to both internal and external partners Participate in special projects and additional duties as assigned Required Associate’s or bachelor’s degree in business, Finance, or a related field 1–2 years of experience in B2B credit, collections, or accounts receivable Excellent communication skills in English (B2+ or higher) and ability to collaborate across functions and geographies.

> ...ter data is accurate and up to date Deliver excellent customer service to both internal and external partners Participate in special projects and additional duties as assigned Required Associate’s or bachelor’s degree in business, Finance, or a related field 1–2 years of experience in B2B credit, collections, or accounts receivable Excellent communication skills in English (B2+ or higher) and abil...
>
> contexto: ...ter data is accurate and up to date Deliver excellent customer service to both internal and external partners Participate in special projects and additional duties as assigned Required Associate’s or bachelor’s degree in business, Finance, or a related field 1–2 years of experience in B2B credit, collections, or accounts receivable Excellent communication skills in English (B2+ or higher) and ability to col...

### 50. `workday-Data-Analytics-Intern_1210982` — Data Analytics Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Management Level Definition: Responsibilities: Develop interactive dashboards using Power BI, Tableau, or similar visualization platforms Create clear visualizations that communicate trends, anomalies, and key performance indicators Collaborate with stakeholders to understand reporting requirements Design executive-ready reports with an emphasis on usability and clarity Improve existing dashboards by enhancing performance and user experience Develop Python or R scripts to automate repetitive analysis and reporting tasks Build scheduled reporting processes Assist with exploratory data analysis to identify patterns and opportunities Implement automated data validation and exception reporting Support predictive analytics and machine learning projects where appropriate Design, develop, and maintain ETL/ELT data pipelines Acquire, clean, transform, and validate structured and semi-structured datasets Build automated workflows for recurring data processing tasks Develop reusable data models and standardized datasets for analytics Optimize SQL queries and data extraction processes for performance Assist in integrating data from APIs, databases, flat files, and cloud storage Monitor pipeline health and troubleshoot data quality issues Document datasets, schemas, and engineering processes Education & Experience: Currently pursuing a Bachelor's degree in Engineering, Computer Science, Information Technology, or a related technical field.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Knowledge & Skills: Experience with: Python or R, SQL and Microsoft Excel Familiarity with: Relational databases, Git or other version control systems, Data cleaning and transformation techniques Strong analytical and problem-solving abilities Curiosity to learn new technologies quickly Ability to explain technical concepts to non-technical audiences Excellent written and verbal communication Attention to detail Self-motivated with strong organizational skills Ability to work independently and within cross-functional teams Impact/Scope: University students actively enrolled in a university/college/institution pursuing a Bachelor's degree in a technical area of study, and who typically works during school breaks and then returns to their university.

> Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
>
> contexto: ...up opportunities with HPE. Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field. Assists in various tasks aligned with their field of study, including research, collaboration on team initiatives and projects, problem-solving, and creative thinking...

### 51. `workday-Director--Corporate-Accounting_JR-0111126` — Director, Corporate Accounting

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > About You Required Qualifications: Bachelor’s degree in Accounting, Finance, or a related field required.

> About You Required Qualifications: Bachelor’s degree in Accounting, Finance, or a related field required.
>
> contexto: ...accounting operations and decision-making. Ensure work is appropriately prioritized, documented, controlled, and aligned with broader Accounting and Finance goals. About You Required Qualifications: Bachelor’s degree in Accounting, Finance, or a related field required. 10+ years of progressive accounting experience, including significant corporate accounting leadership experience. Solid working knowledge o...

### 52. `workday-Director--Manufacturing-Engineering_REQ-2026-18566` — Director, Manufacturing Engineering

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Education & Experience Bachelor’s degree in Manufacturing, Mechanical, Electrical, Industrial, or a related Engineering discipline required;
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Education and Experience: Minimum Requirements: • Bachelor’s Degree in Engineering • 7+ years of management experience in a high-volume manufacturing environment, with at least 3+ years of departmental leadership.

> Education & Experience Bachelor’s degree in Manufacturing, Mechanical, Electrical, Industrial, or a related Engineering discipline required
>
> contexto: ...training systems, and a culture of accountability, inclusion, continuous improvement, and operational excellence. Perform other duties and lead additional projects as required. Education & Experience Bachelor’s degree in Manufacturing, Mechanical, Electrical, Industrial, or a related Engineering discipline required; master’s degree or MBA preferred. 10+ years of progressive experience in high-volume manufac...

### 53. `workday-Director--Manufacturing-Operations_REQ-2026-18565-1` — Director, Manufacturing Operations

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Education & Experience Bachelor’s degree in Engineering, Manufacturing, Operations, Business, or a related discipline required;
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Education and Experience: Minimum Requirements: Bachelor’s Degree in Operations, Engineering, or experience in related field preferred plus 12 years’ experience in the field.

> Education & Experience Bachelor’s degree in Engineering, Manufacturing, Operations, Business, or a related discipline required
>
> contexto: ...ional forums; communicate performance, priorities, risks, and resource needs to executive leadership. Perform other duties and lead additional business initiatives as required. Education & Experience Bachelor’s degree in Engineering, Manufacturing, Operations, Business, or a related discipline required; master’s degree or MBA preferred. 10+ years pf progressive experience in high-volume manufacturing or ope...

### 54. `workday-Director--Quality-Operations_REQ-2026-18476` — Director, Quality Operations

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Candidates are expected to transition to an onsite work arrangement once the facility is ready Required Experience & Qualifications • Bachelor's degree in Engineering, Science, or related discipline;
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Required Experience & Qualifications • Bachelor's degree in Engineering, Science, or related discipline;

> Bachelor's degree in Engineering, Science, or related discipline
>
> contexto: ...aunch of our new greenfield site, this role will start as remote. Candidates are expected to transition to an onsite work arrangement once the facility is ready Required Experience & Qualifications • Bachelor's degree in Engineering, Science, or related discipline; advanced degree preferred. • 12+ years of progressive medical device quality leadership experience, including significant manufacturing quality...

### 55. `workday-Document-Control-Intern_1210991` — Document Control Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Impact/Scope: University students actively enrolled in a university/college/institution pursuing a Bachelor's degree in a technical area of study, and who typically works during school breaks and then returns to their university.

> Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
>
> contexto: ...up opportunities with HPE. Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field. Assists in various tasks aligned with their field of study, including research, collaboration on team initiatives and projects, problem-solving, and creative thinking...

### 56. `workday-Embedded-Software-Engineer-Internship_1214117` — Embedded Software Engineer Internship

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Impact/Scope: University students actively enrolled in a university/college/institution pursuing a Bachelor's degree in a technical area of study, and who typically works during school breaks and then returns to their university.

> Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
>
> contexto: ...up opportunities with HPE. Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field. Assists in various tasks aligned with their field of study, including research, collaboration on team initiatives and projects, problem-solving, and creative thinking...

### 57. `workday-Finance-Accounting-Group-Manager---C14_261004389` — Finance Accounting Group Manager - C14

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > 6+ years of experience in accounting management with commensurate stakeholder management experience Education: Bachelor’s/University degree, Master’s degree preferred ------------------------------------------------------ Job Family Group: Finance ------------------------------------------------------ Job Family: Financial Accounting ------------------------------------------------------ Time Type: Full time ------------------------------------------------------ Most Relevant Skills Accounting Processes and Financial Controls, Assessment, Credible Challenge, Financial Accounting, Management Reporting, Policy and Regulation, Risk Management.

> ...6+ years of experience in accounting management with commensurate stakeholder management experience Education: Bachelor’s/University degree, Master’s degree preferred ------------------------------------------------------ Job Family Group: Finance ------------------------------------------------------ Job Fami...
>
> contexto: ...rtered Accountant (CA) or equivalent combination of education, desired but not required. 6+ years of experience in accounting management with commensurate stakeholder management experience Education: Bachelor’s/University degree, Master’s degree preferred ------------------------------------------------------ Job Family Group: Finance ------------------------------------------------------ Job Family: Financ...

### 58. `workday-Finance-Intern-CARICAM_549690` — Finance Intern CARICAM

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Basic Qualifications: We are looking for professionals with these required skills to achieve our goals: Currently pursuing a Bachelor’s degree in Accounting, Finance, or a related field.

> Basic Qualifications: We are looking for professionals with these required skills to achieve our goals: Currently pursuing a Bachelor’s degree in Accounting, Finance, or a related field.
>
> contexto: ...a compilation. Participate in continuous improvement initiatives. Why you? Basic Qualifications: We are looking for professionals with these required skills to achieve our goals: Currently pursuing a Bachelor’s degree in Accounting, Finance, or a related field. Technical High School degree in Accounting (highly desirable). Basic knowledge of IFRS or US GAAP. Advanced Excel skills. Intermediate proficiency i...

### 59. `workday-Finance-SOX-Testing-Analyst_R274171` — Finance SOX Testing Analyst

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Qualifications: Bachelor's degree in Accounting, Finance, Information Systems, or related field.

> Qualifications: Bachelor's degree in Accounting, Finance, Information Systems, or related field.
>
> contexto: ...ntation to support compliance and audit requirements. Monitor status of remediation plans and retesting as needed. Stay updated on SOX regulations and internal control best practices. Qualifications: Bachelor's degree in Accounting, Finance, Information Systems, or related field. 2–5 years of experience in SOX testing, internal audit, or external audit. Excellent communication skills in English (B2+ or high...

### 60. `workday-Fraud-Prevention-Analyst_3170439-1` — Fraud Prevention Analyst

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'University degree'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='University degree'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Qualifications: University degree or comparable proven experience desired.

> Qualifications: University degree or comparable proven experience desired.
>
> contexto: ...ybrid work model, requiring three (3) days on-site at the AFZ location, with the remaining days working remotely, in alignment with business needs and team collaboration requirements. Qualifications: University degree or comparable proven experience desired. Very Fluent English (90%+) (oral and written). Strong written and verbal communication skills. Intermediate skills required with Microsoft Excel, PowerPoint,...

### 61. `workday-Ingeniero-de-Manufactura_20186958` — Ingeniero de Manufactura

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Requirements Bachelor’s Degree in Industrial Engineering, Mechanical Engineering, Electromechanical Engineering, Electrical/Electronic Engineering, or related engineering discipline.

> Requirements Bachelor’s Degree in Industrial Engineering, Mechanical Engineering, Electromechanical Engineering, Electrical/Electronic Engineering, or related engineering discipline.
>
> contexto: ...ross-functional teams. Ensure compliance with GMP, FDA, ISO 13485, and applicable regulatory requirements. Provide technical leadership, training, and support to manufacturing personnel. Requirements Bachelor’s Degree in Industrial Engineering, Mechanical Engineering, Electromechanical Engineering, Electrical/Electronic Engineering, or related engineering discipline. 3+ years of manufacturing engineering ex...

### 62. `workday-Intern---Bachelor-s-Tech_1216552` — Intern - Bachelor's Tech

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Job Description: Job Family Definition: Students of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in Engineering, Computer Science, Information Technology, or a related technical field.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Education & Experience: Currently pursuing a Bachelor's degree in Engineering, Computer Science, Information Technology, or a related technical field.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Impact/Scope: University students actively enrolled in a university/college/institution pursuing a Bachelor's degree in a technical area of study, and who typically works during school breaks and then returns to their university.
  - `value_text="Bachelor's"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Intern - Bachelor's Tech This role has been designed as 'Hybrid' with a requirement that you will work on average 2 days per week from an HPE office.

> Job Description: Job Family Definition: Students of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in Engineering, Computer Science, Information Technology, or a related technical field.
>
> contexto: ...l embrace you. Open up opportunities with HPE. Job Description: Job Family Definition: Students of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in Engineering, Computer Science, Information Technology, or a related technical field. Assists in various tasks aligned with their field of study, including research, collaboratio...

### 63. `workday-Intern---Bachelors-Tech_1214221` — Intern - Bachelors Tech

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Education & Experience: Currently pursuing a Bachelor's degree in Engineering, Computer Science, Information Technology, or a related technical field.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Impact/Scope: University students actively enrolled in a university/college/institution pursuing a Bachelor's degree in a technical area of study, and who typically works during school breaks and then returns to their university.

> Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
>
> contexto: ...up opportunities with HPE. Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field. Assists in various tasks aligned with their field of study, including research, collaboration on team initiatives and projects, problem-solving, and creative thinking...

### 64. `workday-Inventory-Analyst---Fixed-Term-9-Months_450413` — Inventory Analyst - Fixed Term 9 Months

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Basic Qualifications We are seeking professionals with the following skills and qualifications: Bachelor’s degree in Accounting, Business Administration, Finance, or a related field.

> Basic Qualifications We are seeking professionals with the following skills and qualifications: Bachelor’s degree in Accounting, Business Administration, Finance, or a related field.
>
> contexto: ...bal teams to drive process improvements, automation, data quality, and operational efficiency. Why You? Basic Qualifications We are seeking professionals with the following skills and qualifications: Bachelor’s degree in Accounting, Business Administration, Finance, or a related field. Strong accounting fundamentals and understanding of financial processes. Candidates who have solid accounting knowledge but...

### 65. `workday-Leader--Customer-Support_2022544-1` — Leader, Customer Support

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=False · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Our minimum requirements for this role · Bachelor's degree and 7 years of related experience, or a master's degree and 4 years of related experience, or a PhD and 1 year of related experience.

> Bachelor's degree and 7 years of related experience, or a master's degree and 4 years of related experience, or a PhD and 1 year of related experience.
>
> contexto: ...artners. · A people leader who coaches through change, develops capability, encourages responsible use of AI and automation, and creates psychological safety. Our minimum requirements for this role · Bachelor's degree and 7 years of related experience, or a master's degree and 4 years of related experience, or a PhD and 1 year of related experience. · Previous supervisory or team lead experience. · At least...

### 66. `workday-Manager--Business-Continuity_Req-49141` — Manager, Business Continuity

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What you'll need (Required): • Bachelor's degree in business administration, Supply Chain Management, Emergency Management, Risk Management, Engineering, or related field, with 8+ years' experience • Master's degree with 6+ years of relevant experience may substitute for bachelor's with 8+ years • Professional experience relevant to business continuity and organizational resilience, which may include BCM, IT disaster recovery (ITDR), emergency management, recovery planning, business impact or risk assessments, continuity exercises, supply chain resilience, or incident response.

> Bachelor's degree in business administration, Supply Chain Management, Emergency Management, Risk Management, Engineering, or related field, with 8+ years' experience
>
> contexto: ...ior leaders and serve as a BCM subject matter expert to adjacent resilience and risk initiatives, including strategic sourcing resilience and IT resilience assessments. What you'll need (Required): • Bachelor's degree in business administration, Supply Chain Management, Emergency Management, Risk Management, Engineering, or related field, with 8+ years' experience • Master's degree with 6+ years of relevant...

### 67. `workday-Master-Data-Analyst_R-01358585` — Master Data Analyst

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > REQUIRED QUALIFICATIONS Education: Bachelor’s degree in supply chain, Business Administration, Information Technology, or related field Experience: Minimum 2 years of experience with SAP in Operations/Warehouse/ Manufacturing or related environment, preferably in the pharmaceutical industry.

> REQUIRED QUALIFICATIONS Education: Bachelor’s degree in supply chain, Business Administration, Information Technology, or related field Experience: Minimum 2 years of experience with SAP in Operations/Warehouse/ Manufacturing or related environment, preferably in the pharmaceutical industry.
>
> contexto: ...ment reports, support performance tracking (data accuracy, reporting accuracy, standards alignment, timely updates), and act as backup for the Supply Chain Analyst. REQUIRED QUALIFICATIONS Education: Bachelor’s degree in supply chain, Business Administration, Information Technology, or related field Experience: Minimum 2 years of experience with SAP in Operations/Warehouse/ Manufacturing or related environm...

### 68. `workday-Payroll-Intern_J-020465` — Payroll Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications Currently pursuing a Bachelor's or Licentiate degree in Industrial Engineering, Business Administration or related field, with more than 75% of the degree program completed.

> Minimum Qualifications Currently pursuing a Bachelor's or Licentiate degree in Industrial Engineering, Business Administration or related field, with more than 75% of the degree program completed.
>
> contexto: ...edia on Mondays, Wednesdays, and Thursdays. Please note that there may be occasions where additional office days are required, due specific business needs. Minimum Qualifications Currently pursuing a Bachelor's or Licentiate degree in Industrial Engineering, Business Administration or related field, with more than 75% of the degree program completed. Written and spoken proficiency in English (B2+). Proficie...

### 69. `workday-Payroll-Lead-Analyst_261008688` — Payroll Lead Analyst

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='preferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Education: Bachelor’s/University degree, Master’s degree preferred ------------------------------------------------------ Job Family Group: Operations - Services ------------------------------------------------------ Job Family: Payroll ------------------------------------------------------ Time Type: Full time ------------------------------------------------------ Most Relevant Skills Please see the requirements listed above.

> ...Education: Bachelor’s/University degree, Master’s degree preferred ------------------------------------------------------ Job Family Group: Operations - Services -------------------------------------------------...
>
> contexto: ...calating, managing and reporting control issues with transparency. Recommended Qualifications: 6-10 years of experience in a related role with commensurate experience in people management. Education: Bachelor’s/University degree, Master’s degree preferred ------------------------------------------------------ Job Family Group: Operations - Services ------------------------------------------------------ Job...

### 70. `workday-Planner-II_31164664` — Planner II

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Shift: Administrative Required Qualifications Bachelor´s Degree in Engineering or related field.

> Shift: Administrative Required Qualifications Bachelor´s Degree in Engineering or related field.
>
> contexto: ...Ops on product commitments, exception management and new product introductions. Planning and MFG execution reports. Ensure Planning KPI metrics are met. Shift: Administrative Required Qualifications Bachelor´s Degree in Engineering or related field. Experience 2-4 years in: Related work experience with a complete understanding of specified functional area. Planning and Scheduling: Planning resources, bal...

### 71. `workday-Principal-Engineer--Quality_Req-51750` — Principal Engineer, Quality

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `alternativa` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- **decisión firmada** (2ª persona, `educacion`): veredicto `bloqueo_real` · revisor `Giovanni Vargas` · fecha `2026-11-08`
  - criterio: El aviso exige, en «What you'll need (Required): Bachelor's degree in engineering or Scientific field», un titulo universitario en ingenieria (o superior). Las alternativas son titulos SUPERIORES en la misma disciplina («Master's Degree or equivalent», «Ph.D. or equivalent»), no una via por experiencia: sin titulo universitario no hay acceso -> bloqueo real.
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > analyze results, make recommendations and develop reports • Train, coach, and guide lower level employees on more complex procedures • Develop technical content of risk management files • Manage Supplier Quality Activities as needed • Other incidental duties What you'll need (Required): Bachelor's degree in engineering or Scientific field, 6 years of experience minimum of experience, including either industry or industry/education or Master's Degree or equivalent in Engineering or Scientific field, 5 years of experience minimum of experience, including either industry or industry/education or Ph.D.

> Other incidental duties What you'll need (Required): Bachelor's degree in engineering or Scientific field, 6 years of experience minimum of experience, including either industry or industry/education or Master's Degree or equivalent in Engineering or Scientific field, 5 years of experience minimum of experience, including either industry or industry/education or Ph.D.
>
> contexto: ...r level employees on more complex procedures • Develop technical content of risk management files • Manage Supplier Quality Activities as needed • Other incidental duties What you'll need (Required): Bachelor's degree in engineering or Scientific field, 6 years of experience minimum of experience, including either industry or industry/education or Master's Degree or equivalent in Engineering or Scientific f...

### 72. `workday-Process-Engineer_887921` — Process Engineer

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachillerato Universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachillerato Universitario'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Para tener éxito en este puesto, necesitarás las siguientes calificaciones: Bachillerato Universitario en Ingeniería Industrial, Producción Industrial o carreras afines.

> Para tener éxito en este puesto, necesitarás las siguientes calificaciones: Bachillerato Universitario en Ingeniería Industrial, Producción Industrial o carreras afines.
>
> contexto: ...PIs. Generar planes de acción para solucionar los hallazgos encontrados en la gestión del puesto, y los procesos asociados. Para tener éxito en este puesto, necesitarás las siguientes calificaciones: Bachillerato Universitario en Ingeniería Industrial, Producción Industrial o carreras afines. Mínimo 1 año de experiencia en procesos de producción, análisis de datos estadísticos. Manejo intermedio de Excel. Nivel de Inglés:...

### 73. `workday-Production-Supervisor-I_31165535` — Production Supervisor I

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='preferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Demonstrated capacity to effectively lead/influence peers and other functions Preferred Qualifications Bachelor’s degree in Business Administration, Engineering or similar field.
  - `value_text='bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > On-Site position Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Industrial Engineering, Administration or related field.

> On-Site position Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Industrial Engineering, Administration or related field.
>
> contexto: ...mechanisms to ensure that all processes are in compliance with standard procedures. Shift: A (Monday - Friday from 5:50 am to 3:15 pm). On-Site position Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Industrial Engineering, Administration or related field. 0-2 years supervisory experience. Preferably in a medical device, pharmaceutical, or...

### 74. `workday-Production-Supervisor-I_31165743` — Production Supervisor I

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='preferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Demonstrated capacity to effectively lead/influence peers and other functions Preferred Qualifications • Bachelor’s degree in Business Administration, Engineering or similar field.
  - `value_text='bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > On-Site position Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Industrial Engineering, Administration or related field.

> On-Site position Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Industrial Engineering, Administration or related field.
>
> contexto: ...Interprets daily production metrics and establishes mechanisms to ensure that all processes are in compliance with standard procedures. On-Site position Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Industrial Engineering, Administration or related field. 0-2 years supervisory experience. Preferably in a medical device, pharmaceutical, or...

### 75. `workday-Purchasing-Manager--Global-Procurement-Center_R572335` — Purchasing Manager, Global Procurement Center

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What You Will Need Required Qualifications Bachelor’s degree in Business, Supply Chain Management, Engineering, or a related field.

> What You Will Need Required Qualifications Bachelor’s degree in Business, Supply Chain Management, Engineering, or a related field.
>
> contexto: ...g development plans for managers and buyers. Ensure compliance with applicable quality and regulatory requirements and support internal and external audits. What You Will Need Required Qualifications Bachelor’s degree in Business, Supply Chain Management, Engineering, or a related field. Minimum 8 years of experience in Supply Chain, Purchasing, Procurement, Manufacturing, or a related field. Minimum 3 year...

### 76. `workday-Quality-Engineer-III_31166281` — Quality Engineer III

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Required Qualifications Bachelor´s Degree Engineering.

> Required Qualifications Bachelor´s Degree Engineering.
>
> contexto: ...Inspection and Test Method Qualifications, typically with minimum mentorship from higher level engineering. Perform supervisor activities to Quality Technicians, if required. Required Qualifications Bachelor´s Degree Engineering. 2-4 years of experience in Quality or Engineering positions. At least 2 years of experience in quality or manufacturing engineering roles. Proficiency in computer applications (...

### 77. `workday-R-D-Process-Coordinator_R-106675` — R&D Process Coordinator

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Responsabilidades Liderar la comercialización e industrialización de nuevos productos y cambios de proceso, desde las etapas de laboratorio/piloto hasta la producción a escala industrial Definir y desarrollar procesos de manufactura end-to-end para productos estables a temperatura ambiente, incluyendo condimentos, vegetales y alimentos para bebés Desarrollar diagramas de flujo de procesos, balances de masa y energía, dimensionamiento de equipos, modelos de capacidad de línea y ventanas operativas Establecer y optimizar parámetros de proceso para etapas críticas como cocción, calentamiento, mezclado, emulsificación, homogeneización y desaireación Diseñar y optimizar procesos relacionados con el manejo de partículas, incluyendo preparación de vegetales, integridad y distribución de partículas, control de sedimentación y selección de bombas Definir y controlar parámetros relacionados con pH, acidificación y sólidos (Brix/viscosidad) para garantizar los objetivos de estabilidad y vida útil de los productos Asegurar el cumplimiento de los requerimientos de procesos térmicos relacionados con Seguridad Alimentaria y Calidad, incluyendo hot-fill, cold-fill, pasteurización y procesos de retorta cuando corresponda Establecer y gestionar los parámetros críticos de proceso y atributos críticos de calidad (CPPs/CQAs), incluyendo pH, viscosidad, Brix/sólidos, tamaño y distribución de partículas, temperatura de llenado, tiempo de retención, headspace, vacío, torque de cierre, integridad del cierre y contenido neto Liderar la ejecución de pruebas industriales, incluyendo planes de prueba, evaluaciones de riesgo, ejecución y elaboración de reportes técnicos Crear y mantener documentación técnica, incluyendo SOPs, estándares de setpoints, descripciones de procesos, protocolos de pruebas, parámetros de sanitización/CIP y materiales de capacitación Liderar procesos de control de cambios y evaluaciones de riesgo para modificaciones de formulación, procesos, packaging y equipos Requisitos Licenciatura/Ingeniería completa en Ingeniería Química, Mecánica, Industrial, de Manufactura, Alimentos o áreas relacionadas Más de 5 años de experiencia en ingeniería de procesos y/o ambientes de manufactura Experiencia en diseño de procesos, escalamiento e industrialización de productos Conocimiento de control de procesos, análisis de causa raíz y metodologías de mejora continua Experiencia trabajando en ambientes productivos y en proyectos cross-functional Manejo de herramientas como Excel y Minitab, JMP o software estadístico similar Experiencia con sistemas ERP/MES será considerada un diferencial Inglés avanzado será requerido Portugués será considerado un diferencial Location(s) San Jose, Costa Rica Local Office Kraft Heinz is an Equal Opportunity Employer – Underrepresented Ethnic Minority Groups/Women/Veterans/Individuals with Disabilities/Sexual Orientation/Gender Identity and other protected classes .

> ...arámetros de sanitización/CIP y materiales de capacitación Liderar procesos de control de cambios y evaluaciones de riesgo para modificaciones de formulación, procesos, packaging y equipos Requisitos Licenciatura/Ingeniería completa en Ingeniería Química, Mecánica, Industrial, de Manufactura, Alimentos o áreas relacionadas Más de 5 años de experiencia en ingeniería de procesos y/o ambientes de man...
>
> contexto: ...arámetros de sanitización/CIP y materiales de capacitación Liderar procesos de control de cambios y evaluaciones de riesgo para modificaciones de formulación, procesos, packaging y equipos Requisitos Licenciatura/Ingeniería completa en Ingeniería Química, Mecánica, Industrial, de Manufactura, Alimentos o áreas relacionadas Más de 5 años de experiencia en ingeniería de procesos y/o ambientes de manufactura Exp...

### 78. `workday-Security-Engineer_2025477` — Security Engineer

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications Bachelor’s degree with 3+ years of related experience, or a Master’s degree with 3+ years of related experience working in cybersecurity engineering, infrastructure engineering, DevOps, or a large enterprise technology environment.

> Minimum Qualifications Bachelor’s degree with 3+ years of related experience, or a Master’s degree with 3+ years of related experience working in cybersecurity engineering, infrastructure engineering, DevOps, or a large enterprise technology environment.
>
> contexto: ...ithin the organization, conducting training sessions or "lunch-and-learns" to improve the overall security awareness and coding practices of cross-functional development teams. Minimum Qualifications Bachelor’s degree with 3+ years of related experience, or a Master’s degree with 3+ years of related experience working in cybersecurity engineering, infrastructure engineering, DevOps, or a large enterprise te...

### 79. `workday-Senior-Analyst--Finance--Internal-Auditor-_Req-51202-1` — Senior Analyst, Finance (Internal Audit)

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's Degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What you'll need (Required): • Bachelor's Degree in related field is required • Minimum 5 years of previous related experience is required • Experience working in a medical device or a related manufacturing environment is required • Advance English level is required • Public accounting experience (e.g., Big Four CPA firms) preferred What else we look for (Preferred): • Strong knowledge of internal controls, risk assessment methodologies, audit practices, Generally Accepted Accounting Principles (GAAP), and Sarbanes-Oxley (SOX) requirements.

> Bachelor's Degree in related field is required
>
> contexto: ...ernal audit requests. • Support continuous improvement of audit methodologies, tools, analytics, and processes. • Perform other duties and special projects as assigned. What you'll need (Required): • Bachelor's Degree in related field is required • Minimum 5 years of previous related experience is required • Experience working in a medical device or a related manufacturing environment is required • Advance...

### 80. `workday-Senior-Director--Quality-Engineering_Req-50066` — Senior Director, Quality Engineering

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's Degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What you'll need (Required): Bachelor's Degree in related field with at least 10 years experience in engineering and leadership positions in the medical device industry Experience in Quality Engineering, Quality Management, and/or Regulatory Compliance within the medical device industry Demonstrated track record in management of technical and/or engineering disciplines Proven successful interaction with Regulators and Notified Bodies Experience influencing teams in a global environment What else we look for (Preferred): • Proven successful project management leadership skills • Proven expertise in both Microsoft Office Suite and related systems • Excellent problem-solving, organizational, analytical and critical thinking skills including high discretion/judgment in decision making • Excellent documentation and communication skills and interpersonal relationship skills including negotiating and relationship management skills with ability to drive achievement of objectives • Expert understanding of engineering procedures while looking beyond existing methodologies and own discipline to define and resolve complex problems • Expert understanding of related aspects of quality engineering processes and/or systems • Expert knowledge of domestic and international regulatory requirements • Expert knowledge of design of experiments, process capability studies, failure mode and effects analysis, statistical process control, industrial statistical methods and Lean Manufacturing • Knowledge of financial acumen as it relates to the business as well as quality engineering • Demonstrated ability to direct teams and provide coaching and feedback, including responsibility for all employee actions including hire/fire authority and partnering with HR on all aspects of employee relations • Ability to develop and integrate metrics into the projects and operations that clearly demonstrate the value of quality engineering to the business • Serve as core partner to senior leaders in Business Units, Functional Groups, Regions and IT • Strict attention to detail • Ability to interact professionally with all organizational levels and proactively escalate issues to appropriate levels of management in the organization • Ability to work and excel within a fast paced, dynamic, and constantly changing work environment • Interacts with senior management, and others concerning matters of significance to the company • Conduct business and technical briefings for senior and top management and for external representatives • Regularly interacts with executives and/or major customers;

> ...What you'll need (Required): Bachelor's Degree in related field with at least 10 years experience in engineering and leadership positions in the medical device industry Experience in Quality Engineering, Quality Management, and/o...
>
> contexto: ...es. Provide quality engagement to audits including resources support, technical and procedural expertise, presentation of information, and effective resolution of issues. What you'll need (Required): Bachelor's Degree in related field with at least 10 years experience in engineering and leadership positions in the medical device industry Experience in Quality Engineering, Quality Management, and/or Regulato...

### 81. `workday-Senior-Quality-Engineer_R567778` — Quality Engineer

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.

> What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.
>
> contexto: ...l analysis and risk management tools, including Failure Mode and Effects Analysis (FMEA), to support decision-making and continuous improvement initiatives. What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field. Minimum 3 years of experience in Quality Engineering. Working knowledge of 21 CFR Part 820, ISO 13485, and the Medical Device Single Audit Program...

### 82. `workday-Senior-Software-Quality-Engineer_R262277` — Senior Technology Project Manager – Quality & Delivery

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Required Qualifications Bachelor’s degree in Computer Science, Information Technology, Engineering, Business, Project Management, or a related field.

> Required Qualifications Bachelor’s degree in Computer Science, Information Technology, Engineering, Business, Project Management, or a related field.
>
> contexto: ...l teams, business stakeholders, and leadership. Promote consistent project management, testing, process improvement, and technology delivery best practices across initiatives. Required Qualifications Bachelor’s degree in Computer Science, Information Technology, Engineering, Business, Project Management, or a related field. 6+ years of experience in Technology Project Management, IT Project Management, Tech...

### 83. `workday-Senior-Supervisor--Manufacturing_Req-50617` — Senior Supervisor, Manufacturing

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What you’ll need (Required): Bachelor's degree in Industrial Engineering, Business Administration or related field.

> What you’ll need (Required): Bachelor's degree in Industrial Engineering, Business Administration or related field.
>
> contexto: ...outcomes of assigned unit/group of employees May guide and mentor entry level supervisors May provide management duties in the absence of Manager Other incidental duties. What you’ll need (Required): Bachelor's degree in Industrial Engineering, Business Administration or related field. More than 5 years of experience in personnel supervisory with full responsibility for all personnel and handling all aspect...

### 84. `workday-SharePoint-Application-Developer_R55630-1` — SharePoint Application Developer

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `alternativa` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- **decisión firmada** (2ª persona, `educacion`): veredicto `bloqueo_real` · revisor `Giovanni Vargas` · fecha `2026-11-08`
  - criterio: El texto dice «Bachelor's Degree with Computer Science / MIS field of study required». El «or equivalent hands-on experience with Microsoft 365 development» se refiere a los estudios AVANZADOS PREFERIDOS («Advanced study preferred»), NO al bachillerato: el titulo es obligatorio -> bloqueo real.
- requisitos `education` extraídos:
  - `value_text="Bachelor's Degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Bachelor's Degree with Computer Science / MIS field of study required.

> Bachelor's Degree with Computer Science / MIS field of study required.
>
> contexto: ...mentation. Collaborate with business users, IT teams, and vendors to deliver solutions. Performs other additional duties as assigned. What We’re Looking For: 3 to 5 Years of relevant work experience. Bachelor's Degree with Computer Science / MIS field of study required. Core SharePoint Skills SharePoint Online SharePoint Framework (SPFx) SharePoint site architecture Lists, libraries, and content types Permi...

### 85. `workday-Software-Engineering-Systems--Intern_1210981` — Software Engineering(Systems) Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Education & Experience: Currently pursuing a Bachelor's degree in Engineering, Computer Science, Information Technology, or a related technical field.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Impact/Scope: University students actively enrolled in a university/college/institution pursuing a Bachelor's degree in a technical area of study, and who typically works during school breaks and then returns to their university.

> Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
>
> contexto: ...up opportunities with HPE. Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field. Assists in various tasks aligned with their field of study, including research, collaboration on team initiatives and projects, problem-solving, and creative thinking...

### 86. `workday-Sr-Supv--Accounts-Payable_Req-51765` — Sr Supv, Accounts Payable

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What you´ll need (Required): Bachelor’s degree in a related field and 8 years of previous Accounts Payable experience, including demonstrated experience supervising Accounts Payable employees.

> What you´ll need (Required): Bachelor’s degree in a related field and 8 years of previous Accounts Payable experience, including demonstrated experience supervising Accounts Payable employees.
>
> contexto: ...g to internal customers on Accounts Payable requirements, invoice processing, approvals, and related processes. Perform other incidental duties as assigned by leadership. What you´ll need (Required): Bachelor’s degree in a related field and 8 years of previous Accounts Payable experience, including demonstrated experience supervising Accounts Payable employees. What Else We Look For (Preferred): Strong know...

### 87. `workday-Sr-Technical-Architect_WD30279546` — Sr Technical Architect

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Qualifications Bachelor’s degree in IT or a similar technology-related discipline.

> Qualifications Bachelor’s degree in IT or a similar technology-related discipline.
>
> contexto: ...by sharing information openly and early. Communicate with clarity so stakeholders understand trade-offs, dependencies, risks, and the technical approach required to move work forward. Qualifications Bachelor’s degree in IT or a similar technology-related discipline. Minimum 8 years of IT experience. Minimum 3 years of experience architecting integration solutions using APIs. Minimum 5 years of development...

### 88. `workday-Staff-Quality-Engineer--Onsite-_R576831` — Staff Quality Engineer (Onsite)

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=False · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What you will need Required • Bachelor’s degree in Engineering or a related technical field .

> Bachelor’s degree in Engineering or a related technical field .
>
> contexto: ...ith Quality Assurance, Manufacturing, Engineering, Research & Development, and Regulatory teams to resolve quality issues and escalate risks requiring management review. What you will need Required • Bachelor’s degree in Engineering or a related technical field . • Minimum 5 years of Quality Engineering experience . • Professional proficiency in English and Spanish , written and verbal. • Working knowledge...

### 89. `workday-Storage-Hardware-Operations-Intern_1210994` — Storage Hardware Operations Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Impact/Scope: University students actively enrolled in a university/college/institution pursuing a Bachelor's degree in a technical area of study, and who typically works during school breaks and then returns to their university.
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Education and Experience Required Currently pursuing a Bachelor's degree in Engineering, Supply Chain, Information Systems, Data Analytics, Business, Computer Science, or a related field.

> Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
>
> contexto: ...up opportunities with HPE. Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field. Assists in various tasks aligned with their field of study, including research, collaboration on team initiatives and projects, problem-solving, and creative thinking...

### 90. `workday-Student-Intern--Collaboration-Services-System-Programmer_JR0287833` — Student Intern, Collaboration Services System Programmer

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Currently pursuing a Bachelor's degree in Computer Science, Information Technology, Information Systems, Software Engineering, or a related field.

> Currently pursuing a Bachelor's degree in Computer Science, Information Technology, Information Systems, Software Engineering, or a related field.
>
> contexto: ...d commitment to documenting solutions for future reuse. Qualifications: Minimum Qualifications : Minimum qualifications are required to be initially considered for this position. Currently pursuing a Bachelor's degree in Computer Science, Information Technology, Information Systems, Software Engineering, or a related field. Approximately two years remaining before graduation. Basic understanding of Microsof...

### 91. `workday-Supplier-Quality-Engineer-III_31162905` — Supplier Quality Engineer III

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > As required , supervise technical personal for task execution Shift: Administrative Required Qualifications Bachelor's degree in engineering, Science, or equivalent field of study.

> As required , supervise technical personal for task execution Shift: Administrative Required Qualifications Bachelor's degree in engineering, Science, or equivalent field of study.
>
> contexto: ...ed . Mentors employees by sharing technical expertise and providing feedback and guidance . As required , supervise technical personal for task execution Shift: Administrative Required Qualifications Bachelor's degree in engineering, Science, or equivalent field of study. 2 of experience in engineering related position. Intermediate command of English. Apply Now Follow your career aspirations to Abbott for...

### 92. `workday-Switching-Technical-Support-Engineer-Intern---Switching-Support---EX-Products_1214133` — Switching Technical Support Engineer Intern | Switching Support – EX Products

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Education and Experience Currently pursuing a Bachelor’s degree in: Computer Science.
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Impact/Scope: University students actively enrolled in a university/college/institution pursuing a Bachelor's degree in a technical area of study, and who typically works during school breaks and then returns to their university.

> Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
>
> contexto: ...up opportunities with HPE. Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field. Assists in various tasks aligned with their field of study, including research, collaboration on team initiatives and projects, problem-solving, and creative thinking...

### 93. `workday-Tax-Audit-Senior-Specialist_888004-1` — Tax Compliance Analyst III

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > To succeed in this role, you will need the following qualifications: Bachelor's degree in finance, accounting, internal control or related field along with experience in USGAAP, preparing Income Tax Returns, Informative reports, compliance reports and attending tax audits.

> To succeed in this role, you will need the following qualifications: Bachelor's degree in finance, accounting, internal control or related field along with experience in USGAAP, preparing Income Tax Returns, Informative reports, compliance reports and attending tax audits.
>
> contexto: ...entic caring. You want to be part of a company actively dedicated to sustainability, inclusion, wellbeing, and career development. To succeed in this role, you will need the following qualifications: Bachelor's degree in finance, accounting, internal control or related field along with experience in USGAAP, preparing Income Tax Returns, Informative reports, compliance reports and attending tax audits. More...

### 94. `workday-Technical-Consulting-Engineer_2024456` — Technical Consulting Engineer

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications Possess a Bachelor’s degree in Computer Science, Engineering, Information Technology, or have work experience.

> Minimum Qualifications Possess a Bachelor’s degree in Computer Science, Engineering, Information Technology, or have work experience.
>
> contexto: ...ineering fixes. Document technical findings, diagnostic procedures, and solutions in internal knowledge bases to improve incident readiness and peer-to-peer learning. Minimum Qualifications Possess a Bachelor’s degree in Computer Science, Engineering, Information Technology, or have work experience. Have 5 or more years of experience in an advanced technical support role supporting complex enterprise softwa...

### 95. `workday-Technical-Support-Delivery-Intern_JR-0110629-1` — Technical Support Delivery Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='pursuing'`
    - evidencia literal del requisito: > #LI-DNI About You Basic Qualifications Currently pursuing a Bachelor’s degree in Computer Science, Information Technology, or related field, with an anticipated graduation date of June/July 2027 Must be able to commit to the full duration of the 23 week internship (Start Date: Feb 8, 2027) in Heredia, Costa Rica Must be able to work Shift 1 (8am - 5pm) Bilingual in Spanish and English Strong interest in technology and willingness to learn new applications.

> ...#LI-DNI About You Basic Qualifications Currently pursuing a Bachelor’s degree in Computer Science, Information Technology, or related field, with an anticipated graduation date of June/July 2027 Must be able to commit to the full duration of the 23 week intern...
>
> contexto: ...living our Core Values. Let’s make work days brighter. Apply today to start your career as a member of the Workday Intern & Co-Op Program! #LI-DNI About You Basic Qualifications Currently pursuing a Bachelor’s degree in Computer Science, Information Technology, or related field, with an anticipated graduation date of June/July 2027 Must be able to commit to the full duration of the 23 week internship (Star...

### 96. `workday-Technical-Support-Engineer-Intern---Wireless-Technologies_1214131` — Technical Support Engineer Intern – Wireless Technologies

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Education and Experience Currently pursuing a Bachelor’s degree in: Computer Science.
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Impact/Scope: University students actively enrolled in a university/college/institution pursuing a Bachelor's degree in a technical area of study, and who typically works during school breaks and then returns to their university.

> Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
>
> contexto: ...up opportunities with HPE. Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field. Assists in various tasks aligned with their field of study, including research, collaboration on team initiatives and projects, problem-solving, and creative thinking...

### 97. `workday-Technical-Writing-Intern_1214060` — Technical Writing Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Job Description: Job Family Definition: Students of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Education & Experience: Currently pursuing a Bachelor's degree in Engineering, Computer Science, Information Technology, or a related technical field.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Impact/Scope: University students actively enrolled in a university/college/institution pursuing a Bachelor's degree in a technical area of study, and who typically works during school breaks and then returns to their university.

> Job Description: Job Family Definition: Students of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
>
> contexto: ...l embrace you. Open up opportunities with HPE. Job Description: Job Family Definition: Students of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field. Assists in various tasks aligned with their field of study, including research, collaboration on team initiatives and projects, problem-solving, and creative thinking...

### 98. `workday-US-Marketing-Governance--Regulatory-and-Policy-Lead_25928925` — US Marketing Governance Regulatory and Policy Lead

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's"` · `requirement_level='preferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Education : Bachelor's/University degree, Master's degree preferred ------------------------------------------------------ Job Family Group: Controls Governance & Oversight ------------------------------------------------------ Job Family: Cross-disciplinary Controls ------------------------------------------------------ Time Type: Full time ------------------------------------------------------ Most Relevant Skills Analytical Thinking, Business Acumen, Communication, Constructive Debate, Controls Assessment, Controls Lifecycle, Escalation Management, Issue Management, Risk Management, Stakeholder Management.

> ...Education : Bachelor's/University degree, Master's degree preferred ------------------------------------------------------ Job Family Group: Controls Governance & Oversight ---------------------------------------...
>
> contexto: ...nd work well as part of a team. Exceptional oral and written communication skills, with ability to synthesize complex concepts, and influence change. Proficient in Microsoft Office Suite. Education : Bachelor's/University degree, Master's degree preferred ------------------------------------------------------ Job Family Group: Controls Governance & Oversight -------------------------------------------------...

### 99. `workday-VLSI-Engineer-Internship_1214036` — VLSI Engineer Internship

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Education & Experience: Currently pursuing a Bachelor's degree in Electric / Electronic Engineering, Familiarity with programming languages or technical tools relevant to the role.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Impact/Scope: University students actively enrolled in a university/college/institution pursuing a Bachelor's degree in a technical area of study, and who typically works during school breaks and then returns to their university.

> Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
>
> contexto: ...up opportunities with HPE. Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field. Assists in various tasks aligned with their field of study, including research, collaboration on team initiatives and projects, problem-solving, and creative thinking...

### 100. `workday-ingeniero-de-Manufactura_20184428` — ingeniero de Manufactura

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Qualifications/Responsibilities 2-4 years of experience in a highly regulated industry Bachelor’s degree in Engineering or a related field required.

> Qualifications/Responsibilities 2-4 years of experience in a highly regulated industry Bachelor’s degree in Engineering or a related field required.
>
> contexto: ...ives. Also designs process improvements to reduce product cost, process cycle time and improved product quality. Qualifications/Responsibilities 2-4 years of experience in a highly regulated industry Bachelor’s degree in Engineering or a related field required. Intermediate English proficiency (B1), Experience leading projects and supporting cost-reduction and quality-improvement initiatives within producti...

## 5. Las 1 `revisar_a_mano / educacion_no_confirmada` — por qué el MOTOR no las descarta

Son requisitos universitarios **obligatorios** que el TEXTO no confirma
(negación o alternativa). Van a revisión manual y a la HOJA DE REVISIÓN
pendiente (`docs/PASO5_REVISION_PENDIENTES.md`): el estado es el del
**motor**; el veredicto humano queda ABIERTO hasta que una segunda
persona firme en esa hoja.

> Los casos de esta lista **con firma "dudoso"** siguen ABIERTOS
> (falta una decisión de negocio): ver la sección 6.

### 1. `workday-Production-Supervisor-I_31163511` — Production Supervisor I

- detección textual: `alternativa` (término: `'bachelor’s'`)
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='preferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Preferred Qualifications Bachelor’s degree in business administration, Engineering or similar field.
  - `value_text='bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience.

> Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience.
>
> contexto: ...ation. Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience. 0-2 years supervisory experience. Preferably in a medical devic...

## 6. Las 29 decisiones FIRMADAS (2ª persona) y su efecto

El motor NO puede decidir, por sí solo, si un título universitario
**bloquea** o no (la regla es conservadora: `descartada` solo si el texto
confirma el título obligatorio SIN negación y SIN alternativa). Cuando el
texto deja una vía alternativa, el caso queda en `revisar_a_mano /
educacion_no_confirmada` y espera el veredicto de una **segunda persona**
(la revisión previa la hizo el autor de la regla → se descarta por sesgo).

Cada decisión está anclada al **sha256 del texto exacto que se leyó**: si el
aviso se vuelve a raspar y su texto cambia, la firma deja de aplicar y el
caso vuelve a `educacion_no_confirmada`.

| aviso | veredicto | efecto en la corrida | revisor | fecha |
|---|---|---|---|---|
| `recruitee-transperfect-2770002` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workable-cynet-corp-9613AEDBB4` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Accounting-Analyst_JR-0111160-1` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Accounts-Payable-Representative_J-020440` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Analyst-Payroll_R273170` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Audience-Management_26999789` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Buyer-Planner-Sr_31163601` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Clinical-Project-Manager_R18034-1` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Commercial-Analyst_R-01372758` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Creative-Execution-Manager--CrM-_261002442` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Credit---Collections-Specialist--2_R232432` | `bloqueo_real` | `descartada` / `titulo_universitario_requerido` | Giovanni Vargas | 2026-11-08 |
| `workday-Datacenter-Engineer--L3-ERT_1212932-2` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Datacenter-Engineer--L3-ERT_1212933-2` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Environmental-Program-Manager---Latin-America_R-69389-1` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Governance-Reporting---Analysis-Sr-Analyst---C12---HEREDIA_261007965` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-HR-Operations-Support-Lead-Analyst_25848722` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Network-Support-Engineer_1211197` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Operations-Engineer_R0007464` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Premium-Support-Engineer-Expert_1210068` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Principal-Engineer--Quality_Req-51750` | `bloqueo_real` | `descartada` / `titulo_universitario_requerido` | Giovanni Vargas | 2026-11-08 |
| `workday-Production-Supervisor-I_31163511` | `dudoso` | `revisar_a_mano` / `educacion_no_confirmada` | Giovanni Vargas | 2026-11-08 |
| `workday-Sales-Specialist_R-117581` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Security-Governance---Compliance-Specialist_2022361-1` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Security-Governance---Compliance-Specialist_2023168-1` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Senior-Client-Services-Executive_R2025-244318` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Senior-Engineer---WLAN_1210063-2` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Senior-Project-Manager_R13442` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-Senior-Specialist--Technical-Training_R576356` | `no_bloqueo` | `revisar_a_mano` / `educacion_no_cumple` | Giovanni Vargas | 2026-11-08 |
| `workday-SharePoint-Application-Developer_R55630-1` | `bloqueo_real` | `descartada` / `titulo_universitario_requerido` | Giovanni Vargas | 2026-11-08 |

### Criterio firmado (cita literal del aviso)

- `recruitee-transperfect-2770002` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Minimum Bachelor’s degree or its equivalent». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workable-cynet-corp-9613AEDBB4` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Bachelor’s degree in Finance, Economics, Business, Data Analytics, or a related field (or equivalent work experience)». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Accounting-Analyst_JR-0111160-1` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Bachelor's degree in Accounting, Finance, or a related discipline, or equivalent practical experience». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Accounts-Payable-Representative_J-020440` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «alternatively, 3+ years of relevant professional experience in Accounts Payable or Accounting may be considered in lieu of a degree». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Analyst-Payroll_R273170` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Equivalent combination of education and relevant experience may be considered.». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Audience-Management_26999789` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Education: Bachelors/University degree or equivalent experience». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Buyer-Planner-Sr_31163601` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Bachelor Degree, engineering, science or closely related discipline is desired, or equivalent technical». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Clinical-Project-Manager_R18034-1` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «What We Look For Bachelor’s degree required or equivalent experience». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Commercial-Analyst_R-01372758` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Education and Experience: Bachelor's degree or equivalent experience». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Creative-Execution-Manager--CrM-_261002442` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Education: Bachelors/University degree or equivalent experience». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Credit---Collections-Specialist--2_R232432` (bloqueo_real): El aviso pide «Required Associate’s or bachelor’s degree in business, Finance, or a related field». REGLA DE NEGOCIO (decidida el 2026-11-08; escalera de niveles y fuentes en docs/REGLAS_NEGOCIO_EDUCACION.md): el aviso ofrece DOS vias alternativas y la permisiva es «Associate’s» = titulo academico superior de ciclo corto (escalera: posgrado > titulo universitario > estudiante sin graduar con 80% o mas de creditos > diploma tecnico > bachillerato de secundaria; fuente: U.S. Department of State - InfoUSA, Structure of U.S. Education, usinfo.state.gov/infousa/education/overview/edlite-structure-us.html). El perfil SI tiene ese nivel (Diplomado en Electronica, INTEC) pero NO en el campo que pide el aviso (Electronica, no business/Finance): el NIVEL se cumple, el CAMPO no -> el requisito no se cumple -> BLOQUEO REAL -> la vacante se descarta.
- `workday-Datacenter-Engineer--L3-ERT_1212932-2` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Education: Bachelor's or Master’s degree in Mechanical, Electrical, Computer Science, or equivalent». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Datacenter-Engineer--L3-ERT_1212933-2` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Education: Bachelor's or Master’s degree in Mechanical, Electrical, Computer Science, or equivalent». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Environmental-Program-Manager---Latin-America_R-69389-1` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Education: Bachelor's degree or equivalent in environmental science, environmental engineering». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Governance-Reporting---Analysis-Sr-Analyst---C12---HEREDIA_261007965` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Education : Bachelor's/University degree or equivalent experience». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-HR-Operations-Support-Lead-Analyst_25848722` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Education: Bachelor’s degree/University degree or equivalent experience». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Network-Support-Engineer_1211197` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Higher education (Bachelor or Master degree in electrical engineering or computer science or equivalent )». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Operations-Engineer_R0007464` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Bachelor’s degree in computer science, electronics, telecommunication, or equivalent work experience». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Premium-Support-Engineer-Expert_1210068` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Bachelor's or Master's degree in Mechanical, Electrical, or other Engineering, Computer Science, or equivalent». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Principal-Engineer--Quality_Req-51750` (bloqueo_real): El aviso exige, en «What you'll need (Required): Bachelor's degree in engineering or Scientific field», un titulo universitario en ingenieria (o superior). Las alternativas son titulos SUPERIORES en la misma disciplina («Master's Degree or equivalent», «Ph.D. or equivalent»), no una via por experiencia: sin titulo universitario no hay acceso -> bloqueo real.
- `workday-Production-Supervisor-I_31163511` (dudoso): El aviso pide «80% completeness of a bachelor’s degree program from a four-year college or university». REGLA DE NEGOCIO YA DECIDIDA (2026-11-08; ver docs/REGLAS_NEGOCIO_EDUCACION.md): «80%» es el escalon 'estudiante sin graduar con la mayoria de los creditos completados (80% o mas)', que va POR DEBAJO del titulo universitario y por encima del diploma tecnico (fuente: U.S. Department of State - InfoUSA, Structure of U.S. Education). Lo que falta ya no es la regla sino el DATO del perfil: no hay ningun hecho educativo 'en curso' registrado, asi que no se puede afirmar que el perfil alcance ese escalon. El veredicto queda DUDOSO y el caso ABIERTO: si se registra ese hecho, el motor lo cierra como cumplido; si no, corresponde firmarlo como bloqueo real.
- `workday-Sales-Specialist_R-117581` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «A four year college degree (or additional experience in a related field)». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Security-Governance---Compliance-Specialist_2022361-1` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Bachelor’s degree plus 5+ years of experience in technical compliance, security, risk, audit, or a related field; equivalent practical experience may be considered.». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Security-Governance---Compliance-Specialist_2023168-1` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Must-have Qualifications Bachelor's degree or equivalent work experience required». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Senior-Client-Services-Executive_R2025-244318` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Minimum Bachelor’s degree or its equivalent». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Senior-Engineer---WLAN_1210063-2` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Computer Science, Electrical Engineering, Computer Engineering, or a related discipline, or equivalent practical experience». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Senior-Project-Manager_R13442` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Appropriate Education and Experience: A minimum of a Bachelor's degree or equivalent experience». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-Senior-Specialist--Technical-Training_R576356` (no_bloqueo): El texto ofrece una via alternativa al titulo universitario: «Bachelor’s degree in Business, Education, Human Resources, or related field (or equivalent experience)». No es un bloqueo duro: el requisito educativo no bloquea -> no bloqueo.
- `workday-SharePoint-Application-Developer_R55630-1` (bloqueo_real): El texto dice «Bachelor's Degree with Computer Science / MIS field of study required». El «or equivalent hands-on experience with Microsoft 365 development» se refiere a los estudios AVANZADOS PREFERIDOS («Advanced study preferred»), NO al bachillerato: el titulo es obligatorio -> bloqueo real.

## 7. Medición AMPLIADA de `educacion_no_cumple` (43 casos)

La muestra pequeña inicial (5 de 10) no era suficiente para decidir la
regla. Se amplió a **43 casos** del grupo `educacion_no_cumple` de la
corrida `20261029_171039` (106 vacantes en total):

- **Estrato A (13)**: las 13 que la regla "el texto decide" promovió a
  `descartada` — se revisan **todas**.
- **Estrato B (30)**: 30 sistemáticas de las 93 restantes (una de cada
  tres, ordenadas por `job_id`).

Cada caso se revisó a mano contra la frase literal del aviso.
`Estado final` es el de la corrida vigente `20261108_214123`.

| # | job_id | veredicto manual | por qué | estado final | motivo final |
|---|---|---|---|---|---|
| A1 | `cinde-4901` | BLOQUEO | ESSENCIAL QUALIFICATIONS + Bachelor's degree | descartada | `titulo_universitario_requerido` |
| A2 | `workday-Accounts-Payable-Representative_J-020440` | NO BLOQUEO | via alternativa: 'alternatively, 3+ years of relevant professional experience' | revisar_a_mano | `educacion_no_cumple` |
| A3 | `workday-Business-Analyst--Contract-Pricing-and-Accuracy_R265403` | BLOQUEO | QUALIFICATIONS AND SKILLS + Bachelor's degree | descartada | `titulo_universitario_requerido` |
| A4 | `workday-Continuous-Improvement-Intern_J-020427` | BLOQUEO | estudiante activo: 'Currently pursuing a Bachelor's' | descartada | `titulo_universitario_en_curso_requerido` |
| A5 | `workday-Contract-Administrator--Internship-_1213007` | BLOQUEO | estudiante activo: 'University students actively enrolled' | descartada | `titulo_universitario_en_curso_requerido` |
| A6 | `workday-Contracts-Negotiator_JR-0110562` | BLOQUEO | Basic Qualifications + Bachelor's Degree or above | purgado | purgado |
| A7 | `workday-Director--Corporate-Accounting_JR-0111126` | BLOQUEO | Required Qualifications: Bachelor's degree ... required | descartada | `titulo_universitario_requerido` |
| A8 | `workday-Product-Portfolio-Intern_J-020242` | BLOQUEO | estudiante activo: 'Must be enrolled as a full-time student' | purgado | purgado |
| A9 | `workday-Senior-Analyst--Finance--Internal-Auditor-_Req-51202-1` | BLOQUEO | What you'll need (Required): Bachelor's Degree ... is required | descartada | `titulo_universitario_requerido` |
| A10 | `workday-Senior-Director--Quality-Engineering_Req-50066` | BLOQUEO | What you'll need (Required): Bachelor's Degree | descartada | `titulo_universitario_requerido` |
| A11 | `workday-Service-Delivery-Manager_R77891-2` | BLOQUEO | Qualifications Required Qualifications Bachelor's degree | purgado | purgado |
| A12 | `workday-Sr-Technical-Architect_WD30279546` | BLOQUEO | Qualifications + Bachelor's degree | descartada | `titulo_universitario_requerido` |
| A13 | `workday-Tax-Audit-Senior-Specialist_888004-1` | BLOQUEO | To succeed in this role, you will need the following qualifications: | descartada | `titulo_universitario_requerido` |
| B1 | `cinde-4887` | BLOQUEO | estudiante activo: 'Bachillerato universitario incompleto' | descartada | `titulo_universitario_en_curso_requerido` |
| B2 | `cinde-4892` | BLOQUEO | Job Requirements: Active university student + Currently pursuing | descartada | `titulo_universitario_en_curso_requerido` |
| B3 | `cinde-4898` | BLOQUEO | Formacion: Licenciatura | descartada | `titulo_universitario_requerido` |
| B4 | `workable-valatam-A30B8CD1CD` | NO BLOQUEO | 'Bachelor's or Associate's degree preferred' | datos_insuficientes | `educacion_no_cumple` |
| B5 | `workday-Analista-de-CPFR_887589` | BLOQUEO | Licenciatura o bachillerato universitario (ambos son=title universit.) | purgado | purgado |
| B6 | `workday-Applications-Support-Sr-Analyst_26963530` | NO BLOQUEO | or equivalent experience | purgado | purgado |
| B7 | `workday-Audience-Management_26999789` | NO BLOQUEO | or equivalent experience | revisar_a_mano | `educacion_no_cumple` |
| B8 | `workday-Commercial-Support-Specialist_202609-124777` | NO BLOQUEO | 'Bachelor's or Master's degree preferred' | purgado | purgado |
| B9 | `workday-Content-Review-Operations-Specialist_202610-127168` | NO BLOQUEO | or equivalent experience | purgado | purgado |
| B10 | `workday-Data-Governance-Foundation-Lead-Analyst_26983548` | BLOQUEO | Education: Bachelor's/University degree (el 'preferred' es del Master's) | purgado | purgado |
| B11 | `workday-Datacenter-Engineer--L3-ERT_1212933-2` | NO BLOQUEO | or equivalent (sin calificar) -> conservador | revisar_a_mano | `educacion_no_cumple` |
| B12 | `workday-Digital-Campaign-Delivery-Associate_202609-122817` | BLOQUEO | Further requirements + Bachelor's degree | purgado | purgado |
| B13 | `workday-Director--Manufacturing-Engineering_REQ-2026-18566` | BLOQUEO | Education & Experience + discipline required | descartada | `titulo_universitario_requerido` |
| B14 | `workday-Document-Control-Intern_1210991` | BLOQUEO | estudiante activo: 'pursuing diplomas or degrees' | descartada | `titulo_universitario_en_curso_requerido` |
| B15 | `workday-Escalation-Engineer_1212930-2` | BLOQUEO | What you need to bring: + Bachelor's degree | purgado | purgado |
| B16 | `workday-HR-Generalist-Senior---Global-Discipline-Delivery_261004191` | NO BLOQUEO | or equivalent experience | purgado | purgado |
| B17 | `workday-Ingeniero-Principal-de-OpEx_20188241` | NO BLOQUEO | preferred Bachelor's degree / or equivalent work experience | revisar_a_mano | `educacion_no_cumple` |
| B18 | `workday-Intern---Bachelors-Tech_1214077` | BLOQUEO | estudiante activo: 'actively enrolled ... pursuing a Bachelor's degree' | purgado | purgado |
| B19 | `workday-Lead-Mobile-Application-Engineer--NET-MAUI-_R18405` | NO BLOQUEO | or equivalent practical experience | revisar_a_mano | `educacion_no_cumple` |
| B20 | `workday-Network-Support-Engineer_1211197` | NO BLOQUEO | or equivalent | revisar_a_mano | `educacion_no_cumple` |
| B21 | `workday-Principal-Engineer--Quality_Req-51750` | NO BLOQUEO | or equivalent | descartada | `titulo_universitario_requerido` |
| B22 | `workday-Programmatic-Media-Associate---Citi-Commerce_261002988` | NO BLOQUEO | or equivalent experience | revisar_a_mano | `educacion_no_cumple` |
| B23 | `workday-Regulatory-Specialist-Diagnostics_202610-126607` | NO BLOQUEO | or equivalent experience | purgado | purgado |
| B24 | `workday-Sales-Commercial-Manager_R-257732` | BLOQUEO | Role Requirements + Bachelor's degree | purgado | purgado |
| B25 | `workday-Senior-Data-Scientist---ML-Engineering---MLOps_202609-123431` | NO BLOQUEO | 'Who You Are' es ambiguo -> se deja en revision | purgado | purgado |
| B26 | `workday-Software-Engineering-Systems--Intern_1210981` | BLOQUEO | estudiante activo: 'Education & Experience: Currently pursuing' | descartada | `titulo_universitario_en_curso_requerido` |
| B27 | `workday-Sr-Customer-Service-Representative_R-01366409` | NO BLOQUEO | 'preferred but not essential' | revisar_a_mano | `educacion_no_cumple` |
| B28 | `workday-Strategy---Business-Operations-Head---CAMCAR_R-255612` | BLOQUEO | Role Requirements Education + Bachelor's Degree | purgado | purgado |
| B29 | `workday-Switching-Technical-Support-Engineer-Intern---Switching-Support---EX-Products_1214133` | BLOQUEO | estudiante activo: 'Education and Experience Currently pursuing' | descartada | `titulo_universitario_en_curso_requerido` |
| B30 | `workday-Technical-Project-Manager---HiredScore_JR-0108592-1` | NO BLOQUEO | Preferred Qualifications + Bachelor's degree | revisar_a_mano | `educacion_no_cumple` |

> 16 de los 43 avisos de la muestra ya NO están en la BD actual (purgados por una limpieza posterior): se listan con `purgado` y no entran en el cómputo.

**Resultado: 26 de 27 verificables coinciden con el veredicto manual.**

- Estrato A: 12 de 13 eran bloqueos reales; **1 falso descarte**
  (`workday-Accounts-Payable-Representative_J-020440`: "… and 1+ year of
  relevant experience; **alternatively, 3+ years of relevant professional
  experience**") → corregido por la regla.
- Estrato B: 14 de 30 eran bloqueos reales que el motor NO detectaba
  (falsos negativos) → promovidos con frase literal.
- Proporción de bloqueos reales en la muestra: **26 de 43 (60%)**; la
  muestra inicial daba 5 de 10 (50%%). La proporción **se mantiene o
  sube** → la regla NO estaba sobreajustada.
- La regla nueva acierta en **26 de 27** casos verificables: donde el
  texto obliga descarta y donde el texto no obliga deja la vacante para
  revisión.

### 6.1. Frase literal de cada caso

- **A1 `cinde-4901`** — ESSENCIAL QUALIFICATIONS + Bachelor's degree
  > Formación: Bachillerato universitario completo.
- **A2 `workday-Accounts-Payable-Representative_J-020440`** — via alternativa: 'alternatively, 3+ years of relevant professional experience'
  > Minimum Qualifications Bachelor’s degree coursework in Accounting, Finance, Business Administration, or a related discipline and 1+ year of relevant experience
- **A3 `workday-Business-Analyst--Contract-Pricing-and-Accuracy_R265403`** — QUALIFICATIONS AND SKILLS + Bachelor's degree
  > QUALIFICATIONS AND SKILLS: Bachelor’s degree in Industrial Engineering, Business Administration, or a related field.
- **A4 `workday-Continuous-Improvement-Intern_J-020427`** — estudiante activo: 'Currently pursuing a Bachelor's'
  > Minimum Qualifications Currently pursuing a Bachelor's or Licentiate degree in Industrial Engineering, with more than 75% of the degree program completed.
- **A5 `workday-Contract-Administrator--Internship-_1213007`** — estudiante activo: 'University students actively enrolled'
  > Job Description: Job Family Definition: Students pursuing a Bachelor's degree in Business Administration, Industrial Engineering, Finance, Accounting or related fields.
- **A6 `workday-Contracts-Negotiator_JR-0110562`** — Basic Qualifications + Bachelor's Degree or above
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **A7 `workday-Director--Corporate-Accounting_JR-0111126`** — Required Qualifications: Bachelor's degree ... required
  > About You Required Qualifications: Bachelor’s degree in Accounting, Finance, or a related field required.
- **A8 `workday-Product-Portfolio-Intern_J-020242`** — estudiante activo: 'Must be enrolled as a full-time student'
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **A9 `workday-Senior-Analyst--Finance--Internal-Auditor-_Req-51202-1`** — What you'll need (Required): Bachelor's Degree ... is required
  > Bachelor's Degree in related field is required
- **A10 `workday-Senior-Director--Quality-Engineering_Req-50066`** — What you'll need (Required): Bachelor's Degree
  > ...What you'll need (Required): Bachelor's Degree in related field with at least 10 years experience in engineering and leadership positions in the medical device industry Experience in Quality Engineering, Quality Management, and/o...
- **A11 `workday-Service-Delivery-Manager_R77891-2`** — Qualifications Required Qualifications Bachelor's degree
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **A12 `workday-Sr-Technical-Architect_WD30279546`** — Qualifications + Bachelor's degree
  > Qualifications Bachelor’s degree in IT or a similar technology-related discipline.
- **A13 `workday-Tax-Audit-Senior-Specialist_888004-1`** — To succeed in this role, you will need the following qualifications:
  > To succeed in this role, you will need the following qualifications: Bachelor's degree in finance, accounting, internal control or related field along with experience in USGAAP, preparing Income Tax Returns, Informative reports, compliance reports and attending tax audits.
- **B1 `cinde-4887`** — estudiante activo: 'Bachillerato universitario incompleto'
  > Formación: Bachillerato universitario incompleto.
- **B2 `cinde-4892`** — Job Requirements: Active university student + Currently pursuing
  > Formación: Bachillerato universitario incompleto.
- **B3 `cinde-4898`** — Formacion: Licenciatura
  > Formación: Licenciatura.
- **B4 `workable-valatam-A30B8CD1CD`** — 'Bachelor's or Associate's degree preferred'
  > - Bachelor’s or Associate’s degree preferred.
- **B5 `workday-Analista-de-CPFR_887589`** — Licenciatura o bachillerato universitario (ambos son=title universit.)
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **B6 `workday-Applications-Support-Sr-Analyst_26963530`** — or equivalent experience
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **B7 `workday-Audience-Management_26999789`** — or equivalent experience
  > ...Digital Marketing and Email Deployment experience a plus Education: Bachelors/University degree or equivalent experience ------------------------------------------------------ Job Family Group: Marketing ------------------------------------------------------ Job Famil...
- **B8 `workday-Commercial-Support-Specialist_202609-124777`** — 'Bachelor's or Master's degree preferred'
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **B9 `workday-Content-Review-Operations-Specialist_202610-127168`** — or equivalent experience
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **B10 `workday-Data-Governance-Foundation-Lead-Analyst_26983548`** — Education: Bachelor's/University degree (el 'preferred' es del Master's)
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **B11 `workday-Datacenter-Engineer--L3-ERT_1212933-2`** — or equivalent (sin calificar) -> conservador
  > Education: Bachelor's or Master’s degree in Mechanical, Electrical, Computer Science, or equivalent.
- **B12 `workday-Digital-Campaign-Delivery-Associate_202609-122817`** — Further requirements + Bachelor's degree
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **B13 `workday-Director--Manufacturing-Engineering_REQ-2026-18566`** — Education & Experience + discipline required
  > Education & Experience Bachelor’s degree in Manufacturing, Mechanical, Electrical, Industrial, or a related Engineering discipline required
- **B14 `workday-Document-Control-Intern_1210991`** — estudiante activo: 'pursuing diplomas or degrees'
  > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
- **B15 `workday-Escalation-Engineer_1212930-2`** — What you need to bring: + Bachelor's degree
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **B16 `workday-HR-Generalist-Senior---Global-Discipline-Delivery_261004191`** — or equivalent experience
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **B17 `workday-Ingeniero-Principal-de-OpEx_20188241`** — preferred Bachelor's degree / or equivalent work experience
  > ...Qualifications 4-8 years of experience, preferred Bachelor's degree in related field, or equivalent work experience, preferred English Advanced CSSBB or ready to be certified, Project management skills preferred What is expected of you and others at ...
- **B18 `workday-Intern---Bachelors-Tech_1214077`** — estudiante activo: 'actively enrolled ... pursuing a Bachelor's degree'
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **B19 `workday-Lead-Mobile-Application-Engineer--NET-MAUI-_R18405`** — or equivalent practical experience
  > ...What We Look For Bachelor’s degree in Computer Science, Engineering, or a related field, or equivalent practical experience 7+ years of professional software development experience, including substantial hands-on expe...
- **B20 `workday-Network-Support-Engineer_1211197`** — or equivalent
  > ...able tools is an essential element of the role Develop a "Can-Do" attitude and suggest ways to improve the team performance and increase customer's satisfaction Basic Qualifications Higher education (Bachelor or Master degree in electrical engineering or computer science or equivalent ) 3+ years of working experience in a network support role, 2-3 of these years would be spent supporting large IP ...
- **B21 `workday-Principal-Engineer--Quality_Req-51750`** — or equivalent
  > Other incidental duties What you'll need (Required): Bachelor's degree in engineering or Scientific field, 6 years of experience minimum of experience, including either industry or industry/education or Master's Degree or equivalent in Engineering or Scientific field, 5 years of experience minimum of experience, including either industry or industry/education or Ph.D.
- **B22 `workday-Programmatic-Media-Associate---Citi-Commerce_261002988`** — or equivalent experience
  > ...ng and delivery aligned to campaign goals Experience providing clear, timely campaign reporting and issue resolutions Experience documenting operational playbooks and trafficking standards Education: Bachelors/University degree or equivalent experience (Highly preferred bachelor’s degree in Business, Marketing, or related field) This job description provides a high-level review of the types of wor...
- **B23 `workday-Regulatory-Specialist-Diagnostics_202610-126607`** — or equivalent experience
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **B24 `workday-Sales-Commercial-Manager_R-257732`** — Role Requirements + Bachelor's degree
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **B25 `workday-Senior-Data-Scientist---ML-Engineering---MLOps_202609-123431`** — 'Who You Are' es ambiguo -> se deja en revision
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **B26 `workday-Software-Engineering-Systems--Intern_1210981`** — estudiante activo: 'Education & Experience: Currently pursuing'
  > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
- **B27 `workday-Sr-Customer-Service-Representative_R-01366409`** — 'preferred but not essential'
  > Preferred Qualifications A Bachelor’s Degree is preferred but not essential.
- **B28 `workday-Strategy---Business-Operations-Head---CAMCAR_R-255612`** — Role Requirements Education + Bachelor's Degree
  > (purgado en la limpieza 2026-10-31: sin frase verificable)
- **B29 `workday-Switching-Technical-Support-Engineer-Intern---Switching-Support---EX-Products_1214133`** — estudiante activo: 'Education and Experience Currently pursuing'
  > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
- **B30 `workday-Technical-Project-Manager---HiredScore_JR-0108592-1`** — Preferred Qualifications + Bachelor's degree
  > ...ers and internal teams even when priorities or requirements are evolving Strong problem-solving skills, with the ability to troubleshoot technical issues and drive resolution Preferred Qualifications Bachelor’s degree in Business, Information Systems, Industrial Engineering, or a related field 2+ years of experience delivering AI-enabled solutions, intelligent automation, or ML-powered features wi...

## 8. DELTA vs. la corrida anterior `20261108_213837` (0 avisos cambian)

Cada cambio se midió ANTES de escribir la corrida nueva (evaluación en
seco contra la BD) y aquí queda documentado con la frase literal del
aviso.

| # | job_id | antes | ahora | por qué |
|---|---|---|---|---|

### 7.1. Frase literal de cada cambio

