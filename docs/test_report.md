# Test report

Generated 2026-11-02 16:29 UTC by `python -m scripts.test_report` from a real run of the suite (offline: MOCK_MODE, temporary databases, fake Groq clients for live code paths).

**652 tests: 652 passed, 0 failed, 0 skipped** (405 s of test time).

## By module

| Type | Area | Module | Tests | Passed |
|---|---|---|---|---|
| Unit | Settings and environment | `test_config` | 8 | 8 |
| Unit | Domain syllabi, role topics and colour slots | `test_syllabus` | 13 | 13 |
| Unit | Pydantic output schemas | `test_schemas` | 10 | 10 |
| Unit | Deterministic critic rules | `test_checks` | 23 | 23 |
| Unit | SQLite repository | `test_db` | 13 | 13 |
| Unit | LLM gateway (fake Groq client) | `test_llm` | 16 | 16 |
| Unit | LangGraph critic loop | `test_graph` | 7 | 7 |
| Unit | Resume parsing | `test_resume` | 16 | 16 |
| Unit | Output layer | `test_formatter` | 92 | 92 |
| Integration | Agents through the critic loop | `test_agents` | 37 | 37 |
| Integration | User flows through the service layer | `test_services` | 57 | 57 |
| Integration | Domain topics, multi-topic quizzes, resume versions, Project space | `test_services_syllabus` | 43 | 43 |
| Integration | Demo seed data | `test_seed` | 3 | 3 |
| Integration | Evaluation harness | `test_eval` | 13 | 13 |
| Integration | Results report | `test_report` | 3 | 3 |
| Integration | Model availability check | `test_check_models` | 5 | 5 |
| Integration | Graph export | `test_export_graph` | 2 | 2 |
| Integration | Test report generator | `test_test_report` | 2 | 2 |
| Unit | Screenshot tool helpers | `test_screenshots` | 12 | 12 |
| Unit | Performance tool helpers | `test_perf` | 8 | 8 |
| Unit | Design tokens: contrast and distinctness | `test_theme` | 24 | 24 |
| Unit | Chart builders: encodings and theme | `test_charts` | 16 | 16 |
| Unit | CI workflow settings | `test_ci` | 1 | 1 |
| Unit | Demo tunnel settings | `test_tunnel` | 3 | 3 |
| Unit | Summary PDF builder | `test_summary_pdf` | 13 | 13 |
| Unit | ATS resume builder and PDF compilation | `test_resume_builder` | 26 | 26 |
| Unit | Evaluation scorecard parameters and ratings | `test_scorecard` | 15 | 15 |
| Unit | Degrees and the roles they qualify for | `test_degrees` | 16 | 16 |
| Integration | Local question bank and its share of quizzes | `test_question_bank` | 6 | 6 |
| Integration | HTTP API for the Next.js frontend | `test_server` | 12 | 12 |
| Integration | Every role and domain, resume to interview | `test_all_domains` | 70 | 70 |
| System (UI) | Streamlit pages, headless | `test_ui` | 67 | 67 |

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
| TC-009 | Unit | Domain syllabi, role topics and colour slots | Every domain lists aptitude first and fits the palette | Pass |
| TC-010 | Unit | Domain syllabi, role topics and colour slots | The cs core is the original six topics in their colour order | Pass |
| TC-011 | Unit | Domain syllabi, role topics and colour slots | Every catalog role has a skill list in its domain | Pass |
| TC-012 | Unit | Domain syllabi, role topics and colour slots | An embedded engineer practises electronics not computer science | Pass |
| TC-013 | Unit | Domain syllabi, role topics and colour slots | Tracked topics add chosen domain topics but never another domains | Pass |
| TC-014 | Unit | Domain syllabi, role topics and colour slots | Original cs roles belong to cs and track the core | Pass |
| TC-015 | Unit | Domain syllabi, role topics and colour slots | Colour slots follow the syllabus position | Pass |
| TC-016 | Unit | Domain syllabi, role topics and colour slots | Colour slot collisions move to a free slot | Pass |
| TC-017 | Unit | Domain syllabi, role topics and colour slots | Skills for a topic come from the role map | Pass |
| TC-018 | Unit | Domain syllabi, role topics and colour slots | The builder reads the same catalog | Pass |
| TC-019 | Unit | Domain syllabi, role topics and colour slots | Every catalog role is complete for the builder | Pass |
| TC-020 | Unit | Domain syllabi, role topics and colour slots | The question bank roles are in the catalog | Pass |
| TC-021 | Unit | Domain syllabi, role topics and colour slots | Skill aliases name real skills | Pass |
| TC-022 | Unit | Pydantic output schemas | Bloom level is normalised | Pass |
| TC-023 | Unit | Pydantic output schemas | Question rejects invalid fields [bad0] | Pass |
| TC-024 | Unit | Pydantic output schemas | Question rejects invalid fields [bad1] | Pass |
| TC-025 | Unit | Pydantic output schemas | Question rejects invalid fields [bad2] | Pass |
| TC-026 | Unit | Pydantic output schemas | Question rejects invalid fields [bad3] | Pass |
| TC-027 | Unit | Pydantic output schemas | Question rejects invalid fields [bad4] | Pass |
| TC-028 | Unit | Pydantic output schemas | Question rejects invalid fields [bad5] | Pass |
| TC-029 | Unit | Pydantic output schemas | Plan needs exactly seven days and bounded minutes | Pass |
| TC-030 | Unit | Pydantic output schemas | Minutes by topic sums per topic | Pass |
| TC-031 | Unit | Pydantic output schemas | Answer evaluation bounds and overall | Pass |
| TC-032 | Unit | Deterministic critic rules | Text hash ignores case whitespace and punctuation | Pass |
| TC-033 | Unit | Deterministic critic rules | Weakness prefers quiz evidence over resume gaps | Pass |
| TC-034 | Unit | Deterministic critic rules | Weak topics sorted by weakness and threshold is strict | Pass |
| TC-035 | Unit | Deterministic critic rules | Plan rejected when weak topics underweighted | Pass |
| TC-036 | Unit | Deterministic critic rules | Plan rejected when a weak topic is missing | Pass |
| TC-037 | Unit | Deterministic critic rules | Plan accepted when weak topics dominate | Pass |
| TC-038 | Unit | Deterministic critic rules | Plan without weak topics skips share rule | Pass |
| TC-039 | Unit | Deterministic critic rules | Plan wrong week and bad day numbers | Pass |
| TC-040 | Unit | Deterministic critic rules | Quiz flags duplicates and non distinct options | Pass |
| TC-041 | Unit | Deterministic critic rules | Quiz topic difficulty and count mismatch | Pass |
| TC-042 | Unit | Deterministic critic rules | Clean quiz passes | Pass |
| TC-043 | Unit | Deterministic critic rules | Profile matched skills must come from required list | Pass |
| TC-044 | Unit | Deterministic critic rules | Profile with no skills is rejected | Pass |
| TC-045 | Unit | Deterministic critic rules | Turn checks single question and repeats | Pass |
| TC-046 | Unit | Deterministic critic rules | Question reasons round trip | Pass |
| TC-047 | Unit | Deterministic critic rules | Plan rejected when a weak topic gets less than a strong one | Pass |
| TC-048 | Unit | Deterministic critic rules | Plan rejected when the weakest topic is not first | Pass |
| TC-049 | Unit | Deterministic critic rules | Plan ties in weakness are unconstrained | Pass |
| TC-050 | Unit | Deterministic critic rules | A plan topic outside the students syllabus is rejected | Pass |
| TC-051 | Unit | Deterministic critic rules | Weakness covers exactly the topics given | Pass |
| TC-052 | Unit | Deterministic critic rules | Evidence needs the skill named as whole words | Pass |
| TC-053 | Unit | Deterministic critic rules | Evidence accepts plurals and aliases | Pass |
| TC-054 | Unit | Deterministic critic rules | Readiness weighs syllabus skills double | Pass |
| TC-055 | Unit | SQLite repository | Usn is normalised and identifies the student | Pass |
| TC-056 | Unit | SQLite repository | Usn is required | Pass |
| TC-057 | Unit | SQLite repository | Profile roundtrip and unknown student | Pass |
| TC-058 | Unit | SQLite repository | Failed transaction rolls back | Pass |
| TC-059 | Unit | SQLite repository | Save plan upserts the same week | Pass |
| TC-060 | Unit | SQLite repository | Quiz attempt score history and asked questions | Pass |
| TC-061 | Unit | SQLite repository | Unanswered question counts as wrong and lengths must match | Pass |
| TC-062 | Unit | SQLite repository | Topic performance uses the three most recent attempts | Pass |
| TC-063 | Unit | SQLite repository | Agent stats count failed calls apart from rejections | Pass |
| TC-064 | Unit | SQLite repository | Past turns exclude current session newest first | Pass |
| TC-065 | Unit | SQLite repository | Delete student cascades to all history | Pass |
| TC-066 | Unit | SQLite repository | Agent log marking and stats | Pass |
| TC-067 | Unit | SQLite repository | Plan progress marks days and joins onto the plans | Pass |
| TC-068 | Unit | LLM gateway (fake Groq client) | Mock mode repairs invalid output once | Pass |
| TC-069 | Unit | LLM gateway (fake Groq client) | Mock mode raises after second invalid output | Pass |
| TC-070 | Unit | LLM gateway (fake Groq client) | Model for maps sizes | Pass |
| TC-071 | Unit | LLM gateway (fake Groq client) | Live request shape and logging | Pass |
| TC-072 | Unit | LLM gateway (fake Groq client) | Live repair feeds validation error back and sums tokens | Pass |
| TC-073 | Unit | LLM gateway (fake Groq client) | Live json validate failed is repairable | Pass |
| TC-074 | Unit | LLM gateway (fake Groq client) | Live failed call is logged with its tokens and latency | Pass |
| TC-075 | Unit | LLM gateway (fake Groq client) | Live other bad request raises | Pass |
| TC-076 | Unit | LLM gateway (fake Groq client) | Live unknown model gives actionable error | Pass |
| TC-077 | Unit | LLM gateway (fake Groq client) | Live server error is wrapped | Pass |
| TC-078 | Unit | LLM gateway (fake Groq client) | Live rate limit carries retry after | Pass |
| TC-079 | Unit | LLM gateway (fake Groq client) | Live rate limit without hint | Pass |
| TC-080 | Unit | LLM gateway (fake Groq client) | Interactive agents use key one and background agents key two | Pass |
| TC-081 | Unit | LLM gateway (fake Groq client) | A rate limited key fails over to the other | Pass |
| TC-082 | Unit | LLM gateway (fake Groq client) | Both keys rate limited raises rate limited | Pass |
| TC-083 | Unit | LLM gateway (fake Groq client) | One key still works and needs no numbered keys | Pass |
| TC-084 | Unit | LangGraph critic loop | Loop retries then approves and reports events | Pass |
| TC-085 | Unit | LangGraph critic loop | Loop stops after retry budget | Pass |
| TC-086 | Unit | LangGraph critic loop | Zero retry budget means single attempt | Pass |
| TC-087 | Unit | LangGraph critic loop | Retry receives previous rejection reasons | Pass |
| TC-088 | Unit | LangGraph critic loop | Every attempt is marked in agent logs | Pass |
| TC-089 | Unit | LangGraph critic loop | A verify that raises marks the attempt failed | Pass |
| TC-090 | Unit | LangGraph critic loop | Compiled graph is cached per task and exports mermaid | Pass |
| TC-091 | Unit | Resume parsing | Txt and uppercase extension | Pass |
| TC-092 | Unit | Resume parsing | Docx paragraphs and tables | Pass |
| TC-093 | Unit | Resume parsing | Pdf text is extracted | Pass |
| TC-094 | Unit | Resume parsing | Pdf without text layer is rejected | Pass |
| TC-095 | Unit | Resume parsing | Bad input is rejected [png] | Pass |
| TC-096 | Unit | Resume parsing | Bad input is rejected [no-extension] | Pass |
| TC-097 | Unit | Resume parsing | Bad input is rejected [too-short] | Pass |
| TC-098 | Unit | Resume parsing | Bad input is rejected [too-large] | Pass |
| TC-099 | Unit | Resume parsing | Damaged pdf is rejected with a message [garbage] | Pass |
| TC-100 | Unit | Resume parsing | Damaged pdf is rejected with a message [truncated] | Pass |
| TC-101 | Unit | Resume parsing | Damaged docx is rejected with a message | Pass |
| TC-102 | Unit | Resume parsing | Password protected pdf says so | Pass |
| TC-103 | Unit | Resume parsing | Pdf locked only against editing still reads | Pass |
| TC-104 | Unit | Resume parsing | Password protected docx says so | Pass |
| TC-105 | Unit | Resume parsing | Docx that unpacks past 25 mb is rejected before parsing | Pass |
| TC-106 | Unit | Resume parsing | Only the first 30 pdf pages are read | Pass |
| TC-107 | Unit | Output layer | Profile pieces show counts and handle empty sections | Pass |
| TC-108 | Unit | Output layer | Plan table is ordered by day | Pass |
| TC-109 | Unit | Output layer | Plan minutes has every planned topic and one column per week | Pass |
| TC-110 | Unit | Output layer | Plan summary totals the week and names its main topic | Pass |
| TC-111 | Unit | Output layer | Plan csv has the table columns and one row per day | Pass |
| TC-112 | Unit | Output layer | Next monday is the coming monday [2026-10-19-2026-10-19] | Pass |
| TC-113 | Unit | Output layer | Next monday is the coming monday [2026-10-20-2026-10-26] | Pass |
| TC-114 | Unit | Output layer | Next monday is the coming monday [2026-10-25-2026-10-26] | Pass |
| TC-115 | Unit | Output layer | Plan ics is a calendar with one event per day | Pass |
| TC-116 | Unit | Output layer | Plan ics escapes text and folds long lines | Pass |
| TC-117 | Unit | Output layer | Plan days html lists every day in order with its topic chip | Pass |
| TC-118 | Unit | Output layer | Plan days html marks done days in words | Pass |
| TC-119 | Unit | Output layer | Plan days html escapes model text [<script>alert(1)</script>] | Pass |
| TC-120 | Unit | Output layer | Plan days html escapes model text ["><img src=x onerror=alert(1)>] | Pass |
| TC-121 | Unit | Output layer | Minutes shift headline states the change [before0-after0-OS now gets the most minutes] | Pass |
| TC-122 | Unit | Output layer | Minutes shift headline states the change [before1-after1-OS gets 240 more minutes and DBMS 360 fewer than in week 3] | Pass |
| TC-123 | Unit | Output layer | Minutes shift headline states the change [before2-after2-CN gets 60 more minutes than in week 3] | Pass |
| TC-124 | Unit | Output layer | Minutes shift headline states the change [before3-after3-DBMS gets 360 fewer minutes than in week 3] | Pass |
| TC-125 | Unit | Output layer | Minutes shift headline states the change [before4-after4-The same minutes per topic as in week 3] | Pass |
| TC-126 | Unit | Output layer | Minutes shift alt reads every planned topic in syllabus order | Pass |
| TC-127 | Unit | Output layer | Weakness source explains both inputs | Pass |
| TC-128 | Unit | Output layer | Quiz review marks right wrong and unanswered with icon and word | Pass |
| TC-129 | Unit | Output layer | Blanks md names the unanswered questions | Pass |
| TC-130 | Unit | Output layer | Quiz setup lines explain the hint and the suggestion | Pass |
| TC-131 | Unit | Output layer | Result md says what the score changes [easy-medium-trending_up] | Pass |
| TC-132 | Unit | Output layer | Result md says what the score changes [hard-hard-trending_flat] | Pass |
| TC-133 | Unit | Output layer | Result md says what the score changes [hard-medium-trending_down] | Pass |
| TC-134 | Unit | Output layer | Md escape shows text literally [*p-\\*p] | Pass |
| TC-135 | Unit | Output layer | Md escape shows text literally [__init__-\\_\\_init\\_\\_] | Pass |
| TC-136 | Unit | Output layer | Md escape shows text literally [![x](http://example.com/a.png)-\\!\\[x\\]\\(http://example\\.com/a\\.png\\)] | Pass |
| TC-137 | Unit | Output layer | Md escape shows text literally [<script>alert(1)</script>-\\<script\\>alert\\(1\\)\\</script\\>] | Pass |
| TC-138 | Unit | Output layer | Md escape shows text literally [Costs $5 to $10-Costs \\$5 to \\$10] | Pass |
| TC-139 | Unit | Output layer | Md escape shows text literally [# 1. ----\\# 1\\. \\-\\-\\-] | Pass |
| TC-140 | Unit | Output layer | Md escape keeps code readable | Pass |
| TC-141 | Unit | Output layer | Topic chip follows the scheme and escapes its name | Pass |
| TC-142 | Unit | Output layer | Status pairs an icon with escaped words | Pass |
| TC-143 | Unit | Output layer | Critic text numbers questions like the quiz [critic rejected quiz: question 0: options are not distinct-critic rejected quiz: Q1:] | Pass |
| TC-144 | Unit | Output layer | Critic text numbers questions like the quiz [quiz: rejected after retries: question 3: a; question 11: b-Q4: a; Q12: b] | Pass |
| TC-145 | Unit | Output layer | Critic text numbers questions like the quiz [critic rejected interviewer: question already asked: "x"-question already asked] | Pass |
| TC-146 | Unit | Output layer | Critic text is escaped | Pass |
| TC-147 | Unit | Output layer | Markdown builders escape every dynamic value [*p] | Pass |
| TC-148 | Unit | Output layer | Markdown builders escape every dynamic value [__init__] | Pass |
| TC-149 | Unit | Output layer | Markdown builders escape every dynamic value [![x](http://example.com/a.png)] | Pass |
| TC-150 | Unit | Output layer | Markdown builders escape every dynamic value [<script>alert(1)</script>] | Pass |
| TC-151 | Unit | Output layer | Criteria html escapes criterion names [<script>alert(1)</script>] | Pass |
| TC-152 | Unit | Output layer | Criteria html escapes criterion names ["><img src=x onerror=alert(1)>] | Pass |
| TC-153 | Unit | Output layer | Quiz notes are plain markdown with every question | Pass |
| TC-154 | Unit | Output layer | Interview notes quote answers and list feedback | Pass |
| TC-155 | Unit | Output layer | Notes escape every dynamic value [*p] | Pass |
| TC-156 | Unit | Output layer | Notes escape every dynamic value [__init__] | Pass |
| TC-157 | Unit | Output layer | Notes escape every dynamic value [![x](http://example.com/a.png)] | Pass |
| TC-158 | Unit | Output layer | Notes escape every dynamic value [<script>alert(1)</script>] | Pass |
| TC-159 | Unit | Output layer | Quiz review requires one answer per question | Pass |
| TC-160 | Unit | Output layer | Feedback shows the overall score then each criterion | Pass |
| TC-161 | Unit | Output layer | A multi line model answer keeps its lines in the quote | Pass |
| TC-162 | Unit | Output layer | Session summary pieces show averages and tips | Pass |
| TC-163 | Unit | Output layer | Interview questions say whether they follow up | Pass |
| TC-164 | Unit | Output layer | Interview progress counts questions [0-True-shown0] | Pass |
| TC-165 | Unit | Output layer | Interview progress counts questions [1-False-shown1] | Pass |
| TC-166 | Unit | Output layer | Interview progress counts questions [4-True-shown2] | Pass |
| TC-167 | Unit | Output layer | Interview progress counts questions [5-False-shown3] | Pass |
| TC-168 | Unit | Output layer | Mastery words pair every trend with an icon and words | Pass |
| TC-169 | Unit | Output layer | Topic scores headline names the biggest move [scores0-OS is up from 30% to 70%] | Pass |
| TC-170 | Unit | Output layer | Topic scores headline names the biggest move [scores1-OS is down from 70% to 30%] | Pass |
| TC-171 | Unit | Output layer | Topic scores headline names the biggest move [scores2-Scores are level since your first quizzes] | Pass |
| TC-172 | Unit | Output layer | Topic scores headline names the biggest move [scores3-Take a second quiz on a topic to see it move] | Pass |
| TC-173 | Unit | Output layer | Dashboard headlines and alt text | Pass |
| TC-174 | Unit | Output layer | Telemetry tables are ready to read | Pass |
| TC-175 | Unit | Output layer | Readiness change and headline never invent a trend | Pass |
| TC-176 | Unit | Output layer | Streak and activity words | Pass |
| TC-177 | Unit | Output layer | Critic plain renumbers without escaping | Pass |
| TC-178 | Unit | Output layer | Results table includes only measured metrics | Pass |
| TC-179 | Unit | Output layer | Results markdown and caption | Pass |
| TC-180 | Unit | Output layer | Results note names the duplicate rate only with that row | Pass |
| TC-181 | Unit | Output layer | Results metrics define each rate and its direction | Pass |
| TC-182 | Unit | Output layer | Compare html draws both systems in their colours | Pass |
| TC-183 | Unit | Output layer | Results svg is well formed with one bar per measured value | Pass |
| TC-184 | Unit | Output layer | Trail tells the critic loop in order | Pass |
| TC-185 | Unit | Output layer | Trail collapses repeats and explains a stop | Pass |
| TC-186 | Unit | Output layer | Relative day uses the students calendar | Pass |
| TC-187 | Unit | Output layer | Weakness headline and alt text state the takeaway | Pass |
| TC-188 | Unit | Output layer | Topic chips colour a topic by its syllabus slot | Pass |
| TC-189 | Unit | Output layer | Spec table counts questions per topic and level with totals | Pass |
| TC-190 | Unit | Output layer | Mix and spec notes read plainly | Pass |
| TC-191 | Unit | Output layer | Run notes escape model text and mark every answer | Pass |
| TC-192 | Unit | Output layer | Resume preview and filename are safe | Pass |
| TC-193 | Unit | Output layer | Project lines escape text and link only the validated url | Pass |
| TC-194 | Unit | Output layer | Diff and advice lines name what to do | Pass |
| TC-195 | Unit | Output layer | Scorecard bars show score and measured value | Pass |
| TC-196 | Unit | Output layer | Accuracy headline compares easy with hard | Pass |
| TC-197 | Unit | Output layer | Role fits group by domain with words and escape names | Pass |
| TC-198 | Unit | Output layer | Resume preview shows jobs and every degree escaped | Pass |
| TC-199 | Integration | Agents through the critic loop | Role map uses only its domains topics | Pass |
| TC-200 | Integration | Agents through the critic loop | The evaluated cs roles keep the six core topics | Pass |
| TC-201 | Integration | Agents through the critic loop | Profile scores are computed in code | Pass |
| TC-202 | Integration | Agents through the critic loop | Profile regenerates when a skill is invented | Pass |
| TC-203 | Integration | Agents through the critic loop | Replan shifts minutes toward low scores | Pass |
| TC-204 | Integration | Agents through the critic loop | Planner inputs carry previous week | Pass |
| TC-205 | Integration | Agents through the critic loop | Quiz avoids previous questions and records scores | Pass |
| TC-206 | Integration | Agents through the critic loop | Mock quiz demonstrates one critic rejection | Pass |
| TC-207 | Integration | Agents through the critic loop | Llm critic rejection triggers regeneration | Pass |
| TC-208 | Integration | Agents through the critic loop | Suggest difficulty [None-medium-medium] | Pass |
| TC-209 | Integration | Agents through the critic loop | Suggest difficulty [85-medium-hard] | Pass |
| TC-210 | Integration | Agents through the critic loop | Suggest difficulty [100-hard-hard] | Pass |
| TC-211 | Integration | Agents through the critic loop | Suggest difficulty [30-medium-easy] | Pass |
| TC-212 | Integration | Agents through the critic loop | Suggest difficulty [30-easy-easy] | Pass |
| TC-213 | Integration | Agents through the critic loop | Suggest difficulty [60-medium-medium] | Pass |
| TC-214 | Integration | Agents through the critic loop | Suggest difficulty [80-easy-medium] | Pass |
| TC-215 | Integration | Agents through the critic loop | Suggest difficulty [49.9-hard-medium] | Pass |
| TC-216 | Integration | Agents through the critic loop | Interview follows up on vague answers | Pass |
| TC-217 | Integration | Agents through the critic loop | Mock interview never repeats a follow up | Pass |
| TC-218 | Integration | Agents through the critic loop | Mock follow up quotes answers cleanly | Pass |
| TC-219 | Integration | Agents through the critic loop | Interview memory avoids past questions | Pass |
| TC-220 | Integration | Agents through the critic loop | Interview final turn is enforced in code | Pass |
| TC-221 | Integration | Agents through the critic loop | Answer evaluation overall is mean | Pass |
| TC-222 | Integration | Agents through the critic loop | Only flagged questions are regenerated | Pass |
| TC-223 | Integration | Agents through the critic loop | Critic judges each question once | Pass |
| TC-224 | Integration | Agents through the critic loop | Critic with one based indices is understood | Pass |
| TC-225 | Integration | Agents through the critic loop | Critic verdicts count only when their numbering is unambiguous [indices0-5] | Pass |
| TC-226 | Integration | Agents through the critic loop | Critic verdicts count only when their numbering is unambiguous [indices1-5] | Pass |
| TC-227 | Integration | Agents through the critic loop | Critic verdicts count only when their numbering is unambiguous [indices2-0] | Pass |
| TC-228 | Integration | Agents through the critic loop | Critic verdicts count only when their numbering is unambiguous [indices3-0] | Pass |
| TC-229 | Integration | Agents through the critic loop | Critic verdicts count only when their numbering is unambiguous [indices4-0] | Pass |
| TC-230 | Integration | Agents through the critic loop | Critic verdicts count only when their numbering is unambiguous [indices5-0] | Pass |
| TC-231 | Integration | Agents through the critic loop | Critic verdicts count only when their numbering is unambiguous [indices6-0] | Pass |
| TC-232 | Integration | Agents through the critic loop | Missing critic verdict counts as rejection | Pass |
| TC-233 | Integration | Agents through the critic loop | Unknown role is rejected before any llm call | Pass |
| TC-234 | Integration | Agents through the critic loop | A claimed skill the resume never names does not count | Pass |
| TC-235 | Integration | Agents through the critic loop | An alias on the resume counts as the skill | Pass |
| TC-236 | Integration | User flows through the service layer | Onboard creates student and profile | Pass |
| TC-237 | Integration | User flows through the service layer | Invalid usn is rejected [] | Pass |
| TC-238 | Integration | User flows through the service layer | Invalid usn is rejected [   ] | Pass |
| TC-239 | Integration | User flows through the service layer | Invalid usn is rejected [AB1] | Pass |
| TC-240 | Integration | User flows through the service layer | Invalid usn is rejected [AB 123] | Pass |
| TC-241 | Integration | User flows through the service layer | Invalid usn is rejected [AB-123] | Pass |
| TC-242 | Integration | User flows through the service layer | Invalid usn is rejected [xxxxxxxxxxxxxxxxxxxxx] | Pass |
| TC-243 | Integration | User flows through the service layer | Invalid usn is rejected [None] | Pass |
| TC-244 | Integration | User flows through the service layer | Usn is normalised | Pass |
| TC-245 | Integration | User flows through the service layer | Onboard rejects unknown role and empty resume | Pass |
| TC-246 | Integration | User flows through the service layer | Sample list is read once | Pass |
| TC-247 | Integration | User flows through the service layer | Samples load only from the listed files | Pass |
| TC-248 | Integration | User flows through the service layer | Read resume surfaces parser errors | Pass |
| TC-249 | Integration | User flows through the service layer | Operations require an onboarded student | Pass |
| TC-250 | Integration | User flows through the service layer | Plans are numbered and adapt to quiz scores | Pass |
| TC-251 | Integration | User flows through the service layer | Quiz round trip and adaptive difficulty | Pass |
| TC-252 | Integration | User flows through the service layer | Quiz setup ranks topics and suggests from the latest attempt | Pass |
| TC-253 | Integration | User flows through the service layer | Quiz result counts correct answers and quiz key is stable | Pass |
| TC-254 | Integration | User flows through the service layer | Start quiz validates parameters [Maths-easy] | Pass |
| TC-255 | Integration | User flows through the service layer | Start quiz validates parameters [OS-extreme] | Pass |
| TC-256 | Integration | User flows through the service layer | Submit quiz validates answers | Pass |
| TC-257 | Integration | User flows through the service layer | Interview runs to completion and persists turns | Pass |
| TC-258 | Integration | User flows through the service layer | Interview answer validation | Pass |
| TC-259 | Integration | User flows through the service layer | Failed follow up can be retried without reanswering | Pass |
| TC-260 | Integration | User flows through the service layer | New session remembers earlier questions | Pass |
| TC-261 | Integration | User flows through the service layer | Unknown interview type | Pass |
| TC-262 | Integration | User flows through the service layer | Dashboard aggregates everything | Pass |
| TC-263 | Integration | User flows through the service layer | Evaluation summary | Pass |
| TC-264 | Integration | User flows through the service layer | Next action without a profile is onboarding | Pass |
| TC-265 | Integration | User flows through the service layer | Next action without a plan is week 1 | Pass |
| TC-266 | Integration | User flows through the service layer | Next action quizzes the weakest unpractised topic first | Pass |
| TC-267 | Integration | User flows through the service layer | Next action returns to a weak topic after a week at the suggested level | Pass |
| TC-268 | Integration | User flows through the service layer | Next action suggests an interview once weak topics are practised | Pass |
| TC-269 | Integration | User flows through the service layer | Next action adapts the plan when it is a week old with new scores | Pass |
| TC-270 | Integration | User flows through the service layer | Next action otherwise practises the weakest topic | Pass |
| TC-271 | Integration | User flows through the service layer | Home gathers focus checklist and recent activity | Pass |
| TC-272 | Integration | User flows through the service layer | Home for a new student starts with a plan | Pass |
| TC-273 | Integration | User flows through the service layer | Home reports an unreadable database safely | Pass |
| TC-274 | Integration | User flows through the service layer | Usn owner finds the student behind a usn | Pass |
| TC-275 | Integration | User flows through the service layer | Delete student needs the matching usn | Pass |
| TC-276 | Integration | User flows through the service layer | Interview summary averages each criterion and tips the weak ones | Pass |
| TC-277 | Integration | User flows through the service layer | Streaks count consecutive days [active0-20-expected0] | Pass |
| TC-278 | Integration | User flows through the service layer | Streaks count consecutive days [active1-20-expected1] | Pass |
| TC-279 | Integration | User flows through the service layer | Streaks count consecutive days [active2-20-expected2] | Pass |
| TC-280 | Integration | User flows through the service layer | Streaks count consecutive days [active3-20-expected3] | Pass |
| TC-281 | Integration | User flows through the service layer | Streaks count consecutive days [active4-20-expected4] | Pass |
| TC-282 | Integration | User flows through the service layer | Streaks count consecutive days [active5-20-expected5] | Pass |
| TC-283 | Integration | User flows through the service layer | Activity days use the students calendar not utc | Pass |
| TC-284 | Integration | User flows through the service layer | Study streak combines quizzes and interview sessions | Pass |
| TC-285 | Integration | User flows through the service layer | Score trend compares the latest quiz with the ones before [scores0-new] | Pass |
| TC-286 | Integration | User flows through the service layer | Score trend compares the latest quiz with the ones before [scores1-new] | Pass |
| TC-287 | Integration | User flows through the service layer | Score trend compares the latest quiz with the ones before [scores2-improving] | Pass |
| TC-288 | Integration | User flows through the service layer | Score trend compares the latest quiz with the ones before [scores3-steady] | Pass |
| TC-289 | Integration | User flows through the service layer | Score trend compares the latest quiz with the ones before [scores4-slipping] | Pass |
| TC-290 | Integration | User flows through the service layer | Score trend compares the latest quiz with the ones before [scores5-steady] | Pass |
| TC-291 | Integration | User flows through the service layer | Topic mastery matches the planners weakness and ranks weakest first | Pass |
| TC-292 | Integration | User flows through the service layer | Days done are validated and reach the overviews | Pass |
| TC-293 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | An ece students pages show only their domains topics | Pass |
| TC-294 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | A quiz on another domains topic leaves the syllabus unchanged | Pass |
| TC-295 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | A chosen domain topic is tracked from its first quiz | Pass |
| TC-296 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | The mix slider always adds up to 100 [0-0] | Pass |
| TC-297 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | The mix slider always adds up to 100 [20-80] | Pass |
| TC-298 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | The mix slider always adds up to 100 [35-35] | Pass |
| TC-299 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | The mix slider always adds up to 100 [100-100] | Pass |
| TC-300 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | The mix slider always adds up to 100 [80-20] | Pass |
| TC-301 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Split by mix hands out every question [1] | Pass |
| TC-302 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Split by mix hands out every question [5] | Pass |
| TC-303 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Split by mix hands out every question [7] | Pass |
| TC-304 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Split by mix hands out every question [50] | Pass |
| TC-305 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Split by mix follows the percentages | Pass |
| TC-306 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Quiz spec rejects bad setups [counts0-mix0-at least one topic] | Pass |
| TC-307 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Quiz spec rejects bad setups [counts1-mix1-1 to 50] | Pass |
| TC-308 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Quiz spec rejects bad setups [counts2-mix2-1 to 50] | Pass |
| TC-309 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Quiz spec rejects bad setups [counts3-mix3-at most 100] | Pass |
| TC-310 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Quiz spec rejects bad setups [counts4-mix4-Not in your syllabus] | Pass |
| TC-311 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Quiz spec rejects bad setups [counts5-mix5-add up to 100] | Pass |
| TC-312 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Quiz spec rejects bad setups [counts6-mix6-only easy, medium and hard] | Pass |
| TC-313 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | A quiz spec lists parts topic by topic easy to hard | Pass |
| TC-314 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | A large part is generated in critic checked batches without repeats | Pass |
| TC-315 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Submitting a run saves each part and breaks the result down | Pass |
| TC-316 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Submit rejects answers that do not fit the run | Pass |
| TC-317 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Recent averages weigh quizzes by their size | Pass |
| TC-318 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Saving a resume versions the same student and locks the domain | Pass |
| TC-319 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Saving without a student creates one from the resume | Pass |
| TC-320 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Save resume validates before profiling [ece-res0-valid email] | Pass |
| TC-321 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Save resume validates before profiling [ece-res1-full name] | Pass |
| TC-322 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Save resume validates before profiling [cs-res2-not a role in this domain] | Pass |
| TC-323 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Resume advice suggests skills the quizzes now back | Pass |
| TC-324 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Resume advice before any version has no review date | Pass |
| TC-325 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Project space is for computing domains only | Pass |
| TC-326 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Projects are saved logged and fed to the resume | Pass |
| TC-327 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Project inputs are validated [fields0-name of up to 80] | Pass |
| TC-328 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Project inputs are validated [fields1-web address] | Pass |
| TC-329 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Project inputs are validated [fields2-web address] | Pass |
| TC-330 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Project inputs are validated [fields3-Unknown status] | Pass |
| TC-331 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Project inputs are validated [fields4-README] | Pass |
| TC-332 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Project names are unique per student and owned | Pass |
| TC-333 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Save rejects unreadable or reversed dates | Pass |
| TC-334 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Roles for degree validates and lists roles | Pass |
| TC-335 | Integration | Domain topics, multi-topic quizzes, resume versions, Project space | Education from text prefills the form | Pass |
| TC-336 | Integration | Demo seed data | Seed builds four weeks of history | Pass |
| TC-337 | Integration | Demo seed data | Seeded plans follow the scores | Pass |
| TC-338 | Integration | Demo seed data | Seed is idempotent | Pass |
| TC-339 | Integration | Evaluation harness | Refuses mock mode without flag | Pass |
| TC-340 | Integration | Evaluation harness | Mock smoke run writes all outputs | Pass |
| TC-341 | Integration | Evaluation harness | Each run starts with a fresh eval db | Pass |
| TC-342 | Integration | Evaluation harness | Csv writer handles error rows first | Pass |
| TC-343 | Integration | Evaluation harness | Rate limit stops the run but keeps partial results | Pass |
| TC-344 | Integration | Evaluation harness | Resume continues after a rate limit without redoing cases | Pass |
| TC-345 | Integration | Evaluation harness | Resume refuses to mix mock and live | Pass |
| TC-346 | Integration | Evaluation harness | Consecutive quizzes measure memory | Pass |
| TC-347 | Integration | Evaluation harness | Interview probe measures follow up relevance | Pass |
| TC-348 | Integration | Evaluation harness | Progress is saved even when a case crashes | Pass |
| TC-349 | Integration | Evaluation harness | Consecutive quizzes resume per topic | Pass |
| TC-350 | Integration | Evaluation harness | Consecutive quizzes resume mid topic without redoing quizzes | Pass |
| TC-351 | Integration | Evaluation harness | Every case is checkpointed | Pass |
| TC-352 | Integration | Results report | Report writes markdown and svg | Pass |
| TC-353 | Integration | Results report | Report requires a summary | Pass |
| TC-354 | Integration | Results report | Report from a real mock run | Pass |
| TC-355 | Integration | Model availability check | Mock mode has nothing to check | Pass |
| TC-356 | Integration | Model availability check | Missing configuration exits 2 | Pass |
| TC-357 | Integration | Model availability check | Served models pass and report quota | Pass |
| TC-358 | Integration | Model availability check | Retired model fails | Pass |
| TC-359 | Integration | Model availability check | Non json reply fails | Pass |
| TC-360 | Integration | Graph export | Export writes raw and github renderable mermaid | Pass |
| TC-361 | Integration | Graph export | Docs copy is up to date | Pass |
| TC-362 | Integration | Test report generator | Table is built from junit results | Pass |
| TC-363 | Integration | Test report generator | Every test module has a layer | Pass |
| TC-364 | Unit | Screenshot tool helpers | Page list matches the app navigation | Pass |
| TC-365 | Unit | Screenshot tool helpers | Every capture is checked by a marker | Pass |
| TC-366 | Unit | Screenshot tool helpers | Interview answers are detailed and distinct | Pass |
| TC-367 | Unit | Screenshot tool helpers | Shot names follow the convention | Pass |
| TC-368 | Unit | Screenshot tool helpers | Planned shots cover pages states flows widths and schemes | Pass |
| TC-369 | Unit | Screenshot tool helpers | Unknown widths are rejected [] | Pass |
| TC-370 | Unit | Screenshot tool helpers | Unknown widths are rejected [1440,800] | Pass |
| TC-371 | Unit | Screenshot tool helpers | Unknown widths are rejected [1024] | Pass |
| TC-372 | Unit | Screenshot tool helpers | Widths and schemes parse | Pass |
| TC-373 | Unit | Screenshot tool helpers | Isolated env never reaches groq or the real env | Pass |
| TC-374 | Unit | Screenshot tool helpers | Compress png shrinks and keeps the size | Pass |
| TC-375 | Unit | Screenshot tool helpers | Pages filter parses known slugs only | Pass |
| TC-376 | Unit | Performance tool helpers | Percentile is nearest rank [values0-50-3] | Pass |
| TC-377 | Unit | Performance tool helpers | Percentile is nearest rank [values1-90-7] | Pass |
| TC-378 | Unit | Performance tool helpers | Percentile is nearest rank [values2-90-10] | Pass |
| TC-379 | Unit | Performance tool helpers | Percentile is nearest rank [values3-50-4] | Pass |
| TC-380 | Unit | Performance tool helpers | Dir size | Pass |
| TC-381 | Unit | Performance tool helpers | Query counter counts calls and statements and restores tx | Pass |
| TC-382 | Unit | Performance tool helpers | Markdown table | Pass |
| TC-383 | Unit | Performance tool helpers | Modes default to fresh and rerun is available | Pass |
| TC-384 | Unit | Design tokens: contrast and distinctness | Config toml mirrors the tokens [light] | Pass |
| TC-385 | Unit | Design tokens: contrast and distinctness | Config toml mirrors the tokens [dark] | Pass |
| TC-386 | Unit | Design tokens: contrast and distinctness | Text reaches 4 5 to 1 on every layer [light] | Pass |
| TC-387 | Unit | Design tokens: contrast and distinctness | Text reaches 4 5 to 1 on every layer [dark] | Pass |
| TC-388 | Unit | Design tokens: contrast and distinctness | Alert text reaches 4 5 to 1 on its tint [light] | Pass |
| TC-389 | Unit | Design tokens: contrast and distinctness | Alert text reaches 4 5 to 1 on its tint [dark] | Pass |
| TC-390 | Unit | Design tokens: contrast and distinctness | Buttons edges and chart marks reach 3 to 1 [light] | Pass |
| TC-391 | Unit | Design tokens: contrast and distinctness | Buttons edges and chart marks reach 3 to 1 [dark] | Pass |
| TC-392 | Unit | Design tokens: contrast and distinctness | Every topic slot has its own colour [light] | Pass |
| TC-393 | Unit | Design tokens: contrast and distinctness | Every topic slot has its own colour [dark] | Pass |
| TC-394 | Unit | Design tokens: contrast and distinctness | Status and primary colours stay away from topic colours [light] | Pass |
| TC-395 | Unit | Design tokens: contrast and distinctness | Status and primary colours stay away from topic colours [dark] | Pass |
| TC-396 | Unit | Design tokens: contrast and distinctness | Neutral chart marks read in both schemes | Pass |
| TC-397 | Unit | Design tokens: contrast and distinctness | The threshold rejects the old amber accent | Pass |
| TC-398 | Unit | Design tokens: contrast and distinctness | Quiz outcome colours read in both schemes and differ | Pass |
| TC-399 | Unit | Design tokens: contrast and distinctness | Fonts are self hosted woff2 files with their licences | Pass |
| TC-400 | Unit | Design tokens: contrast and distinctness | Type scale keeps text legible at a distance | Pass |
| TC-401 | Unit | Design tokens: contrast and distinctness | Sequential ramp runs away from the background [light] | Pass |
| TC-402 | Unit | Design tokens: contrast and distinctness | Sequential ramp runs away from the background [dark] | Pass |
| TC-403 | Unit | Design tokens: contrast and distinctness | Stylesheet is small and targets only data testids | Pass |
| TC-404 | Unit | Design tokens: contrast and distinctness | Brand svgs are self contained and on palette [mark.svg] | Pass |
| TC-405 | Unit | Design tokens: contrast and distinctness | Brand svgs are self contained and on palette [wordmark.svg] | Pass |
| TC-406 | Unit | Design tokens: contrast and distinctness | Brand colour reads on every background | Pass |
| TC-407 | Unit | Design tokens: contrast and distinctness | A selected pill uses the readable teal text | Pass |
| TC-408 | Unit | Chart builders: encodings and theme | Weakness bars run weakest first in topic colours | Pass |
| TC-409 | Unit | Chart builders: encodings and theme | Weakness bars take an optional takeaway title | Pass |
| TC-410 | Unit | Chart builders: encodings and theme | Minutes shift is a dumbbell from grey to topic colour | Pass |
| TC-411 | Unit | Chart builders: encodings and theme | Readiness ring fills the score in the brand teal | Pass |
| TC-412 | Unit | Chart builders: encodings and theme | Shared theme sets fonts and drops the frame | Pass |
| TC-413 | Unit | Chart builders: encodings and theme | View specs are the charts as plain vega lite without altairs size default | Pass |
| TC-414 | Unit | Chart builders: encodings and theme | Cached specs hand out fresh copies | Pass |
| TC-415 | Unit | Chart builders: encodings and theme | Score spark draws one topic in its colour without axes | Pass |
| TC-416 | Unit | Chart builders: encodings and theme | Week mix stacks topics in order per week | Pass |
| TC-417 | Unit | Chart builders: encodings and theme | Interview trend is a 0 to 5 line in the brand teal | Pass |
| TC-418 | Unit | Chart builders: encodings and theme | Readiness trend is a 0 to 100 line per profile | Pass |
| TC-419 | Unit | Chart builders: encodings and theme | Dashboard specs match their charts | Pass |
| TC-420 | Unit | Chart builders: encodings and theme | Activity heatmap is a 12 week calendar with neutral empty days | Pass |
| TC-421 | Unit | Chart builders: encodings and theme | Outcome bars stack correct wrong and skipped in fixed colours | Pass |
| TC-422 | Unit | Chart builders: encodings and theme | Accuracy grid is a topic by difficulty heatmap | Pass |
| TC-423 | Unit | Chart builders: encodings and theme | Ats trend is a 0 to 100 line per version | Pass |
| TC-424 | Unit | CI workflow settings | Ci token can only read the repository | Pass |
| TC-425 | Unit | Demo tunnel settings | Config toml keeps cors and xsrf protection on | Pass |
| TC-426 | Unit | Demo tunnel settings | Tunnel script lifts the checks on the command line | Pass |
| TC-427 | Unit | Demo tunnel settings | Tunnel bat runs the powershell script | Pass |
| TC-428 | Unit | Summary PDF builder | Quotes the evaluation numbers | Pass |
| TC-429 | Unit | Summary PDF builder | Facts come from the code | Pass |
| TC-430 | Unit | Summary PDF builder | Names the topics when the duplicate run stopped early | Pass |
| TC-431 | Unit | Summary PDF builder | Leaves out what was not measured | Pass |
| TC-432 | Unit | Summary PDF builder | Refuses a mock or incomplete summary [changes0-mock run] | Pass |
| TC-433 | Unit | Summary PDF builder | Refuses a mock or incomplete summary [changes1-both systems] | Pass |
| TC-434 | Unit | Summary PDF builder | Topic names are escaped | Pass |
| TC-435 | Unit | Summary PDF builder | Fonts and mark are embedded so nothing is fetched | Pass |
| TC-436 | Unit | Summary PDF builder | Percentages drop trailing zeros [0.65-0-65%] | Pass |
| TC-437 | Unit | Summary PDF builder | Percentages drop trailing zeros [1.0-0-100%] | Pass |
| TC-438 | Unit | Summary PDF builder | Percentages drop trailing zeros [0.053-1-5.3%] | Pass |
| TC-439 | Unit | Summary PDF builder | Percentages drop trailing zeros [0.0-1-0%] | Pass |
| TC-440 | Unit | Summary PDF builder | Percentages drop trailing zeros [0.25-1-25%] | Pass |
| TC-441 | Unit | ATS resume builder and PDF compilation | List domains | Pass |
| TC-442 | Unit | ATS resume builder and PDF compilation | Roles for domain | Pass |
| TC-443 | Unit | ATS resume builder and PDF compilation | Get role info | Pass |
| TC-444 | Unit | ATS resume builder and PDF compilation | Build ats resume data and eval | Pass |
| TC-445 | Unit | ATS resume builder and PDF compilation | Generate ats pdf | Pass |
| TC-446 | Unit | ATS resume builder and PDF compilation | Generate candidate id and onboard | Pass |
| TC-447 | Unit | ATS resume builder and PDF compilation | The builder invents no skills projects certificates or education | Pass |
| TC-448 | Unit | ATS resume builder and PDF compilation | The builder keeps entered projects certificates and the raw form | Pass |
| TC-449 | Unit | ATS resume builder and PDF compilation | Ats keywords match whole words only | Pass |
| TC-450 | Unit | ATS resume builder and PDF compilation | Ats completeness counts filled sections | Pass |
| TC-451 | Unit | ATS resume builder and PDF compilation | The pdf survives typography and symbols the core font lacks | Pass |
| TC-452 | Unit | ATS resume builder and PDF compilation | Resume text has every section for the profile agent | Pass |
| TC-453 | Unit | ATS resume builder and PDF compilation | Diff lists what changed between versions | Pass |
| TC-454 | Unit | ATS resume builder and PDF compilation | Parse month reads common formats [2024-06-ym0] | Pass |
| TC-455 | Unit | ATS resume builder and PDF compilation | Parse month reads common formats [06/2024-ym1] | Pass |
| TC-456 | Unit | ATS resume builder and PDF compilation | Parse month reads common formats [Jun 2024-ym2] | Pass |
| TC-457 | Unit | ATS resume builder and PDF compilation | Parse month reads common formats [September 2023-ym3] | Pass |
| TC-458 | Unit | ATS resume builder and PDF compilation | Parse month reads common formats [2025-ym4] | Pass |
| TC-459 | Unit | ATS resume builder and PDF compilation | Parse month reads common formats [Junk 2024-None] | Pass |
| TC-460 | Unit | ATS resume builder and PDF compilation | Parse month reads common formats [2024-13-None] | Pass |
| TC-461 | Unit | ATS resume builder and PDF compilation | Parse month reads common formats [-None] | Pass |
| TC-462 | Unit | ATS resume builder and PDF compilation | Experience months merge overlaps and keep internships apart | Pass |
| TC-463 | Unit | ATS resume builder and PDF compilation | Entries build the resume and years come from the dates | Pass |
| TC-464 | Unit | ATS resume builder and PDF compilation | A version saved before entry lists still reads | Pass |
| TC-465 | Unit | ATS resume builder and PDF compilation | Text pdf and diff cover work and education | Pass |
| TC-466 | Unit | ATS resume builder and PDF compilation | Ats reads job bullets and checks the degree rule | Pass |
| TC-467 | Unit | Evaluation scorecard parameters and ratings | Rating thresholds [10.0-Excellent-done] | Pass |
| TC-468 | Unit | Evaluation scorecard parameters and ratings | Rating thresholds [9.0-Excellent-done] | Pass |
| TC-469 | Unit | Evaluation scorecard parameters and ratings | Rating thresholds [7.5-Good-done] | Pass |
| TC-470 | Unit | Evaluation scorecard parameters and ratings | Rating thresholds [5.0-Fair-warning] | Pass |
| TC-471 | Unit | Evaluation scorecard parameters and ratings | Rating thresholds [4.9-Needs work-error] | Pass |
| TC-472 | Unit | Evaluation scorecard parameters and ratings | Rating thresholds [None-Not measured-todo] | Pass |
| TC-473 | Unit | Evaluation scorecard parameters and ratings | Answer key balance is 1 when even and 0 when one position | Pass |
| TC-474 | Unit | Evaluation scorecard parameters and ratings | Longest answer cue counts only a strictly longest correct option | Pass |
| TC-475 | Unit | Evaluation scorecard parameters and ratings | Human validity needs labels | Pass |
| TC-476 | Unit | Evaluation scorecard parameters and ratings | First draft validity counts cases valid on attempt one | Pass |
| TC-477 | Unit | Evaluation scorecard parameters and ratings | Followup precision is the judges agreement with the flags | Pass |
| TC-478 | Unit | Evaluation scorecard parameters and ratings | Cost per valid quiz counts critic share retries and validity | Pass |
| TC-479 | Unit | Evaluation scorecard parameters and ratings | Build scores every measured parameter and skips the rest | Pass |
| TC-480 | Unit | Evaluation scorecard parameters and ratings | Weak focus scores the share between 25 and 75 percent | Pass |
| TC-481 | Unit | Evaluation scorecard parameters and ratings | Overall is a weighted mean and head to head drops one sided parameters | Pass |
| TC-482 | Unit | Degrees and the roles they qualify for | The list runs from school to doctorate with unique codes | Pass |
| TC-483 | Unit | Degrees and the roles they qualify for | Parse reads the degree a line names [B.E. in Electronics & Communication, 2026-B.E] | Pass |
| TC-484 | Unit | Degrees and the roles they qualify for | Parse reads the degree a line names [BTech CSE-B.Tech] | Pass |
| TC-485 | Unit | Degrees and the roles they qualify for | Parse reads the degree a line names [Pursuing M.E in VLSI-M.E] | Pass |
| TC-486 | Unit | Degrees and the roles they qualify for | Parse reads the degree a line names [Bachelor of Commerce-B.Com] | Pass |
| TC-487 | Unit | Degrees and the roles they qualify for | Parse reads the degree a line names [II PUC (Science)-Class 12] | Pass |
| TC-488 | Unit | Degrees and the roles they qualify for | Parse reads the degree a line names [BA LLB, 2024-BA LL.B] | Pass |
| TC-489 | Unit | Degrees and the roles they qualify for | Parse reads the degree a line names [MCA-MCA] | Pass |
| TC-490 | Unit | Degrees and the roles they qualify for | Two letter codes count only in capitals | Pass |
| TC-491 | Unit | Degrees and the roles they qualify for | Groups expand and any graduate skips school and diplomas | Pass |
| TC-492 | Unit | Degrees and the roles they qualify for | A role with fields needs a matching branch | Pass |
| TC-493 | Unit | Degrees and the roles they qualify for | A degree names its own field | Pass |
| TC-494 | Unit | Degrees and the roles they qualify for | Completed beats pursuing and pursuing opens on completion | Pass |
| TC-495 | Unit | Degrees and the roles they qualify for | Roles for lists open roles first across domains | Pass |
| TC-496 | Unit | Degrees and the roles they qualify for | Entry label reads naturally | Pass |
| TC-497 | Unit | Degrees and the roles they qualify for | Every catalog role has a valid degree rule | Pass |
| TC-498 | Integration | Local question bank and its share of quizzes | Every mapped topic is a syllabus topic | Pass |
| TC-499 | Integration | Local question bank and its share of quizzes | No bank file means an empty bank | Pass |
| TC-500 | Integration | Local question bank and its share of quizzes | Only valid distinct mapped questions load | Pass |
| TC-501 | Integration | Local question bank and its share of quizzes | Draw is reproducible avoids seen text and maps the answer | Pass |
| TC-502 | Integration | Local question bank and its share of quizzes | A quiz part takes a share from the bank after the generated questions | Pass |
| TC-503 | Integration | Local question bank and its share of quizzes | A one question part is always generated | Pass |
| TC-504 | Integration | HTTP API for the Next.js frontend | Catalog lists every domain role and degree | Pass |
| TC-505 | Integration | HTTP API for the Next.js frontend | Roles for degree | Pass |
| TC-506 | Integration | HTTP API for the Next.js frontend | A quiz comes from the bank without answers and is graded on submit | Pass |
| TC-507 | Integration | HTTP API for the Next.js frontend | A candidates quiz is saved and moves their weakness | Pass |
| TC-508 | Integration | HTTP API for the Next.js frontend | Quiz errors are 400s | Pass |
| TC-509 | Integration | HTTP API for the Next.js frontend | Plan and dashboard | Pass |
| TC-510 | Integration | HTTP API for the Next.js frontend | Interview tracks follow the domain and the degree | Pass |
| TC-511 | Integration | HTTP API for the Next.js frontend | An interview streams steps then the approved question | Pass |
| TC-512 | Integration | HTTP API for the Next.js frontend | An interview error arrives as an event | Pass |
| TC-513 | Integration | HTTP API for the Next.js frontend | Resume ats and pdf | Pass |
| TC-514 | Integration | HTTP API for the Next.js frontend | Enhance bullet rewrites without inventing numbers | Pass |
| TC-515 | Integration | HTTP API for the Next.js frontend | Check bullet rejects invented numbers | Pass |
| TC-516 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Software Engineer] | Pass |
| TC-517 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Data Scientist] | Pass |
| TC-518 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Frontend Engineer] | Pass |
| TC-519 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Backend Developer] | Pass |
| TC-520 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Full Stack Developer] | Pass |
| TC-521 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [DevOps & Cloud Engineer] | Pass |
| TC-522 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Data Analyst & BI Specialist] | Pass |
| TC-523 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Machine Learning / AI Engineer] | Pass |
| TC-524 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Cybersecurity Analyst] | Pass |
| TC-525 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Database Administrator (DBA)] | Pass |
| TC-526 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Mobile App Developer] | Pass |
| TC-527 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [QA & Test Automation Engineer] | Pass |
| TC-528 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Site Reliability Engineer (SRE)] | Pass |
| TC-529 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [VLSI & Chip Design Engineer] | Pass |
| TC-530 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Embedded Systems & Firmware Engineer] | Pass |
| TC-531 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Embedded Software Engineer] | Pass |
| TC-532 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [IoT & Edge Hardware Engineer] | Pass |
| TC-533 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Robotics & Control Systems Engineer] | Pass |
| TC-534 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Signal Processing Engineer] | Pass |
| TC-535 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Telecommunications & RF Engineer] | Pass |
| TC-536 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Automotive & EV Systems Engineer] | Pass |
| TC-537 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [CAD/CAM & Product Design Engineer] | Pass |
| TC-538 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Manufacturing & Production Engineer] | Pass |
| TC-539 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Robotics & Mechatronics Engineer] | Pass |
| TC-540 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Thermal & HVAC Design Engineer] | Pass |
| TC-541 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Structural Design Engineer] | Pass |
| TC-542 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Construction Project Manager] | Pass |
| TC-543 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Geotechnical & Foundation Engineer] | Pass |
| TC-544 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Transportation & Highway Engineer] | Pass |
| TC-545 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Water Resources & Environmental Engineer] | Pass |
| TC-546 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Industrial Automation & PLC Engineer] | Pass |
| TC-547 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [EV Powertrain & Battery Engineer] | Pass |
| TC-548 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Power Systems & Grid Engineer] | Pass |
| TC-549 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Renewable Energy Systems Engineer] | Pass |
| TC-550 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Bioinformatics Analyst] | Pass |
| TC-551 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Biomedical Instrumentation Engineer] | Pass |
| TC-552 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Bioprocess / Fermentation Engineer] | Pass |
| TC-553 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Clinical Research Associate (CRA)] | Pass |
| TC-554 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Hospital Operations Administrator] | Pass |
| TC-555 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Clinical Pharmacist] | Pass |
| TC-556 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [General Medical Officer (Resident Doctor)] | Pass |
| TC-557 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Medical Lab Technologist (MLT)] | Pass |
| TC-558 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Public Health Program Coordinator] | Pass |
| TC-559 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Corporate Legal Counsel] | Pass |
| TC-560 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Financial Analyst] | Pass |
| TC-561 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Digital Marketing & Brand Strategist] | Pass |
| TC-562 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Human Resources (HR) Specialist] | Pass |
| TC-563 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Product Manager] | Pass |
| TC-564 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Supply Chain & Logistics Specialist] | Pass |
| TC-565 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [UPSC Civil Services Aspirant] | Pass |
| TC-566 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Public Sector Bank PO (SBI / IBPS)] | Pass |
| TC-567 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [DRDO / ISRO Scientist-Engineer] | Pass |
| TC-568 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Defense Accounts & Audit Officer (CAG/DAD)] | Pass |
| TC-569 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Railway Recruitment Board (RRB) SSE] | Pass |
| TC-570 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [SSC CGL Assistant Section Officer (ASO)] | Pass |
| TC-571 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [State Administrative Officer (KAS / PCS)] | Pass |
| TC-572 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Assistant Engineer (PWD / Irrigation)] | Pass |
| TC-573 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Commercial Tax / Revenue Inspector] | Pass |
| TC-574 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [Panchayat Development Officer (PDO)] | Pass |
| TC-575 | Integration | Every role and domain, resume to interview | A role works from resume to readiness [State Police Sub-Inspector (PSI / DySP)] | Pass |
| TC-576 | Integration | Every role and domain, resume to interview | A domain gets a plan instant quizzes and five interview tracks [cs] | Pass |
| TC-577 | Integration | Every role and domain, resume to interview | A domain gets a plan instant quizzes and five interview tracks [ece] | Pass |
| TC-578 | Integration | Every role and domain, resume to interview | A domain gets a plan instant quizzes and five interview tracks [mech] | Pass |
| TC-579 | Integration | Every role and domain, resume to interview | A domain gets a plan instant quizzes and five interview tracks [civil] | Pass |
| TC-580 | Integration | Every role and domain, resume to interview | A domain gets a plan instant quizzes and five interview tracks [eee] | Pass |
| TC-581 | Integration | Every role and domain, resume to interview | A domain gets a plan instant quizzes and five interview tracks [biotech] | Pass |
| TC-582 | Integration | Every role and domain, resume to interview | A domain gets a plan instant quizzes and five interview tracks [health] | Pass |
| TC-583 | Integration | Every role and domain, resume to interview | A domain gets a plan instant quizzes and five interview tracks [corp] | Pass |
| TC-584 | Integration | Every role and domain, resume to interview | A domain gets a plan instant quizzes and five interview tracks [govt_central] | Pass |
| TC-585 | Integration | Every role and domain, resume to interview | A domain gets a plan instant quizzes and five interview tracks [govt_state] | Pass |
| TC-586 | System (UI) | Streamlit pages, headless | A page render never repeats a query [views/onboard.py] | Pass |
| TC-587 | System (UI) | Streamlit pages, headless | A page render never repeats a query [views/plan.py] | Pass |
| TC-588 | System (UI) | Streamlit pages, headless | A page render never repeats a query [views/quiz.py] | Pass |
| TC-589 | System (UI) | Streamlit pages, headless | A page render never repeats a query [views/interview.py] | Pass |
| TC-590 | System (UI) | Streamlit pages, headless | A page render never repeats a query [views/dashboard.py] | Pass |
| TC-591 | System (UI) | Streamlit pages, headless | A page render never repeats a query [views/results.py] | Pass |
| TC-592 | System (UI) | Streamlit pages, headless | Onboard prefills the selected students usn | Pass |
| TC-593 | System (UI) | Streamlit pages, headless | Design system components render | Pass |
| TC-594 | System (UI) | Streamlit pages, headless | Navigation groups pages with material icons | Pass |
| TC-595 | System (UI) | Streamlit pages, headless | Sidebar shows readiness and a quiet mock badge | Pass |
| TC-596 | System (UI) | Streamlit pages, headless | Onboard with sample resume | Pass |
| TC-597 | System (UI) | Streamlit pages, headless | Onboard without a student explains what happens next | Pass |
| TC-598 | System (UI) | Streamlit pages, headless | Onboard profile shows readiness skills and fixes | Pass |
| TC-599 | System (UI) | Streamlit pages, headless | Onboard reprofile without a resume shows the error | Pass |
| TC-600 | System (UI) | Streamlit pages, headless | Onboarding a usn that is taken asks before replacing that student | Pass |
| TC-601 | System (UI) | Streamlit pages, headless | Reprofiling the selected student closes their open quiz and interview | Pass |
| TC-602 | System (UI) | Streamlit pages, headless | Reprofiling the selected student needs no confirmation | Pass |
| TC-603 | System (UI) | Streamlit pages, headless | Deleting a student needs their usn then returns home | Pass |
| TC-604 | System (UI) | Streamlit pages, headless | Onboard rejects missing usn | Pass |
| TC-605 | System (UI) | Streamlit pages, headless | Pages require a student [views/plan.py] | Pass |
| TC-606 | System (UI) | Streamlit pages, headless | Pages require a student [views/quiz.py] | Pass |
| TC-607 | System (UI) | Streamlit pages, headless | Pages require a student [views/interview.py] | Pass |
| TC-608 | System (UI) | Streamlit pages, headless | Pages require a student [views/dashboard.py] | Pass |
| TC-609 | System (UI) | Streamlit pages, headless | The empty state points to the sidebar when students exist | Pass |
| TC-610 | System (UI) | Streamlit pages, headless | Plan generates next week and compares | Pass |
| TC-611 | System (UI) | Streamlit pages, headless | Plan shows the latest week day by day with why and the shift | Pass |
| TC-612 | System (UI) | Streamlit pages, headless | Plan week one has no shift and table view shows the table | Pass |
| TC-613 | System (UI) | Streamlit pages, headless | Plan days marked done are saved and counted on home and dashboard | Pass |
| TC-614 | System (UI) | Streamlit pages, headless | Plan week exports as calendar and table | Pass |
| TC-615 | System (UI) | Streamlit pages, headless | Plan export files are built only when downloaded | Pass |
| TC-616 | System (UI) | Streamlit pages, headless | Plan without a plan yet invites week one | Pass |
| TC-617 | System (UI) | Streamlit pages, headless | Quiz generate answer and review | Pass |
| TC-618 | System (UI) | Streamlit pages, headless | Quiz setup offers the syllabus counts and a mix that adds to 100 | Pass |
| TC-619 | System (UI) | Streamlit pages, headless | Quiz over several topics caps the total | Pass |
| TC-620 | System (UI) | Streamlit pages, headless | Quiz review shows a score card breakdowns and mistakes | Pass |
| TC-621 | System (UI) | Streamlit pages, headless | Quiz with blank answers asks before submitting | Pass |
| TC-622 | System (UI) | Streamlit pages, headless | Critic log numbers questions like the quiz | Pass |
| TC-623 | System (UI) | Streamlit pages, headless | Quiz text and options are shown literally | Pass |
| TC-624 | System (UI) | Streamlit pages, headless | Interview answer is shown literally | Pass |
| TC-625 | System (UI) | Streamlit pages, headless | Interview session runs to completion | Pass |
| TC-626 | System (UI) | Streamlit pages, headless | Interview setup describes each type | Pass |
| TC-627 | System (UI) | Streamlit pages, headless | Interview shows progress scored feedback and the critic trail | Pass |
| TC-628 | System (UI) | Streamlit pages, headless | Dashboard renders | Pass |
| TC-629 | System (UI) | Streamlit pages, headless | Dashboard readiness shows a delta and trend only after a second profile | Pass |
| TC-630 | System (UI) | Streamlit pages, headless | Dashboard keeps system telemetry in its own section | Pass |
| TC-631 | System (UI) | Streamlit pages, headless | Dashboard for a new student explains each empty section | Pass |
| TC-632 | System (UI) | Streamlit pages, headless | Dashboard error state offers a retry | Pass |
| TC-633 | System (UI) | Streamlit pages, headless | Onboard requires a resume or sample | Pass |
| TC-634 | System (UI) | Streamlit pages, headless | Onboarding another student drops the previous students session | Pass |
| TC-635 | System (UI) | Streamlit pages, headless | Failed follow up offers retry without reanswering | Pass |
| TC-636 | System (UI) | Streamlit pages, headless | Failed quiz generation stays visible | Pass |
| TC-637 | System (UI) | Streamlit pages, headless | Results page without and with results | Pass |
| TC-638 | System (UI) | Streamlit pages, headless | Results note mentions the duplicate rate only when it is shown | Pass |
| TC-639 | System (UI) | Streamlit pages, headless | Seed demo fills an empty database on start | Pass |
| TC-640 | System (UI) | Streamlit pages, headless | Home without a student explains the loop | Pass |
| TC-641 | System (UI) | Streamlit pages, headless | Home quick start opens onboard with a sample | Pass |
| TC-642 | System (UI) | Streamlit pages, headless | Home shows todays focus for the demo student | Pass |
| TC-643 | System (UI) | Streamlit pages, headless | Todays focus opens the page it names | Pass |
| TC-644 | System (UI) | Streamlit pages, headless | Todays focus preselects the quiz topic | Pass |
| TC-645 | System (UI) | Streamlit pages, headless | Home error state offers a retry | Pass |
| TC-646 | System (UI) | Streamlit pages, headless | An ece students home and quiz show electronics topics | Pass |
| TC-647 | System (UI) | Streamlit pages, headless | Project space is in the navigation for computing domains only | Pass |
| TC-648 | System (UI) | Streamlit pages, headless | Project space creates a repository and logs work | Pass |
| TC-649 | System (UI) | Streamlit pages, headless | Project space shows a bad link as an error | Pass |
| TC-650 | System (UI) | Streamlit pages, headless | Resume builder starts empty for a new student | Pass |
| TC-651 | System (UI) | Streamlit pages, headless | Resume builder saves versions and locks the domain | Pass |
| TC-652 | System (UI) | Streamlit pages, headless | Resume builder finds roles by degree and lists jobs | Pass |
