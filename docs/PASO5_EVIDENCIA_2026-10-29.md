# Paso 5 — Evidencia del bloqueante educativo (corrida `20261029_205348`)

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

## 2. Trazabilidad de corridas (`job_match`)

```
corrida          filas  valida=1
20261029_132455  447    0
20261029_133621  447    0
20261029_160358  447    0
20261029_170343  447    0
20261029_171039  447    0
20261029_183231  447    0
20261029_205348  447    447
```

## 3. Conteo por estado y motivo (corrida vigente `20261029_205348`)

```
calificada             | cumple_umbral                          | 102
datos_insuficientes    | cobertura_insuficiente                 | 27
datos_insuficientes    | educacion_no_cumple                    | 2
datos_insuficientes    | skill_faltante                         | 1
descartada             | titulo_universitario_en_curso_requerido | 24
descartada             | titulo_universitario_requerido         | 56
revisar_a_mano         | educacion_no_confirmada                | 19
revisar_a_mano         | educacion_no_cumple                    | 57
revisar_a_mano         | experiencia_no_verificable             | 4
revisar_a_mano         | licencia_no_comparable                 | 3
revisar_a_mano         | skill_faltante                         | 11
sin_requisitos         | sin_requisitos_mapeados                | 141
```

## 4. Las 80 `descartada` — evidencia literal

### 1. `cinde-4887` — Engineering Consultant Apprentice- TMV execution - Medical Device #2612

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachillerato universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachillerato universitario'` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Formación: Bachillerato universitario incompleto.

> Formación: Bachillerato universitario incompleto.
>
> contexto: ...Categoría: Calidad. Nivel: Profesional Jr.. Experiencia: de 1 a 2 años. Formación: Bachillerato universitario incompleto. Idiomas: Inglés-B2+. Modalidad: Presencial What you'll do Support Stack Analysis Support the design of plastic parts in SolidWorks. Support the development of Test Methods: Protocols gene...

### 2. `cinde-4888` — IT Software Developer II

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

### 3. `cinde-4889` — IT Systems Engineer II

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

### 4. `cinde-4890` — Cloud Engineer III

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachillerato universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachillerato universitario'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Formación: Bachillerato universitario completo.

> Formación: Bachillerato universitario completo.
>
> contexto: ...Categoría: Soporte Técnico. Nivel: Profesional Sr.. Experiencia: de 5 a 8 años. Formación: Bachillerato universitario completo. Idiomas: Inglés-B2. Modalidad: 100% virtual AWS FinOps Engineer III Job Description At World Fuel Services, our employees are key to our global success. We are industry leaders because of t...

### 5. `cinde-4892` — AI Finance Intern

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

### 6. `cinde-4896` — Lead Data Engineer

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachillerato universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachillerato universitario'` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Formación: Bachillerato universitario incompleto.

> Formación: Bachillerato universitario incompleto.
>
> contexto: ...Categoría: Informática / Sistemas. Nivel: Profesional. Experiencia: de 3 a 5 años. Formación: Bachillerato universitario incompleto. Idiomas: Inglés-B2. Modalidad: Híbrido. Vacantes: 3 We are looking for a Lead Data Engineer who will be responsible for defining data engineering standards, building reusable patterns, me...

### 7. `cinde-4897` — Full Stack Lead Engineer

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachillerato universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachillerato universitario'` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Formación: Bachillerato universitario incompleto.

> Formación: Bachillerato universitario incompleto.
>
> contexto: ...Categoría: Informática / Sistemas. Nivel: Profesional. Experiencia: de 3 a 5 años. Formación: Bachillerato universitario incompleto. Idiomas: Inglés-B2. Modalidad: Híbrido. Vacantes: 5 We are seeking an experienced Full Stack Lead Engineer to drive engineering excellence, mentor technical talent, and support the delive...

### 8. `cinde-4898` — Lead Software Engineer

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Formación: Licenciatura.

> Formación: Licenciatura.
>
> contexto: ...Categoría: Diseño de Software. Nivel: Supervisores/Líderes de Equipo. Experiencia: de 5 a 8 años. Formación: Licenciatura. Idiomas: Inglés-C1;Español-C2. Modalidad: Híbrido We are looking for an experienced Lead Software Engineer / Chapter Lead who combines strong hands-on technical expertise with engineering leadership...

### 9. `cinde-4901` — Regulatory Affairs Specialist

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

### 10. `workday-Accounting-Analyst-I_R-01369018` — Accounting Analyst I

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's Degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > REQUIREMENTS: • Bachelor's Degree required with 4 years of previous experience • Preferred Fields of Study: Accounting, Finance, or related field • Professional accounting qualification (CPA, ACCA, CIMA) is advantageous • Proficiency in major ERP systems (SAP, Oracle, JD Edwards) and Microsoft Excel • Strong understanding of accounting principles, month-end close processes, and financial controls • Advanced analytical and problem-solving capabilities with high attention to detail • Excellent written and verbal communication skills in English • Experience with account reconciliations and journal entry preparation • Knowledge of SOX compliance and internal control frameworks • Strong organizational skills with ability to meet strict deadlines • Proven ability to work independently while collaborating effectively across teams • Experience with financial reporting tools and systems (Hyperion, BlackLine) preferred • System automation and process improvement mindset • Customer-focused approach with ability to build strong stakeholder relationships • Ability to adapt to new technologies and processes • Demonstrated commitment to integrity and professional ethics

> Bachelor's Degree required with 4 years of previous experience
>
> contexto: ...lts. • Find a better way every day. Problem Solving. • Attention to detail. • Presentation skills. • Prioritization. • Pro-activeness. • Drives engagement. • Communicates effectively. REQUIREMENTS: • Bachelor's Degree required with 4 years of previous experience • Preferred Fields of Study: Accounting, Finance, or related field • Professional accounting qualification (CPA, ACCA, CIMA) is advantageous • Prof...

### 11. `workday-Accounting-Team-Lead_J-020415` — Accounting Team Lead

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications Bachelor Accounting Degree required 7+ years of accounting experience 2+ years of supervisory or people leadership experience Advanced English Skills and knowledge Strong analytical skills Proficient with MS Excel.

> Minimum Qualifications Bachelor Accounting Degree required 7+ years of accounting experience 2+ years of supervisory or people leadership experience Advanced English Skills and knowledge Strong analytical skills Proficient with MS Excel.
>
> contexto: ...ur office in AFZ, Heredia on Mondays, Wednesdays, and Thursdays. Please note that there may be occasions where additional office days are required, due specific business needs. Minimum Qualifications Bachelor Accounting Degree required 7+ years of accounting experience 2+ years of supervisory or people leadership experience Advanced English Skills and knowledge Strong analytical skills Proficient with MS...

### 12. `workday-Analista-de-CPFR_887589` — Analista de CPFR

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Para tener éxito en este puesto, necesitarás las siguientes calificaciones: Licenciatura o bachillerato universitario en Administración de Empresas, Ingeniería Industrial, Logística, Supply Chain o una carrera afín.

> Para tener éxito en este puesto, necesitarás las siguientes calificaciones: Licenciatura o bachillerato universitario en Administración de Empresas, Ingeniería Industrial, Logística, Supply Chain o una carrera afín.
>
> contexto: ...tes foros, participando activamente en las conversaciones y respondiendo a las necesidades de los principales stakeholders. Para tener éxito en este puesto, necesitarás las siguientes calificaciones: Licenciatura o bachillerato universitario en Administración de Empresas, Ingeniería Industrial, Logística, Supply Chain o una carrera afín. 3+ años de experiencia en posiciones de CPFR . Experiencia previa maneja...

### 13. `workday-Analyst--Compensation_Req-51280` — Analyst, Compensation

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What You'll Need (Required): Bachelor's degree in human resources, Business Administration, Finance, Economics, or a related field and minimum 3 years of experience in Compensation, Human Resources, or related roles.

> What You'll Need (Required): Bachelor's degree in human resources, Business Administration, Finance, Economics, or a related field and minimum 3 years of experience in Compensation, Human Resources, or related roles.
>
> contexto: ...tion. Support continuous improvement initiatives that enhance compensation programs, tools, and operational effectiveness. Perform other duties as assigned by management. What You'll Need (Required): Bachelor's degree in human resources, Business Administration, Finance, Economics, or a related field and minimum 3 years of experience in Compensation, Human Resources, or related roles. What Else We Look For...

### 14. `workday-Associate-Manager-Technical-Services_R567836` — Associate Manager Technical Services

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.

> What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.
>
> contexto: ...as the operational backup for the Technical Services leader, ensuring continuity of decision-making, prioritization, and execution across the organization. What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field. Minimum 7 years of experience in Quality Engineering, Technical Services, Microbiology, Sterilization, Calibrations, Receiving Inspection, or relat...

### 15. `workday-Business-Analyst--Contract-Pricing-and-Accuracy_R265403` — Business Analyst, Contract Pricing and Accuracy

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > QUALIFICATIONS AND SKILLS: Bachelor’s degree in Industrial Engineering, Business Administration, or a related field.

> QUALIFICATIONS AND SKILLS: Bachelor’s degree in Industrial Engineering, Business Administration, or a related field.
>
> contexto: ...em. Create and maintain user guides, and conduct workshops as needed. Generate reports and dashboards to provide insights into contract status, compliance, and performance. QUALIFICATIONS AND SKILLS: Bachelor’s degree in Industrial Engineering, Business Administration, or a related field. 3 years of experience as a Business Analyst or similar role with emphasis on areas such as contract management, pricing...

### 16. `workday-Business-Operations---Customer-Delivery-Intern_3170188-1` — Business Operations & Customer Delivery Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text="bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university.

> Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university.
>
> contexto: ...hnology journey to drive business outcomes, enhance employee experiences, and accelerate innovation. Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university. Preferred Majors/Programs: Business Administration Finance Economics Industrial Engineering Business Analytics Data Ana...

### 17. `workday-Business-Process-Automation---Data-Analytics-Intern_3170183-1` — Business Process Automation & Data Analytics Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text="bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university.

> Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university.
>
> contexto: ...hnology journey to drive business outcomes, enhance employee experiences, and accelerate innovation. Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university. Preferred Majors/Programs: Computer Science Data Engineering / Data Analytics Industrial Engineering Process Engineerin...

### 18. `workday-Buyer-GPC_R571353` — Buyer GPC

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Required Qualifications Bachelor’s degree in Supply Chain Management, Business Administration, Industrial Engineering, Operations Management, or a related field.

> Required Qualifications Bachelor’s degree in Supply Chain Management, Business Administration, Industrial Engineering, Operations Management, or a related field.
>
> contexto: ...oject progress, and operational results. Support strategic initiatives, including product lifecycle management, cost reduction projects, and supply chain optimization efforts. Required Qualifications Bachelor’s degree in Supply Chain Management, Business Administration, Industrial Engineering, Operations Management, or a related field. Minimum 3 years of experience in purchasing, supply planning, materials...

### 19. `workday-Buyer-Procurement-Operations_J-020161` — Buyer Procurement Operations

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications Bachelor's degree in Logistics, Supply Chain, Engineering, Business Administration, or a related field.

> Minimum Qualifications Bachelor's degree in Logistics, Supply Chain, Engineering, Business Administration, or a related field.
>
> contexto: ...ur office in AFZ, Heredia on Mondays, Wednesdays, and Thursdays. Please note that there may be occasions where additional office days are required, due specific business needs. Minimum Qualifications Bachelor's degree in Logistics, Supply Chain, Engineering, Business Administration, or a related field. Experience/educational requirements may be waived for internal candidates. 1+ years of direct experience i...

### 20. `workday-Buyer-Procurement-Operations_J-020337` — Buyer Procurement Operations

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications : Bachelor’s degree in Logistics, Supply Chain, Engineering, Business Administration or related with 1+ years of related experience.

> Minimum Qualifications : Bachelor’s degree in Logistics, Supply Chain, Engineering, Business Administration or related with 1+ years of related experience.
>
> contexto: ...office in AFZ, Heredia on Mondays, Wednesdays, and Thursdays. Please note that there may be occasions where additional office days are required, due specific business needs. Minimum Qualifications : Bachelor’s degree in Logistics, Supply Chain, Engineering, Business Administration or related with 1+ years of related experience. Understanding of procurement and purchasing processes. Proficiency in Microsoft...

### 21. `workday-Canada-P-F-Lead_548946-1` — Canada P&F Lead

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Basic Requirements Bachelor’s degree in Finance, Accounting, Economics, Business Administration, or related discipline.

> Basic Requirements Bachelor’s degree in Finance, Accounting, Economics, Business Administration, or related discipline.
>
> contexto: ...ties and obtain feedback. Document P&F processes, deliverables, model logic, and control points. Identify opportunities to standardize, simplify, and automate recurring activities. Basic Requirements Bachelor’s degree in Finance, Accounting, Economics, Business Administration, or related discipline. Minimum 5–8 years of progressive experience in Financial Planning & Analysis, Planning & Forecasting, Finance...

### 22. `workday-Compensation-Analyst_R268777` — Compensation Analyst

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Provide support to Senior Analysts and Leadership regarding all compensation related projects and initiatives Education Required: Bachelor’s degree in human resources, Business Administration, Finance, or related field.

> Provide support to Senior Analysts and Leadership regarding all compensation related projects and initiatives Education Required: Bachelor’s degree in human resources, Business Administration, Finance, or related field.
>
> contexto: ...s. Support the payroll team with the WCC or SOC codes when necessary. Provide support to Senior Analysts and Leadership regarding all compensation related projects and initiatives Education Required: Bachelor’s degree in human resources, Business Administration, Finance, or related field. Excellent communication skills in English (B2+ or higher) and ability to collaborate across functions and geographies. 2...

### 23. `workday-Continuous-Improvement-Intern_J-020427` — Continuous Improvement Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications Currently pursuing a Bachelor's or Licentiate degree in Industrial Engineering, with more than 75% of the degree program completed.

> Minimum Qualifications Currently pursuing a Bachelor's or Licentiate degree in Industrial Engineering, with more than 75% of the degree program completed.
>
> contexto: ...when additional office days are required due to specific business needs. The candidate must have an unrestricted right to work for Huntsman in Costa Rica. Minimum Qualifications Currently pursuing a Bachelor's or Licentiate degree in Industrial Engineering, with more than 75% of the degree program completed. Demonstrated interest in Continuous Improvement, problem-solving, and process optimization. Written...

### 24. `workday-Contract-Administrator--Internship-_1213007` — Contract Administrator (Internship)

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

### 25. `workday-Contract-Pricing-Team-Lead_R265399` — Contract Pricing Team Lead

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Qualifications and Skills Bachelor's degree in Business Administration or a related field required.

> Qualifications and Skills Bachelor's degree in Business Administration or a related field required.
>
> contexto: ...ghts clearly and effectively. Support change management efforts tied to process or system enhancements. Provide training and support to end-users on new tools and workflows. Qualifications and Skills Bachelor's degree in Business Administration or a related field required. Excellent communication skills in English (B2+ or higher) and ability to collaborate across functions and geographies. Minimum 5 years o...

### 26. `workday-Contracts-Negotiator_JR-0110562` — Contracts Negotiator

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Review proposed modifications to contracts and work with internal business partners and third parties to negotiate terms, and obtain approvals for modifications as required Draft and revise contract wording to address various situations as they arise Maintain processes between the legal department and other groups and collaborate on ways to continually improve the contracts administration process Provide support to in-house legal staff, including research, correspondence and record-keeping Execute assigned projects as determined by needs of the business and department About You Basic Qualifications 5+ years of experience managing contracts (including drafting and negotiation) in a corporate environment Bachelor’s Degree or above Experience in a law firm or legal department is required Licensed attorney is desired but not required Other Qualifications Proficient in Microsoft Office products and Google applications Experience with a contract management system, e.g..

> ...projects as determined by needs of the business and department About You Basic Qualifications 5+ years of experience managing contracts (including drafting and negotiation) in a corporate environment Bachelor’s Degree or above Experience in a law firm or legal department is required Licensed attorney is desired but not required Other Qualifications Proficient in Microsoft Office products and Googl...
>
> contexto: ...projects as determined by needs of the business and department About You Basic Qualifications 5+ years of experience managing contracts (including drafting and negotiation) in a corporate environment Bachelor’s Degree or above Experience in a law firm or legal department is required Licensed attorney is desired but not required Other Qualifications Proficient in Microsoft Office products and Google applicat...

### 27. `workday-Cybersecurity-Analyst---Monitoring---Incident-Response_202604-108991-1` — Cybersecurity Analyst - Monitoring & Incident Response

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=False · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Responsibilities: Monitoring and Incident Response for a global environment Take decisions, often under pressure, given partial information Contribute to proactive threat detection efforts Lead containment and remediation efforts during active security incidents Perform forensic analysis of relevant artifacts to support investigations Contribute to detection engineering activities across a global team Brief team members and leadership on relevant threats to the Roche group Communicate information security concepts and situations to senior management Contribute operational feedback to continuously strengthen detection and response processes Mentor newer team members Who You Are: Bachelor’s degree in a technical field and 7+ years of experience in information security, including at least 3 years in a SOC/CERT/CSIRT environment Familiarity with TLP and information sharing best practices Ability to communicate information security-related concepts and situations to a non-technical audience Demonstrated ability to analyze, triage, and escalate information security incidents Knowledge of detection engineering and threat-hunting concepts Scripting and programming skills (Python, Javascript, Go, Rust, …) Demonstrated knowledge of operating systems (Windows, Linux, macOs) Excellent organization and communication skills.

> ...te information security concepts and situations to senior management Contribute operational feedback to continuously strengthen detection and response processes Mentor newer team members Who You Are: Bachelor’s degree in a technical field and 7+ years of experience in information security, including at least 3 years in a SOC/CERT/CSIRT environment Familiarity with TLP and information sharing best ...
>
> contexto: ...te information security concepts and situations to senior management Contribute operational feedback to continuously strengthen detection and response processes Mentor newer team members Who You Are: Bachelor’s degree in a technical field and 7+ years of experience in information security, including at least 3 years in a SOC/CERT/CSIRT environment Familiarity with TLP and information sharing best practices...

### 28. `workday-Data-Analytics-Intern_1210982` — Data Analytics Intern

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

### 29. `workday-Data-Governance-Foundation-Lead-Analyst_26983548` — Data Governance Foundation Lead Analyst

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Responsibilities: Partner with multiple teams to implement relevant Data Governance policies and/or Data Risk and Control framework Provide expertise on Data Governance and/or Data Risk and Controls framework including design, effectiveness, performance monitoring and self-assessment processes Oversight and analysis of data-related issues, tracking of ownership and target dates and associated metrics and reporting Support and coordinate with business lines and global functions on enterprise Data Governance strategy roll out, including new Data risk taxonomy and associated changes to key risk indicators and control framework Gather and synthesize metrics on existing Data Governance and/or Data Risk and Controls principles, policies, practices and standards, e.g., understanding industry best practices Produce recommendations for enterprise-wide guiding principles, policies, processes and practices Determine requirements for and prioritize development of new enterprise-wide principles, policies, processes and practices as needed Develop and manage approach for measuring adoption of principles, policies, processes and practices Recommended Qualifications : 6-10 years relevant experience in a Data Governance/ Data Management/ Process Engineering or related area Advanced understanding of Project Management methodologies and tools Requires basic commercial awareness Ability to monitor tight deadlines or unexpected requirement changes, with the ability to anticipate and balance needs of multiple stakeholders Ability to communicate effectively to develop and deliver multi-mode communications that convey a clear understanding of the unique needs of different audiences Education: Bachelor's/University degree, Master's degree preferred •Working Environment: office setting, minimal travelling and working hours in the office may be required during projects.

> ...ds of multiple stakeholders Ability to communicate effectively to develop and deliver multi-mode communications that convey a clear understanding of the unique needs of different audiences Education: Bachelor's/University degree, Master's degree preferred...
>
> contexto: ...ds of multiple stakeholders Ability to communicate effectively to develop and deliver multi-mode communications that convey a clear understanding of the unique needs of different audiences Education: Bachelor's/University degree, Master's degree preferred •Working Environment: office setting, minimal travelling and working hours in the office may be required during projects. • Effort: minimal physical effor...

### 30. `workday-Digital-Campaign-Delivery-Associate_202609-122817` — Digital Campaign Delivery Associate

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Further requirements ● Bachelor's degree in Marketing, Business, Communications, or a related field.

> Further requirements ● Bachelor's degree in Marketing, Business, Communications, or a related field.
>
> contexto: ...ficiently, ensuring timely and high- quality delivery. You excel at collaborating with diverse stakeholders and adapting to their feedback to meet their needs and expectations. Further requirements ● Bachelor's degree in Marketing, Business, Communications, or a related field. ● Strong understanding of digital marketing principles and campaign management. ● Excellent organizational and multitasking abilitie...

### 31. `workday-Director--Corporate-Accounting_JR-0111126` — Director, Corporate Accounting

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > About You Required Qualifications: Bachelor’s degree in Accounting, Finance, or a related field required.

> About You Required Qualifications: Bachelor’s degree in Accounting, Finance, or a related field required.
>
> contexto: ...accounting operations and decision-making. Ensure work is appropriately prioritized, documented, controlled, and aligned with broader Accounting and Finance goals. About You Required Qualifications: Bachelor’s degree in Accounting, Finance, or a related field required. 10+ years of progressive accounting experience, including significant corporate accounting leadership experience. Solid working knowledge o...

### 32. `workday-Director--Manufacturing-Engineering_REQ-2026-18566` — Director, Manufacturing Engineering

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

### 33. `workday-Director--Manufacturing-Operations_REQ-2026-18565-1` — Director, Manufacturing Operations

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

### 34. `workday-Director--Quality-Operations_REQ-2026-18476` — Director, Quality Operations

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

### 35. `workday-Document-Control-Intern_1210991` — Document Control Intern

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

### 36. `workday-Embedded-Software-Engineer-Internship_1214117` — Embedded Software Engineer Internship

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

### 37. `workday-Escalation-Engineer_1212930-2` — Escalation Engineer

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > ________________________________________ Required Technical Skills (L2 Level) Advanced Networking • Deep understanding of: o Layer 2/Layer 3 protocols o Routing convergence & failure detection o High availability campus & data-center designs • Strong packet-level troubleshooting using PCAPs ________________________________________ Aruba Switching Mastery • Expert-level knowledge of: o AOS-CX architecture o VSX o Advanced LACP o Central Managed Switching • Familiarity with: o AOS-CX REST APIs (basic awareness) o Automation & telemetry ________________________________________ System & Debugging Tools • Linux log analysis • Core-dump and crash file interpretation • Wireshark advanced filters • Python for basic log parsing (nice to have) ________________________________________ Soft Skills & Leadership • Executive-level communication during outages • Strong ownership mindset • Cross-functional collaboration skills • Technical coaching & mentorship ability • Calm decision-making under pressure ________________________________________ What you need to bring: • Bachelor’s degree in Engineering / Computer Science / IT • 2-4 years of experience in: o Enterprise switching TAC o Network engineering o Data-center / campus networking ________________________________________ Preferred Certifications • Aruba ACSP/ACSX • CCNP Enterprise / Data Center • ITIL Expert (nice to have) ________________________________________ Key Performance Indicators (KPIs) • Mean Time to Resolution (MTTR) • Escalation Effectiveness • RCA Quality Score • Sev-1 Recovery Time • CSAT & Executive Satisfaction • L1 Coaching & Readiness Metrics Accessibility HPE is committed to creating an inclusive and accessible workplace and encourages applications from all qualified individuals, including those with disabilities.

> Bachelor’s degree in Engineering / Computer Science / IT
>
> contexto: ...ship mindset • Cross-functional collaboration skills • Technical coaching & mentorship ability • Calm decision-making under pressure ________________________________________ What you need to bring: • Bachelor’s degree in Engineering / Computer Science / IT • 2-4 years of experience in: o Enterprise switching TAC o Network engineering o Data-center / campus networking ________________________________________...

### 38. `workday-Global-Supply-Chain-Data-Analyst--Temporary-_J-019858` — Supply Chain Data Analyst (Temporary)

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications • Bachelor’s degree in Supply Chain Management, Business Analytics, Industrial Engineering, or a related field.

> Bachelor’s degree in Supply Chain Management, Business Analytics, Industrial Engineering, or a related field.
>
> contexto: ...s, and Thursdays. Please note that there may be occasions where additional office days are required, especially during corporate visits or when specific business needs arise. Minimum Qualifications • Bachelor’s degree in Supply Chain Management, Business Analytics, Industrial Engineering, or a related field. • 5+ years of experience in supply chain analytics or a related role. • Strong proficiency in data a...

### 39. `workday-Ingeniero-de-Manufactura_20186958` — Ingeniero de Manufactura

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Requirements Bachelor’s Degree in Industrial Engineering, Mechanical Engineering, Electromechanical Engineering, Electrical/Electronic Engineering, or related engineering discipline.

> Requirements Bachelor’s Degree in Industrial Engineering, Mechanical Engineering, Electromechanical Engineering, Electrical/Electronic Engineering, or related engineering discipline.
>
> contexto: ...ross-functional teams. Ensure compliance with GMP, FDA, ISO 13485, and applicable regulatory requirements. Provide technical leadership, training, and support to manufacturing personnel. Requirements Bachelor’s Degree in Industrial Engineering, Mechanical Engineering, Electromechanical Engineering, Electrical/Electronic Engineering, or related engineering discipline. 3+ years of manufacturing engineering ex...

### 40. `workday-Intern---Bachelor-s-Tech_1216552` — Intern - Bachelor's Tech

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

### 41. `workday-Intern---Bachelors-Tech_1214077` — Intern - Bachelors Tech

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

### 42. `workday-Intern---Bachelors-Tech_1214221` — Intern - Bachelors Tech

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

### 43. `workday-LATAM-COE-Senior-Tax-Analyst_549089` — LATAM COE Senior Tax Analyst

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Basic Qualifications: We are looking for professionals with the required skills to achieve our goals: Bachelor’s Degree in Accounting, Finance, or a related field.

> Basic Qualifications: We are looking for professionals with the required skills to achieve our goals: Bachelor’s Degree in Accounting, Finance, or a related field.
>
> contexto: ...ng, Shared Services, and local market teams to ensure accurate reporting and compliance. Why you? Basic Qualifications: We are looking for professionals with the required skills to achieve our goals: Bachelor’s Degree in Accounting, Finance, or a related field. 5+ years of experience in Tax, Audit, Risk Management, or related areas, preferably within a Shared Services environment. Intermediate to advanced E...

### 44. `workday-Leader--Customer-Support_2022544-1` — Leader, Customer Support

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=False · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Our minimum requirements for this role · Bachelor's degree and 7 years of related experience, or a master's degree and 4 years of related experience, or a PhD and 1 year of related experience.

> Bachelor's degree and 7 years of related experience, or a master's degree and 4 years of related experience, or a PhD and 1 year of related experience.
>
> contexto: ...artners. · A people leader who coaches through change, develops capability, encourages responsible use of AI and automation, and creates psychological safety. Our minimum requirements for this role · Bachelor's degree and 7 years of related experience, or a master's degree and 4 years of related experience, or a PhD and 1 year of related experience. · Previous supervisory or team lead experience. · At least...

### 45. `workday-Manager--Business-Continuity_Req-49141` — Manager, Business Continuity

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What you'll need (Required): • Bachelor's degree in business administration, Supply Chain Management, Emergency Management, Risk Management, Engineering, or related field, with 8+ years' experience • Master's degree with 6+ years of relevant experience may substitute for bachelor's with 8+ years • Professional experience relevant to business continuity and organizational resilience, which may include BCM, IT disaster recovery (ITDR), emergency management, recovery planning, business impact or risk assessments, continuity exercises, supply chain resilience, or incident response.

> Bachelor's degree in business administration, Supply Chain Management, Emergency Management, Risk Management, Engineering, or related field, with 8+ years' experience
>
> contexto: ...ior leaders and serve as a BCM subject matter expert to adjacent resilience and risk initiatives, including strategic sourcing resilience and IT resilience assessments. What you'll need (Required): • Bachelor's degree in business administration, Supply Chain Management, Emergency Management, Risk Management, Engineering, or related field, with 8+ years' experience • Master's degree with 6+ years of relevant...

### 46. `workday-Master-Data-Analyst_R-01358585` — Master Data Analyst

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > REQUIRED QUALIFICATIONS Education: Bachelor’s degree in supply chain, Business Administration, Information Technology, or related field Experience: Minimum 2 years of experience with SAP in Operations/Warehouse/ Manufacturing or related environment, preferably in the pharmaceutical industry.

> REQUIRED QUALIFICATIONS Education: Bachelor’s degree in supply chain, Business Administration, Information Technology, or related field Experience: Minimum 2 years of experience with SAP in Operations/Warehouse/ Manufacturing or related environment, preferably in the pharmaceutical industry.
>
> contexto: ...ment reports, support performance tracking (data accuracy, reporting accuracy, standards alignment, timely updates), and act as backup for the Supply Chain Analyst. REQUIRED QUALIFICATIONS Education: Bachelor’s degree in supply chain, Business Administration, Information Technology, or related field Experience: Minimum 2 years of experience with SAP in Operations/Warehouse/ Manufacturing or related environm...

### 47. `workday-Planner-II_31164664` — Planner II

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Shift: Administrative Required Qualifications Bachelor´s Degree in Engineering or related field.

> Shift: Administrative Required Qualifications Bachelor´s Degree in Engineering or related field.
>
> contexto: ...Ops on product commitments, exception management and new product introductions. Planning and MFG execution reports. Ensure Planning KPI metrics are met. Shift: Administrative Required Qualifications Bachelor´s Degree in Engineering or related field. Experience 2-4 years in: Related work experience with a complete understanding of specified functional area. Planning and Scheduling: Planning resources, bal...

### 48. `workday-Process-Engineer_887921` — Process Engineer

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachillerato Universitario'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachillerato Universitario'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Para tener éxito en este puesto, necesitarás las siguientes calificaciones: Bachillerato Universitario en Ingeniería Industrial, Producción Industrial o carreras afines.

> Para tener éxito en este puesto, necesitarás las siguientes calificaciones: Bachillerato Universitario en Ingeniería Industrial, Producción Industrial o carreras afines.
>
> contexto: ...PIs. Generar planes de acción para solucionar los hallazgos encontrados en la gestión del puesto, y los procesos asociados. Para tener éxito en este puesto, necesitarás las siguientes calificaciones: Bachillerato Universitario en Ingeniería Industrial, Producción Industrial o carreras afines. Mínimo 1 año de experiencia en procesos de producción, análisis de datos estadísticos. Manejo intermedio de Excel. Nivel de Inglés:...

### 49. `workday-Product-Portfolio-Intern_J-020242` — Product Portfolio Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Minimum Qualifications Currently pursuing a Bachelor's degree in Business Administration, Project Management, Marketing, Finance, Data Analytics, Engineering, or a related field.

> Minimum Qualifications Currently pursuing a Bachelor's degree in Business Administration, Project Management, Marketing, Finance, Data Analytics, Engineering, or a related field.
>
> contexto: ...edia on Mondays, Wednesdays, and Thursdays. Please note that there may be occasions where additional office days are required, due specific business needs. Minimum Qualifications Currently pursuing a Bachelor's degree in Business Administration, Project Management, Marketing, Finance, Data Analytics, Engineering, or a related field. Must be enrolled as a full-time student at an accredited university through...

### 50. `workday-Purchasing-Manager--Global-Procurement-Center_R572335` — Purchasing Manager, Global Procurement Center

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What You Will Need Required Qualifications Bachelor’s degree in Business, Supply Chain Management, Engineering, or a related field.

> What You Will Need Required Qualifications Bachelor’s degree in Business, Supply Chain Management, Engineering, or a related field.
>
> contexto: ...g development plans for managers and buyers. Ensure compliance with applicable quality and regulatory requirements and support internal and external audits. What You Will Need Required Qualifications Bachelor’s degree in Business, Supply Chain Management, Engineering, or a related field. Minimum 8 years of experience in Supply Chain, Purchasing, Procurement, Manufacturing, or a related field. Minimum 3 year...

### 51. `workday-R-D-Process-Coordinator_R-106675` — R&D Process Coordinator

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Responsabilidades Liderar la comercialización e industrialización de nuevos productos y cambios de proceso, desde las etapas de laboratorio/piloto hasta la producción a escala industrial Definir y desarrollar procesos de manufactura end-to-end para productos estables a temperatura ambiente, incluyendo condimentos, vegetales y alimentos para bebés Desarrollar diagramas de flujo de procesos, balances de masa y energía, dimensionamiento de equipos, modelos de capacidad de línea y ventanas operativas Establecer y optimizar parámetros de proceso para etapas críticas como cocción, calentamiento, mezclado, emulsificación, homogeneización y desaireación Diseñar y optimizar procesos relacionados con el manejo de partículas, incluyendo preparación de vegetales, integridad y distribución de partículas, control de sedimentación y selección de bombas Definir y controlar parámetros relacionados con pH, acidificación y sólidos (Brix/viscosidad) para garantizar los objetivos de estabilidad y vida útil de los productos Asegurar el cumplimiento de los requerimientos de procesos térmicos relacionados con Seguridad Alimentaria y Calidad, incluyendo hot-fill, cold-fill, pasteurización y procesos de retorta cuando corresponda Establecer y gestionar los parámetros críticos de proceso y atributos críticos de calidad (CPPs/CQAs), incluyendo pH, viscosidad, Brix/sólidos, tamaño y distribución de partículas, temperatura de llenado, tiempo de retención, headspace, vacío, torque de cierre, integridad del cierre y contenido neto Liderar la ejecución de pruebas industriales, incluyendo planes de prueba, evaluaciones de riesgo, ejecución y elaboración de reportes técnicos Crear y mantener documentación técnica, incluyendo SOPs, estándares de setpoints, descripciones de procesos, protocolos de pruebas, parámetros de sanitización/CIP y materiales de capacitación Liderar procesos de control de cambios y evaluaciones de riesgo para modificaciones de formulación, procesos, packaging y equipos Requisitos Licenciatura/Ingeniería completa en Ingeniería Química, Mecánica, Industrial, de Manufactura, Alimentos o áreas relacionadas Más de 5 años de experiencia en ingeniería de procesos y/o ambientes de manufactura Experiencia en diseño de procesos, escalamiento e industrialización de productos Conocimiento de control de procesos, análisis de causa raíz y metodologías de mejora continua Experiencia trabajando en ambientes productivos y en proyectos cross-functional Manejo de herramientas como Excel y Minitab, JMP o software estadístico similar Experiencia con sistemas ERP/MES será considerada un diferencial Inglés avanzado será requerido Portugués será considerado un diferencial Location(s) San Jose, Costa Rica Local Office Kraft Heinz is an Equal Opportunity Employer – Underrepresented Ethnic Minority Groups/Women/Veterans/Individuals with Disabilities/Sexual Orientation/Gender Identity and other protected classes .

> ...arámetros de sanitización/CIP y materiales de capacitación Liderar procesos de control de cambios y evaluaciones de riesgo para modificaciones de formulación, procesos, packaging y equipos Requisitos Licenciatura/Ingeniería completa en Ingeniería Química, Mecánica, Industrial, de Manufactura, Alimentos o áreas relacionadas Más de 5 años de experiencia en ingeniería de procesos y/o ambientes de man...
>
> contexto: ...arámetros de sanitización/CIP y materiales de capacitación Liderar procesos de control de cambios y evaluaciones de riesgo para modificaciones de formulación, procesos, packaging y equipos Requisitos Licenciatura/Ingeniería completa en Ingeniería Química, Mecánica, Industrial, de Manufactura, Alimentos o áreas relacionadas Más de 5 años de experiencia en ingeniería de procesos y/o ambientes de manufactura Exp...

### 52. `workday-Sales-Commercial-Manager_R-257732` — Sales Commercial Manager

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Role Requirements Bachelor's degree in Business Administration, Marketing, Economics, Life Sciences, or a related field.

> Role Requirements Bachelor's degree in Business Administration, Marketing, Economics, Life Sciences, or a related field.
>
> contexto: ...tiveness, commercial execution, and decision-making. Promote a culture of innovation, customer centricity, continuous improvement, and commercial excellence across the organization. Role Requirements Bachelor's degree in Business Administration, Marketing, Economics, Life Sciences, or a related field. Proven experience leading commercial teams and managing strategic customer relationships within the pharmac...

### 53. `workday-Security-Engineer_2025477` — Security Engineer

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications Bachelor’s degree with 3+ years of related experience, or a Master’s degree with 3+ years of related experience working in cybersecurity engineering, infrastructure engineering, DevOps, or a large enterprise technology environment.

> Minimum Qualifications Bachelor’s degree with 3+ years of related experience, or a Master’s degree with 3+ years of related experience working in cybersecurity engineering, infrastructure engineering, DevOps, or a large enterprise technology environment.
>
> contexto: ...ithin the organization, conducting training sessions or "lunch-and-learns" to improve the overall security awareness and coding practices of cross-functional development teams. Minimum Qualifications Bachelor’s degree with 3+ years of related experience, or a Master’s degree with 3+ years of related experience working in cybersecurity engineering, infrastructure engineering, DevOps, or a large enterprise te...

### 54. `workday-Senior-Analyst--Finance--Internal-Auditor-_Req-51202-1` — Senior Analyst, Finance (Internal Audit)

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's Degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What you'll need (Required): • Bachelor's Degree in related field is required • Minimum 5 years of previous related experience is required • Experience working in a medical device or a related manufacturing environment is required • Advance English level is required • Public accounting experience (e.g., Big Four CPA firms) preferred What else we look for (Preferred): • Strong knowledge of internal controls, risk assessment methodologies, audit practices, Generally Accepted Accounting Principles (GAAP), and Sarbanes-Oxley (SOX) requirements.

> Bachelor's Degree in related field is required
>
> contexto: ...ernal audit requests. • Support continuous improvement of audit methodologies, tools, analytics, and processes. • Perform other duties and special projects as assigned. What you'll need (Required): • Bachelor's Degree in related field is required • Minimum 5 years of previous related experience is required • Experience working in a medical device or a related manufacturing environment is required • Advance...

### 55. `workday-Senior-Director--Quality-Engineering_Req-50066` — Senior Director, Quality Engineering

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's Degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What you'll need (Required): Bachelor's Degree in related field with at least 10 years experience in engineering and leadership positions in the medical device industry Experience in Quality Engineering, Quality Management, and/or Regulatory Compliance within the medical device industry Demonstrated track record in management of technical and/or engineering disciplines Proven successful interaction with Regulators and Notified Bodies Experience influencing teams in a global environment What else we look for (Preferred): • Proven successful project management leadership skills • Proven expertise in both Microsoft Office Suite and related systems • Excellent problem-solving, organizational, analytical and critical thinking skills including high discretion/judgment in decision making • Excellent documentation and communication skills and interpersonal relationship skills including negotiating and relationship management skills with ability to drive achievement of objectives • Expert understanding of engineering procedures while looking beyond existing methodologies and own discipline to define and resolve complex problems • Expert understanding of related aspects of quality engineering processes and/or systems • Expert knowledge of domestic and international regulatory requirements • Expert knowledge of design of experiments, process capability studies, failure mode and effects analysis, statistical process control, industrial statistical methods and Lean Manufacturing • Knowledge of financial acumen as it relates to the business as well as quality engineering • Demonstrated ability to direct teams and provide coaching and feedback, including responsibility for all employee actions including hire/fire authority and partnering with HR on all aspects of employee relations • Ability to develop and integrate metrics into the projects and operations that clearly demonstrate the value of quality engineering to the business • Serve as core partner to senior leaders in Business Units, Functional Groups, Regions and IT • Strict attention to detail • Ability to interact professionally with all organizational levels and proactively escalate issues to appropriate levels of management in the organization • Ability to work and excel within a fast paced, dynamic, and constantly changing work environment • Interacts with senior management, and others concerning matters of significance to the company • Conduct business and technical briefings for senior and top management and for external representatives • Regularly interacts with executives and/or major customers;

> ...What you'll need (Required): Bachelor's Degree in related field with at least 10 years experience in engineering and leadership positions in the medical device industry Experience in Quality Engineering, Quality Management, and/o...
>
> contexto: ...es. Provide quality engagement to audits including resources support, technical and procedural expertise, presentation of information, and effective resolution of issues. What you'll need (Required): Bachelor's Degree in related field with at least 10 years experience in engineering and leadership positions in the medical device industry Experience in Quality Engineering, Quality Management, and/or Regulato...

### 56. `workday-Senior-Project-Accountant_J000703933` — Senior Project Accountant

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=False · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Ensure project invoices are accurate, approved, and sent on time • Compliance & Audits: Help maintain a strong control environment that is compliant with company policies and accounting standards Your Background: • Bachelor’s Degree in Accounting, Finance, or a closely related field • At least 5+ years of progressive project accounting experience or related accounting or finance roles • In collaboration with the Manager, Project Accounting establish priorities, meet deadlines, multi-task, and work independently, and execute objectives, under supervision where required.

> Bachelor’s Degree in Accounting, Finance, or a closely related field
>
> contexto: ...invoices are accurate, approved, and sent on time • Compliance & Audits: Help maintain a strong control environment that is compliant with company policies and accounting standards Your Background: • Bachelor’s Degree in Accounting, Finance, or a closely related field • At least 5+ years of progressive project accounting experience or related accounting or finance roles • In collaboration with the Manager,...

### 57. `workday-Senior-Quality-Engineer_R567778` — Quality Engineer

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.

> What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.
>
> contexto: ...l analysis and risk management tools, including Failure Mode and Effects Analysis (FMEA), to support decision-making and continuous improvement initiatives. What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field. Minimum 3 years of experience in Quality Engineering. Working knowledge of 21 CFR Part 820, ISO 13485, and the Medical Device Single Audit Program...

### 58. `workday-Senior-Quality-Incoming-Process-Supervisor_R567857` — Senior Quality Incoming/Process Supervisor

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.

> What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.
>
> contexto: ...t product and process improvements. Support internal and external audits and maintain compliance with applicable quality system and regulatory requirements. What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field. Minimum 5 years of experience in Quality Engineering, Quality Control, or Quality Assurance within a regulated manufacturing environment. Minimum 2...

### 59. `workday-Senior-Software-Quality-Engineer_R262277` — Senior Technology Project Manager – Quality & Delivery

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Required Qualifications Bachelor’s degree in Computer Science, Information Technology, Engineering, Business, Project Management, or a related field.

> Required Qualifications Bachelor’s degree in Computer Science, Information Technology, Engineering, Business, Project Management, or a related field.
>
> contexto: ...l teams, business stakeholders, and leadership. Promote consistent project management, testing, process improvement, and technology delivery best practices across initiatives. Required Qualifications Bachelor’s degree in Computer Science, Information Technology, Engineering, Business, Project Management, or a related field. 6+ years of experience in Technology Project Management, IT Project Management, Tech...

### 60. `workday-Senior-Supervisor--Manufacturing_Req-50617` — Senior Supervisor, Manufacturing

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What you’ll need (Required): Bachelor's degree in Industrial Engineering, Business Administration or related field.

> What you’ll need (Required): Bachelor's degree in Industrial Engineering, Business Administration or related field.
>
> contexto: ...outcomes of assigned unit/group of employees May guide and mentor entry level supervisors May provide management duties in the absence of Manager Other incidental duties. What you’ll need (Required): Bachelor's degree in Industrial Engineering, Business Administration or related field. More than 5 years of experience in personnel supervisory with full responsibility for all personnel and handling all aspect...

### 61. `workday-Service-Delivery-Manager_R77891-2` — Service Delivery Manager.

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Baccalaureate'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Requires a Baccalaureate degree (or for degrees earned outside of the United States, a degree which satisfies the requirements of 8 C.F.R.
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Qualifications Required Qualifications Bachelor's degree in Information Technology, Computer Science, Business Administration, or related field.

> Qualifications Required Qualifications Bachelor's degree in Information Technology, Computer Science, Business Administration, or related field.
>
> contexto: ...nitiatives, and strategic roadmaps. Facilitate communication between business partners and service providers to ensure alignment with organizational priorities. Qualifications Required Qualifications Bachelor's degree in Information Technology, Computer Science, Business Administration, or related field. 7+ years of experience in IT service delivery, endpoint management, infrastructure operations, or workpl...

### 62. `workday-Software-Engineering-Systems--Intern_1210981` — Software Engineering(Systems) Intern

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

### 63. `workday-Sourcing-Manager_JR-0110357` — Sourcing Manager

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Responsibilities: Execute sourcing projects in alignment with category-level strategies and established processes for low to medium dollar sourcing projects Manage a high volume of sourcing requests, primarily low-to-medium dollar value, often with standardized procedures Support the creation, review, and negotiation of contracts, ensuring favorable terms and conditions Negotiate with suppliers on pricing, service level agreements, and other key commercial and legal terms to maximize savings and achieve defined goals Conduct risk assessments to identify and mitigate potential supplier-related risks Execute low-complexity RFQs and quick bids to identify the best-value suppliers Prioritize the utilization of preferred and existing suppliers whenever possible Meet or exceed service level agreements (SLAs) and key performance indicators (KPIs) for project completion and efficiency Maintain accurate and up-to-date information in procurement systems Critical Skills: Sourcing and Procurement - ability to identify, evaluate, and acquire goods or services from external sources in a cost-effective and efficient manner Contract Management - ability to efficiently manage contractual agreements with suppliers to maximize performance and minimize risk, involving understanding the terms and conditions of contracts, legal implications, risk management techniques, and managing contract creation, execution, and analysis Negotiation - ability to analyze and evaluate different options to facilitate agreements and close deals with suppliers to reach an optimal outcome Program Management - ability to manage multiple projects simultaneously, prioritize tasks, and meet deadlines in a fast-paced environment through the effective management of stakeholders, interdependencies, and risks Relationship Building - ability to establish and nurture strong connections with stakeholders by understanding interpersonal dynamics, effective communication strategies, empathy, and the ability to manage conflicts or disagreements Supplier Relationship Management - ability to develop and manage partnerships with vendors that supply goods, materials, and services, while understanding procurement strategies, supplier performance monitoring, and risk management Sourcing Strategies - the implementation of methods to manage procurement processes effectively, involves understanding the supply market, assessing total cost of ownership, risk management, and negotiation tactics Results-Oriented - ability to focus on the desired outcome of a project or task, while setting clear goals and prioritizing tasks to achieve the desired outcome Analytical Thinking - breaking down complex information or identifying trends and insights for better understanding, decision making, and problem-solving About You Requirements: Bachelor's degree in Supply Chain Management, Business Administration, or a related field Minimum 4 years of experience in procurement or sourcing, preferably in a high-volume environment Proficiency in procurement processes Strong analytical and problem-solving skills Excellent English written and verbal communication skills Our Approach to Flexible Work With Flex Work, we’re combining the best of both worlds: in-person time and remote.

> ...e the desired outcome Analytical Thinking - breaking down complex information or identifying trends and insights for better understanding, decision making, and problem-solving About You Requirements: Bachelor's degree in Supply Chain Management, Business Administration, or a related field Minimum 4 years of experience in procurement or sourcing, preferably in a high-volume environment Proficiency ...
>
> contexto: ...e the desired outcome Analytical Thinking - breaking down complex information or identifying trends and insights for better understanding, decision making, and problem-solving About You Requirements: Bachelor's degree in Supply Chain Management, Business Administration, or a related field Minimum 4 years of experience in procurement or sourcing, preferably in a high-volume environment Proficiency in procure...

### 64. `workday-Sourcing-Manager_R571931` — Sourcing Manager

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What You Will Need Required Qualifications Bachelor's degree in Supply Chain Management, Business, Engineering, or a related field.

> What You Will Need Required Qualifications Bachelor's degree in Supply Chain Management, Business, Engineering, or a related field.
>
> contexto: ...d risk metrics. Partner with Quality, Engineering, Finance, Legal, Logistics, and Procurement teams to execute sourcing strategies and supplier transitions. What You Will Need Required Qualifications Bachelor's degree in Supply Chain Management, Business, Engineering, or a related field. Minimum 7 years of professional experience in supply chain, procurement, sourcing, or a related function. Minimum 1 year...

### 65. `workday-Sr-Supv--Accounts-Payable_Req-51765` — Sr Supv, Accounts Payable

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What you´ll need (Required): Bachelor’s degree in a related field and 8 years of previous Accounts Payable experience, including demonstrated experience supervising Accounts Payable employees.

> What you´ll need (Required): Bachelor’s degree in a related field and 8 years of previous Accounts Payable experience, including demonstrated experience supervising Accounts Payable employees.
>
> contexto: ...g to internal customers on Accounts Payable requirements, invoice processing, approvals, and related processes. Perform other incidental duties as assigned by leadership. What you´ll need (Required): Bachelor’s degree in a related field and 8 years of previous Accounts Payable experience, including demonstrated experience supervising Accounts Payable employees. What Else We Look For (Preferred): Strong know...

### 66. `workday-Sr-Technical-Architect_WD30279546` — Sr Technical Architect

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Qualifications Bachelor’s degree in IT or a similar technology-related discipline.

> Qualifications Bachelor’s degree in IT or a similar technology-related discipline.
>
> contexto: ...by sharing information openly and early. Communicate with clarity so stakeholders understand trade-offs, dependencies, risks, and the technical approach required to move work forward. Qualifications Bachelor’s degree in IT or a similar technology-related discipline. Minimum 8 years of IT experience. Minimum 3 years of experience architecting integration solutions using APIs. Minimum 5 years of development...

### 67. `workday-Staff-Solution-Program-Manager_REQ-2026-18440` — Staff Solution Program Manager

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Responsibilities • Lead and manage IT infrastructure and facility projects related to new office build outs, existing office remodels, and any other similar IT infrastructure network office efforts projects from inception to completion, ensuring they are delivered on time, within scope, and within budget • Collaborate with stakeholders to define project scope, objectives, and deliverables • Build and maintain overall detailed project plan, Gantt chart, status updates, and RAIDE Register (Risks, Assumptions, Issues, Dependencies and Escalations) integrating all cross-functional workstreams • Maintain and update project schedule and dependencies integrated with Agile teams, ARTs, and Solutions PI Plan • Effectively communicate project status/reports to stakeholders • Lead release-based program core team and steering committee meetings for assigned program(s) • Lead project-related activities of project team members, providing guidance on conformance to established computer systems validation procedures • Identify and assess mitigation options for program risks and issues, and escalate as needed to ensure program success • Assist Business Process Owners and core teams in problem solving and scenario analysis to assess impact of change requests • Provide input to Agile teams and ARTs review during PI planning and assess impact of PI Planning output to overall plan • Adhere to all regulatory agency standards, company quality standards and corporate policies • Must be able to travel domestically and internationally as business needs demand • Perform other duties as required Key Decision Rights • Contributes to 12-month program schedule & supporting detailed integrated project plan, identification and communication of major programs risks, issues, and blockers impacting overall program delivery • Influences program timelines, budget, and priorities, change management of any changes impacting overall program timeline Required Leadership/Interpersonal Skills & Behaviors • Strong influence management skills – track record of influencing behaviors • Excellent communication, collaboration, problem solving, and people skills • Desire to learn and to help teams continuously improve • Courage to challenge & advise various stakeholders, including senior leaders • undefined Required Skills & Competencies • Agile experience • Project management certification preferred • Experience in managing IT infrastructure and facility projects, including but not limited to: o Network administration and optimization o Server management and maintenance o Implementation of Cybersecurity measures o Coordination with contractors, vendors, and stakeholders • Experienced working with Agile teams to develop and launch strategic programs against concreate deadlines • Knowledge of computer systems validation and QMS compliance • Demonstrated flexibility and ability to function in a fast-paced, growth industry and work environment • Proficient in the following computer software applications: MS 365 Suite (Word, Excel, PowerPoint Project, Outlook, Teams), Smartsheet, SharePoint • Helpful to have working knowledge or familiarity with: o Agile applications (Jira & Confluence) o CRM Environments (SalesForce, Marketing Cloud) o SAP ERP Programs o Integrations (MuleSoft) o PLM & QMS applications (Arena) o PPM tools (Clarity) Education and Experience • Bachelor’s degree in Business, Computer Science, Information Technology, Engineering, or a related field;

> Bachelor’s degree in Business, Computer Science, Information Technology, Engineering, or a related field
>
> contexto: ...ons (Jira & Confluence) o CRM Environments (SalesForce, Marketing Cloud) o SAP ERP Programs o Integrations (MuleSoft) o PLM & QMS applications (Arena) o PPM tools (Clarity) Education and Experience • Bachelor’s degree in Business, Computer Science, Information Technology, Engineering, or a related field; Advanced degree preferred • At least 10 years of overall work experience in a technical discipline and 5...

### 68. `workday-Storage-Hardware-Operations-Intern_1210994` — Storage Hardware Operations Intern

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

### 69. `workday-Storage-NPI-Program-Management-Intern_1210990` — Storage NPI Program Management Intern

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

### 70. `workday-Strategy---Business-Operations-Head---CAMCAR_R-255612` — Strategy & Business Operations Head – CAMCAR

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Role Requirements Education Bachelor’s Degree in Business Administration, Economics, Finance, Engineering, Strategy, Life Sciences or related disciplines.

> Role Requirements Education Bachelor’s Degree in Business Administration, Economics, Finance, Engineering, Strategy, Life Sciences or related disciplines.
>
> contexto: ...dership Team, LATAM organization and key regional stakeholders. Support executive communications, leadership presentations and strategic storytelling for senior audiences. Role Requirements Education Bachelor’s Degree in Business Administration, Economics, Finance, Engineering, Strategy, Life Sciences or related disciplines. MBA or Master’s Degree preferred. Experience Demonstrated success in Strategy, Busi...

### 71. `workday-Supplier-Quality-Engineer-III_31162905` — Supplier Quality Engineer III

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > As required , supervise technical personal for task execution Shift: Administrative Required Qualifications Bachelor's degree in engineering, Science, or equivalent field of study.

> As required , supervise technical personal for task execution Shift: Administrative Required Qualifications Bachelor's degree in engineering, Science, or equivalent field of study.
>
> contexto: ...ed . Mentors employees by sharing technical expertise and providing feedback and guidance . As required , supervise technical personal for task execution Shift: Administrative Required Qualifications Bachelor's degree in engineering, Science, or equivalent field of study. 2 of experience in engineering related position. Intermediate command of English. Apply Now Follow your career aspirations to Abbott for...

### 72. `workday-Supply-Chain-Planning-Intern_1212998` — Supply Chain Planning Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Education & Experience Currently pursuing a Bachelor's degree in Industrial Engineering, Business Administration, or a related field.
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
    - evidencia literal del requisito: > Impact/Scope: University students actively enrolled in a university/college/institution pursuing a Bachelor's degree in a non-technical area of study, and who typically works during school breaks and then returns to their university.

> Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
>
> contexto: ...up opportunities with HPE. Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field. Assists in various tasks aligned with their field of study, including research, collaboration on team initiatives and projects, problem-solving, and creative thinking...

### 73. `workday-Switching-Technical-Support-Engineer-Intern---Switching-Support---EX-Products_1214133` — Switching Technical Support Engineer Intern | Switching Support – EX Products

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

### 74. `workday-Tax-Audit-Senior-Specialist_888004-1` — Tax Compliance Analyst III

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
    - evidencia literal del requisito: > To succeed in this role, you will need the following qualifications: Bachelor's degree in finance, accounting, internal control or related field along with experience in USGAAP, preparing Income Tax Returns, Informative reports, compliance reports and attending tax audits.

> To succeed in this role, you will need the following qualifications: Bachelor's degree in finance, accounting, internal control or related field along with experience in USGAAP, preparing Income Tax Returns, Informative reports, compliance reports and attending tax audits.
>
> contexto: ...entic caring. You want to be part of a company actively dedicated to sustainability, inclusion, wellbeing, and career development. To succeed in this role, you will need the following qualifications: Bachelor's degree in finance, accounting, internal control or related field along with experience in USGAAP, preparing Income Tax Returns, Informative reports, compliance reports and attending tax audits. More...

### 75. `workday-Technical-Support-Delivery-Intern_JR-0110629-1` — Technical Support Delivery Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='pursuing'`
    - evidencia literal del requisito: > #LI-DNI About You Basic Qualifications Currently pursuing a Bachelor’s degree in Computer Science, Information Technology, or related field, with an anticipated graduation date of June/July 2027 Must be able to commit to the full duration of the 23 week internship (Start Date: Feb 8, 2027) in Heredia, Costa Rica Must be able to work Shift 1 (8am - 5pm) Bilingual in Spanish and English Strong interest in technology and willingness to learn new applications.

> ...#LI-DNI About You Basic Qualifications Currently pursuing a Bachelor’s degree in Computer Science, Information Technology, or related field, with an anticipated graduation date of June/July 2027 Must be able to commit to the full duration of the 23 week intern...
>
> contexto: ...living our Core Values. Let’s make work days brighter. Apply today to start your career as a member of the Workday Intern & Co-Op Program! #LI-DNI About You Basic Qualifications Currently pursuing a Bachelor’s degree in Computer Science, Information Technology, or related field, with an anticipated graduation date of June/July 2027 Must be able to commit to the full duration of the 23 week internship (Star...

### 76. `workday-Technical-Support-Engineer-Intern---Wireless-Technologies_1214131` — Technical Support Engineer Intern – Wireless Technologies

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

### 77. `workday-Technical-Writing-Intern_1214060` — Technical Writing Intern

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

### 78. `workday-US-Marketing-Governance--Regulatory-and-Policy-Lead_25928925` — US Marketing Governance Regulatory and Policy Lead

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's"` · `requirement_level='preferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Education : Bachelor's/University degree, Master's degree preferred ------------------------------------------------------ Job Family Group: Controls Governance & Oversight ------------------------------------------------------ Job Family: Cross-disciplinary Controls ------------------------------------------------------ Time Type: Full time ------------------------------------------------------ Most Relevant Skills Analytical Thinking, Business Acumen, Communication, Constructive Debate, Controls Assessment, Controls Lifecycle, Escalation Management, Issue Management, Risk Management, Stakeholder Management.

> ...Education : Bachelor's/University degree, Master's degree preferred ------------------------------------------------------ Job Family Group: Controls Governance & Oversight ---------------------------------------...
>
> contexto: ...nd work well as part of a team. Exceptional oral and written communication skills, with ability to synthesize complex concepts, and influence change. Proficient in Microsoft Office Suite. Education : Bachelor's/University degree, Master's degree preferred ------------------------------------------------------ Job Family Group: Controls Governance & Oversight -------------------------------------------------...

### 79. `workday-VLSI-Engineer-Internship_1214036` — VLSI Engineer Internship

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

### 80. `workday-ingeniero-de-Manufactura_20184428` — ingeniero de Manufactura

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Qualifications/Responsibilities 2-4 years of experience in a highly regulated industry Bachelor’s degree in Engineering or a related field required.

> Qualifications/Responsibilities 2-4 years of experience in a highly regulated industry Bachelor’s degree in Engineering or a related field required.
>
> contexto: ...ives. Also designs process improvements to reduce product cost, process cycle time and improved product quality. Qualifications/Responsibilities 2-4 years of experience in a highly regulated industry Bachelor’s degree in Engineering or a related field required. Intermediate English proficiency (B1), Experience leading projects and supporting cost-reduction and quality-improvement initiatives within producti...

## 5. Las 19 `revisar_a_mano / educacion_no_confirmada` — por qué NO se descartan

Son requisitos universitarios **obligatorios** que el TEXTO no confirma
(negación o alternativa). Van a revisión manual (Paso 7).

### 1. `linkedin-4483157697` — Technical Support Specialist (Tier 2)

- detección textual: `negacion` (término: `'university degree'`)
- requisitos `education` extraídos:
  - `value_text='university degree'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > No university degree required.

> No university degree required.

### 2. `workday-Accounting-Analyst---Temporary_J-020392` — Accounting Analyst – Temporary

- detección textual: `alternativa` (término: `'Bachelor’s'`)
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications Bachelor’s degree in Accounting, Finance, or a related field , or advanced university studies in Accounting.

> Minimum Qualifications Bachelor’s degree in Accounting, Finance, or a related field , or advanced university studies in Accounting.

### 3. `workday-Assistant-Director-of-Engineering_REQ10393409` — Assistant Director of Engineering

- detección textual: `alternativa` (término: `'Bachelor’s'`)
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Required Qualifications Education Bachelor’s degree or technical degree in Mechanical Engineering, Electrical Engineering, Electromechanical Engineering, Industrial Maintenance, Facilities Management, Civil Engineering, or a related field.

> Required Qualifications Education Bachelor’s degree or technical degree in Mechanical Engineering, Electrical Engineering, Electromechanical Engineering, Industrial Maintenance, Facilities Management, Civil Engineering, or a related field.

### 4. `workday-Associate--Repair-III_R-118081` — Associate, Repair III

- detección textual: `sin_termino` (término: `None`)
- requisitos `education` extraídos:
  - `value_text='High School Diploma'` · `requirement_level='inferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > OR High School Diploma or equivalent and 5 years functional experience, preferably at a senior level.
  - `value_text='college degree'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Two year college degree or equivalent experience and minimum 3 year experience in functional area.

> (el texto NO menciona un título universitario; la cita del
> requisito extraído es la que lo demuestra)

### 5. `workday-Buyer-Planner-Sr_31163601` — Buyer Planner Sr

- detección textual: `alternativa` (término: `'Bachelor'`)
- requisitos `education` extraídos:
  - `value_text='Bachelor Degree'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Required Qualifications Bachelor Degree, engineering, science or closely related discipline is desired, or equivalent technical.

> Required Qualifications Bachelor Degree, engineering, science or closely related discipline is desired, or equivalent technical.

### 6. `workday-Cardiac-Specialist-II_R18282-1` — Cardiac Specialist II

- detección textual: `alternativa` (término: `"Bachelor's"`)
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What We Look For Bachelor's degree, ECG certification, or an equivalent combination of education and relevant experience required.

> What We Look For Bachelor's degree, ECG certification, or an equivalent combination of education and relevant experience required.

### 7. `workday-Clinical-Project-Manager_R18034-1` — Clinical Project Manager

- detección textual: `alternativa` (término: `'Bachelor’s'`)
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What We Look For Bachelor’s degree required or equivalent experience;

> What We Look For Bachelor’s degree required or equivalent experience

### 8. `workday-Creative-Execution-Manager--CrM-_261002442` — Creative Execution Manager (CrM)

- detección textual: `alternativa` (término: `'Bachelors'`)
- requisitos `education` extraídos:
  - `value_text='University degree'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Required Licensing/Registration: Series 7, Series 63 Education: Bachelors/University degree or equivalent experience This job description provides a high-level review of the types of work performed.

> Required Licensing/Registration: Series 7, Series 63 Education: Bachelors/University degree or equivalent experience This job description provides a high-level review of the types of work performed.

### 9. `workday-Credit---Collections-Specialist--2_R232432` — Credit & Collections Specialist

- detección textual: `alternativa` (término: `'bachelor’s'`)
- requisitos `education` extraídos:
  - `value_text='bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Responsibilities Manage and collect accounts receivable for an assigned portfolio of B2B customers Monitor customer aging and enforce credit terms and limits using ERP and A/R systems (SAP, Esker or similar) Review credit applications and evaluate customer creditworthiness using credit bureaus and references Approve new customer credit limits within assigned authority and prepare recommendations for higher limits Place accounts on credit hold , issue final notices, and recommend escalation to third-party collections when necessary Collaborate closely with Sales Representatives to resolve past-due balances and communicate account status changes Maintain accurate documentation of all collection and credit activities in the system Research and resolve discrepancies such as short pays, deductions, overpayments, and unapplied cash Support credit memo requests and payment arrangements with appropriate approvals Ensure customer master data is accurate and up to date Deliver excellent customer service to both internal and external partners Participate in special projects and additional duties as assigned Required Associate’s or bachelor’s degree in business, Finance, or a related field 1–2 years of experience in B2B credit, collections, or accounts receivable Excellent communication skills in English (B2+ or higher) and ability to collaborate across functions and geographies.

> ...ter data is accurate and up to date Deliver excellent customer service to both internal and external partners Participate in special projects and additional duties as assigned Required Associate’s or bachelor’s degree in business, Finance, or a related field 1–2 years of experience in B2B credit, collections, or accounts receivable Excellent communication skills in English (B2+ or higher) and abil...

### 10. `workday-HPE---Professional-Sales-HIT--Compute-and-Hybrid-Cloud-_R-116879` — HPE - Professional Sales HIT (Compute and Hybrid Cloud)

- detección textual: `alternativa` (término: `'four year college degree'`)
- requisitos `education` extraídos:
  - `value_text='college degree'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > A four year college degree (or additional experience in a related field) and 3 years functional experience including a minimum 1 year position specific experience.

> A four year college degree (or additional experience in a related field) and 3 years functional experience including a minimum 1 year position specific experience.

### 11. `workday-Instructional-Designer_R17971` — Instructional Designer – Hybrid

- detección textual: `alternativa` (término: `"Bachelor's"`)
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > What We Look For Hybrid Work Availability: Candidates must be available to work in a hybrid setting, including regular on-site presence as required Bachelor's degree or certification in Learning and Development, Education, Business, or a related field.

> What We Look For Hybrid Work Availability: Candidates must be available to work in a hybrid setting, including regular on-site presence as required Bachelor's degree or certification in Learning and Development, Education, Business, or a related field.

### 12. `workday-Principal-Cybersecurity-Engineer_R0007423` — Principal Cybersecurity Engineer

- detección textual: `alternativa` (término: `'Bachelor’s'`)
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Required Qualifications: · Bachelor’s degree in Computer Science, Information Security, or a related field, or equivalent professional experience.

> Bachelor’s degree in Computer Science, Information Security, or a related field, or equivalent professional experience.

### 13. `workday-Production-Supervisor-I_31163511` — Production Supervisor I

- detección textual: `alternativa` (término: `'bachelor’s'`)
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='preferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Preferred Qualifications Bachelor’s degree in business administration, Engineering or similar field.
  - `value_text='bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience.

> Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience.

### 14. `workday-Production-Supervisor-I_31163518` — Production Supervisor I

- detección textual: `alternativa` (término: `'bachelor’s'`)
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='preferred'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Preferred Qualifications Bachelor’s degree in business administration, Engineering or similar field.
  - `value_text='bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience.

> Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience.

### 15. `workday-Sales-Specialist_R-117581` — Sales Specialist

- detección textual: `alternativa` (término: `'four year college degree'`)
- requisitos `education` extraídos:
  - `value_text='college degree'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > A four year college degree (or additional experience in a related field) and 3 years functional experience including a minimum 1 year position specific experience.

> A four year college degree (or additional experience in a related field) and 3 years functional experience including a minimum 1 year position specific experience.

### 16. `workday-Security-Governance---Compliance-Specialist_2022361-1` — Security Governance & Compliance Specialist

- detección textual: `alternativa` (término: `'Bachelor’s'`)
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Minimum Qualifications Bachelor’s degree plus 5+ years of experience in technical compliance, security, risk, audit, or a related field;

> Minimum Qualifications Bachelor’s degree plus 5+ years of experience in technical compliance, security, risk, audit, or a related field

### 17. `workday-Security-Governance---Compliance-Specialist_2023168-1` — Security Governance & Compliance Specialist

- detección textual: `alternativa` (término: `"Bachelor's"`)
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Must-have Qualifications Bachelor's degree or equivalent work experience required.

> Must-have Qualifications Bachelor's degree or equivalent work experience required.

### 18. `workday-Senior-Client-Services-Executive_R2025-244318` — Senior Client Services Executive

- detección textual: `alternativa` (término: `'Bachelor’s'`)
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > must be able to take active measures to solve problems and commit to a high level of service · Effective time management and ability to multi-task in a fast-paced environment · Superior written and spoken communication skills in English Required Experience and Qualifications: · Experience in customer service · Minimum Bachelor’s degree or its equivalent · Strong MS Office/computer skills

> Minimum Bachelor’s degree or its equivalent

### 19. `workday-TnF-Manager-Systems---Software_1214477-2` — TnF Manager Systems / Software

- detección textual: `alternativa` (término: `"Bachelor's"`)
- requisitos `education` extraídos:
  - `value_text="Bachelor's"` · `requirement_level='required'` · `education_status='unspecified'`
    - evidencia literal del requisito: > Education and Experience Required: Bachelor's or Master's degree in Computer Science, Computer/Electronics Engineering, Information Systems, or equivalent.

> Education and Experience Required: Bachelor's or Master's degree in Computer Science, Computer/Electronics Engineering, Information Systems, or equivalent.

## 6. Medición AMPLIADA de `educacion_no_cumple` (43 casos)

La muestra pequeña inicial (5 de 10) no era suficiente para decidir la
regla. Se amplió a **43 casos** del grupo `educacion_no_cumple` de la
corrida `20261029_171039` (106 vacantes en total):

- **Estrato A (13)**: las 13 que la regla "el texto decide" promovió a
  `descartada` — se revisan **todas**.
- **Estrato B (30)**: 30 sistemáticas de las 93 restantes (una de cada
  tres, ordenadas por `job_id`).

Cada caso se revisó a mano contra la frase literal del aviso.
`Estado final` es el de la corrida vigente `20261029_205348`.

| # | job_id | veredicto manual | por qué | estado final | motivo final |
|---|---|---|---|---|---|
| A1 | `cinde-4901` | BLOQUEO | ESSENCIAL QUALIFICATIONS + Bachelor's degree | descartada | `titulo_universitario_requerido` |
| A2 | `workday-Accounts-Payable-Representative_J-020440` | NO BLOQUEO | via alternativa: 'alternatively, 3+ years of relevant professional experience' | revisar_a_mano | `educacion_no_cumple` |
| A3 | `workday-Business-Analyst--Contract-Pricing-and-Accuracy_R265403` | BLOQUEO | QUALIFICATIONS AND SKILLS + Bachelor's degree | descartada | `titulo_universitario_requerido` |
| A4 | `workday-Continuous-Improvement-Intern_J-020427` | BLOQUEO | estudiante activo: 'Currently pursuing a Bachelor's' | descartada | `titulo_universitario_en_curso_requerido` |
| A5 | `workday-Contract-Administrator--Internship-_1213007` | BLOQUEO | estudiante activo: 'University students actively enrolled' | descartada | `titulo_universitario_en_curso_requerido` |
| A6 | `workday-Contracts-Negotiator_JR-0110562` | BLOQUEO | Basic Qualifications + Bachelor's Degree or above | descartada | `titulo_universitario_requerido` |
| A7 | `workday-Director--Corporate-Accounting_JR-0111126` | BLOQUEO | Required Qualifications: Bachelor's degree ... required | descartada | `titulo_universitario_requerido` |
| A8 | `workday-Product-Portfolio-Intern_J-020242` | BLOQUEO | estudiante activo: 'Must be enrolled as a full-time student' | descartada | `titulo_universitario_en_curso_requerido` |
| A9 | `workday-Senior-Analyst--Finance--Internal-Auditor-_Req-51202-1` | BLOQUEO | What you'll need (Required): Bachelor's Degree ... is required | descartada | `titulo_universitario_requerido` |
| A10 | `workday-Senior-Director--Quality-Engineering_Req-50066` | BLOQUEO | What you'll need (Required): Bachelor's Degree | descartada | `titulo_universitario_requerido` |
| A11 | `workday-Service-Delivery-Manager_R77891-2` | BLOQUEO | Qualifications Required Qualifications Bachelor's degree | descartada | `titulo_universitario_requerido` |
| A12 | `workday-Sr-Technical-Architect_WD30279546` | BLOQUEO | Qualifications + Bachelor's degree | descartada | `titulo_universitario_requerido` |
| A13 | `workday-Tax-Audit-Senior-Specialist_888004-1` | BLOQUEO | To succeed in this role, you will need the following qualifications: | descartada | `titulo_universitario_requerido` |
| B1 | `cinde-4887` | BLOQUEO | estudiante activo: 'Bachillerato universitario incompleto' | descartada | `titulo_universitario_en_curso_requerido` |
| B2 | `cinde-4892` | BLOQUEO | Job Requirements: Active university student + Currently pursuing | descartada | `titulo_universitario_en_curso_requerido` |
| B3 | `cinde-4898` | BLOQUEO | Formacion: Licenciatura | descartada | `titulo_universitario_requerido` |
| B4 | `workable-valatam-A30B8CD1CD` | NO BLOQUEO | 'Bachelor's or Associate's degree preferred' | datos_insuficientes | `educacion_no_cumple` |
| B5 | `workday-Analista-de-CPFR_887589` | BLOQUEO | Licenciatura o bachillerato universitario (ambos son=title universit.) | descartada | `titulo_universitario_requerido` |
| B6 | `workday-Applications-Support-Sr-Analyst_26963530` | NO BLOQUEO | or equivalent experience | revisar_a_mano | `educacion_no_cumple` |
| B7 | `workday-Audience-Management_26999789` | NO BLOQUEO | or equivalent experience | revisar_a_mano | `educacion_no_cumple` |
| B8 | `workday-Commercial-Support-Specialist_202609-124777` | NO BLOQUEO | 'Bachelor's or Master's degree preferred' | revisar_a_mano | `educacion_no_cumple` |
| B9 | `workday-Content-Review-Operations-Specialist_202610-127168` | NO BLOQUEO | or equivalent experience | revisar_a_mano | `educacion_no_cumple` |
| B10 | `workday-Data-Governance-Foundation-Lead-Analyst_26983548` | BLOQUEO | Education: Bachelor's/University degree (el 'preferred' es del Master's) | descartada | `titulo_universitario_requerido` |
| B11 | `workday-Datacenter-Engineer--L3-ERT_1212933-2` | NO BLOQUEO | or equivalent (sin calificar) -> conservador | revisar_a_mano | `educacion_no_cumple` |
| B12 | `workday-Digital-Campaign-Delivery-Associate_202609-122817` | BLOQUEO | Further requirements + Bachelor's degree | descartada | `titulo_universitario_requerido` |
| B13 | `workday-Director--Manufacturing-Engineering_REQ-2026-18566` | BLOQUEO | Education & Experience + discipline required | descartada | `titulo_universitario_requerido` |
| B14 | `workday-Document-Control-Intern_1210991` | BLOQUEO | estudiante activo: 'pursuing diplomas or degrees' | descartada | `titulo_universitario_en_curso_requerido` |
| B15 | `workday-Escalation-Engineer_1212930-2` | BLOQUEO | What you need to bring: + Bachelor's degree | descartada | `titulo_universitario_requerido` |
| B16 | `workday-HR-Generalist-Senior---Global-Discipline-Delivery_261004191` | NO BLOQUEO | or equivalent experience | revisar_a_mano | `educacion_no_cumple` |
| B17 | `workday-Ingeniero-Principal-de-OpEx_20188241` | NO BLOQUEO | preferred Bachelor's degree / or equivalent work experience | revisar_a_mano | `educacion_no_cumple` |
| B18 | `workday-Intern---Bachelors-Tech_1214077` | BLOQUEO | estudiante activo: 'actively enrolled ... pursuing a Bachelor's degree' | descartada | `titulo_universitario_en_curso_requerido` |
| B19 | `workday-Lead-Mobile-Application-Engineer--NET-MAUI-_R18405` | NO BLOQUEO | or equivalent practical experience | revisar_a_mano | `educacion_no_cumple` |
| B20 | `workday-Network-Support-Engineer_1211197` | NO BLOQUEO | or equivalent | revisar_a_mano | `educacion_no_cumple` |
| B21 | `workday-Principal-Engineer--Quality_Req-51750` | NO BLOQUEO | or equivalent | revisar_a_mano | `educacion_no_cumple` |
| B22 | `workday-Programmatic-Media-Associate---Citi-Commerce_261002988` | NO BLOQUEO | or equivalent experience | revisar_a_mano | `educacion_no_cumple` |
| B23 | `workday-Regulatory-Specialist-Diagnostics_202610-126607` | NO BLOQUEO | or equivalent experience | revisar_a_mano | `educacion_no_cumple` |
| B24 | `workday-Sales-Commercial-Manager_R-257732` | BLOQUEO | Role Requirements + Bachelor's degree | descartada | `titulo_universitario_requerido` |
| B25 | `workday-Senior-Data-Scientist---ML-Engineering---MLOps_202609-123431` | NO BLOQUEO | 'Who You Are' es ambiguo -> se deja en revision | revisar_a_mano | `educacion_no_cumple` |
| B26 | `workday-Software-Engineering-Systems--Intern_1210981` | BLOQUEO | estudiante activo: 'Education & Experience: Currently pursuing' | descartada | `titulo_universitario_en_curso_requerido` |
| B27 | `workday-Sr-Customer-Service-Representative_R-01366409` | NO BLOQUEO | 'preferred but not essential' | revisar_a_mano | `educacion_no_cumple` |
| B28 | `workday-Strategy---Business-Operations-Head---CAMCAR_R-255612` | BLOQUEO | Role Requirements Education + Bachelor's Degree | descartada | `titulo_universitario_requerido` |
| B29 | `workday-Switching-Technical-Support-Engineer-Intern---Switching-Support---EX-Products_1214133` | BLOQUEO | estudiante activo: 'Education and Experience Currently pursuing' | descartada | `titulo_universitario_en_curso_requerido` |
| B30 | `workday-Technical-Project-Manager---HiredScore_JR-0108592-1` | NO BLOQUEO | Preferred Qualifications + Bachelor's degree | revisar_a_mano | `educacion_no_cumple` |

**Resultado: 43 de 43 coinciden con el veredicto manual.**

- Estrato A: 12 de 13 eran bloqueos reales; **1 falso descarte**
  (`workday-Accounts-Payable-Representative_J-020440`: "… and 1+ year of
  relevant experience; **alternatively, 3+ years of relevant professional
  experience**") → corregido por la regla.
- Estrato B: 14 de 30 eran bloqueos reales que el motor NO detectaba
  (falsos negativos) → promovidos con frase literal.
- Proporción de bloqueos reales en la muestra: **%d de 43 (%.0f%%)**; la
  muestra inicial daba 5 de 10 (50%%). La proporción **se mantiene o
  sube** → la regla NO estaba sobreajustada.
- La regla nueva acierta en **%d de 43** casos: donde el texto obliga
  descarta y donde el texto no obliga deja la vacante para revisión.

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
  > ...projects as determined by needs of the business and department About You Basic Qualifications 5+ years of experience managing contracts (including drafting and negotiation) in a corporate environment Bachelor’s Degree or above Experience in a law firm or legal department is required Licensed attorney is desired but not required Other Qualifications Proficient in Microsoft Office products and Googl...
- **A7 `workday-Director--Corporate-Accounting_JR-0111126`** — Required Qualifications: Bachelor's degree ... required
  > About You Required Qualifications: Bachelor’s degree in Accounting, Finance, or a related field required.
- **A8 `workday-Product-Portfolio-Intern_J-020242`** — estudiante activo: 'Must be enrolled as a full-time student'
  > Minimum Qualifications Currently pursuing a Bachelor's degree in Business Administration, Project Management, Marketing, Finance, Data Analytics, Engineering, or a related field.
- **A9 `workday-Senior-Analyst--Finance--Internal-Auditor-_Req-51202-1`** — What you'll need (Required): Bachelor's Degree ... is required
  > Bachelor's Degree in related field is required
- **A10 `workday-Senior-Director--Quality-Engineering_Req-50066`** — What you'll need (Required): Bachelor's Degree
  > ...What you'll need (Required): Bachelor's Degree in related field with at least 10 years experience in engineering and leadership positions in the medical device industry Experience in Quality Engineering, Quality Management, and/o...
- **A11 `workday-Service-Delivery-Manager_R77891-2`** — Qualifications Required Qualifications Bachelor's degree
  > Qualifications Required Qualifications Bachelor's degree in Information Technology, Computer Science, Business Administration, or related field.
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
  > Para tener éxito en este puesto, necesitarás las siguientes calificaciones: Licenciatura o bachillerato universitario en Administración de Empresas, Ingeniería Industrial, Logística, Supply Chain o una carrera afín.
- **B6 `workday-Applications-Support-Sr-Analyst_26963530`** — or equivalent experience
  > ...Education: Bachelor’s/University degree or equivalent experience - Fluent English - Linux - Unix - Oracle - Graphana - Snow ------------------------------------------------------ Job Family Group: Technology ---...
- **B7 `workday-Audience-Management_26999789`** — or equivalent experience
  > ...Digital Marketing and Email Deployment experience a plus Education: Bachelors/University degree or equivalent experience ------------------------------------------------------ Job Family Group: Marketing ------------------------------------------------------ Job Famil...
- **B8 `workday-Commercial-Support-Specialist_202609-124777`** — 'Bachelor's or Master's degree preferred'
  > Who you are: Bachelor’s or Master’s degree preferred in Business Administration, Finance, IT, or a related economics discipline.
- **B9 `workday-Content-Review-Operations-Specialist_202610-127168`** — or equivalent experience
  > Who You Are Bachelor’s degree or equivalent experience, with 3+ years of professional experience in content operations, digital asset management, content review/approval processes, project coordination, or marketing operations.
- **B10 `workday-Data-Governance-Foundation-Lead-Analyst_26983548`** — Education: Bachelor's/University degree (el 'preferred' es del Master's)
  > ...ds of multiple stakeholders Ability to communicate effectively to develop and deliver multi-mode communications that convey a clear understanding of the unique needs of different audiences Education: Bachelor's/University degree, Master's degree preferred...
- **B11 `workday-Datacenter-Engineer--L3-ERT_1212933-2`** — or equivalent (sin calificar) -> conservador
  > Education: Bachelor's or Master’s degree in Mechanical, Electrical, Computer Science, or equivalent.
- **B12 `workday-Digital-Campaign-Delivery-Associate_202609-122817`** — Further requirements + Bachelor's degree
  > Further requirements ● Bachelor's degree in Marketing, Business, Communications, or a related field.
- **B13 `workday-Director--Manufacturing-Engineering_REQ-2026-18566`** — Education & Experience + discipline required
  > Education & Experience Bachelor’s degree in Manufacturing, Mechanical, Electrical, Industrial, or a related Engineering discipline required
- **B14 `workday-Document-Control-Intern_1210991`** — estudiante activo: 'pursuing diplomas or degrees'
  > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
- **B15 `workday-Escalation-Engineer_1212930-2`** — What you need to bring: + Bachelor's degree
  > Bachelor’s degree in Engineering / Computer Science / IT
- **B16 `workday-HR-Generalist-Senior---Global-Discipline-Delivery_261004191`** — or equivalent experience
  > ...Bachelor’s degree/University degree or equivalent experience English advanced ------------------------------------------------------ Job Family Group: Human Resources ----------------------------------...
- **B17 `workday-Ingeniero-Principal-de-OpEx_20188241`** — preferred Bachelor's degree / or equivalent work experience
  > ...Qualifications 4-8 years of experience, preferred Bachelor's degree in related field, or equivalent work experience, preferred English Advanced CSSBB or ready to be certified, Project management skills preferred What is expected of you and others at ...
- **B18 `workday-Intern---Bachelors-Tech_1214077`** — estudiante activo: 'actively enrolled ... pursuing a Bachelor's degree'
  > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
- **B19 `workday-Lead-Mobile-Application-Engineer--NET-MAUI-_R18405`** — or equivalent practical experience
  > ...What We Look For Bachelor’s degree in Computer Science, Engineering, or a related field, or equivalent practical experience 7+ years of professional software development experience, including substantial hands-on expe...
- **B20 `workday-Network-Support-Engineer_1211197`** — or equivalent
  > ...able tools is an essential element of the role Develop a "Can-Do" attitude and suggest ways to improve the team performance and increase customer's satisfaction Basic Qualifications Higher education (Bachelor or Master degree in electrical engineering or computer science or equivalent ) 3+ years of working experience in a network support role, 2-3 of these years would be spent supporting large IP ...
- **B21 `workday-Principal-Engineer--Quality_Req-51750`** — or equivalent
  > Other incidental duties What you'll need (Required): Bachelor's degree in engineering or Scientific field, 6 years of experience minimum of experience, including either industry or industry/education or Master's Degree or equivalent in Engineering or Scientific field, 5 years of experience minimum of experience, including either industry or industry/education or Ph.D.
- **B22 `workday-Programmatic-Media-Associate---Citi-Commerce_261002988`** — or equivalent experience
  > ...ng and delivery aligned to campaign goals Experience providing clear, timely campaign reporting and issue resolutions Experience documenting operational playbooks and trafficking standards Education: Bachelors/University degree or equivalent experience (Highly preferred bachelor’s degree in Business, Marketing, or related field) This job description provides a high-level review of the types of wor...
- **B23 `workday-Regulatory-Specialist-Diagnostics_202610-126607`** — or equivalent experience
  > Who you are: Bachelor’s/Master’s degree or equivalent experience, preferably with a completed university degree in Biology, Biochemistry or Analytical Chemistry
- **B24 `workday-Sales-Commercial-Manager_R-257732`** — Role Requirements + Bachelor's degree
  > Role Requirements Bachelor's degree in Business Administration, Marketing, Economics, Life Sciences, or a related field.
- **B25 `workday-Senior-Data-Scientist---ML-Engineering---MLOps_202609-123431`** — 'Who You Are' es ambiguo -> se deja en revision
  > Who You Are Bachelor’s or Master’s degree in Computer Science, Data Science, Engineering, Statistics, or a quantitative discipline.
- **B26 `workday-Software-Engineering-Systems--Intern_1210981`** — estudiante activo: 'Education & Experience: Currently pursuing'
  > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
- **B27 `workday-Sr-Customer-Service-Representative_R-01366409`** — 'preferred but not essential'
  > Preferred Qualifications A Bachelor’s Degree is preferred but not essential.
- **B28 `workday-Strategy---Business-Operations-Head---CAMCAR_R-255612`** — Role Requirements Education + Bachelor's Degree
  > Role Requirements Education Bachelor’s Degree in Business Administration, Economics, Finance, Engineering, Strategy, Life Sciences or related disciplines.
- **B29 `workday-Switching-Technical-Support-Engineer-Intern---Switching-Support---EX-Products_1214133`** — estudiante activo: 'Education and Experience Currently pursuing'
  > Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.
- **B30 `workday-Technical-Project-Manager---HiredScore_JR-0108592-1`** — Preferred Qualifications + Bachelor's degree
  > ...ers and internal teams even when priorities or requirements are evolving Strong problem-solving skills, with the ability to troubleshoot technical issues and drive resolution Preferred Qualifications Bachelor’s degree in Business, Information Systems, Industrial Engineering, or a related field 2+ years of experience delivering AI-enabled solutions, intelligent automation, or ML-powered features wi...
