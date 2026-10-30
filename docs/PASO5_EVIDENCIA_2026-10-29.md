# Paso 5 — Evidencia del bloqueante educativo (corrida `20261029_183231`)

> Documento GENERADO por `generar_evidencia_paso5.py` (no editado a mano).
> Todo el texto citado es **literal** de `jobs.requirements_raw` +
> `jobs.description_raw`. Regla: `descartada` solo si el TEXTO confirma un
> título universitario **obligatorio**, **sin negación y sin alternativa**;
> si el texto no lo confirma → `revisar_a_mano` (`educacion_no_confirmada`).

## 1. Criterio aplicado

- **La obligatoriedad la decide el TEXTO**, no solo `requirement_level`:
  si la cláusula exige el título ("Required Qualifications", "Minimum
  Qualifications", "Basic Qualifications", "must have", "degree or
  above", "Requisitos") bloquea aunque el extractor lo marque
  `ambiguous`/`inferred`. Si el texto solo lo prefiere ("Preferred") NO
  bloquea.
- **Negación** → no se descarta ("No university degree required.").
- **Alternativa** → no se descarta ("or equivalent experience", "Associate's
  or bachelor's degree", "or advanced university studies").
- **Excepción**: "or equivalent field of study / discipline / degree" NO es
  una vía alternativa: sigue exigiendo un título universitario.
- **Estudiante activo** ("currently pursuing", "must be enrolled") es un
  criterio DISTINTO del título completado → motivo
  `titulo_universitario_en_curso_requerido`; se cumple solo si el perfil
  registra un hecho educativo `education_status='pursuing'`.

## 2. Trazabilidad de corridas (`job_match`)

```
corrida          filas  valida=1
20261029_132455  447    0
20261029_133621  447    0
20261029_160358  447    0
20261029_170343  447    0
20261029_171039  447    0
20261029_183231  447    447
```

## 3. Conteo por estado y motivo (corrida vigente `20261029_183231`)

```
calificada             | cumple_umbral                          | 102
datos_insuficientes    | cobertura_insuficiente                 | 27
datos_insuficientes    | educacion_no_cumple                    | 3
datos_insuficientes    | skill_faltante                         | 1
descartada             | titulo_universitario_en_curso_requerido | 8
descartada             | titulo_universitario_requerido         | 37
revisar_a_mano         | educacion_no_confirmada                | 20
revisar_a_mano         | educacion_no_cumple                    | 90
revisar_a_mano         | experiencia_no_verificable             | 4
revisar_a_mano         | licencia_no_comparable                 | 3
revisar_a_mano         | skill_faltante                         | 11
sin_requisitos         | sin_requisitos_mapeados                | 141
```

## 4. Las 45 `descartada` — evidencia literal

### 1. `cinde-4901` — Regulatory Affairs Specialist

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='unspecified'`
  - `value_text='Bachillerato universitario'` · `requirement_level='inferred'` · `education_status='unspecified'`

> Perform other duties as assigned ESSENCIAL QUALIFICATIONS Bachelor's degree in Engineering (e.g., Industrial, Biomedical, or Chemical), Biotechnology, Chemistry, or a related scientific or technical discipline.
>
> contexto: ...ts, and audit readiness for MDSAP, notified body, FDA, and customer audits, with emphasis on regulatory records and compliance documentation. Perform other duties as assigned ESSENCIAL QUALIFICATIONS Bachelor's degree in Engineering (e.g., Industrial, Biomedical, or Chemical), Biotechnology, Chemistry, or a related scientific or technical discipline. 1-2 years of experience in regulatory affairs within the...

### 2. `workday-Accounting-Team-Lead_J-020415` — Accounting Team Lead

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> Minimum Qualifications Bachelor Accounting Degree required 7+ years of accounting experience 2+ years of supervisory or people leadership experience Advanced English Skills and knowledge Strong analytical skills Proficient with MS Excel.
>
> contexto: ...ur office in AFZ, Heredia on Mondays, Wednesdays, and Thursdays. Please note that there may be occasions where additional office days are required, due specific business needs. Minimum Qualifications Bachelor Accounting Degree required 7+ years of accounting experience 2+ years of supervisory or people leadership experience Advanced English Skills and knowledge Strong analytical skills Proficient with MS...

### 3. `workday-Accounts-Payable-Representative_J-020440` — Accounts Payable Representative

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`

> Minimum Qualifications Bachelor’s degree coursework in Accounting, Finance, Business Administration, or a related discipline and 1+ year of relevant experience
>
> contexto: ...ur office in AFZ, Heredia on Mondays, Wednesdays, and Thursdays. Please note that there may be occasions where additional office days are required, due specific business needs. Minimum Qualifications Bachelor’s degree coursework in Accounting, Finance, Business Administration, or a related discipline and 1+ year of relevant experience; alternatively, 3+ years of relevant professional experience in Accounts...

### 4. `workday-Analyst--Compensation_Req-51280` — Analyst, Compensation

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`

> What You'll Need (Required): Bachelor's degree in human resources, Business Administration, Finance, Economics, or a related field and minimum 3 years of experience in Compensation, Human Resources, or related roles.
>
> contexto: ...tion. Support continuous improvement initiatives that enhance compensation programs, tools, and operational effectiveness. Perform other duties as assigned by management. What You'll Need (Required): Bachelor's degree in human resources, Business Administration, Finance, Economics, or a related field and minimum 3 years of experience in Compensation, Human Resources, or related roles. What Else We Look For...

### 5. `workday-Associate-Manager-Technical-Services_R567836` — Associate Manager Technical Services

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.
>
> contexto: ...as the operational backup for the Technical Services leader, ensuring continuity of decision-making, prioritization, and execution across the organization. What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field. Minimum 7 years of experience in Quality Engineering, Technical Services, Microbiology, Sterilization, Calibrations, Receiving Inspection, or relat...

### 6. `workday-Business-Analyst--Contract-Pricing-and-Accuracy_R265403` — Business Analyst, Contract Pricing and Accuracy

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='unspecified'`

> QUALIFICATIONS AND SKILLS: Bachelor’s degree in Industrial Engineering, Business Administration, or a related field.
>
> contexto: ...em. Create and maintain user guides, and conduct workshops as needed. Generate reports and dashboards to provide insights into contract status, compliance, and performance. QUALIFICATIONS AND SKILLS: Bachelor’s degree in Industrial Engineering, Business Administration, or a related field. 3 years of experience as a Business Analyst or similar role with emphasis on areas such as contract management, pricing...

### 7. `workday-Business-Operations---Customer-Delivery-Intern_3170188-1` — Business Operations & Customer Delivery Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text="bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`

> Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university.
>
> contexto: ...hnology journey to drive business outcomes, enhance employee experiences, and accelerate innovation. Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university. Preferred Majors/Programs: Business Administration Finance Economics Industrial Engineering Business Analytics Data Ana...

### 8. `workday-Business-Process-Automation---Data-Analytics-Intern_3170183-1` — Business Process Automation & Data Analytics Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text="bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`

> Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university.
>
> contexto: ...hnology journey to drive business outcomes, enhance employee experiences, and accelerate innovation. Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university. Preferred Majors/Programs: Computer Science Data Engineering / Data Analytics Industrial Engineering Process Engineerin...

### 9. `workday-Buyer-GPC_R571353` — Buyer GPC

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> Required Qualifications Bachelor’s degree in Supply Chain Management, Business Administration, Industrial Engineering, Operations Management, or a related field.
>
> contexto: ...oject progress, and operational results. Support strategic initiatives, including product lifecycle management, cost reduction projects, and supply chain optimization efforts. Required Qualifications Bachelor’s degree in Supply Chain Management, Business Administration, Industrial Engineering, Operations Management, or a related field. Minimum 3 years of experience in purchasing, supply planning, materials...

### 10. `workday-Buyer-Procurement-Operations_J-020161` — Buyer Procurement Operations

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`

> Minimum Qualifications Bachelor's degree in Logistics, Supply Chain, Engineering, Business Administration, or a related field.
>
> contexto: ...ur office in AFZ, Heredia on Mondays, Wednesdays, and Thursdays. Please note that there may be occasions where additional office days are required, due specific business needs. Minimum Qualifications Bachelor's degree in Logistics, Supply Chain, Engineering, Business Administration, or a related field. Experience/educational requirements may be waived for internal candidates. 1+ years of direct experience i...

### 11. `workday-Buyer-Procurement-Operations_J-020337` — Buyer Procurement Operations

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> Minimum Qualifications : Bachelor’s degree in Logistics, Supply Chain, Engineering, Business Administration or related with 1+ years of related experience.
>
> contexto: ...office in AFZ, Heredia on Mondays, Wednesdays, and Thursdays. Please note that there may be occasions where additional office days are required, due specific business needs. Minimum Qualifications : Bachelor’s degree in Logistics, Supply Chain, Engineering, Business Administration or related with 1+ years of related experience. Understanding of procurement and purchasing processes. Proficiency in Microsoft...

### 12. `workday-Compensation-Analyst_R268777` — Compensation Analyst

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> Provide support to Senior Analysts and Leadership regarding all compensation related projects and initiatives Education Required: Bachelor’s degree in human resources, Business Administration, Finance, or related field.
>
> contexto: ...s. Support the payroll team with the WCC or SOC codes when necessary. Provide support to Senior Analysts and Leadership regarding all compensation related projects and initiatives Education Required: Bachelor’s degree in human resources, Business Administration, Finance, or related field. Excellent communication skills in English (B2+ or higher) and ability to collaborate across functions and geographies. 2...

### 13. `workday-Continuous-Improvement-Intern_J-020427` — Continuous Improvement Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's"` · `requirement_level='ambiguous'` · `education_status='unspecified'`

> Minimum Qualifications Currently pursuing a Bachelor's or Licentiate degree in Industrial Engineering, with more than 75% of the degree program completed.
>
> contexto: ...when additional office days are required due to specific business needs. The candidate must have an unrestricted right to work for Huntsman in Costa Rica. Minimum Qualifications Currently pursuing a Bachelor's or Licentiate degree in Industrial Engineering, with more than 75% of the degree program completed. Demonstrated interest in Continuous Improvement, problem-solving, and process optimization. Written...

### 14. `workday-Contract-Administrator--Internship-_1213007` — Contract Administrator (Internship)

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='pursuing'`
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='pursuing'`

> ...ormance, efficiency and customer satisfaction Develops understanding of internal and external relationships with stakeholders for performance expectations and needs Education and Experience Required: Bachelor's degree in Business Administration, Industrial Engineering, Finance, Accounting or related fields....
>
> contexto: ...and are a force for good. If you are looking to stretch and grow your career our culture will embrace you. Open up opportunities with HPE. Job Description: Job Family Definition: Students pursuing a Bachelor's degree in Business Administration, Industrial Engineering, Finance, Accounting or related fields. Assists in various tasks aligned with their field of study, including research, collaboration on team...

### 15. `workday-Contract-Pricing-Team-Lead_R265399` — Contract Pricing Team Lead

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`

> Qualifications and Skills Bachelor's degree in Business Administration or a related field required.
>
> contexto: ...ghts clearly and effectively. Support change management efforts tied to process or system enhancements. Provide training and support to end-users on new tools and workflows. Qualifications and Skills Bachelor's degree in Business Administration or a related field required. Excellent communication skills in English (B2+ or higher) and ability to collaborate across functions and geographies. Minimum 5 years o...

### 16. `workday-Contracts-Negotiator_JR-0110562` — Contracts Negotiator

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`

> ...projects as determined by needs of the business and department About You Basic Qualifications 5+ years of experience managing contracts (including drafting and negotiation) in a corporate environment Bachelor’s Degree or above Experience in a law firm or legal department is required Licensed attorney is desired but not required Other Qualifications Proficient in Microsoft Office products and Googl...
>
> contexto: ...projects as determined by needs of the business and department About You Basic Qualifications 5+ years of experience managing contracts (including drafting and negotiation) in a corporate environment Bachelor’s Degree or above Experience in a law firm or legal department is required Licensed attorney is desired but not required Other Qualifications Proficient in Microsoft Office products and Google applicat...

### 17. `workday-Cybersecurity-Analyst---Monitoring---Incident-Response_202604-108991-1` — Cybersecurity Analyst - Monitoring & Incident Response

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=False · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> ...te information security concepts and situations to senior management Contribute operational feedback to continuously strengthen detection and response processes Mentor newer team members Who You Are: Bachelor’s degree in a technical field and 7+ years of experience in information security, including at least 3 years in a SOC/CERT/CSIRT environment Familiarity with TLP and information sharing best ...
>
> contexto: ...te information security concepts and situations to senior management Contribute operational feedback to continuously strengthen detection and response processes Mentor newer team members Who You Are: Bachelor’s degree in a technical field and 7+ years of experience in information security, including at least 3 years in a SOC/CERT/CSIRT environment Familiarity with TLP and information sharing best practices...

### 18. `workday-Director--Corporate-Accounting_JR-0111126` — Director, Corporate Accounting

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='ambiguous'` · `education_status='unspecified'`

> About You Required Qualifications: Bachelor’s degree in Accounting, Finance, or a related field required.
>
> contexto: ...accounting operations and decision-making. Ensure work is appropriately prioritized, documented, controlled, and aligned with broader Accounting and Finance goals. About You Required Qualifications: Bachelor’s degree in Accounting, Finance, or a related field required. 10+ years of progressive accounting experience, including significant corporate accounting leadership experience. Solid working knowledge o...

### 19. `workday-Global-Supply-Chain-Data-Analyst--Temporary-_J-019858` — Supply Chain Data Analyst (Temporary)

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> Bachelor’s degree in Supply Chain Management, Business Analytics, Industrial Engineering, or a related field.
>
> contexto: ...s, and Thursdays. Please note that there may be occasions where additional office days are required, especially during corporate visits or when specific business needs arise. Minimum Qualifications • Bachelor’s degree in Supply Chain Management, Business Analytics, Industrial Engineering, or a related field. • 5+ years of experience in supply chain analytics or a related role. • Strong proficiency in data a...

### 20. `workday-Intern---Bachelor-s-Tech_1216552` — Intern - Bachelor's Tech

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=False · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='pursuing'`
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
  - `value_text="Bachelor's"` · `requirement_level='required'` · `education_status='unspecified'`

> Job Description: Job Family Definition: Students of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in Engineering, Computer Science, Information Technology, or a related technical field.
>
> contexto: ...l embrace you. Open up opportunities with HPE. Job Description: Job Family Definition: Students of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in Engineering, Computer Science, Information Technology, or a related technical field. Assists in various tasks aligned with their field of study, including research, collaboratio...

### 21. `workday-LATAM-COE-Senior-Tax-Analyst_549089` — LATAM COE Senior Tax Analyst

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> Basic Qualifications: We are looking for professionals with the required skills to achieve our goals: Bachelor’s Degree in Accounting, Finance, or a related field.
>
> contexto: ...ng, Shared Services, and local market teams to ensure accurate reporting and compliance. Why you? Basic Qualifications: We are looking for professionals with the required skills to achieve our goals: Bachelor’s Degree in Accounting, Finance, or a related field. 5+ years of experience in Tax, Audit, Risk Management, or related areas, preferably within a Shared Services environment. Intermediate to advanced E...

### 22. `workday-Leader--Customer-Support_2022544-1` — Leader, Customer Support

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=False · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`

> Bachelor's degree and 7 years of related experience, or a master's degree and 4 years of related experience, or a PhD and 1 year of related experience.
>
> contexto: ...artners. · A people leader who coaches through change, develops capability, encourages responsible use of AI and automation, and creates psychological safety. Our minimum requirements for this role · Bachelor's degree and 7 years of related experience, or a master's degree and 4 years of related experience, or a PhD and 1 year of related experience. · Previous supervisory or team lead experience. · At least...

### 23. `workday-Manager--Business-Continuity_Req-49141` — Manager, Business Continuity

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=False · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`

> Bachelor's degree in business administration, Supply Chain Management, Emergency Management, Risk Management, Engineering, or related field, with 8+ years' experience
>
> contexto: ...ior leaders and serve as a BCM subject matter expert to adjacent resilience and risk initiatives, including strategic sourcing resilience and IT resilience assessments. What you'll need (Required): • Bachelor's degree in business administration, Supply Chain Management, Emergency Management, Risk Management, Engineering, or related field, with 8+ years' experience • Master's degree with 6+ years of relevant...

### 24. `workday-Master-Data-Analyst_R-01358585` — Master Data Analyst

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> REQUIRED QUALIFICATIONS Education: Bachelor’s degree in supply chain, Business Administration, Information Technology, or related field Experience: Minimum 2 years of experience with SAP in Operations/Warehouse/ Manufacturing or related environment, preferably in the pharmaceutical industry.
>
> contexto: ...ment reports, support performance tracking (data accuracy, reporting accuracy, standards alignment, timely updates), and act as backup for the Supply Chain Analyst. REQUIRED QUALIFICATIONS Education: Bachelor’s degree in supply chain, Business Administration, Information Technology, or related field Experience: Minimum 2 years of experience with SAP in Operations/Warehouse/ Manufacturing or related environm...

### 25. `workday-Planner-II_31164664` — Planner II

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> Shift: Administrative Required Qualifications Bachelor´s Degree in Engineering or related field.
>
> contexto: ...Ops on product commitments, exception management and new product introductions. Planning and MFG execution reports. Ensure Planning KPI metrics are met. Shift: Administrative Required Qualifications Bachelor´s Degree in Engineering or related field. Experience 2-4 years in: Related work experience with a complete understanding of specified functional area. Planning and Scheduling: Planning resources, bal...

### 26. `workday-Product-Portfolio-Intern_J-020242` — Product Portfolio Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='pursuing'`

> Minimum Qualifications Currently pursuing a Bachelor's degree in Business Administration, Project Management, Marketing, Finance, Data Analytics, Engineering, or a related field.
>
> contexto: ...edia on Mondays, Wednesdays, and Thursdays. Please note that there may be occasions where additional office days are required, due specific business needs. Minimum Qualifications Currently pursuing a Bachelor's degree in Business Administration, Project Management, Marketing, Finance, Data Analytics, Engineering, or a related field. Must be enrolled as a full-time student at an accredited university through...

### 27. `workday-Purchasing-Manager--Global-Procurement-Center_R572335` — Purchasing Manager, Global Procurement Center

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> What You Will Need Required Qualifications Bachelor’s degree in Business, Supply Chain Management, Engineering, or a related field.
>
> contexto: ...g development plans for managers and buyers. Ensure compliance with applicable quality and regulatory requirements and support internal and external audits. What You Will Need Required Qualifications Bachelor’s degree in Business, Supply Chain Management, Engineering, or a related field. Minimum 8 years of experience in Supply Chain, Purchasing, Procurement, Manufacturing, or a related field. Minimum 3 year...

### 28. `workday-R-D-Process-Coordinator_R-106675` — R&D Process Coordinator

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Licenciatura'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Licenciatura'` · `requirement_level='required'` · `education_status='unspecified'`

> ...arámetros de sanitización/CIP y materiales de capacitación Liderar procesos de control de cambios y evaluaciones de riesgo para modificaciones de formulación, procesos, packaging y equipos Requisitos Licenciatura/Ingeniería completa en Ingeniería Química, Mecánica, Industrial, de Manufactura, Alimentos o áreas relacionadas Más de 5 años de experiencia en ingeniería de procesos y/o ambientes de man...
>
> contexto: ...arámetros de sanitización/CIP y materiales de capacitación Liderar procesos de control de cambios y evaluaciones de riesgo para modificaciones de formulación, procesos, packaging y equipos Requisitos Licenciatura/Ingeniería completa en Ingeniería Química, Mecánica, Industrial, de Manufactura, Alimentos o áreas relacionadas Más de 5 años de experiencia en ingeniería de procesos y/o ambientes de manufactura Exp...

### 29. `workday-Security-Engineer_2025477` — Security Engineer

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> Minimum Qualifications Bachelor’s degree with 3+ years of related experience, or a Master’s degree with 3+ years of related experience working in cybersecurity engineering, infrastructure engineering, DevOps, or a large enterprise technology environment.
>
> contexto: ...ithin the organization, conducting training sessions or "lunch-and-learns" to improve the overall security awareness and coding practices of cross-functional development teams. Minimum Qualifications Bachelor’s degree with 3+ years of related experience, or a Master’s degree with 3+ years of related experience working in cybersecurity engineering, infrastructure engineering, DevOps, or a large enterprise te...

### 30. `workday-Senior-Analyst--Finance--Internal-Auditor-_Req-51202-1` — Senior Analyst, Finance (Internal Audit)

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's Degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`

> Bachelor's Degree in related field is required
>
> contexto: ...ernal audit requests. • Support continuous improvement of audit methodologies, tools, analytics, and processes. • Perform other duties and special projects as assigned. What you'll need (Required): • Bachelor's Degree in related field is required • Minimum 5 years of previous related experience is required • Experience working in a medical device or a related manufacturing environment is required • Advance...

### 31. `workday-Senior-Director--Quality-Engineering_Req-50066` — Senior Director, Quality Engineering

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's Degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`

> ...What you'll need (Required): Bachelor's Degree in related field with at least 10 years experience in engineering and leadership positions in the medical device industry Experience in Quality Engineering, Quality Management, and/o...
>
> contexto: ...es. Provide quality engagement to audits including resources support, technical and procedural expertise, presentation of information, and effective resolution of issues. What you'll need (Required): Bachelor's Degree in related field with at least 10 years experience in engineering and leadership positions in the medical device industry Experience in Quality Engineering, Quality Management, and/or Regulato...

### 32. `workday-Senior-Project-Accountant_J000703933` — Senior Project Accountant

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=False · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> Bachelor’s Degree in Accounting, Finance, or a closely related field
>
> contexto: ...invoices are accurate, approved, and sent on time • Compliance & Audits: Help maintain a strong control environment that is compliant with company policies and accounting standards Your Background: • Bachelor’s Degree in Accounting, Finance, or a closely related field • At least 5+ years of progressive project accounting experience or related accounting or finance roles • In collaboration with the Manager,...

### 33. `workday-Senior-Quality-Engineer_R567778` — Quality Engineer

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.
>
> contexto: ...l analysis and risk management tools, including Failure Mode and Effects Analysis (FMEA), to support decision-making and continuous improvement initiatives. What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field. Minimum 3 years of experience in Quality Engineering. Working knowledge of 21 CFR Part 820, ISO 13485, and the Medical Device Single Audit Program...

### 34. `workday-Senior-Quality-Incoming-Process-Supervisor_R567857` — Senior Quality Incoming/Process Supervisor

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.
>
> contexto: ...t product and process improvements. Support internal and external audits and maintain compliance with applicable quality system and regulatory requirements. What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field. Minimum 5 years of experience in Quality Engineering, Quality Control, or Quality Assurance within a regulated manufacturing environment. Minimum 2...

### 35. `workday-Senior-Software-Quality-Engineer_R262277` — Senior Technology Project Manager – Quality & Delivery

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> Required Qualifications Bachelor’s degree in Computer Science, Information Technology, Engineering, Business, Project Management, or a related field.
>
> contexto: ...l teams, business stakeholders, and leadership. Promote consistent project management, testing, process improvement, and technology delivery best practices across initiatives. Required Qualifications Bachelor’s degree in Computer Science, Information Technology, Engineering, Business, Project Management, or a related field. 6+ years of experience in Technology Project Management, IT Project Management, Tech...

### 36. `workday-Senior-Supervisor--Manufacturing_Req-50617` — Senior Supervisor, Manufacturing

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`

> What you’ll need (Required): Bachelor's degree in Industrial Engineering, Business Administration or related field.
>
> contexto: ...outcomes of assigned unit/group of employees May guide and mentor entry level supervisors May provide management duties in the absence of Manager Other incidental duties. What you’ll need (Required): Bachelor's degree in Industrial Engineering, Business Administration or related field. More than 5 years of experience in personnel supervisory with full responsibility for all personnel and handling all aspect...

### 37. `workday-Service-Delivery-Manager_R77891-2` — Service Delivery Manager.

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Baccalaureate'` · `requirement_level='ambiguous'` · `education_status='unspecified'`
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`

> Qualifications Required Qualifications Bachelor's degree in Information Technology, Computer Science, Business Administration, or related field.
>
> contexto: ...nitiatives, and strategic roadmaps. Facilitate communication between business partners and service providers to ensure alignment with organizational priorities. Qualifications Required Qualifications Bachelor's degree in Information Technology, Computer Science, Business Administration, or related field. 7+ years of experience in IT service delivery, endpoint management, infrastructure operations, or workpl...

### 38. `workday-Sourcing-Manager_R571931` — Sourcing Manager

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`

> What You Will Need Required Qualifications Bachelor's degree in Supply Chain Management, Business, Engineering, or a related field.
>
> contexto: ...d risk metrics. Partner with Quality, Engineering, Finance, Legal, Logistics, and Procurement teams to execute sourcing strategies and supplier transitions. What You Will Need Required Qualifications Bachelor's degree in Supply Chain Management, Business, Engineering, or a related field. Minimum 7 years of professional experience in supply chain, procurement, sourcing, or a related function. Minimum 1 year...

### 39. `workday-Sr-Supv--Accounts-Payable_Req-51765` — Sr Supv, Accounts Payable

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> What you´ll need (Required): Bachelor’s degree in a related field and 8 years of previous Accounts Payable experience, including demonstrated experience supervising Accounts Payable employees.
>
> contexto: ...g to internal customers on Accounts Payable requirements, invoice processing, approvals, and related processes. Perform other incidental duties as assigned by leadership. What you´ll need (Required): Bachelor’s degree in a related field and 8 years of previous Accounts Payable experience, including demonstrated experience supervising Accounts Payable employees. What Else We Look For (Preferred): Strong know...

### 40. `workday-Sr-Technical-Architect_WD30279546` — Sr Technical Architect

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='unspecified'`

> Qualifications Bachelor’s degree in IT or a similar technology-related discipline.
>
> contexto: ...by sharing information openly and early. Communicate with clarity so stakeholders understand trade-offs, dependencies, risks, and the technical approach required to move work forward. Qualifications Bachelor’s degree in IT or a similar technology-related discipline. Minimum 8 years of IT experience. Minimum 3 years of experience architecting integration solutions using APIs. Minimum 5 years of development...

### 41. `workday-Storage-Hardware-Operations-Intern_1210994` — Storage Hardware Operations Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='inferred'` · `education_status='pursuing'`
  - `value_text="Bachelor's degree"` · `requirement_level='inferred'` · `education_status='pursuing'`
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='pursuing'`

> Education and Experience Required Currently pursuing a Bachelor's degree in Engineering, Supply Chain, Information Systems, Data Analytics, Business, Computer Science, or a related field.
>
> contexto: ...d enhance decision-making within the Storage Hardware organization. Support special projects and continuous improvement initiatives as assigned. Education and Experience Required Currently pursuing a Bachelor's degree in Engineering, Supply Chain, Information Systems, Data Analytics, Business, Computer Science, or a related field. Knowledge and Skills Strong organizational skills and attention to detail. An...

### 42. `workday-Supplier-Quality-Engineer-III_31162905` — Supplier Quality Engineer III

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='required'` · `education_status='unspecified'`

> As required , supervise technical personal for task execution Shift: Administrative Required Qualifications Bachelor's degree in engineering, Science, or equivalent field of study.
>
> contexto: ...ed . Mentors employees by sharing technical expertise and providing feedback and guidance . As required , supervise technical personal for task execution Shift: Administrative Required Qualifications Bachelor's degree in engineering, Science, or equivalent field of study. 2 of experience in engineering related position. Intermediate command of English. Apply Now Follow your career aspirations to Abbott for...

### 43. `workday-Tax-Audit-Senior-Specialist_888004-1` — Tax Compliance Analyst III

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `"Bachelor's"`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · `education_status='unspecified'`

> To succeed in this role, you will need the following qualifications: Bachelor's degree in finance, accounting, internal control or related field along with experience in USGAAP, preparing Income Tax Returns, Informative reports, compliance reports and attending tax audits.
>
> contexto: ...entic caring. You want to be part of a company actively dedicated to sustainability, inclusion, wellbeing, and career development. To succeed in this role, you will need the following qualifications: Bachelor's degree in finance, accounting, internal control or related field along with experience in USGAAP, preparing Income Tax Returns, Informative reports, compliance reports and attending tax audits. More...

### 44. `workday-Technical-Support-Delivery-Intern_JR-0110629-1` — Technical Support Delivery Intern

- motivo en BD: `titulo_universitario_en_curso_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=True · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='pursuing'`

> ...#LI-DNI About You Basic Qualifications Currently pursuing a Bachelor’s degree in Computer Science, Information Technology, or related field, with an anticipated graduation date of June/July 2027 Must be able to commit to the full duration of the 23 week intern...
>
> contexto: ...living our Core Values. Let’s make work days brighter. Apply today to start your career as a member of the Workday Intern & Co-Op Program! #LI-DNI About You Basic Qualifications Currently pursuing a Bachelor’s degree in Computer Science, Information Technology, or related field, with an anticipated graduation date of June/July 2027 Must be able to commit to the full duration of the 23 week internship (Star...

### 45. `workday-ingeniero-de-Manufactura_20184428` — ingeniero de Manufactura

- motivo en BD: `titulo_universitario_requerido`
- detección textual: `confirmado` (término: `'Bachelor’s'`) · obligatorio=True · en_curso=False · suave=False
- requisitos `education` extraídos:
  - `value_text='Bachelor'` · `requirement_level='required'` · `education_status='unspecified'`

> Qualifications/Responsibilities 2-4 years of experience in a highly regulated industry Bachelor’s degree in Engineering or a related field required.
>
> contexto: ...ives. Also designs process improvements to reduce product cost, process cycle time and improved product quality. Qualifications/Responsibilities 2-4 years of experience in a highly regulated industry Bachelor’s degree in Engineering or a related field required. Intermediate English proficiency (B1), Experience leading projects and supporting cost-reduction and quality-improvement initiatives within producti...

## 5. Las 20 `revisar_a_mano / educacion_no_confirmada` — por qué NO se descartan

Son requisitos universitarios **obligatorios** que el TEXTO no confirma
(negación o alternativa). Van a revisión manual (Paso 6).

### 1. `cinde-4888` — IT Software Developer II

- detección textual: `alternativa` (término: `"Bachelor's"`)

> What We're Looking For Required Qualifications Bachelor's degree in Computer Science, Software Engineering, Information Technology, or a related field, or equivalent practical experience.

### 2. `linkedin-4483157697` — Technical Support Specialist (Tier 2)

- detección textual: `negacion` (término: `'university degree'`)

> No university degree required.

### 3. `workday-Accounting-Analyst---Temporary_J-020392` — Accounting Analyst – Temporary

- detección textual: `alternativa` (término: `'Bachelor’s'`)

> Minimum Qualifications Bachelor’s degree in Accounting, Finance, or a related field , or advanced university studies in Accounting.

### 4. `workday-Assistant-Director-of-Engineering_REQ10393409` — Assistant Director of Engineering

- detección textual: `alternativa` (término: `'Bachelor’s'`)

> Required Qualifications Education Bachelor’s degree or technical degree in Mechanical Engineering, Electrical Engineering, Electromechanical Engineering, Industrial Maintenance, Facilities Management, Civil Engineering, or a related field.

### 5. `workday-Associate--Repair-III_R-118081` — Associate, Repair III

- detección textual: `sin_termino` (término: `None`)

### 6. `workday-Buyer-Planner-Sr_31163601` — Buyer Planner Sr

- detección textual: `alternativa` (término: `'Bachelor'`)

> Required Qualifications Bachelor Degree, engineering, science or closely related discipline is desired, or equivalent technical.

### 7. `workday-Cardiac-Specialist-II_R18282-1` — Cardiac Specialist II

- detección textual: `alternativa` (término: `"Bachelor's"`)

> What We Look For Bachelor's degree, ECG certification, or an equivalent combination of education and relevant experience required.

### 8. `workday-Clinical-Project-Manager_R18034-1` — Clinical Project Manager

- detección textual: `alternativa` (término: `'Bachelor’s'`)

> What We Look For Bachelor’s degree required or equivalent experience

### 9. `workday-Creative-Execution-Manager--CrM-_261002442` — Creative Execution Manager (CrM)

- detección textual: `alternativa` (término: `'Bachelors'`)

> Required Licensing/Registration: Series 7, Series 63 Education: Bachelors/University degree or equivalent experience This job description provides a high-level review of the types of work performed.

### 10. `workday-Credit---Collections-Specialist--2_R232432` — Credit & Collections Specialist

- detección textual: `alternativa` (término: `'bachelor’s'`)

> ...ter data is accurate and up to date Deliver excellent customer service to both internal and external partners Participate in special projects and additional duties as assigned Required Associate’s or bachelor’s degree in business, Finance, or a related field 1–2 years of experience in B2B credit, collections, or accounts receivable Excellent communication skills in English (B2+ or higher) and abil...

### 11. `workday-HPE---Professional-Sales-HIT--Compute-and-Hybrid-Cloud-_R-116879` — HPE - Professional Sales HIT (Compute and Hybrid Cloud)

- detección textual: `alternativa` (término: `'four year college degree'`)

> A four year college degree (or additional experience in a related field) and 3 years functional experience including a minimum 1 year position specific experience.

### 12. `workday-Instructional-Designer_R17971` — Instructional Designer – Hybrid

- detección textual: `alternativa` (término: `"Bachelor's"`)

> What We Look For Hybrid Work Availability: Candidates must be available to work in a hybrid setting, including regular on-site presence as required Bachelor's degree or certification in Learning and Development, Education, Business, or a related field.

### 13. `workday-Principal-Cybersecurity-Engineer_R0007423` — Principal Cybersecurity Engineer

- detección textual: `alternativa` (término: `'Bachelor’s'`)

> Bachelor’s degree in Computer Science, Information Security, or a related field, or equivalent professional experience.

### 14. `workday-Production-Supervisor-I_31163511` — Production Supervisor I

- detección textual: `alternativa` (término: `'bachelor’s'`)

> Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience.

### 15. `workday-Production-Supervisor-I_31163518` — Production Supervisor I

- detección textual: `alternativa` (término: `'bachelor’s'`)

> Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience.

### 16. `workday-Sales-Specialist_R-117581` — Sales Specialist

- detección textual: `alternativa` (término: `'four year college degree'`)

> A four year college degree (or additional experience in a related field) and 3 years functional experience including a minimum 1 year position specific experience.

### 17. `workday-Security-Governance---Compliance-Specialist_2022361-1` — Security Governance & Compliance Specialist

- detección textual: `alternativa` (término: `'Bachelor’s'`)

> Minimum Qualifications Bachelor’s degree plus 5+ years of experience in technical compliance, security, risk, audit, or a related field

### 18. `workday-Security-Governance---Compliance-Specialist_2023168-1` — Security Governance & Compliance Specialist

- detección textual: `alternativa` (término: `"Bachelor's"`)

> Must-have Qualifications Bachelor's degree or equivalent work experience required.

### 19. `workday-Senior-Client-Services-Executive_R2025-244318` — Senior Client Services Executive

- detección textual: `alternativa` (término: `'Bachelor’s'`)

> Minimum Bachelor’s degree or its equivalent

### 20. `workday-TnF-Manager-Systems---Software_1214477-2` — TnF Manager Systems / Software

- detección textual: `alternativa` (término: `"Bachelor's"`)

> Education and Experience Required: Bachelor's or Master's degree in Computer Science, Computer/Electronics Engineering, Information Systems, or equivalent.

## 6. Medición de `educacion_no_cumple` (muestra de 10)

Muestra cada 10º `job_id` del grupo `revisar_a_mano / educacion_no_cumple`
de la corrida anterior (`20261029_171039`), para medir cuántos eran
bloqueos REALES escondidos por el nivel `ambiguous`/`inferred` del
extractor.

| job_id | veredicto manual | evidencia |
|---|---|---|
| `cinde-4887` | BLOQUEO REAL | Bachillerato universitario incompleto; el texto exige estudiante activo |
| `workday-Contracts-Negotiator_JR-0110562` | BLOQUEO REAL | Basic Qualifications … Bachelor's Degree or above |
| `workday-Product-Portfolio-Intern_J-020242` | BLOQUEO REAL | Currently pursuing a Bachelor's degree … Must be enrolled |
| `workday-Senior-Data-Scientist---Generative-AI---Agentic-Systems_202609-123437` | BLOQUEO REAL | el texto exige título universitario en sección de requisitos |
| `workday-Sr-Technical-Architect_WD30279546` | BLOQUEO REAL | Qualifications Bachelor's degree in IT or a similar technology-related discipline |

Resultado: **5 de 10** eran bloqueos reales → el texto decide la
obligatoriedad, no solo `requirement_level`. Con la regla nueva, esas
vacantes pasan a `descartada` (con evidencia literal) y las que el texto
no obliga siguen en `revisar_a_mano`.
