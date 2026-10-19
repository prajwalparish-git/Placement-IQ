# Test report

Generated 2026-10-19 08:31 UTC by `python -m scripts.test_report` from a real run of the suite (offline: MOCK_MODE, temporary databases, fake Groq clients for live code paths).

**172 tests: 172 passed, 0 failed, 0 skipped** (73 s of test time).

## By module

| Type | Area | Module | Tests | Passed |
|---|---|---|---|---|
| Unit | Settings and environment | `test_config` | 8 | 8 |
| Unit | Pydantic output schemas | `test_schemas` | 10 | 10 |
| Unit | Deterministic critic rules | `test_checks` | 18 | 18 |
| Unit | SQLite repository | `test_db` | 11 | 11 |
| Unit | LLM gateway (fake Groq client) | `test_llm` | 11 | 11 |
| Unit | LangGraph critic loop | `test_graph` | 6 | 6 |
| Unit | Resume parsing | `test_resume` | 8 | 8 |
| Unit | Output layer | `test_formatter` | 11 | 11 |
| Integration | Agents through the critic loop | `test_agents` | 25 | 25 |
| Integration | User flows through the service layer | `test_services` | 25 | 25 |
| Integration | Demo seed data | `test_seed` | 3 | 3 |
| Integration | Evaluation harness | `test_eval` | 12 | 12 |
| Integration | Results report | `test_report` | 3 | 3 |
| Integration | Model availability check | `test_check_models` | 5 | 5 |
| Integration | Graph export | `test_export_graph` | 2 | 2 |
| Integration | Test report generator | `test_test_report` | 2 | 2 |
| System (UI) | Streamlit pages, headless | `test_ui` | 12 | 12 |

## Test cases

| ID | Type | Area | Test case (expected behaviour) | Result |
|---|---|---|---|---|
| TC-001 | Unit | Settings and environment | Defaults to mock mode | Pass |
| TC-002 | Unit | Settings and environment | Truthy mock flags [1] | Pass |
| TC-003 | Unit | Settings and environment | Truthy mock flags [YES] | Pass |
| TC-004 | Unit | Settings and environment | Truthy mock flags [ true ] | Pass |
| TC-005 | Unit | Settings and environment | Truthy mock flags [True] | Pass |
| TC-006 | Unit | Settings and environment | Live mode requires key and both models | Pass |
| TC-007 | Unit | Settings and environment | Dotenv file is read without overriding real env | Pass |
| TC-008 | Unit | Settings and environment | Seed demo is opt in | Pass |
| TC-009 | Unit | Pydantic output schemas | Bloom level is normalised | Pass |
| TC-010 | Unit | Pydantic output schemas | Question rejects invalid fields [bad0] | Pass |
| TC-011 | Unit | Pydantic output schemas | Question rejects invalid fields [bad1] | Pass |
| TC-012 | Unit | Pydantic output schemas | Question rejects invalid fields [bad2] | Pass |
| TC-013 | Unit | Pydantic output schemas | Question rejects invalid fields [bad3] | Pass |
| TC-014 | Unit | Pydantic output schemas | Question rejects invalid fields [bad4] | Pass |
| TC-015 | Unit | Pydantic output schemas | Question rejects invalid fields [bad5] | Pass |
| TC-016 | Unit | Pydantic output schemas | Plan needs exactly seven days and bounded minutes | Pass |
| TC-017 | Unit | Pydantic output schemas | Minutes by topic sums per topic | Pass |
| TC-018 | Unit | Pydantic output schemas | Answer evaluation bounds and overall | Pass |
| TC-019 | Unit | Deterministic critic rules | Text hash ignores case whitespace and punctuation | Pass |
| TC-020 | Unit | Deterministic critic rules | Weakness prefers quiz evidence over resume gaps | Pass |
| TC-021 | Unit | Deterministic critic rules | Weak topics sorted by weakness and threshold is strict | Pass |
| TC-022 | Unit | Deterministic critic rules | Plan rejected when weak topics underweighted | Pass |
| TC-023 | Unit | Deterministic critic rules | Plan rejected when a weak topic is missing | Pass |
| TC-024 | Unit | Deterministic critic rules | Plan accepted when weak topics dominate | Pass |
| TC-025 | Unit | Deterministic critic rules | Plan without weak topics skips share rule | Pass |
| TC-026 | Unit | Deterministic critic rules | Plan wrong week and bad day numbers | Pass |
| TC-027 | Unit | Deterministic critic rules | Quiz flags duplicates and non distinct options | Pass |
| TC-028 | Unit | Deterministic critic rules | Quiz topic difficulty and count mismatch | Pass |
| TC-029 | Unit | Deterministic critic rules | Clean quiz passes | Pass |
| TC-030 | Unit | Deterministic critic rules | Profile matched skills must come from required list | Pass |
| TC-031 | Unit | Deterministic critic rules | Profile with no skills is rejected | Pass |
| TC-032 | Unit | Deterministic critic rules | Turn checks single question and repeats | Pass |
| TC-033 | Unit | Deterministic critic rules | Question reasons round trip | Pass |
| TC-034 | Unit | Deterministic critic rules | Plan rejected when a weak topic gets less than a strong one | Pass |
| TC-035 | Unit | Deterministic critic rules | Plan rejected when the weakest topic is not first | Pass |
| TC-036 | Unit | Deterministic critic rules | Plan ties in weakness are unconstrained | Pass |
| TC-037 | Unit | SQLite repository | Usn is normalised and identifies the student | Pass |
| TC-038 | Unit | SQLite repository | Usn is required | Pass |
| TC-039 | Unit | SQLite repository | Profile roundtrip and unknown student | Pass |
| TC-040 | Unit | SQLite repository | Failed transaction rolls back | Pass |
| TC-041 | Unit | SQLite repository | Save plan upserts the same week | Pass |
| TC-042 | Unit | SQLite repository | Quiz attempt score history and asked questions | Pass |
| TC-043 | Unit | SQLite repository | Unanswered question counts as wrong and lengths must match | Pass |
| TC-044 | Unit | SQLite repository | Topic performance uses the three most recent attempts | Pass |
| TC-045 | Unit | SQLite repository | Past turns exclude current session newest first | Pass |
| TC-046 | Unit | SQLite repository | Delete student cascades to all history | Pass |
| TC-047 | Unit | SQLite repository | Agent log marking and stats | Pass |
| TC-048 | Unit | LLM gateway (fake Groq client) | Mock mode repairs invalid output once | Pass |
| TC-049 | Unit | LLM gateway (fake Groq client) | Mock mode raises after second invalid output | Pass |
| TC-050 | Unit | LLM gateway (fake Groq client) | Model for maps sizes | Pass |
| TC-051 | Unit | LLM gateway (fake Groq client) | Live request shape and logging | Pass |
| TC-052 | Unit | LLM gateway (fake Groq client) | Live repair feeds validation error back and sums tokens | Pass |
| TC-053 | Unit | LLM gateway (fake Groq client) | Live json validate failed is repairable | Pass |
| TC-054 | Unit | LLM gateway (fake Groq client) | Live other bad request raises | Pass |
| TC-055 | Unit | LLM gateway (fake Groq client) | Live unknown model gives actionable error | Pass |
| TC-056 | Unit | LLM gateway (fake Groq client) | Live server error is wrapped | Pass |
| TC-057 | Unit | LLM gateway (fake Groq client) | Live rate limit carries retry after | Pass |
| TC-058 | Unit | LLM gateway (fake Groq client) | Live rate limit without hint | Pass |
| TC-059 | Unit | LangGraph critic loop | Loop retries then approves and reports events | Pass |
| TC-060 | Unit | LangGraph critic loop | Loop stops after retry budget | Pass |
| TC-061 | Unit | LangGraph critic loop | Zero retry budget means single attempt | Pass |
| TC-062 | Unit | LangGraph critic loop | Retry receives previous rejection reasons | Pass |
| TC-063 | Unit | LangGraph critic loop | Every attempt is marked in agent logs | Pass |
| TC-064 | Unit | LangGraph critic loop | Compiled graph is cached per task and exports mermaid | Pass |
| TC-065 | Unit | Resume parsing | Txt and uppercase extension | Pass |
| TC-066 | Unit | Resume parsing | Docx paragraphs and tables | Pass |
| TC-067 | Unit | Resume parsing | Pdf text is extracted | Pass |
| TC-068 | Unit | Resume parsing | Pdf without text layer is rejected | Pass |
| TC-069 | Unit | Resume parsing | Bad input is rejected [png] | Pass |
| TC-070 | Unit | Resume parsing | Bad input is rejected [no-extension] | Pass |
| TC-071 | Unit | Resume parsing | Bad input is rejected [too-short] | Pass |
| TC-072 | Unit | Resume parsing | Bad input is rejected [too-large] | Pass |
| TC-073 | Unit | Output layer | Profile md shows score and handles empty sections | Pass |
| TC-074 | Unit | Output layer | Plan table is ordered by day | Pass |
| TC-075 | Unit | Output layer | Plan minutes has every topic and one column per week | Pass |
| TC-076 | Unit | Output layer | Quiz review marks right wrong and unanswered | Pass |
| TC-077 | Unit | Output layer | Quiz review requires one answer per question | Pass |
| TC-078 | Unit | Output layer | Evaluation md and small labels | Pass |
| TC-079 | Unit | Output layer | Weakness table sorted desc | Pass |
| TC-080 | Unit | Output layer | Score trend pivots by attempt and handles empty | Pass |
| TC-081 | Unit | Output layer | Results table includes only measured metrics | Pass |
| TC-082 | Unit | Output layer | Results markdown and caption | Pass |
| TC-083 | Unit | Output layer | Results svg is well formed with one bar per measured value | Pass |
| TC-084 | Integration | Agents through the critic loop | Role map uses only syllabus topics | Pass |
| TC-085 | Integration | Agents through the critic loop | Profile scores are computed in code | Pass |
| TC-086 | Integration | Agents through the critic loop | Profile regenerates when a skill is invented | Pass |
| TC-087 | Integration | Agents through the critic loop | Replan shifts minutes toward low scores | Pass |
| TC-088 | Integration | Agents through the critic loop | Planner inputs carry previous week | Pass |
| TC-089 | Integration | Agents through the critic loop | Quiz avoids previous questions and records scores | Pass |
| TC-090 | Integration | Agents through the critic loop | Mock quiz demonstrates one critic rejection | Pass |
| TC-091 | Integration | Agents through the critic loop | Llm critic rejection triggers regeneration | Pass |
| TC-092 | Integration | Agents through the critic loop | Suggest difficulty [None-medium-medium] | Pass |
| TC-093 | Integration | Agents through the critic loop | Suggest difficulty [85-medium-hard] | Pass |
| TC-094 | Integration | Agents through the critic loop | Suggest difficulty [100-hard-hard] | Pass |
| TC-095 | Integration | Agents through the critic loop | Suggest difficulty [30-medium-easy] | Pass |
| TC-096 | Integration | Agents through the critic loop | Suggest difficulty [30-easy-easy] | Pass |
| TC-097 | Integration | Agents through the critic loop | Suggest difficulty [60-medium-medium] | Pass |
| TC-098 | Integration | Agents through the critic loop | Suggest difficulty [80-easy-medium] | Pass |
| TC-099 | Integration | Agents through the critic loop | Suggest difficulty [49.9-hard-medium] | Pass |
| TC-100 | Integration | Agents through the critic loop | Interview follows up on vague answers | Pass |
| TC-101 | Integration | Agents through the critic loop | Interview memory avoids past questions | Pass |
| TC-102 | Integration | Agents through the critic loop | Interview final turn is enforced in code | Pass |
| TC-103 | Integration | Agents through the critic loop | Answer evaluation overall is mean | Pass |
| TC-104 | Integration | Agents through the critic loop | Only flagged questions are regenerated | Pass |
| TC-105 | Integration | Agents through the critic loop | Critic judges each question once | Pass |
| TC-106 | Integration | Agents through the critic loop | Critic with one based indices is understood | Pass |
| TC-107 | Integration | Agents through the critic loop | Missing critic verdict counts as rejection | Pass |
| TC-108 | Integration | Agents through the critic loop | Unknown role is rejected before any llm call | Pass |
| TC-109 | Integration | User flows through the service layer | Onboard creates student and profile | Pass |
| TC-110 | Integration | User flows through the service layer | Invalid usn is rejected [] | Pass |
| TC-111 | Integration | User flows through the service layer | Invalid usn is rejected [   ] | Pass |
| TC-112 | Integration | User flows through the service layer | Invalid usn is rejected [AB1] | Pass |
| TC-113 | Integration | User flows through the service layer | Invalid usn is rejected [AB 123] | Pass |
| TC-114 | Integration | User flows through the service layer | Invalid usn is rejected [AB-123] | Pass |
| TC-115 | Integration | User flows through the service layer | Invalid usn is rejected [xxxxxxxxxxxxxxxxxxxxx] | Pass |
| TC-116 | Integration | User flows through the service layer | Invalid usn is rejected [None] | Pass |
| TC-117 | Integration | User flows through the service layer | Usn is normalised | Pass |
| TC-118 | Integration | User flows through the service layer | Onboard rejects unknown role and empty resume | Pass |
| TC-119 | Integration | User flows through the service layer | Samples load only from the listed files | Pass |
| TC-120 | Integration | User flows through the service layer | Read resume surfaces parser errors | Pass |
| TC-121 | Integration | User flows through the service layer | Operations require an onboarded student | Pass |
| TC-122 | Integration | User flows through the service layer | Plans are numbered and adapt to quiz scores | Pass |
| TC-123 | Integration | User flows through the service layer | Quiz round trip and adaptive difficulty | Pass |
| TC-124 | Integration | User flows through the service layer | Start quiz validates parameters [Maths-easy] | Pass |
| TC-125 | Integration | User flows through the service layer | Start quiz validates parameters [OS-extreme] | Pass |
| TC-126 | Integration | User flows through the service layer | Submit quiz validates answers | Pass |
| TC-127 | Integration | User flows through the service layer | Interview runs to completion and persists turns | Pass |
| TC-128 | Integration | User flows through the service layer | Interview answer validation | Pass |
| TC-129 | Integration | User flows through the service layer | Failed follow up can be retried without reanswering | Pass |
| TC-130 | Integration | User flows through the service layer | New session remembers earlier questions | Pass |
| TC-131 | Integration | User flows through the service layer | Unknown interview type | Pass |
| TC-132 | Integration | User flows through the service layer | Dashboard aggregates everything | Pass |
| TC-133 | Integration | User flows through the service layer | Evaluation summary | Pass |
| TC-134 | Integration | Demo seed data | Seed builds four weeks of history | Pass |
| TC-135 | Integration | Demo seed data | Seeded plans follow the scores | Pass |
| TC-136 | Integration | Demo seed data | Seed is idempotent | Pass |
| TC-137 | Integration | Evaluation harness | Refuses mock mode without flag | Pass |
| TC-138 | Integration | Evaluation harness | Mock smoke run writes all outputs | Pass |
| TC-139 | Integration | Evaluation harness | Each run starts with a fresh eval db | Pass |
| TC-140 | Integration | Evaluation harness | Csv writer handles error rows first | Pass |
| TC-141 | Integration | Evaluation harness | Rate limit stops the run but keeps partial results | Pass |
| TC-142 | Integration | Evaluation harness | Resume continues after a rate limit without redoing cases | Pass |
| TC-143 | Integration | Evaluation harness | Resume refuses to mix mock and live | Pass |
| TC-144 | Integration | Evaluation harness | Consecutive quizzes measure memory | Pass |
| TC-145 | Integration | Evaluation harness | Interview probe measures follow up relevance | Pass |
| TC-146 | Integration | Evaluation harness | Progress is saved even when a case crashes | Pass |
| TC-147 | Integration | Evaluation harness | Consecutive quizzes resume per topic | Pass |
| TC-148 | Integration | Evaluation harness | Every case is checkpointed | Pass |
| TC-149 | Integration | Results report | Report writes markdown and svg | Pass |
| TC-150 | Integration | Results report | Report requires a summary | Pass |
| TC-151 | Integration | Results report | Report from a real mock run | Pass |
| TC-152 | Integration | Model availability check | Mock mode has nothing to check | Pass |
| TC-153 | Integration | Model availability check | Missing configuration exits 2 | Pass |
| TC-154 | Integration | Model availability check | Served models pass and report quota | Pass |
| TC-155 | Integration | Model availability check | Retired model fails | Pass |
| TC-156 | Integration | Model availability check | Non json reply fails | Pass |
| TC-157 | Integration | Graph export | Export writes raw and github renderable mermaid | Pass |
| TC-158 | Integration | Graph export | Docs copy is up to date | Pass |
| TC-159 | Integration | Test report generator | Table is built from junit results | Pass |
| TC-160 | Integration | Test report generator | Every test module has a layer | Pass |
| TC-161 | System (UI) | Streamlit pages, headless | Onboard with sample resume | Pass |
| TC-162 | System (UI) | Streamlit pages, headless | Onboard rejects missing usn | Pass |
| TC-163 | System (UI) | Streamlit pages, headless | Pages require a student | Pass |
| TC-164 | System (UI) | Streamlit pages, headless | Plan generates next week and compares | Pass |
| TC-165 | System (UI) | Streamlit pages, headless | Quiz generate answer and review | Pass |
| TC-166 | System (UI) | Streamlit pages, headless | Interview session runs to completion | Pass |
| TC-167 | System (UI) | Streamlit pages, headless | Dashboard renders | Pass |
| TC-168 | System (UI) | Streamlit pages, headless | Onboard requires a resume or sample | Pass |
| TC-169 | System (UI) | Streamlit pages, headless | Failed follow up offers retry without reanswering | Pass |
| TC-170 | System (UI) | Streamlit pages, headless | Failed quiz generation stays visible | Pass |
| TC-171 | System (UI) | Streamlit pages, headless | Results page without and with results | Pass |
| TC-172 | System (UI) | Streamlit pages, headless | Seed demo fills an empty database on start | Pass |
