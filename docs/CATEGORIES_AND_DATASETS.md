# PlacementIQ Multi-Disciplinary Expansion: Job Roles, Categories & Dataset Specifications

This document outlines the expanded multi-disciplinary architecture for **PlacementIQ**, scaling beyond Computer Science to encompass all major engineering branches, medical/healthcare, business/law, and Indian government sectors (Central & State).

---

## 1. Executive Summary & Design Principles

PlacementIQ is an adaptive placement-readiness coach. To extend this system to 50–60 diverse roles while maintaining its lightweight mini-project architecture (single process, SQLite, zero heavy external databases), the system introduces:

1. **Domain-Specific Syllabus Mapping:** Rather than forcing all careers into CS subjects (DBMS, OS, DSA), each discipline maps to 4–6 core focus topics plus fundamental General Aptitude / Reasoning.
2. **Dynamic Role Capabilities:**
   - **Full Tech Pipeline:** Resume Profile → Weekly Study Plan → Topic Quizzes → Mock Interviews.
   - **Exam / Syllabus Centric (Govt / Civil Services):** Resume Profile → Exam Plan → High-Yield Subject Quizzes → Interview / Personality Assessment.
   - **Profile & Resume Centric (e.g. Legal / Corporate):** In-depth resume critique, skill gap analysis, case study / scenario practice, and tailored interview drills.
3. **Pre-Cached Local Question Bank (CSV Dataset):**
   - Ingests pre-curated question sets from CSV files into SQLite.
   - Quizzes query local question banks first (instant loading, zero API latency, zero Groq quota consumption).
   - Seamless fallback to LLM generation if the local pool is exhausted.

---

## 2. Curated 58 Job Roles Across 10 Domains

### Domain 1: Computer Science & Software Engineering (12 Roles)
*Focus Topics: Data Structures & Algorithms, Object-Oriented Programming, Database Management Systems, Operating Systems, Computer Networks, System Design, Aptitude.*

| # | Job Role | Typical Degree / Background | Key Required Skills | Core Quiz Topics |
|---|---|---|---|---|
| 1 | **Frontend Engineer** | B.E / B.Tech CS/IT/BCA | React, TypeScript, HTML/CSS, Web Performance, REST APIs | OOP, CN, WebTech, Aptitude |
| 2 | **Backend Developer (Java/Python)** | B.E / B.Tech CS/IT | Java/Python, Spring Boot/Django, SQL, Microservices, Redis | OOP, DBMS, OS, DSA, CN |
| 3 | **Full Stack Developer** | B.E / B.Tech CS/IT | JavaScript/TypeScript, React, Node.js, SQL/NoSQL, Git | OOP, DBMS, CN, DSA |
| 4 | **Mobile App Developer** | B.E / B.Tech CS/IT | Flutter/React Native/Kotlin, State Management, REST, SQLite | OOP, MobileDev, CN, Aptitude |
| 5 | **DevOps & Cloud Engineer** | B.E / B.Tech CS/IT | Linux, Docker, Kubernetes, CI/CD, AWS/Azure, Terraform | OS, CN, CloudDevOps, Aptitude |
| 6 | **Data Analyst & BI Specialist** | B.E / B.Tech CS/IT/Stats | SQL, Python, Excel, Power BI/Tableau, Statistics | DBMS, Stats, Python, Aptitude |
| 7 | **Machine Learning / AI Engineer** | B.E / B.Tech CS/AI/DS | Python, PyTorch/TensorFlow, Math/Linear Algebra, Scikit-Learn | DSA, ML_Fundamentals, Stats |
| 8 | **Cybersecurity Analyst** | B.E / B.Tech CS/IT/Cyber | Network Security, Cryptography, Vulnerability Assessment, Linux | CN, OS, Security, Aptitude |
| 9 | **QA & Test Automation Engineer** | B.E / B.Tech CS/IT | Selenium, Cypress, PyTest/JUnit, Test Lifecycle, SQL | OOP, DBMS, Testing, Aptitude |
| 10 | **Embedded Software Engineer** | B.E / B.Tech CS/EC/EE | Embedded C, RTOS, Microcontrollers, Device Drivers | OS, C_Prog, Microcontrollers |
| 11 | **Database Administrator (DBA)** | B.E / B.Tech CS/IT | PostgreSQL/MySQL/Oracle, Indexing, Backup/Recovery, Sharding | DBMS, OS, SQL, Aptitude |
| 12 | **Site Reliability Engineer (SRE)** | B.E / B.Tech CS/IT | Linux internals, Python/Go, Monitoring (Prometheus), Distributed Systems | OS, CN, DistributedSystems |

---

### Domain 2: Electronics & Communication Engineering (ECE) (6 Roles)
*Focus Topics: Digital Electronics, Signals & Systems, Microcontrollers/VLSI, Analog Circuits, Communication Systems, Aptitude.*

| # | Job Role | Typical Degree / Background | Key Required Skills | Core Quiz Topics |
|---|---|---|---|---|
| 13 | **VLSI & Chip Design Engineer** | B.E / B.Tech ECE/EEE | Verilog/VHDL, Digital Logic, Static Timing Analysis (STA), CMOS | Digital_Electronics, VLSI_Design |
| 14 | **Embedded Systems & Firmware Engineer** | B.E / B.Tech ECE/EEE | C/C++, ARM Cortex, I2C/SPI/UART, PCB Debugging | Microcontrollers, Embedded_C, Digital_Electronics |
| 15 | **IoT & Edge Hardware Engineer** | B.E / B.Tech ECE/CS | ESP32/Arduino, Sensor Interfacing, MQTT, Edge Computing | Microcontrollers, CN, Sensors_IoT |
| 16 | **Telecommunications & RF Engineer** | B.E / B.Tech ECE | 4G/5G Architectures, RF Design, Microwave, Antenna Theory | Telecom_Systems, Signals_Systems |
| 17 | **Robotics & Control Systems Engineer** | B.E / B.Tech ECE/ME | Control Systems, PID Controllers, Sensors, Actuators, MATLAB | Control_Systems, Digital_Electronics |
| 18 | **Signal Processing Engineer** | B.E / B.Tech ECE/EE | DSP, Fourier Transforms, MATLAB/Python, Filter Design | Signals_Systems, DSP, Aptitude |

---

### Domain 3: Mechanical Engineering (5 Roles)
*Focus Topics: Thermodynamics, Fluid Mechanics, Strength of Materials, Manufacturing Processes, Machine Design, Aptitude.*

| # | Job Role | Typical Degree / Background | Key Required Skills | Core Quiz Topics |
|---|---|---|---|---|
| 19 | **Thermal & HVAC Design Engineer** | B.E / B.Tech ME | Thermodynamics, Heat Transfer, HVAC System Design, AutoCAD | Thermodynamics, Heat_Transfer |
| 20 | **Automotive & EV Systems Engineer** | B.E / B.Tech ME/Automobile | Powertrain Dynamics, Chassis Design, Battery Thermal Management | Machine_Design, Automotive_Systems |
| 21 | **CAD/CAM & Product Design Engineer** | B.E / B.Tech ME | SolidWorks, CATIA, GD&T, FEA / Ansys, DFM | CAD_CAM, Strength_of_Materials |
| 22 | **Manufacturing & Production Engineer** | B.E / B.Tech ME/Prod | CNC Machining, Casting & Welding, Six Sigma, Lean Manufacturing | Manufacturing_Processes, Quality_Eng |
| 23 | **Robotics & Mechatronics Engineer** | B.E / B.Tech ME/ECE | Kinematics, Pneumatics/Hydraulics, PLC Programming, Sensor Integration | Mechatronics, Control_Systems |

---

### Domain 4: Civil Engineering (5 Roles)
*Focus Topics: Structural Analysis, Geotechnical Engineering, Surveying, Construction Planning, Fluid Mechanics/Hydraulics, Aptitude.*

| # | Job Role | Typical Degree / Background | Key Required Skills | Core Quiz Topics |
|---|---|---|---|---|
| 24 | **Structural Design Engineer** | B.E / B.Tech Civil | RCC Design, Steel Structures, STAAD Pro, ETABS, IS Codes | Structural_Analysis, RCC_Steel |
| 25 | **Geotechnical & Foundation Engineer**| B.E / B.Tech Civil | Soil Mechanics, Foundation Design, Borehole Logging, Soil Testing | Geotechnical_Eng, Foundation_Design |
| 26 | **Construction Project Manager** | B.E / B.Tech Civil | Estimation & Costing, Primavera/MS Project, Quality Control, Site Safety | Construction_Mgmt, Estimation_Costing |
| 27 | **Transportation & Highway Engineer** | B.E / B.Tech Civil | Pavement Design, Traffic Engineering, IRC Standards, Highway Alignment | Highway_Eng, Traffic_Eng |
| 28 | **Water Resources & Environmental Engineer** | B.E / B.Tech Civil/Env | Hydrology, Open Channel Flow, Water Treatment, Sewerage Design | Fluid_Mechanics, Environmental_Eng |

---

### Domain 5: Electrical & Electronics Engineering (EEE) (4 Roles)
*Focus Topics: Power Systems, Electrical Machines, Power Electronics, Control Systems, Circuit Theory, Aptitude.*

| # | Job Role | Typical Degree / Background | Key Required Skills | Core Quiz Topics |
|---|---|---|---|---|
| 29 | **Power Systems & Grid Engineer** | B.E / B.Tech EEE | Load Flow Analysis, Switchgear & Protection, High Voltage, ETAP | Power_Systems, Electrical_Machines |
| 30 | **EV Powertrain & Battery Engineer** | B.E / B.Tech EEE/ECE | Battery Management Systems (BMS), Motor Drives, Inverters, DC-DC | Power_Electronics, EV_Systems |
| 31 | **Industrial Automation & PLC Engineer**| B.E / B.Tech EEE/ECE | PLC Ladder Logic, SCADA, VFD Drives, Industrial Sensors | Automation_PLC, Control_Systems |
| 32 | **Renewable Energy Systems Engineer** | B.E / B.Tech EEE/ME | Solar PV Plant Design, Wind Turbines, Grid Inverters, PVSyst | Power_Systems, Renewable_Energy |

---

### Domain 6: Biotechnology & Bio-Engineering (4 Roles)
*Focus Topics: Molecular Biology, Biochemistry, Bioprocess Engineering, Bioinformatics, Microbiology, Aptitude.*

| # | Job Role | Typical Degree / Background | Key Required Skills | Core Quiz Topics |
|---|---|---|---|---|
| 33 | **Bioinformatics Analyst** | B.E / B.Tech BioT/Bioinformatics | Python/R, Sequence Alignment (BLAST), Genomics, Molecular Docking | Bioinformatics, Molecular_Biology |
| 34 | **Biomedical Instrumentation Engineer**| B.E / B.Tech BioMed/ECE | Biosensors, Medical Imaging (ECG/MRI), Patient Monitoring Systems | Biomedical_Devices, Digital_Electronics |
| 35 | **Bioprocess / Fermentation Engineer** | B.E / B.Tech BioT/Chemical | Bioreactor Design, Fermentation Scale-up, Downstream Purification | Bioprocess_Eng, Microbiology |
| 36 | **Clinical Research Associate (CRA)** | B.Sc/B.Tech BioT/Pharma | GCP/ICH Guidelines, Clinical Trial Protocols, Regulatory Documentation | Clinical_Research, Pharmacology |

---

### Domain 7: Healthcare & Medical Sciences (5 Roles)
*Focus Topics: Human Anatomy & Physiology, Pathology & Pharmacology, Hospital Administration, Public Health, Clinical Guidelines.*

| # | Job Role | Typical Degree / Background | Key Required Skills | Core Quiz Topics |
|---|---|---|---|---|
| 37 | **General Medical Officer (Resident Doctor)** | MBBS | Patient Assessment, Emergency Care, Pharmacology, Diagnostic Protocols | Clinical_Medicine, Pharmacology, Pathology |
| 38 | **Hospital Operations Administrator** | MHA / MBA Healthcare / MBBS | NABH Accreditation, Bed Turnover, Patient Flow, Hospital Inventory | Hospital_Admin, Healthcare_Quality |
| 39 | **Clinical Pharmacist** | B.Pharm / Pharm.D | Drug Dispensing, Drug-Drug Interactions, Pharmacovigilance, Posology | Pharmacology, Clinical_Pharmacy |
| 40 | **Public Health Program Coordinator** | MPH / MBBS / B.Sc Nursing | Epidemiological Surveillance, Immunization Protocols, Health Policy | Public_Health, Epidemiology |
| 41 | **Medical Lab Technologist (MLT)** | B.Sc MLT / Biochemistry | Hematology, Clinical Biochemistry, Serology, Specimen Processing | Clinical_Pathology, Biochemistry |

---

### Domain 8: Corporate Management, Finance & Law (6 Roles)
*Focus Topics: Financial Accounting & Analysis, Corporate Governance & Law, Operations Management, Quantitative Analysis, Marketing Strategy.*

| # | Job Role | Typical Degree / Background | Key Required Skills | Core Quiz Topics |
|---|---|---|---|---|
| 42 | **Corporate Legal Counsel / Associate** | LL.B / B.A. LL.B | Contract Drafting, Companies Act, IP & Trademarks, Dispute Resolution | Corporate_Law, Contract_Law, Constitutional_Law |
| 43 | **Financial Analyst & Investment Associate**| B.Com / BBA / MBA / CA | Financial Modeling, DCF Valuation, Corporate Finance, Excel | Financial_Analysis, Accounting, Quantitative_Aptitude |
| 44 | **Human Resources (HR) Specialist** | MBA HR / BBA | Talent Acquisition, Labor Laws, Employee Relations, Performance Mgmt | HR_Principles, Labor_Laws, Verbal_Ability |
| 45 | **Product Manager** | Any Graduate / MBA | Product Roadmap, User Stories, A/B Testing, Market Research, Agile | Product_Strategy, Quantitative_Aptitude |
| 46 | **Supply Chain & Logistics Specialist**| B.E / MBA Operations | Demand Forecasting, Inventory Management, Vendor Relations, ERP | Supply_Chain, Quantitative_Aptitude |
| 47 | **Digital Marketing & Brand Strategist** | Any Graduate / BBA / MBA | SEO/SEM, Google Analytics, Content Marketing, Paid Social Ads | Digital_Marketing, Marketing_Strategy |

---

### Domain 9: Indian Central Government Services (6 Roles)
*Focus Topics: Indian Polity & Constitution, Modern History, Quantitative Aptitude & Reasoning, General Science, Current Affairs & Economy.*

| # | Job Role | Exam Conducting Body | Key Selection Criteria | Core Quiz Topics |
|---|---|---|---|---|
| 48 | **UPSC Civil Services Officer (IAS/IPS/IFS)**| UPSC CSE | Prelims & Mains General Studies, Essay, Interview | Indian_Polity, Indian_Economy, History_Geography, Aptitude |
| 49 | **SSC CGL Assistant Section Officer (ASO)**| SSC CGL | Tier I & Tier II: Quant, Reasoning, English, General Awareness | Quantitative_Aptitude, Reasoning, English_Language, General_Awareness |
| 50 | **Public Sector Bank PO (SBI / IBPS PO)** | IBPS / SBI | Quant, Logical Reasoning, English, Banking Awareness | Banking_Awareness, Quantitative_Aptitude, Reasoning |
| 51 | **Railway Recruitment Board (RRB) SSE** | RRB | General Engineering (Civil/Mech/Elec), Quant, Technical Syllabus | Engineering_Fundamentals, Aptitude, General_Science |
| 52 | **DRDO / ISRO Scientist-Engineer** | DRDO / ISRO / GATE | Core Branch Engineering Concepts, Math, Technical Aptitude | Core_Engineering, Engineering_Math, Aptitude |
| 53 | **Audit Officer (CAG / DAD)** | SSC CGL / UPSC | Auditing Standards, Financial Accounting, Government Accounts | Indian_Polity, Auditing_Accounting, Aptitude |

---

### Domain 10: Indian State Government Services (5 Roles)
*Focus Topics: State Administration & Polity, State Land & Revenue Regulations, Quantitative Aptitude, State History & Geography, Public Works.*

| # | Job Role | Typical Department | Key Selection Criteria | Core Quiz Topics |
|---|---|---|---|---|
| 54 | **State Civil Service Officer (KAS / PCS)** | State PSC | State General Studies, State History/Geography, Administration | State_Polity_History, Indian_Polity, General_Aptitude |
| 55 | **State Police Sub-Inspector (PSI / DySP)** | State Police Board | Criminal Procedure Basics, Law & Order, Mental Ability, Physical | Indian_Constitution, Mental_Ability, General_Knowledge |
| 56 | **Assistant Engineer (PWD / Irrigation)** | State PWD / WRD | Civil/Electrical Engineering State Technical Exam, General Studies | Civil_Engineering_Basics, Aptitude, State_GK |
| 57 | **Panchayat Development Officer (PDO)** | Rural Development Dept | Panchayati Raj Act, Rural Economy, Government Welfare Schemes | Panchayati_Raj_Acts, Rural_Development, General_Studies |
| 58 | **Commercial Tax / Revenue Inspector** | State Revenue Dept | Land Revenue Codes, State Taxation / GST Basics, General Studies | Revenue_Codes, General_Aptitude, Indian_Economy |

---

## 3. Standardized Question Bank CSV Template Structure

To enable offline caching, instant zero-latency loading, and avoid exhausting LLM quotas, questions should be formatted using the following standardized CSV specifications.

### A. Multiple Choice Questions (MCQ) CSV Template
*Filename suggestion:* `data/questions/mcq_<domain>_<topic>.csv` (or one master `mcq_bank.csv`)

| Column Name | Data Type | Required? | Description & Allowed Values | Example Value |
|---|---|---|---|---|
| `category` | String | Yes | The broad industry/academic domain | `Computer Science` |
| `role_or_stream` | String | Yes | Specific job role or general stream | `Frontend Engineer` |
| `topic` | String | Yes | Topic name matching syllabus | `WebTech` |
| `difficulty` | Enum | Yes | `easy`, `medium`, or `hard` | `medium` |
| `question` | String | Yes | Question stem (plain text, markdown-safe) | `What is the main purpose of the useEffect hook in React?` |
| `option_a` | String | Yes | First choice | `To directly mutate the DOM tree` |
| `option_b` | String | Yes | Second choice | `To perform side effects in functional components` |
| `option_c` | String | Yes | Third choice | `To force immediate re-rendering of child props` |
| `option_d` | String | Yes | Fourth choice | `To define Redux global stores` |
| `correct_option` | Enum | Yes | `A`, `B`, `C`, or `D` (or `0`, `1`, `2`, `3`) | `B` |
| `explanation` | String | Yes | 1–2 sentences explaining the answer | `useEffect manages side effects such as data fetching, subscriptions, or manual DOM manipulation after rendering.` |
| `bloom_level` | Enum | Optional | `remember`, `understand`, `apply`, `analyze` | `understand` |

#### Raw CSV Header & Sample Rows (MCQs)
```csv
category,role_or_stream,topic,difficulty,question,option_a,option_b,option_c,option_d,correct_option,explanation,bloom_level
Computer Science,Frontend Engineer,WebTech,medium,"What is the main purpose of the useEffect hook in React?","To directly mutate the DOM tree","To perform side effects in functional components","To force immediate re-rendering of child props","To define Redux global stores",B,"useEffect executes side effects after render cycles.",understand
Mechanical Engineering,Thermal & HVAC Design Engineer,Thermodynamics,easy,"Which law of thermodynamics defines the concept of temperature?","First Law","Second Law","Third Law","Zeroth Law",D,"The Zeroth Law establishes thermal equilibrium and defines temperature.",remember
Indian Central Government,UPSC Civil Services Officer,Indian_Polity,medium,"Which Article of the Indian Constitution provides for the Finance Commission?","Article 280","Article 324","Article 356","Article 370",A,"Article 280 provides for the constitution of the Finance Commission every five years.",remember
Corporate Management,Corporate Legal Counsel,Contract_Law,medium,"An agreement without consideration is void under which Section of the Indian Contract Act?","Section 10","Section 25","Section 56","Section 73",B,"Section 25 of the Indian Contract Act states that an agreement without consideration is void with limited exceptions.",understand
```

---

### B. Interview Questions CSV Template
*Filename suggestion:* `data/questions/interview_bank.csv`

| Column Name | Data Type | Required? | Description & Allowed Values | Example Value |
|---|---|---|---|---|
| `category` | String | Yes | Domain name | `Electronics` |
| `role` | String | Yes | Target job role | `Embedded Systems & Firmware Engineer` |
| `interview_type` | Enum | Yes | `Technical`, `HR`, `Project`, or `Situational` | `Technical` |
| `difficulty` | Enum | Yes | `easy`, `medium`, `hard` | `medium` |
| `question` | String | Yes | The interview question | `Explain the difference between polling and interrupt-driven I/O in microcontrollers.` |
| `key_evaluation_points` | String | Yes | Semi-colon separated key points the candidate must mention | `CPU utilization; latency; priority handling; ISR overhead` |
| `model_answer` | String | Yes | Exemplary concise answer (~100 words) | `In polling, the CPU continuously checks device status, which wastes processor cycles. In interrupt-driven I/O, the hardware device signals the CPU via an interrupt line only when ready, allowing the CPU to execute other tasks until required.` |

---

## 4. Recommendations for Submission & Dataset Curation

1. **Volume target:** Aim for **30 to 50 curated MCQs per topic**, or ~150–200 questions per domain. A total of ~1,500 to 2,000 questions across all domains is optimal for a robust offline mini-project.
2. **Distinct Options:** Ensure all 4 options are distinct (avoid "All of the above" or "None of the above" to keep critic and validation passes clean).
3. **Encoding:** Save all CSV files in **UTF-8** encoding without BOM.
4. **Formatting:** Any question or option containing commas must be enclosed in double quotes (`"..."`).
