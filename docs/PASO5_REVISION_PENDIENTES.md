# Paso 5 — HOJA DE REVISIÓN PENDIENTE (corrida `20261031_114039`)

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

## Casos a revisar (30)

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

### 2. `recruitee-transperfect-2770002` — Client Service Executive

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> ve time management and ability to multi-task in a fast-paced environment · Superior written and spoken communication skills in English · Ability to work well with people from a variety of different backgrounds and cultures, work independently and as part of a team · Strong MS Office/computer skills Required Experience and Qualifications: · Minimum Bachelor’s degree or its equivalent · Experience in customer service · Experience coordinating projects and assignment of resource

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='required'` · evidencia: > Description: · Respond to client requests for new project initiatives through our centralized technology · Collaborate with various members of the production team to assess the scope of work and produce cost and timeline estimates for translation projects and requests · Initiate all project related work by providing detailed budget, schedule and instructions to the project team and by anticipating pitfalls or potential roadblocks to successful completion · Ensure that any pitfalls are addressed and resolved with the client before being submitted to the production team · Where applicable, initiate some project specifics to set the production team/individual project up for success · Take a proactive role in learning about clients’ industry, business needs and company culture, educating the project team, and providing a high level of service · Monitor and communicate project progress, ensure strict adherence to deadlines and budgets and ultimately produce high quality deliverables · Serve as the central point of contact for and liaison between external client contact and internal production staff · Set and fulfill client expectations · Comply with all ISO regulations, processes and procedures · Potentially troubleshoot problem projects · Understand and abide by individual project instructions and effectively communicate to the production team · Investigate client complaints where applicable · Discuss issues with clients and production staff and creatively problem solve to alleviate issues · Help with training of more junior team members · Run meetings with production to discuss client feedback, concerns or issues · Hold regular meetings with the client to discuss any concerns and overall satisfaction with TP · Participate in global client services meeting · Handle challenging, demanding and complex projects, taking anything high profile, urgent or critical · Complete any other tasks that are deemed appropriate for the role and assigned by a manager/supervisor Required Skills: · Effective time management and ability to multi-task in a fast-paced environment · Superior written and spoken communication skills in English · Ability to work well with people from a variety of different backgrounds and cultures, work independently and as part of a team · Strong MS Office/computer skills Required Experience and Qualifications: · Minimum Bachelor’s degree or its equivalent · Experience in customer service · Experience coordinating projects and assignment of resource

---

### 3. `workday-Accounts-Payable-Representative_J-020440` — Accounts Payable Representative

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> identifying top candidates. The candidate must have an unrestricted right to work for Huntsman in Costa Rica. All candidates are expected to work at our office in AFZ, Heredia on Mondays, Wednesdays, and Thursdays. Please note that there may be occasions where additional office days are required, due specific business needs. Minimum Qualifications Bachelor’s degree coursework in Accounting, Finance, Business Administration, or a related discipline and 1+ year of relevant experience; alternatively, 3+ years of relevant professional experience in Accounts Payable or Accounting may be considered in lieu of a degree. Demonstrated experience in Accounts Payable, Accounting, or financial transaction processing is required. Proficiency in Microsoft Excel is required, along with proficiency in Microsoft Outlook. English proficiency at C1 level or higher is required, including strong verbal and written communication skills and the ability to communicate effectivel

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='ambiguous'` · evidencia: > Minimum Qualifications Bachelor’s degree coursework in Accounting, Finance, Business Administration, or a related discipline and 1+ year of relevant experience;

---

### 4. `workday-Analyst-Payroll_R273170` — Analyst Payroll

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> ss documentation. Contribute to operational excellence and continuous improvement initiatives. Compliance & Controls Maintain awareness and adherence to SOX controls and internal payroll control requirements. Participate in audits and support compliance reviews as needed. Ensure accurate documentation and retention of payroll records. Requirements Bachelor's degree in Business Administration, Accounting, Finance, Human Resources, or related field. Equivalent combination of education and relevant experience may be considered. Experience supporting multinational payroll qualifies only when the candidate has directly processed U.S. employee payroll; coordination, reporting, or system support alone is not a subs

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · evidencia: > Requirements Bachelor's degree in Business Administration, Accounting, Finance, Human Resources, or related field.

---

### 5. `workday-Audience-Management_26999789` — Audience Management

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> tal marketing and vendor management preferred. Acumen working in a technical environment to solve business related problems. Experience analyzing marketing efforts, including dashboard reporting and MIS. Optimization experience a plus. Salesforce Marketing Cloud experience a plus. Digital Marketing and Email Deployment experience a plus Education: Bachelors/University degree or equivalent experience ------------------------------------------------------ Job Family Group: Marketing ------------------------------------------------------ Job Family: Marketing Program Management ------------------------------------------------------ Time Type: Full time ------------------------------------------------------ Most Relevant

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='University degree'` · `requirement_level='preferred'` · evidencia: > Digital Marketing and Email Deployment experience a plus Education: Bachelors/University degree or equivalent experience ------------------------------------------------------ Job Family Group: Marketing ------------------------------------------------------ Job Family: Marketing Program Management ------------------------------------------------------ Time Type: Full time ------------------------------------------------------ Most Relevant Skills Please see the requirements listed above.

---

### 6. `workday-Buyer-Planner-Sr_31163601` — Buyer Planner Sr

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> n appropriate inventory levels that meet service level objectives to customers balanced with divisional DIOH (Days Inventory On Hand) goals. Manage new product introductions to achieve agreed upon launch dates with targeted launch inventory levels while developing and implementing plans that minimize phase out obsolescence. Required Qualifications Bachelor Degree, engineering, science or closely related discipline is desired, or equivalent technical. 5 +years of experience in Progressively responsible experience in purchasing/commodity management. 3 years working with purchasing/commodity mgt Ability to work in a highly matrixed and geographically diverse business environment. Ability to work within a team

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor Degree'` · `requirement_level='required'` · evidencia: > Required Qualifications Bachelor Degree, engineering, science or closely related discipline is desired, or equivalent technical.

---

### 7. `workday-Cardiac-Specialist-II_R18282-1` — Cardiac Specialist II

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> chieve operational and quality objectives. Assist with User Acceptance Testing (UAT) and system validation activities. Support investigations, edit checks, and quality management activities to maintain data integrity. Create, maintain, and improve workflow documentation, training materials, tracking logs, and procedural documents. What We Look For Bachelor's degree, ECG certification, or an equivalent combination of education and relevant experience required. Minimum of 2 to 3 years of experience processing cardiac safety data in a core laboratory, clinical research environment, or related healthcare setting. Strong knowledge of cardiovascular anatomy, physiology, ECG interpretation, and cardiac rhythm analy

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's degree"` · `requirement_level='required'` · evidencia: > What We Look For Bachelor's degree, ECG certification, or an equivalent combination of education and relevant experience required.

---

### 8. `workday-Clinical-Project-Manager_R18034-1` — Clinical Project Manager

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

### 9. `workday-Commercial-Analyst_R-01372758` — Commercial Analyst

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> ficiency in Microsoft Excel, Word and PowerPoint for analysis and presentation of data. Expect intensive use of Excel and advanced formulas daily. Confidence to handle critical information and make sound recommendations. Strong analytical and quantitative skills with proven understanding of financial budgeting principles. Education and Experience: Bachelor's degree or equivalent experience and relevant formal academic / vocational qualification. Previous experience that provides the knowledge, skills, and abilities to perform the job (comparable to 2 years). Meeting requirements for the role may be possible through a combination of education, training, and relevant experience. Working Environment: We value t

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · evidencia: > Education and Experience: Bachelor's degree or equivalent experience and relevant formal academic / vocational qualification.

---

### 10. `workday-Creative-Execution-Manager--CrM-_261002442` — Creative Execution Manager (CrM)

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> ellent organization skills and ability to manage multiple tasks/projects at once. Creative problem solving and sense of ownership. Solid communication, presentation and project management skills. Ability to work well under tight deadlines in a fast-paced and team-oriented environment. Required Licensing/Registration: Series 7, Series 63 Education: Bachelors/University degree or equivalent experience This job description provides a high-level review of the types of work performed. Other job-related duties may be assigned as required. ------------------------------------------------------ Job Family Group: Marketing ------------------------------------------------------ Job Family: Marketing Program Management ---------

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='University degree'` · `requirement_level='required'` · evidencia: > Required Licensing/Registration: Series 7, Series 63 Education: Bachelors/University degree or equivalent experience This job description provides a high-level review of the types of work performed.

---

### 11. `workday-Credit---Collections-Specialist--2_R232432` — Credit & Collections Specialist

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> o resolve past-due balances and communicate account status changes Maintain accurate documentation of all collection and credit activities in the system Research and resolve discrepancies such as short pays, deductions, overpayments, and unapplied cash Support credit memo requests and payment arrangements with appropriate approvals Ensure customer master data is accurate and up to date Deliver excellent customer service to both internal and external partners Participate in special projects and additional duties as assigned Required Associate’s or bachelor’s degree in business, Finance, or a related field 1–2 years of experience in B2B credit, collections, or accounts receivable Excellent communication skills in English (B2+ or higher) and ability to collaborate across functions and geographies. Strong attention to detail and analytical skills Excellent verbal and written communication skills Intermediate pr

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='bachelor'` · `requirement_level='required'` · evidencia: > Responsibilities Manage and collect accounts receivable for an assigned portfolio of B2B customers Monitor customer aging and enforce credit terms and limits using ERP and A/R systems (SAP, Esker or similar) Review credit applications and evaluate customer creditworthiness using credit bureaus and references Approve new customer credit limits within assigned authority and prepare recommendations for higher limits Place accounts on credit hold , issue final notices, and recommend escalation to third-party collections when necessary Collaborate closely with Sales Representatives to resolve past-due balances and communicate account status changes Maintain accurate documentation of all collection and credit activities in the system Research and resolve discrepancies such as short pays, deductions, overpayments, and unapplied cash Support credit memo requests and payment arrangements with appropriate approvals Ensure customer master data is accurate and up to date Deliver excellent customer service to both internal and external partners Participate in special projects and additional duties as assigned Required Associate’s or bachelor’s degree in business, Finance, or a related field 1–2 years of experience in B2B credit, collections, or accounts receivable Excellent communication skills in English (B2+ or higher) and ability to collaborate across functions and geographies.

---

### 12. `workday-Datacenter-Engineer--L3-ERT_1212932-2` — Datacenter Engineer- L3/ERT

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> ssue resolution documents. Required to communicate effectively with Technical and Non-Technical stakeholders and should have the ability to drive the conversation/discussion. Must be able to interact with colleagues from different countries and backgrounds (own team, members of L1 and L2, other support functions, and Engineering teams). Education: Bachelor's or Master’s degree in Mechanical, Electrical, Computer Science, or equivalent. Experience: 4+ Years’ experience in the Networking field with a minimum of 3 years supporting Data Center Technologies. What you need to bring: Data Networking technologies including Routing, Switching, and Network architecture and management. Working knowledge and understanding of Spine

**Texto 2 (verbatim):**

> ssue resolution documents. Required to communicate effectively with Technical and Non-Technical stakeholders and should have the ability to drive the conversation/discussion. Must be able to interact with colleagues from different countries and backgrounds (own team, members of L1 and L2, other support functions, and Engineering teams). Education: Bachelor's or Master’s degree in Mechanical, Electrical, Computer Science, or equivalent. Experience: 4+ Years’ experience in the Networking field with a minimum of 3 years supporting Data Center Technologies. What you need to bring: Data Networking technologies including Routing, Switching, and Network architecture and management. Working knowledge and understanding of Spine

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's"` · `requirement_level='inferred'` · evidencia: > Education: Bachelor's or Master’s degree in Mechanical, Electrical, Computer Science, or equivalent.
- `value_text="Bachelor's"` · `requirement_level='inferred'` · evidencia: > Education: Bachelor's or Master’s degree in Mechanical, Electrical, Computer Science, or equivalent.

---

### 13. `workday-Datacenter-Engineer--L3-ERT_1212933-2` — Datacenter Engineer- L3/ERT

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> ssue resolution documents. Required to communicate effectively with Technical and Non-Technical stakeholders and should have the ability to drive the conversation/discussion. Must be able to interact with colleagues from different countries and backgrounds (own team, members of L1 and L2, other support functions, and Engineering teams). Education: Bachelor's or Master’s degree in Mechanical, Electrical, Computer Science, or equivalent. Experience: 4+ Years’ experience in the Networking field with a minimum of 3 years supporting Data Center Technologies. What you need to bring: Data Networking technologies including Routing, Switching, and Network architecture and management. Working knowledge and understanding of Spine

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's"` · `requirement_level='inferred'` · evidencia: > Education: Bachelor's or Master’s degree in Mechanical, Electrical, Computer Science, or equivalent.

---

### 14. `workday-Fire-Protection-Project-Development-Specialist_WD30282840` — Fire Protection Project Development Specialist

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> You will use facts, candor, and practical problem solving to improve scopes, estimates, and handoffs. You will improve every day through disciplined follow-up and continuous learning, bringing lessons from each project into the next one. You will win as one team by building trust across sales, engineering, operations, and the field. Qualifications Bachelor’s degree in Engineering, Construction, Business, or a related technical field, or equivalent experience. Experience supporting fire protection, fire alarm, sprinkler, suppression, or related technical project development work. Ability to read and interpret drawings, specifications, scope documents, and customer requirements. Strong communication and coordi

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='ambiguous'` · evidencia: > Qualifications Bachelor’s degree in Engineering, Construction, Business, or a related technical field, or equivalent experience.

---

### 15. `workday-HR-Benefits-Operations-Analyst_261003280` — HR Benefits Operations Analyst

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> years relevant experience Proficient in Microsoft Office with an emphasis on MS Excel Ability to meet deadlines while dealing with multiple priorities. Proven organization and time management skills Demonstrated problem-solving and decision-making skills Consistently demonstrates clear and concise written and verbal communication skills Education: Bachelor’s degree/University degree or equivalent experience This job description provides a high-level review of the types of work performed. Other job-related duties may be assigned as required. Experience in HR roles Advanced English Language required. Portuguese is a plus. Knowledge in Workday, Service Now (desirable) ------------------------------------------------------ Job Fa

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='inferred'` · evidencia: > Proven organization and time management skills Demonstrated problem-solving and decision-making skills Consistently demonstrates clear and concise written and verbal communication skills Education: Bachelor’s degree/University degree or equivalent experience This job description provides a high-level review of the types of work performed.

---

### 16. `workday-HR-Generalist-Senior---Global-Discipline-Delivery_261004191` — HR Generalist Senior - Global Discipline Delivery

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> skills • Self-motivated and detail oriented • Proven organization and time management skills • Demonstrated problem-solving and decision-making skills • Analytical skills • Experience working with remote locations • Working knowledge of HR functions and applicable Employment laws • Working knowledge of industry standards and practices Education: • Bachelor’s degree/University degree or equivalent experience English advanced ------------------------------------------------------ Job Family Group: Human Resources ------------------------------------------------------ Job Family: HR Advisors & Generalist ------------------------------------------------------ Time Type: Full time --------------------------------------------------

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='inferred'` · evidencia: > Qualifications: • 5-8 years of relevant experience • Experience in Human Resources, employee relations or related field • Proficient in Microsoft Office and Human Resources Management Systems • Ability to work unsupervised and adjust priorities quickly as circumstances dictate • Consistently demonstrates clear and concise written and verbal communication skills • Self-motivated and detail oriented • Proven organization and time management skills • Demonstrated problem-solving and decision-making skills • Analytical skills • Experience working with remote locations • Working knowledge of HR functions and applicable Employment laws • Working knowledge of industry standards and practices Education: • Bachelor’s degree/University degree or equivalent experience English advanced ------------------------------------------------------ Job Family Group: Human Resources ------------------------------------------------------ Job Family: HR Advisors & Generalist ------------------------------------------------------ Time Type: Full time ------------------------------------------------------ Most Relevant Skills Please see the requirements listed above.

---

### 17. `workday-HR-Operations-Support-Lead-Analyst_25848722` — HR Operations Support Lead Analyst (C13) hybrid located in Heredia

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> cal judgment regarding personal behavior, conduct and business practices, and escalating, managing and reporting control issues with transparency. Qualifications: 5-10 years of experience Advanced English level Experience in developing risk management programs, identifying all significant processes, risks, and assessing key controls and monitoring associated with these significant processes Self-motivated and detail oriented Proven organization and time management skills Demonstrated problem-solving and decision-making skills Consistently demonstrates clear and concise written and verbal communication skills Education: Bachelor’s degree/University degree or equivalent experience Master’s degree preferred This job description provides a high-level review of the types of work performed. Other job-related duties may be assigned as required. ------------------------------------------------------ Job Family Group: Operations - Core ------------------------------------------------------ Job Family: Operations Support --------------------------

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='preferred'` · evidencia: > Qualifications: 5-10 years of experience Advanced English level Experience in developing risk management programs, identifying all significant processes, risks, and assessing key controls and monitoring associated with these significant processes Self-motivated and detail oriented Proven organization and time management skills Demonstrated problem-solving and decision-making skills Consistently demonstrates clear and concise written and verbal communication skills Education: Bachelor’s degree/University degree or equivalent experience Master’s degree preferred This job description provides a high-level review of the types of work performed.

---

### 18. `workday-IT-Security-Engineer-II_R-01372831` — IT Security Engineer II

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> on plans developed by risk owners and ensure plans are completed appropriately Perform ad-hoc risk analysis as assigned Perform other duties as assigned REQUIREMENTS 3+ years' experience in risk analysis, information risk management, data privacy, information technology, or equivalent with exposure to cybersecurity and/or information security risk Bachelor's Degree in Risk Management, Information Assurance, Information Security, Cybersecurity, IT, Data Privacy or similar area or equivalent work experience Experience with risk analysis Ability to explain complex risk management topics to a broad audience General understanding of cybersecurity technologies and controls with the ability to bridge the gap betwee

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's Degree"` · `requirement_level='preferred'` · evidencia: > Key Responsibilities: Providing key input and assistance in the development and implementation of a global cybersecurity risk management program Maintaining and executing the risk management policy throughout the entire risk lifecycle Executing various risk analysis processes within the team including intake and analysis of reported risks, risk measurement, risk response, and ensuring teams are properly managing plans to reduce risk Execute third party security assessments and analyze identified risks to help with strategic decisions around third party management Ensure consistency of security practice and standards across the organization Conduct Information Security assessments including and documenting controls, identifying potential gaps and or inconsistencies and making sound recommendations for improvement and/or mitigation Collaborate on the technical definitions and oversee implementation of security controls and requirements for systems, infrastructure and solutions Carry out information security risk assessments on technology solutions in line with the company risk management program Conduct third-party risk management activities including vendor/supplier assessments and risk analysis Intake and analysis of identified cyber security issues and risks from a variety of sources including security assessments, compliance checks, automated vulnerability systems, and other internally or externally reported risks Complete analyses and reports to develop a comprehensive view of risk across the company Assist and track for accurate risk measurement and response activities, provide necessary information and analysis to help business leaders prioritize risks Review and track action plans developed by risk owners and ensure plans are completed appropriately Perform ad-hoc risk analysis as assigned Perform other duties as assigned REQUIREMENTS 3+ years' experience in risk analysis, information risk management, data privacy, information technology, or equivalent with exposure to cybersecurity and/or information security risk Bachelor's Degree in Risk Management, Information Assurance, Information Security, Cybersecurity, IT, Data Privacy or similar area or equivalent work experience Experience with risk analysis Ability to explain complex risk management topics to a broad audience General understanding of cybersecurity technologies and controls with the ability to bridge the gap between governance and technical concepts Excellent writing skills, with experience as a writer or technical editor is considered a plus Demonstrated ability to complete work with minimal direction and self-identify tasks Excellent written and verbal communication skills with experience presenting to senior leadership Strong interpersonal, organizational, and excellent documentation skills Excellent customer service skills Relevant certifications such as CRISC, CISSP or CISA are considered a plus Understanding of various risk management frameworks such as the NIST Risk Management Framework or Center for Internet Security Risk Assessment Methodology will be considered plus

---

### 19. `workday-Instructional-Designer_R17971` — Instructional Designer – Hybrid

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> ffectiveness, identify improvement opportunities, and communicate project risks in a timely manner. Support hybrid collaboration through regular in-office participation and effective remote engagement. What We Look For Hybrid Work Availability: Candidates must be available to work in a hybrid setting, including regular on-site presence as required Bachelor's degree or certification in Learning and Development, Education, Business, or a related field. 2+ years of experience in a corporate training, learning and development, or instructional design role. Proven expertise in applying instructional design methodologies to create engaging and impactful learning experiences. Experience developing eLearning and ins

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's degree"` · `requirement_level='required'` · evidencia: > What We Look For Hybrid Work Availability: Candidates must be available to work in a hybrid setting, including regular on-site presence as required Bachelor's degree or certification in Learning and Development, Education, Business, or a related field.

---

### 20. `workday-Network-Support-Engineer_1211197` — Network Support Engineer

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> cumentation (White Papers, KB, Troubleshooting Guides, ) for internal and external use Sound documentation of technical support issues using the available tools is an essential element of the role Develop a "Can-Do" attitude and suggest ways to improve the team performance and increase customer's satisfaction Basic Qualifications Higher education (Bachelor or Master degree in electrical engineering or computer science or equivalent ) 3+ years of working experience in a network support role, 2-3 of these years would be spent supporting large IP networks 3+ years supporting customers on site and via phone. Must be able to support complex and high profile customer base. Strong communication skills, including influencin

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='inferred'` · evidencia: > Work with various technical teams within Juniper Networks and provide input on new products and feature improvements for reliability, availability, and serviceability Work closely with the Service Managers to support them in gaining a good understanding of the technical issues and their resolution, and support them in driving high profile technical escalations Participate in customer conference calls and/or face to face customer meetings to discuss technical issues Develop and maintain skills in his/her core products and technologies, and highlight any need for training as the customers networks evolve Contribute to technical documentation (White Papers, KB, Troubleshooting Guides, ) for internal and external use Sound documentation of technical support issues using the available tools is an essential element of the role Develop a "Can-Do" attitude and suggest ways to improve the team performance and increase customer's satisfaction Basic Qualifications Higher education (Bachelor or Master degree in electrical engineering or computer science or equivalent ) 3+ years of working experience in a network support role, 2-3 of these years would be spent supporting large IP networks 3+ years supporting customers on site and via phone.

---

### 21. `workday-Principal-Cybersecurity-Engineer_R0007423` — Principal Cybersecurity Engineer

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> ive Directory audit data), partnering with SOC and Detection Engineering to close coverage gaps. · Author and maintain Splunk SPL content — alerts, scheduled searches, and lookup- generating pipelines — to support threat detection, compliance reporting, and operational dashboards for the Windows and endpoint environment. Required Qualifications: · Bachelor’s degree in Computer Science, Information Security, or a related field, or equivalent professional experience. · 8+ years of progressive experience in information security or systems engineering, with at least 5 years focused specifically on Windows security engineering or Windows infrastructure hardening. · Deep expertise in Windows Server and Active Dire

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='required'` · evidencia: > Required Qualifications: · Bachelor’s degree in Computer Science, Information Security, or a related field, or equivalent professional experience.

---

### 22. `workday-Principal-Engineer--Quality_Req-51750` — Principal Engineer, Quality

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> for all production processes based on engineering principles; analyze results, make recommendations and develop reports • Train, coach, and guide lower level employees on more complex procedures • Develop technical content of risk management files • Manage Supplier Quality Activities as needed • Other incidental duties What you'll need (Required): Bachelor's degree in engineering or Scientific field, 6 years of experience minimum of experience, including either industry or industry/education or Master's Degree or equivalent in Engineering or Scientific field, 5 years of experience minimum of experience, including either industry or industry/education or Ph.D. or equivalent in Engineering or Scientific field, 2 years of experience minimum of experience, including either industry or industry/education What else we look for (Preferred): • Proven expertise

**Texto 2 (verbatim):**

> olicies and standards that are followed by others • Guides others in resolving basic issues in specialized area based on existing solutions and procedures • Must be able to work in a team environment, including frequent inter-organizational and outside customer contacts • Represents organization in providing solutions to difficult technical issues associated with specific projects • Develops technical solutions to complex problems which require the regular use of creativity • Uses best practices and knowledge of internal or external business issues to improve products/services or processes • Typically resolves complex problems or problems where precedent may not exist • Adhere to all company rules an

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's degree"` · `requirement_level='ambiguous'` · evidencia: > analyze results, make recommendations and develop reports • Train, coach, and guide lower level employees on more complex procedures • Develop technical content of risk management files • Manage Supplier Quality Activities as needed • Other incidental duties What you'll need (Required): Bachelor's degree in engineering or Scientific field, 6 years of experience minimum of experience, including either industry or industry/education or Master's Degree or equivalent in Engineering or Scientific field, 5 years of experience minimum of experience, including either industry or industry/education or Ph.D.

---

### 23. `workday-Production-Supervisor-I_31163511` — Production Supervisor I

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

### 24. `workday-Production-Supervisor-I_31163518` — Production Supervisor I

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

### 25. `workday-Sales-Specialist_R-117581` — Sales Specialist

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> rocedures and practices to determine appropriate action. Receives moderate level of guidance. Work is reviewed for soundness of judgment and overall accuracy. General proficiency with various tools, systems, and procedures required to accomplish the job. May need to consult with Senior/Specialist staff members on some technical issues. A four year college degree (or additional experience in a related field) and 3 years functional experience including a minimum 1 year position specific experience.

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='college degree'` · `requirement_level='required'` · evidencia: > A four year college degree (or additional experience in a related field) and 3 years functional experience including a minimum 1 year position specific experience.

---

### 26. `workday-Security-Governance---Compliance-Specialist_2022361-1` — Security Governance & Compliance Specialist

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> us monitoring activities to maintain compliance posture between audit cycles. Help define, implement, and monitor controls for enterprise AI tools and AI/ML systems, including their secure use, configuration, and governance. Contribute to the ongoing evolution of scalable, AI centric, automation-forward compliance processes. Minimum Qualifications Bachelor’s degree plus 5+ years of experience in technical compliance, security, risk, audit, or a related field; equivalent practical experience may be considered. Direct experience supporting or leading audit or certification programs from scoping through delivery, including control mapping, evidence collection, remediation, and auditor engagement; practical expe

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='required'` · evidencia: > Minimum Qualifications Bachelor’s degree plus 5+ years of experience in technical compliance, security, risk, audit, or a related field;

---

### 27. `workday-Security-Governance---Compliance-Specialist_2023168-1` — Security Governance & Compliance Specialist

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> lkthroughs of risk management processes. Collaborate and maintain strong working relationships across engineering teams and business units to support organizational objectives. Lead difficult conversations professionally and apply judgment to assess criticality and prioritize efforts in alignment with organizational goals. Must-have Qualifications Bachelor's degree or equivalent work experience required. Professional certification(s) such as GIAC, CISSP, CRISC, CISM, CISA, ISO 27001 Lead Implementer/Auditor, CCSK, CCSP, etc. 3-5 + years performing hands-on technical risk assessments in a security risk management role. Demonstrable technical knowledge in cloud environments (AWS, Azure, GCP) — able to read an

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's degree"` · `requirement_level='required'` · evidencia: > Must-have Qualifications Bachelor's degree or equivalent work experience required.

---

### 28. `workday-Senior-Client-Services-Executive_R2025-244318` — Senior Client Services Executive

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> olving and analytical skills; must be able to take active measures to solve problems and commit to a high level of service · Effective time management and ability to multi-task in a fast-paced environment · Superior written and spoken communication skills in English Required Experience and Qualifications: · Experience in customer service · Minimum Bachelor’s degree or its equivalent · Strong MS Office/computer skills

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text='Bachelor'` · `requirement_level='required'` · evidencia: > must be able to take active measures to solve problems and commit to a high level of service · Effective time management and ability to multi-task in a fast-paced environment · Superior written and spoken communication skills in English Required Experience and Qualifications: · Experience in customer service · Minimum Bachelor’s degree or its equivalent · Strong MS Office/computer skills

---

### 29. `workday-SeniorTechnician--Laboratory--Microbiology-_Req-51330` — SeniorTechnician, Laboratory (Microbiology)

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> ocedures and executing PM (preventative maintenance) per established schedule • Support laboratory investigations and propose recommendations for manager view • Prepare data summaries for laboratory reports or technical studies using existing templates as a model as well as review and approve basic laboratory data • Execute testing or instructions associated to equipment and process validation protocols • May train, coach, and guide lower-level technicians on new procedures, assess work techniques and provide feedback on procedures • Other incidental duties What you’ll need (Required): • Technical or Diploma Degree in Laboratory Science, Mircrobiology Laboratory or Related fields with 3 years of previous experience working in a laboratory Required, or Bachelor's Degree or Equivalent in Chemistry and /or Microbiology Preferred. • Availability to work from Monday to Friday from 8.00 a.m. to 05.00 p.m. What else we look for (preferred): • Good written and verbal communication, interpersonal, and relationship building skills • Able to read, comprehend, write and speak English • Good computer skills, including usage

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's Degree"` · `requirement_level='ambiguous'` · evidencia: > • Assist in testing validation/revalidation activities for critical systems and equipment under close supervision • May maintain basic equipment by following procedures and executing PM (preventative maintenance) per established schedule • Support laboratory investigations and propose recommendations for manager view • Prepare data summaries for laboratory reports or technical studies using existing templates as a model as well as review and approve basic laboratory data • Execute testing or instructions associated to equipment and process validation protocols • May train, coach, and guide lower-level technicians on new procedures, assess work techniques and provide feedback on procedures • Other incidental duties What you’ll need (Required): • Technical or Diploma Degree in Laboratory Science, Mircrobiology Laboratory or Related fields with 3 years of previous experience working in a laboratory Required, or Bachelor's Degree or Equivalent in Chemistry and /or Microbiology Preferred.

---

### 30. `workday-SharePoint-Application-Developer_R55630-1` — SharePoint Application Developer

| veredicto | criterio | revisor | fecha |
|---|---|---|---|
|   |   |   |   |

**Texto 1 (verbatim):**

> resolve SharePoint-related issues. Support migrations and modernization from legacy SharePoint environments. Establish development standards and documentation. Collaborate with business users, IT teams, and vendors to deliver solutions. Performs other additional duties as assigned. What We’re Looking For: 3 to 5 Years of relevant work experience. Bachelor's Degree with Computer Science / MIS field of study required. Core SharePoint Skills SharePoint Online SharePoint Framework (SPFx) SharePoint site architecture Lists, libraries, and content types Permissions and security management Development Skills JavaScript (ES6+) TypeScript HTML5 and CSS3 React (most common with SPFx) REST APIs Microsoft Graph API JSON formatting for SharePoint lists and columns XML & CAML C# for CSOM in VS development (legacy but still used) Client-side web parts and extensions PowerShell (PnP) Microsoft Power Platform Power Automate Power Apps Document management Managed metadata and taxonomy Other Education/Certifications: Advanced study preferred (e.g., Master’s in Information Systems/Software Engineering) or equivalent hands-on experience with Microsoft 365 development. Microsoft Certified: Power Platform Developer Associate (PL-400) SharePoint Online architecture and governance: permissions/security management, managed metadata/taxonomy, content types, and PnP PowerShell; migration/modernization experience Working Conditions: Professional environment (Hybrid). Occasional non-standard work hours or overtime as business requires. Represents the company to the customer

**Requisito(s) `education` extraído(s) por el extractor** — la
citas son literales del texto de la oferta:

- `value_text="Bachelor's Degree"` · `requirement_level='ambiguous'` · evidencia: > Bachelor's Degree with Computer Science / MIS field of study required.

---
