# Paso 5 — Evidencia del bloqueante educativo (corrida `20261029_171039`)

> Generado el 2026-10-29 con `evidencia_descartadas.py` / `resumen_bloqueo.py`.
> Todo el texto citado es **literal** de `jobs.requirements_raw` + `jobs.description_raw`.
> Regla: `descartada` solo si el texto completo confirma un título universitario
> con `requirement_level='required'`, **sin negación y sin alternativa**.

## 1. Trazabilidad de corridas (`job_match`)

```
corrida          filas  valida=1
20261029_132455  447    0
20261029_133621  447    0
20261029_160358  447    0
20261029_170343  447    0
20261029_171039  447    447
```

## 2. Conteo por estado y motivo (corrida vigente `20261029_171039`)

```
calificada             | cumple_umbral                    | 102
datos_insuficientes    | cobertura_insuficiente           | 27
datos_insuficientes    | educacion_no_cumple              | 3
datos_insuficientes    | skill_faltante                   | 1
descartada             | titulo_universitario_requerido   | 32
revisar_a_mano         | educacion_no_confirmada          | 20
revisar_a_mano         | educacion_no_cumple              | 103
revisar_a_mano         | experiencia_no_verificable       | 4
revisar_a_mano         | licencia_no_comparable           | 3
revisar_a_mano         | skill_faltante                   | 11
sin_requisitos         | sin_requisitos_mapeados          | 141
```

## 3. Las 32 `descartada` — frase literal que confirma el título

### 1. `workday-Accounting-Analyst---Temporary_J-020392` — Accounting Analyst – Temporary

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> Minimum Qualifications Bachelor’s degree in Accounting, Finance, or a related field , or advanced university studies in Accounting.

### 2. `workday-Accounting-Team-Lead_J-020415` — Accounting Team Lead

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor'`)

> Minimum Qualifications Bachelor Accounting Degree required 7+ years of accounting experience 2+ years of supervisory or people leadership experience Advanced English Skills and knowledge Strong analytical skills Proficient with MS Excel.

### 3. `workday-Analyst--Compensation_Req-51280` — Analyst, Compensation

- requisito bloqueante: `value_text="Bachelor's degree"` · `requirement_level='required'`
- detección textual: `confirmado` (término: `"Bachelor's"`)

> What You'll Need (Required): Bachelor's degree in human resources, Business Administration, Finance, Economics, or a related field and minimum 3 years of experience in Compensation, Human Resources, or related roles.

### 4. `workday-Associate-Manager-Technical-Services_R567836` — Associate Manager Technical Services

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.

### 5. `workday-Business-Operations---Customer-Delivery-Intern_3170188-1` — Business Operations & Customer Delivery Intern

- requisito bloqueante: `value_text="bachelor's degree"` · `requirement_level='required'`
- detección textual: `confirmado` (término: `"bachelor's"`)

> Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university.

### 6. `workday-Business-Process-Automation---Data-Analytics-Intern_3170183-1` — Business Process Automation & Data Analytics Intern

- requisito bloqueante: `value_text="bachelor's degree"` · `requirement_level='required'`
- detección textual: `confirmado` (término: `"bachelor's"`)

> Education and Experience Required: Currently enrolled in a four-year college and graduating with a bachelor's degree in February 2028 Must be enrolled full time at an accredited university.

### 7. `workday-Buyer-GPC_R571353` — Buyer GPC

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> Required Qualifications Bachelor’s degree in Supply Chain Management, Business Administration, Industrial Engineering, Operations Management, or a related field.

### 8. `workday-Buyer-Procurement-Operations_J-020161` — Buyer Procurement Operations

- requisito bloqueante: `value_text="Bachelor's degree"` · `requirement_level='required'`
- detección textual: `confirmado` (término: `"Bachelor's"`)

> Minimum Qualifications Bachelor's degree in Logistics, Supply Chain, Engineering, Business Administration, or a related field.

### 9. `workday-Buyer-Procurement-Operations_J-020337` — Buyer Procurement Operations

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> Minimum Qualifications : Bachelor’s degree in Logistics, Supply Chain, Engineering, Business Administration or related with 1+ years of related experience.

### 10. `workday-Compensation-Analyst_R268777` — Compensation Analyst

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> Provide support to Senior Analysts and Leadership regarding all compensation related projects and initiatives Education Required: Bachelor’s degree in human resources, Business Administration, Finance, or related field.

### 11. `workday-Contract-Pricing-Team-Lead_R265399` — Contract Pricing Team Lead

- requisito bloqueante: `value_text="Bachelor's degree"` · `requirement_level='required'`
- detección textual: `confirmado` (término: `"Bachelor's"`)

> Qualifications and Skills Bachelor's degree in Business Administration or a related field required.

### 12. `workday-Cybersecurity-Analyst---Monitoring---Incident-Response_202604-108991-1` — Cybersecurity Analyst - Monitoring & Incident Response

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> ...te information security concepts and situations to senior management Contribute operational feedback to continuously strengthen detection and response processes Mentor newer team members Who You Are: Bachelor’s degree in a technical field and 7+ years of experience in information security, including at least 3 years in a SOC/CERT/CSIRT environment Familiarity with TLP and information sharing best ...

### 13. `workday-Global-Supply-Chain-Data-Analyst--Temporary-_J-019858` — Supply Chain Data Analyst (Temporary)

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> Bachelor’s degree in Supply Chain Management, Business Analytics, Industrial Engineering, or a related field.

### 14. `workday-Intern---Bachelor-s-Tech_1216552` — Intern - Bachelor's Tech

- requisito bloqueante: `value_text="Bachelor's"` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> Job Description: Job Family Definition: Students of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in Engineering, Computer Science, Information Technology, or a related technical field.

### 15. `workday-LATAM-COE-Senior-Tax-Analyst_549089` — LATAM COE Senior Tax Analyst

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> Basic Qualifications: We are looking for professionals with the required skills to achieve our goals: Bachelor’s Degree in Accounting, Finance, or a related field.

### 16. `workday-Leader--Customer-Support_2022544-1` — Leader, Customer Support

- requisito bloqueante: `value_text="Bachelor's degree"` · `requirement_level='required'`
- detección textual: `confirmado` (término: `"Bachelor's"`)

> Bachelor's degree and 7 years of related experience, or a master's degree and 4 years of related experience, or a PhD and 1 year of related experience.

### 17. `workday-Manager--Business-Continuity_Req-49141` — Manager, Business Continuity

- requisito bloqueante: `value_text="Bachelor's degree"` · `requirement_level='required'`
- detección textual: `confirmado` (término: `"Bachelor's"`)

> Bachelor's degree in business administration, Supply Chain Management, Emergency Management, Risk Management, Engineering, or related field, with 8+ years' experience

### 18. `workday-Master-Data-Analyst_R-01358585` — Master Data Analyst

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> REQUIRED QUALIFICATIONS Education: Bachelor’s degree in supply chain, Business Administration, Information Technology, or related field Experience: Minimum 2 years of experience with SAP in Operations/Warehouse/ Manufacturing or related environment, preferably in the pharmaceutical industry.

### 19. `workday-Planner-II_31164664` — Planner II

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor'`)

> Shift: Administrative Required Qualifications Bachelor´s Degree in Engineering or related field.

### 20. `workday-Purchasing-Manager--Global-Procurement-Center_R572335` — Purchasing Manager, Global Procurement Center

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> What You Will Need Required Qualifications Bachelor’s degree in Business, Supply Chain Management, Engineering, or a related field.

### 21. `workday-R-D-Process-Coordinator_R-106675` — R&D Process Coordinator

- requisito bloqueante: `value_text='Licenciatura'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Licenciatura'`)

> ...arámetros de sanitización/CIP y materiales de capacitación Liderar procesos de control de cambios y evaluaciones de riesgo para modificaciones de formulación, procesos, packaging y equipos Requisitos Licenciatura/Ingeniería completa en Ingeniería Química, Mecánica, Industrial, de Manufactura, Alimentos o áreas relacionadas Más de 5 años de experiencia en ingeniería de procesos y/o ambientes de man...

### 22. `workday-Security-Engineer_2025477` — Security Engineer

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> Minimum Qualifications Bachelor’s degree with 3+ years of related experience, or a Master’s degree with 3+ years of related experience working in cybersecurity engineering, infrastructure engineering, DevOps, or a large enterprise technology environment.

### 23. `workday-Senior-Project-Accountant_J000703933` — Senior Project Accountant

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> Bachelor’s Degree in Accounting, Finance, or a closely related field

### 24. `workday-Senior-Quality-Engineer_R567778` — Quality Engineer

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.

### 25. `workday-Senior-Quality-Incoming-Process-Supervisor_R567857` — Senior Quality Incoming/Process Supervisor

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> What You Will Need Required Qualifications Bachelor’s degree in Engineering or a related technical field.

### 26. `workday-Senior-Software-Quality-Engineer_R262277` — Senior Technology Project Manager – Quality & Delivery

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> Required Qualifications Bachelor’s degree in Computer Science, Information Technology, Engineering, Business, Project Management, or a related field.

### 27. `workday-Senior-Supervisor--Manufacturing_Req-50617` — Senior Supervisor, Manufacturing

- requisito bloqueante: `value_text="Bachelor's degree"` · `requirement_level='required'`
- detección textual: `confirmado` (término: `"Bachelor's"`)

> What you’ll need (Required): Bachelor's degree in Industrial Engineering, Business Administration or related field.

### 28. `workday-Sourcing-Manager_R571931` — Sourcing Manager

- requisito bloqueante: `value_text="Bachelor's degree"` · `requirement_level='required'`
- detección textual: `confirmado` (término: `"Bachelor's"`)

> What You Will Need Required Qualifications Bachelor's degree in Supply Chain Management, Business, Engineering, or a related field.

### 29. `workday-Sr-Supv--Accounts-Payable_Req-51765` — Sr Supv, Accounts Payable

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> What you´ll need (Required): Bachelor’s degree in a related field and 8 years of previous Accounts Payable experience, including demonstrated experience supervising Accounts Payable employees.

### 30. `workday-Storage-Hardware-Operations-Intern_1210994` — Storage Hardware Operations Intern

- requisito bloqueante: `value_text="Bachelor's degree"` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> Job Description: Job Family Definition: Students or recent graduates of college, university, or other accredited academic programs, pursuing diplomas or degrees (Associate, Bachelor’s, Master’s, or PhD) in any field.

### 31. `workday-Technical-Support-Delivery-Intern_JR-0110629-1` — Technical Support Delivery Intern

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> ...#LI-DNI About You Basic Qualifications Currently pursuing a Bachelor’s degree in Computer Science, Information Technology, or related field, with an anticipated graduation date of June/July 2027 Must be able to commit to the full duration of the 23 week intern...

### 32. `workday-ingeniero-de-Manufactura_20184428` — ingeniero de Manufactura

- requisito bloqueante: `value_text='Bachelor'` · `requirement_level='required'`
- detección textual: `confirmado` (término: `'Bachelor’s'`)

> Qualifications/Responsibilities 2-4 years of experience in a highly regulated industry Bachelor’s degree in Engineering or a related field required.

## 4. Las `revisar_a_mano / educacion_no_confirmada` — por qué NO se descartó

Total: **20** vacantes (universitario obligatorio que el texto NO confirma).

### 1. `cinde-4888` — IT Software Developer II

- detección textual: `alternativa` (término: `"Bachelor's"`)

> What We're Looking For Required Qualifications Bachelor's degree in Computer Science, Software Engineering, Information Technology, or a related field, or equivalent practical experience.

### 2. `linkedin-4483157697` — Technical Support Specialist (Tier 2)

- detección textual: `negacion` (término: `'university degree'`)

> No university degree required.

### 3. `workday-Assistant-Director-of-Engineering_REQ10393409` — Assistant Director of Engineering

- detección textual: `alternativa` (término: `'Bachelor’s'`)

> Required Qualifications Education Bachelor’s degree or technical degree in Mechanical Engineering, Electrical Engineering, Electromechanical Engineering, Industrial Maintenance, Facilities Management, Civil Engineering, or a related field.

### 4. `workday-Associate--Repair-III_R-118081` — Associate, Repair III

- detección textual: `sin_termino` (término: `None`)

### 5. `workday-Buyer-Planner-Sr_31163601` — Buyer Planner Sr

- detección textual: `alternativa` (término: `'Bachelor'`)

> Required Qualifications Bachelor Degree, engineering, science or closely related discipline is desired, or equivalent technical.

### 6. `workday-Cardiac-Specialist-II_R18282-1` — Cardiac Specialist II

- detección textual: `alternativa` (término: `"Bachelor's"`)

> What We Look For Bachelor's degree, ECG certification, or an equivalent combination of education and relevant experience required.

### 7. `workday-Clinical-Project-Manager_R18034-1` — Clinical Project Manager

- detección textual: `alternativa` (término: `'Bachelor’s'`)

> What We Look For Bachelor’s degree required or equivalent experience

### 8. `workday-Creative-Execution-Manager--CrM-_261002442` — Creative Execution Manager (CrM)

- detección textual: `alternativa` (término: `'Bachelors'`)

> Required Licensing/Registration: Series 7, Series 63 Education: Bachelors/University degree or equivalent experience This job description provides a high-level review of the types of work performed.

### 9. `workday-Credit---Collections-Specialist--2_R232432` — Credit & Collections Specialist

- detección textual: `alternativa` (término: `'bachelor’s'`)

> ...ter data is accurate and up to date Deliver excellent customer service to both internal and external partners Participate in special projects and additional duties as assigned Required Associate’s or bachelor’s degree in business, Finance, or a related field 1–2 years of experience in B2B credit, collections, or accounts receivable Excellent communication skills in English (B2+ or higher) and abil...

### 10. `workday-HPE---Professional-Sales-HIT--Compute-and-Hybrid-Cloud-_R-116879` — HPE - Professional Sales HIT (Compute and Hybrid Cloud)

- detección textual: `alternativa` (término: `'four year college degree'`)

> A four year college degree (or additional experience in a related field) and 3 years functional experience including a minimum 1 year position specific experience.

### 11. `workday-Instructional-Designer_R17971` — Instructional Designer – Hybrid

- detección textual: `alternativa` (término: `"Bachelor's"`)

> What We Look For Hybrid Work Availability: Candidates must be available to work in a hybrid setting, including regular on-site presence as required Bachelor's degree or certification in Learning and Development, Education, Business, or a related field.

### 12. `workday-Principal-Cybersecurity-Engineer_R0007423` — Principal Cybersecurity Engineer

- detección textual: `alternativa` (término: `'Bachelor’s'`)

> Bachelor’s degree in Computer Science, Information Security, or a related field, or equivalent professional experience.

### 13. `workday-Production-Supervisor-I_31163511` — Production Supervisor I

- detección textual: `alternativa` (término: `'bachelor’s'`)

> Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience.

### 14. `workday-Production-Supervisor-I_31163518` — Production Supervisor I

- detección textual: `alternativa` (término: `'bachelor’s'`)

> Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience.

### 15. `workday-Sales-Specialist_R-117581` — Sales Specialist

- detección textual: `alternativa` (término: `'four year college degree'`)

> A four year college degree (or additional experience in a related field) and 3 years functional experience including a minimum 1 year position specific experience.

### 16. `workday-Security-Governance---Compliance-Specialist_2022361-1` — Security Governance & Compliance Specialist

- detección textual: `alternativa` (término: `'Bachelor’s'`)

> Minimum Qualifications Bachelor’s degree plus 5+ years of experience in technical compliance, security, risk, audit, or a related field

### 17. `workday-Security-Governance---Compliance-Specialist_2023168-1` — Security Governance & Compliance Specialist

- detección textual: `alternativa` (término: `"Bachelor's"`)

> Must-have Qualifications Bachelor's degree or equivalent work experience required.

### 18. `workday-Senior-Client-Services-Executive_R2025-244318` — Senior Client Services Executive

- detección textual: `alternativa` (término: `'Bachelor’s'`)

> Minimum Bachelor’s degree or its equivalent

### 19. `workday-Supplier-Quality-Engineer-III_31162905` — Supplier Quality Engineer III

- detección textual: `alternativa` (término: `"Bachelor's"`)

> As required , supervise technical personal for task execution Shift: Administrative Required Qualifications Bachelor's degree in engineering, Science, or equivalent field of study.

### 20. `workday-TnF-Manager-Systems---Software_1214477-2` — TnF Manager Systems / Software

- detección textual: `alternativa` (término: `"Bachelor's"`)

> Education and Experience Required: Bachelor's or Master's degree in Computer Science, Computer/Electronics Engineering, Information Systems, or equivalent.
