# Diagrams

Report diagrams for PlacementIQ, drawn from the code as built. GitHub renders the Mermaid
blocks below; to put one in the report, paste it into a Mermaid editor and export it as PNG or SVG.
The LangGraph critic loop is generated from the real compiled graph: see
[critic_graph.md](critic_graph.md) (`python -m scripts.export_graph`).

## Use cases
```mermaid
flowchart LR
    student([Student])
    evaluator([Developer / evaluator])
    groq([Groq LLM API])
    subgraph PlacementIQ
        uc1([Onboard with resume and USN])
        uc2([Get weekly study plan])
        uc3([Take adaptive quiz])
        uc4([Practise mock interview])
        uc5([View progress dashboard])
        uc6([Compare against single-prompt baseline])
    end
    student --- uc1 & uc2 & uc3 & uc4 & uc5
    evaluator --- uc6
    uc1 & uc2 & uc3 & uc4 & uc6 -.-> groq
```

## Components
```mermaid
flowchart TB
    views[Streamlit views] --> services[services: controllers]
    views --> formatter[formatter: output layer]
    views --> ui[ui: student selector, visible agent loop]
    services --> agents[agents]
    services --> db[(SQLite via db.py)]
    agents --> checks[checks: deterministic rules]
    agents --> graph[graph: generate, verify, retry]
    graph --> llm[llm gateway]
    llm --> groq([Groq API])
    llm -.->|MOCK_MODE| mock([mock responses])
    llm --> db
```

## Data flow, level 0 (context)
```mermaid
flowchart LR
    S([Student]) -- "resume, role, USN, quiz and interview answers" --> P((PlacementIQ))
    P -- "profile, weekly plan, quizzes, scores, feedback" --> S
    P -- "prompts with JSON schema" --> G([Groq LLM API])
    G -- "JSON outputs" --> P
    P -- "reads and writes" --> D[(SQLite database)]
```

## Data flow, level 1
```mermaid
flowchart TB
    S([Student])
    G([Groq LLM API])
    P1((1.0 Profile resume))
    P2((2.0 Plan week))
    P3((3.0 Generate and verify quiz))
    P4((4.0 Score quiz))
    P5((5.0 Mock interview))
    P6((6.0 Report progress))
    D1[(D1 students and profiles)]
    D2[(D2 plans)]
    D3[(D3 quiz attempts and questions)]
    D4[(D4 interview turns)]
    D5[(D5 agent logs)]

    S -- "resume, role, USN" --> P1
    P1 -- "extraction prompt" --> G
    P1 -- "profile, readiness" --> D1
    D1 -- "missing skills" --> P2
    D3 -- "last 3 scores per topic" --> P2
    D2 -- "previous week" --> P2
    P2 -- "plan prompt" --> G
    P2 -- "weekly plan" --> D2
    D3 -- "asked questions" --> P3
    P3 -- "generate and critic prompts" --> G
    P3 -- "quiz" --> S
    S -- "answers" --> P4
    P4 -- "score, questions" --> D3
    D1 -- "profile" --> P5
    D4 -- "earlier answers (memory)" --> P5
    S -- "answers" --> P5
    P5 -- "question and rubric prompts" --> G
    P5 -- "turns, scores" --> D4
    G -. "tokens, latency, verdicts" .-> D5
    D1 & D2 & D3 & D4 & D5 --> P6
    P6 -- "trends, rejections" --> S
```

## Entity relationships
```mermaid
erDiagram
    STUDENTS ||--o{ PROFILES : "is profiled in"
    STUDENTS ||--o{ PLANS : follows
    STUDENTS ||--o{ QUIZ_ATTEMPTS : takes
    QUIZ_ATTEMPTS ||--|{ QUIZ_QUESTIONS : contains
    STUDENTS ||--o{ INTERVIEW_TURNS : answers
    STUDENTS |o--o{ AGENT_LOGS : "triggers (no FK)"

    STUDENTS {
        TEXT id PK
        TEXT name
        TEXT usn UK "NOT NULL"
        TEXT target_role
        INTEGER readiness_score
        TIMESTAMP created_at
    }
    PROFILES {
        INTEGER id PK
        TEXT student_id FK
        TEXT profile_json
        INTEGER readiness_score
        TIMESTAMP created_at
    }
    PLANS {
        INTEGER id PK
        TEXT student_id FK
        INTEGER week_no "UNIQUE with student_id"
        TEXT plan_json
        TEXT rationale
        TIMESTAMP created_at
    }
    QUIZ_ATTEMPTS {
        INTEGER id PK
        TEXT student_id FK
        TEXT topic
        TEXT difficulty
        INTEGER total
        INTEGER correct
        REAL score_pct
        TIMESTAMP attempted_at
    }
    QUIZ_QUESTIONS {
        INTEGER id PK
        INTEGER attempt_id FK
        TEXT question_hash
        TEXT text
        INTEGER correct_index
        INTEGER chosen_index
    }
    INTERVIEW_TURNS {
        INTEGER id PK
        TEXT student_id FK
        TEXT session_id
        TEXT interview_type
        TEXT question
        TEXT answer
        TEXT scores_json
        REAL overall
        TIMESTAMP created_at
    }
    AGENT_LOGS {
        INTEGER id PK
        TEXT student_id
        TEXT agent_name
        TEXT model_used
        INTEGER input_tokens
        INTEGER output_tokens
        INTEGER latency_ms
        BOOLEAN critic_approved
        INTEGER retry_count
        TEXT reject_reason
        TIMESTAMP created_at
    }
```

## Sequence: resume → plan → quiz → re-plan
```mermaid
sequenceDiagram
    actor S as Student
    participant V as Streamlit views
    participant SV as services
    participant AG as agents + critic graph
    participant L as Groq LLM
    participant DB as SQLite

    S->>V: Resume, target role, USN
    V->>SV: onboard()
    SV->>AG: create_profile()
    AG->>L: Extract skills (small model)
    L-->>AG: ProfileExtraction JSON
    AG->>AG: Matched skills must be in the role list; readiness computed in code
    SV->>DB: Save student and profile

    S->>V: Generate week 1
    V->>SV: generate_next_plan()
    SV->>DB: Read quiz scores
    loop Until approved (max 3 attempts)
        AG->>L: Plan (large model)
        AG->>AG: Week, days, weak share ≥ 50%, minutes ordered by weakness
    end
    SV->>DB: Save plan

    S->>V: Generate OS quiz
    V->>SV: start_quiz()
    loop Until approved (max 3 attempts)
        AG->>L: Generate questions
        AG->>AG: Deterministic checks (count, options, duplicates)
        AG->>L: Critic judges questions not yet judged
        Note over AG,L: A retry replaces only the rejected questions
    end
    S->>V: Submit answers (low score)
    V->>SV: submit_quiz()
    SV->>DB: Save attempt and questions

    S->>V: Generate week 2
    V->>SV: generate_next_plan()
    SV->>DB: Read new scores and last week
    AG->>L: Plan with new weakness
    Note over AG: The weakest topic must now get the most minutes
    SV->>DB: Save week 2
    V-->>S: Week 1 vs week 2 chart
```
