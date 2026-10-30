# Paso 5 — HOJA DE REVISIÓN PENDIENTE (corrida `20261029_205348`)

> Documento GENERADO por `generar_revision_pendientes.py` — contiene
> **solo textos literales de la BD, sin ningún veredicto**.
> Estado de estos casos: **ABIERTOS / NO REVISADOS**.

## Para quién es este documento

La revisión previa de estos casos la hizo **el autor de la regla**, por eso
su veredicto ("ninguna bloquea") se **descarta**: no es una segunda opinión.
Antes de registrar cualquier decisión en la tabla de decisiones del Paso 7
(`job_match_decision`), alguien distinto del autor debe leer cada caso aquí
con el texto completo y firmar un veredicto propio.

## Decisiones de negocio que la revisión necesita (FALTA DECIDIR)

Estas preguntas NO están decididas; el veredicto de los casos afectados
depende de ellas y hay que decidirlas **con una fuente**, no por impulso:

1. **"or advanced university studies"** (aparece en
   `workday-Accounting-Analyst---Temporary_J-020392`): ¿los estudios
   universitarios avanzados SIN título completado cuentan como educación
   universitaria para este perfil? Es una alternativa ACADÉMICA, no
   experiencia laboral.
2. **"two year college degree" / "associate degree"** (aparece en
   `workday-Associate--Repair-III_R-118081`): el código trata 2 años como NO
   universitario. ¿Es correcto en CR? Un **técnico superior universitario**
   sí es educación terciaria/universitaria — hay que decidirlo con fuente
   (p. ej. títulos registrados en CONESUP).
3. **"80% completeness of a bachelor's degree program"** (aparece en los dos
   `workday-Production-Supervisor-I_*`): ¿un bachillerato PARCIAL (80 % de
   la carrera) cuenta como requisito universitario cumplido? A día de hoy
   el módulo NO define qué pasa con estudios parciales.

## Casos a revisar (19)

Columnas de la tabla de firmas: `veredicto` (bloqueo real / no bloqueo /
dudoso), `criterio que lo justifica`, `revisor`, `fecha`.

### 1. `linkedin-4483157697` — Technical Support Specialist (Tier 2)

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> tcpdump. Solid understanding of networking fundamentals, including TCP/IP, DNS, NAT, firewalls, and routing. Strong analytical and problem-solving skills. Ability to troubleshoot technical issues independently using a structured, evidence-based approach. Excellent written and verbal communication skills. Fluent English, both written and spoken. No university degree required. What We Offer Fully remote position. Monthly compensation of USD 1,400 – 1,600. Full-time schedule, Monday through Friday. 10 days of paid time off (PTO). U.S. holidays. Initial training and onboarding. Hiring Process The selection process includes 1–2 interviews and a technical skills assessment. Apply Now! If you have experience troubl

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='university degree'` · `requirement_level='required'` · evidencia: > No university degree required.

---

### 2. `workday-Accounting-Analyst---Temporary_J-020392` — Accounting Analyst – Temporary

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> plus in identifying top candidates. The candidate must have an unrestricted right to work for Huntsman in Costa Rica. All candidates are expected to work at our office in AFZ, Heredia, on Mondays, Wednesdays, and Thursdays. Please note that additional office days may occasionally be required based on specific business needs. Minimum Qualifications Bachelor’s degree in Accounting, Finance, or a related field , or advanced university studies in Accounting. Minimum of 2 years of professional accounting experience. Practical knowledge of core accounting principles and processes, including: Debits and credits Journal entries and postings Account reconciliations Accruals and prepayments Month-end close activities Financial statement fundamentals General understanding of the accoun

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='required'` · evidencia: > Minimum Qualifications Bachelor’s degree in Accounting, Finance, or a related field , or advanced university studies in Accounting.

---

### 3. `workday-Assistant-Director-of-Engineering_REQ10393409` — Assistant Director of Engineering

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> lers, wellness seekers, culinary explorers, and cultural globetrotters. With customized itineraries for families and couples alike, we can’t wait for you to experience “Pura Vida” at Peninsula Papagayo. At Four Seasons we consider life and work to be richer when we truly connect with the people and the environment around us. Our family members are masters at their crafts – a gardener can become an artist, a manager a conductor, a chef an inventor. We are looking for employees who share the Golden Rule: people who, by nature, believe in treating others as we would have them treat us. We look for our people to characterize a shared passion for excellence and to infuse that enthusiasm into everything

**Texto 2 (verbatim):**

> ect hotel operations. 8. Reporting and Performance Management Monitor maintenance KPIs and identify opportunities for improvement. Follow up on work orders and preventive maintenance compliance. Support the Director of Engineering in preparing operational reports, presentations, budgets, and technical analyses. 9. Required Qualifications Education Bachelor’s degree or technical degree in Mechanical Engineering, Electrical Engineering, Electromechanical Engineering, Industrial Maintenance, Facilities Management, Civil Engineering, or a related field. Professional Experience: Previous experience in engineering, maintenance, facilities management, construction, or technical operations. Experience in hotels, resorts, luxury propert

**Texto 3 (verbatim):**

> technical systems and facilities found in a hotel environment, including: Electrical systems, including low- and medium-voltage systems. HVAC systems and chilled water systems. Chillers, pumps, cooling towers, and water distribution systems. Plumbing and domestic water systems. Wastewater and drainage systems. Hot water systems. Swimming pools and associated equipment. Fire alarm and life safety systems. Building Management Systems (BMS). Emergency generators and backup power systems. Kitchen and laundry equipment. Lighting systems and controls. Energy efficiency and sustainability principles. Technical drawings, schematics, and engineering documentation. Preventive and predictive maintenance princip

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='required'` · evidencia: > Required Qualifications Education Bachelor’s degree or technical degree in Mechanical Engineering, Electrical Engineering, Electromechanical Engineering, Industrial Maintenance, Facilities Management, Civil Engineering, or a related field.

---

### 4. `workday-Associate--Repair-III_R-118081` — Associate, Repair III

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> a senior level. Proficient in the various competencies relevant to their job. May act as a lead or mentor to more junior technical or administrative support personnel. Works on assignments that are moderately difficult, requiring judgment in resolving issues or in making recommendations. Generally works independently within established procedures associated with the specific job function. Normally receives little instruction on daily work. Determines methods and procedures on new assignments. May be informal team leader. Two year college degree or equivalent experience and minimum 3 year experience in functional area. OR High School Diploma or equivalent and 5 years functional experience, preferably at a senior level. Has substantial understanding of the job and applies knowledge and skills to complete a wide range of tasks.

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='High School Diploma'` · `requirement_level='inferred'` · evidencia: > OR High School Diploma or equivalent and 5 years functional experience, preferably at a senior level.
- `value_text='college degree'` · `requirement_level='required'` · evidencia: > Two year college degree or equivalent experience and minimum 3 year experience in functional area.

---

### 5. `workday-Buyer-Planner-Sr_31163601` — Buyer Planner Sr

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> n appropriate inventory levels that meet service level objectives to customers balanced with divisional DIOH (Days Inventory On Hand) goals. Manage new product introductions to achieve agreed upon launch dates with targeted launch inventory levels while developing and implementing plans that minimize phase out obsolescence. Required Qualifications Bachelor Degree, engineering, science or closely related discipline is desired, or equivalent technical. 5 +years of experience in Progressively responsible experience in purchasing/commodity management. 3 years working with purchasing/commodity mgt Ability to work in a highly matrixed and geographically diverse business environment. Ability to work within a team

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor Degree'` · `requirement_level='required'` · evidencia: > Required Qualifications Bachelor Degree, engineering, science or closely related discipline is desired, or equivalent technical.

---

### 6. `workday-Cardiac-Specialist-II_R18282-1` — Cardiac Specialist II

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> chieve operational and quality objectives. Assist with User Acceptance Testing (UAT) and system validation activities. Support investigations, edit checks, and quality management activities to maintain data integrity. Create, maintain, and improve workflow documentation, training materials, tracking logs, and procedural documents. What We Look For Bachelor's degree, ECG certification, or an equivalent combination of education and relevant experience required. Minimum of 2 to 3 years of experience processing cardiac safety data in a core laboratory, clinical research environment, or related healthcare setting. Strong knowledge of cardiovascular anatomy, physiology, ECG interpretation, and cardiac rhythm analy

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's degree"` · `requirement_level='required'` · evidencia: > What We Look For Bachelor's degree, ECG certification, or an equivalent combination of education and relevant experience required.

---

### 7. `workday-Clinical-Project-Manager_R18034-1` — Clinical Project Manager

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> sation Comprehensive medical, dental, and vision coverage 401(k) plan with company match Generous paid time off and paid holidays Fully remote work arrangement within the United States. What You’ll Be Doing Lead study start‑up activities by reviewing study requirements and response assessment criteria and collaborating with stakeholders to develop associated plans and documentation Define and manage project plans, including timelines, milestones, staffing needs, and project constraints Establish project reporting schedules and provide regular updates to Business Development leadership, Global Services Managing Directors, and sponsor representatives Communicate timely and appropriate project informati

**Texto 2 (verbatim):**

> cipating in capability presentations, investigator meetings, and professional conferences Oversee project close‑out activities, including coordination of submissions and final deliverables Perform supervisory responsibilities, as applicable, including hiring, onboarding, performance management, and approval of time and attendance. What We Look For Bachelor’s degree required or equivalent experience; degrees in life sciences, pharmacy, nursing, or a related healthcare field are strongly preferred Previous project management or leadership experience in the clinical development of investigational medications 1–3 years of clinical trials experience within a CRO or pharmaceutical research organization, preferably

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='required'` · evidencia: > What We Look For Bachelor’s degree required or equivalent experience;

---

### 8. `workday-Creative-Execution-Manager--CrM-_261002442` — Creative Execution Manager (CrM)

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> ellent organization skills and ability to manage multiple tasks/projects at once. Creative problem solving and sense of ownership. Solid communication, presentation and project management skills. Ability to work well under tight deadlines in a fast-paced and team-oriented environment. Required Licensing/Registration: Series 7, Series 63 Education: Bachelors/University degree or equivalent experience This job description provides a high-level review of the types of work performed. Other job-related duties may be assigned as required. ------------------------------------------------------ Job Family Group: Marketing ------------------------------------------------------ Job Family: Marketing Program Management ---------

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='University degree'` · `requirement_level='required'` · evidencia: > Required Licensing/Registration: Series 7, Series 63 Education: Bachelors/University degree or equivalent experience This job description provides a high-level review of the types of work performed.

---

### 9. `workday-Credit---Collections-Specialist--2_R232432` — Credit & Collections Specialist

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> o resolve past-due balances and communicate account status changes Maintain accurate documentation of all collection and credit activities in the system Research and resolve discrepancies such as short pays, deductions, overpayments, and unapplied cash Support credit memo requests and payment arrangements with appropriate approvals Ensure customer master data is accurate and up to date Deliver excellent customer service to both internal and external partners Participate in special projects and additional duties as assigned Required Associate’s or bachelor’s degree in business, Finance, or a related field 1–2 years of experience in B2B credit, collections, or accounts receivable Excellent communication skills in English (B2+ or higher) and ability to collaborate across functions and geographies. Strong attention to detail and analytical skills Excellent verbal and written communication skills Intermediate pr

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='bachelor'` · `requirement_level='required'` · evidencia: > Responsibilities Manage and collect accounts receivable for an assigned portfolio of B2B customers Monitor customer aging and enforce credit terms and limits using ERP and A/R systems (SAP, Esker or similar) Review credit applications and evaluate customer creditworthiness using credit bureaus and references Approve new customer credit limits within assigned authority and prepare recommendations for higher limits Place accounts on credit hold , issue final notices, and recommend escalation to third-party collections when necessary Collaborate closely with Sales Representatives to resolve past-due balances and communicate account status changes Maintain accurate documentation of all collection and credit activities in the system Research and resolve discrepancies such as short pays, deductions, overpayments, and unapplied cash Support credit memo requests and payment arrangements with appropriate approvals Ensure customer master data is accurate and up to date Deliver excellent customer service to both internal and external partners Participate in special projects and additional duties as assigned Required Associate’s or bachelor’s degree in business, Finance, or a related field 1–2 years of experience in B2B credit, collections, or accounts receivable Excellent communication skills in English (B2+ or higher) and ability to collaborate across functions and geographies.

---

### 10. `workday-HPE---Professional-Sales-HIT--Compute-and-Hybrid-Cloud-_R-116879` — HPE - Professional Sales HIT (Compute and Hybrid Cloud)

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> rocedures and practices to determine appropriate action. Receives moderate level of guidance. Work is reviewed for soundness of judgment and overall accuracy. General proficiency with various tools, systems, and procedures required to accomplish the job. May need to consult with Senior/Specialist staff members on some technical issues. A four year college degree (or additional experience in a related field) and 3 years functional experience including a minimum 1 year position specific experience.

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='college degree'` · `requirement_level='required'` · evidencia: > A four year college degree (or additional experience in a related field) and 3 years functional experience including a minimum 1 year position specific experience.

---

### 11. `workday-Instructional-Designer_R17971` — Instructional Designer – Hybrid

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> ffectiveness, identify improvement opportunities, and communicate project risks in a timely manner. Support hybrid collaboration through regular in-office participation and effective remote engagement. What We Look For Hybrid Work Availability: Candidates must be available to work in a hybrid setting, including regular on-site presence as required Bachelor's degree or certification in Learning and Development, Education, Business, or a related field. 2+ years of experience in a corporate training, learning and development, or instructional design role. Proven expertise in applying instructional design methodologies to create engaging and impactful learning experiences. Experience developing eLearning and ins

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's degree"` · `requirement_level='required'` · evidencia: > What We Look For Hybrid Work Availability: Candidates must be available to work in a hybrid setting, including regular on-site presence as required Bachelor's degree or certification in Learning and Development, Education, Business, or a related field.

---

### 12. `workday-Principal-Cybersecurity-Engineer_R0007423` — Principal Cybersecurity Engineer

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> ive Directory audit data), partnering with SOC and Detection Engineering to close coverage gaps. · Author and maintain Splunk SPL content — alerts, scheduled searches, and lookup- generating pipelines — to support threat detection, compliance reporting, and operational dashboards for the Windows and endpoint environment. Required Qualifications: · Bachelor’s degree in Computer Science, Information Security, or a related field, or equivalent professional experience. · 8+ years of progressive experience in information security or systems engineering, with at least 5 years focused specifically on Windows security engineering or Windows infrastructure hardening. · Deep expertise in Windows Server and Active Dire

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='required'` · evidencia: > Required Qualifications: · Bachelor’s degree in Computer Science, Information Security, or a related field, or equivalent professional experience.

---

### 13. `workday-Production-Supervisor-I_31163511` — Production Supervisor I

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> lated information. Build positive, outgoing relations with the other production supervisors in sharing of product, process or equipment related information. Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience. 0-2 years supervisory experience. Preferably in a medical device, pharmaceutical, or electronic industry. Computer skills. . Demonstrated proficiency on manufacturing systems used to collect data and control/monitor processes. , For example SFA, SAP, Kronos, or simil

**Texto 2 (verbatim):**

> d or applicable to medical industry. For example CQE, 6Sigma black belt, lean coach, problem solving techniques, etc. Flexibility to work on different shifts schedule and areas is preferred. Demonstrated capacity to effectively lead/influence peers and other functions towards organizational goals. Basic Command of English. Preferred Qualifications Bachelor’s degree in business administration, Engineering or similar field. Experience leading teams. Knowledge of Costa Rica laws applicable to direct labor operators is a plus. Apply Now Follow your career aspirations to Abbott for diverse opportunities with a company that can help you build your future and live your best life. Abbott is an Equal Opportunity Empl

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='preferred'` · evidencia: > Preferred Qualifications Bachelor’s degree in business administration, Engineering or similar field.
- `value_text='bachelor'` · `requirement_level='required'` · evidencia: > Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience.

---

### 14. `workday-Production-Supervisor-I_31163518` — Production Supervisor I

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> lated information. Build positive, outgoing relations with the other production supervisors in sharing of product, process or equipment related information. Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience. 0-2 years supervisory experience. Preferably in a medical device, pharmaceutical, or electronic industry. Computer skills. Demonstrated proficiency on manufacturing systems used to collect data and control/monitor processes. , For example SFA, SAP, Kronos, or similar

**Texto 2 (verbatim):**

> d or applicable to medical industry. For example CQE, 6Sigma black belt, lean coach, problem solving techniques, etc. Flexibility to work on different shifts schedule and areas is preferred. Demonstrated capacity to effectively lead/influence peers and other functions towards organizational goals. Basic Command of English. Preferred Qualifications Bachelor’s degree in business administration, Engineering or similar field. Experience leading teams. Knowledge of Costa Rica laws applicable to direct labor operators is a plus. Apply Now Follow your career aspirations to Abbott for diverse opportunities with a company that can help you build your future and live your best life. Abbott is an Equal Opportunity Empl

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='preferred'` · evidencia: > Preferred Qualifications Bachelor’s degree in business administration, Engineering or similar field.
- `value_text='bachelor'` · `requirement_level='required'` · evidencia: > Execute and monitor continuous improvement processes to increase quality, reduce cost and improve overall team productivity in own production line Required Qualifications 80% completeness of a bachelor’s degree program from a four-year college or university in Business Administration, Engineering or other technical/scientific experience.

---

### 15. `workday-Sales-Specialist_R-117581` — Sales Specialist

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> rocedures and practices to determine appropriate action. Receives moderate level of guidance. Work is reviewed for soundness of judgment and overall accuracy. General proficiency with various tools, systems, and procedures required to accomplish the job. May need to consult with Senior/Specialist staff members on some technical issues. A four year college degree (or additional experience in a related field) and 3 years functional experience including a minimum 1 year position specific experience.

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='college degree'` · `requirement_level='required'` · evidencia: > A four year college degree (or additional experience in a related field) and 3 years functional experience including a minimum 1 year position specific experience.

---

### 16. `workday-Security-Governance---Compliance-Specialist_2022361-1` — Security Governance & Compliance Specialist

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> us monitoring activities to maintain compliance posture between audit cycles. Help define, implement, and monitor controls for enterprise AI tools and AI/ML systems, including their secure use, configuration, and governance. Contribute to the ongoing evolution of scalable, AI centric, automation-forward compliance processes. Minimum Qualifications Bachelor’s degree plus 5+ years of experience in technical compliance, security, risk, audit, or a related field; equivalent practical experience may be considered. Direct experience supporting or leading audit or certification programs from scoping through delivery, including control mapping, evidence collection, remediation, and auditor engagement; practical expe

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='required'` · evidencia: > Minimum Qualifications Bachelor’s degree plus 5+ years of experience in technical compliance, security, risk, audit, or a related field;

---

### 17. `workday-Security-Governance---Compliance-Specialist_2023168-1` — Security Governance & Compliance Specialist

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> lkthroughs of risk management processes. Collaborate and maintain strong working relationships across engineering teams and business units to support organizational objectives. Lead difficult conversations professionally and apply judgment to assess criticality and prioritize efforts in alignment with organizational goals. Must-have Qualifications Bachelor's degree or equivalent work experience required. Professional certification(s) such as GIAC, CISSP, CRISC, CISM, CISA, ISO 27001 Lead Implementer/Auditor, CCSK, CCSP, etc. 3-5 + years performing hands-on technical risk assessments in a security risk management role. Demonstrable technical knowledge in cloud environments (AWS, Azure, GCP) — able to read an

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's degree"` · `requirement_level='required'` · evidencia: > Must-have Qualifications Bachelor's degree or equivalent work experience required.

---

### 18. `workday-Senior-Client-Services-Executive_R2025-244318` — Senior Client Services Executive

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> olving and analytical skills; must be able to take active measures to solve problems and commit to a high level of service · Effective time management and ability to multi-task in a fast-paced environment · Superior written and spoken communication skills in English Required Experience and Qualifications: · Experience in customer service · Minimum Bachelor’s degree or its equivalent · Strong MS Office/computer skills

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='required'` · evidencia: > must be able to take active measures to solve problems and commit to a high level of service · Effective time management and ability to multi-task in a fast-paced environment · Superior written and spoken communication skills in English Required Experience and Qualifications: · Experience in customer service · Minimum Bachelor’s degree or its equivalent · Strong MS Office/computer skills

---

### 19. `workday-TnF-Manager-Systems---Software_1214477-2` — TnF Manager Systems / Software

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> nd infrastructure procurement, vendor coordination, and resource justification. Reports project status, risks, and business impact to senior management and stakeholders. Encourages continuous improvement, innovation, and cost savings through in-house solutions that reduce reliance on external tools and equipment. Education and Experience Required: Bachelor's or Master's degree in Computer Science, Computer/Electronics Engineering, Information Systems, or equivalent. Typically 8+ years of software engineering experience, including at least 2–3 years leading or managing engineering teams. English communication skills Knowledge and Skills: Proven experience leading software engineering teams and delivering complex tools, a

**Texto 2 (verbatim):**

> t environments. Experience with project and portfolio management, including prioritization, planning, and risk management. Strong people leadership skills: coaching, performance management, conflict resolution, and team building. Strong analytical, problem-solving, and decision-making skills. Excellent written and verbal communication skills, with mastery of English and the local language. Able to present technical strategy, project status, and resource needs to senior leadership and negotiate options with them. Accessibility HPE is committed to creating an inclusive and accessible workplace and encourages applications from all qualified individuals, including those with disabilities. If you belie

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's"` · `requirement_level='required'` · evidencia: > Education and Experience Required: Bachelor's or Master's degree in Computer Science, Computer/Electronics Engineering, Information Systems, or equivalent.

---
