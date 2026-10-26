# Test report

Generated 2026-10-26 01:57 UTC by `python -m scripts.test_report` from a real run of the suite (offline: MOCK_MODE, temporary databases, fake Groq clients for live code paths).

**402 tests: 402 passed, 0 failed, 0 skipped** (179 s of test time).

## By module

| Type | Area | Module | Tests | Passed |
|---|---|---|---|---|
| Unit | Settings and environment | `test_config` | 8 | 8 |
| Unit | Pydantic output schemas | `test_schemas` | 10 | 10 |
| Unit | Deterministic critic rules | `test_checks` | 18 | 18 |
| Unit | SQLite repository | `test_db` | 13 | 13 |
| Unit | LLM gateway (fake Groq client) | `test_llm` | 12 | 12 |
| Unit | LangGraph critic loop | `test_graph` | 7 | 7 |
| Unit | Resume parsing | `test_resume` | 16 | 16 |
| Unit | Output layer | `test_formatter` | 81 | 81 |
| Integration | Agents through the critic loop | `test_agents` | 34 | 34 |
| Integration | User flows through the service layer | `test_services` | 57 | 57 |
| Integration | Demo seed data | `test_seed` | 3 | 3 |
| Integration | Evaluation harness | `test_eval` | 12 | 12 |
| Integration | Results report | `test_report` | 3 | 3 |
| Integration | Model availability check | `test_check_models` | 5 | 5 |
| Integration | Graph export | `test_export_graph` | 2 | 2 |
| Integration | Test report generator | `test_test_report` | 2 | 2 |
| Unit | Screenshot tool helpers | `test_screenshots` | 12 | 12 |
| Unit | Performance tool helpers | `test_perf` | 8 | 8 |
| Unit | Design tokens: contrast and distinctness | `test_theme` | 23 | 23 |
| Unit | Chart builders: encodings and theme | `test_charts` | 13 | 13 |
| Unit | CI workflow settings | `test_ci` | 1 | 1 |
| Unit | Demo tunnel settings | `test_tunnel` | 3 | 3 |
| System (UI) | Streamlit pages, headless | `test_ui` | 59 | 59 |

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
| TC-045 | Unit | SQLite repository | Agent stats count failed calls apart from rejections | Pass |
| TC-046 | Unit | SQLite repository | Past turns exclude current session newest first | Pass |
| TC-047 | Unit | SQLite repository | Delete student cascades to all history | Pass |
| TC-048 | Unit | SQLite repository | Agent log marking and stats | Pass |
| TC-049 | Unit | SQLite repository | Plan progress marks days and joins onto the plans | Pass |
| TC-050 | Unit | LLM gateway (fake Groq client) | Mock mode repairs invalid output once | Pass |
| TC-051 | Unit | LLM gateway (fake Groq client) | Mock mode raises after second invalid output | Pass |
| TC-052 | Unit | LLM gateway (fake Groq client) | Model for maps sizes | Pass |
| TC-053 | Unit | LLM gateway (fake Groq client) | Live request shape and logging | Pass |
| TC-054 | Unit | LLM gateway (fake Groq client) | Live repair feeds validation error back and sums tokens | Pass |
| TC-055 | Unit | LLM gateway (fake Groq client) | Live json validate failed is repairable | Pass |
| TC-056 | Unit | LLM gateway (fake Groq client) | Live failed call is logged with its tokens and latency | Pass |
| TC-057 | Unit | LLM gateway (fake Groq client) | Live other bad request raises | Pass |
| TC-058 | Unit | LLM gateway (fake Groq client) | Live unknown model gives actionable error | Pass |
| TC-059 | Unit | LLM gateway (fake Groq client) | Live server error is wrapped | Pass |
| TC-060 | Unit | LLM gateway (fake Groq client) | Live rate limit carries retry after | Pass |
| TC-061 | Unit | LLM gateway (fake Groq client) | Live rate limit without hint | Pass |
| TC-062 | Unit | LangGraph critic loop | Loop retries then approves and reports events | Pass |
| TC-063 | Unit | LangGraph critic loop | Loop stops after retry budget | Pass |
| TC-064 | Unit | LangGraph critic loop | Zero retry budget means single attempt | Pass |
| TC-065 | Unit | LangGraph critic loop | Retry receives previous rejection reasons | Pass |
| TC-066 | Unit | LangGraph critic loop | Every attempt is marked in agent logs | Pass |
| TC-067 | Unit | LangGraph critic loop | A verify that raises marks the attempt failed | Pass |
| TC-068 | Unit | LangGraph critic loop | Compiled graph is cached per task and exports mermaid | Pass |
| TC-069 | Unit | Resume parsing | Txt and uppercase extension | Pass |
| TC-070 | Unit | Resume parsing | Docx paragraphs and tables | Pass |
| TC-071 | Unit | Resume parsing | Pdf text is extracted | Pass |
| TC-072 | Unit | Resume parsing | Pdf without text layer is rejected | Pass |
| TC-073 | Unit | Resume parsing | Bad input is rejected [png] | Pass |
| TC-074 | Unit | Resume parsing | Bad input is rejected [no-extension] | Pass |
| TC-075 | Unit | Resume parsing | Bad input is rejected [too-short] | Pass |
| TC-076 | Unit | Resume parsing | Bad input is rejected [too-large] | Pass |
| TC-077 | Unit | Resume parsing | Damaged pdf is rejected with a message [garbage] | Pass |
| TC-078 | Unit | Resume parsing | Damaged pdf is rejected with a message [truncated] | Pass |
| TC-079 | Unit | Resume parsing | Damaged docx is rejected with a message | Pass |
| TC-080 | Unit | Resume parsing | Password protected pdf says so | Pass |
| TC-081 | Unit | Resume parsing | Pdf locked only against editing still reads | Pass |
| TC-082 | Unit | Resume parsing | Password protected docx says so | Pass |
| TC-083 | Unit | Resume parsing | Docx that unpacks past 25 mb is rejected before parsing | Pass |
| TC-084 | Unit | Resume parsing | Only the first 30 pdf pages are read | Pass |
| TC-085 | Unit | Output layer | Profile pieces show counts and handle empty sections | Pass |
| TC-086 | Unit | Output layer | Plan table is ordered by day | Pass |
| TC-087 | Unit | Output layer | Plan minutes has every topic and one column per week | Pass |
| TC-088 | Unit | Output layer | Plan summary totals the week and names its main topic | Pass |
| TC-089 | Unit | Output layer | Plan csv has the table columns and one row per day | Pass |
| TC-090 | Unit | Output layer | Next monday is the coming monday [2026-10-19-2026-10-19] | Pass |
| TC-091 | Unit | Output layer | Next monday is the coming monday [2026-10-20-2026-10-26] | Pass |
| TC-092 | Unit | Output layer | Next monday is the coming monday [2026-10-25-2026-10-26] | Pass |
| TC-093 | Unit | Output layer | Plan ics is a calendar with one event per day | Pass |
| TC-094 | Unit | Output layer | Plan ics escapes text and folds long lines | Pass |
| TC-095 | Unit | Output layer | Plan days html lists every day in order with its topic chip | Pass |
| TC-096 | Unit | Output layer | Plan days html marks done days in words | Pass |
| TC-097 | Unit | Output layer | Plan days html escapes model text [<script>alert(1)</script>] | Pass |
| TC-098 | Unit | Output layer | Plan days html escapes model text ["><img src=x onerror=alert(1)>] | Pass |
| TC-099 | Unit | Output layer | Minutes shift headline states the change [before0-after0-OS now gets the most minutes] | Pass |
| TC-100 | Unit | Output layer | Minutes shift headline states the change [before1-after1-OS gets 240 more minutes and DBMS 360 fewer than in week 3] | Pass |
| TC-101 | Unit | Output layer | Minutes shift headline states the change [before2-after2-CN gets 60 more minutes than in week 3] | Pass |
| TC-102 | Unit | Output layer | Minutes shift headline states the change [before3-after3-DBMS gets 360 fewer minutes than in week 3] | Pass |
| TC-103 | Unit | Output layer | Minutes shift headline states the change [before4-after4-The same minutes per topic as in week 3] | Pass |
| TC-104 | Unit | Output layer | Minutes shift alt reads every topic | Pass |
| TC-105 | Unit | Output layer | Weakness source explains both inputs | Pass |
| TC-106 | Unit | Output layer | Quiz review marks right wrong and unanswered with icon and word | Pass |
| TC-107 | Unit | Output layer | Blanks md names the unanswered questions | Pass |
| TC-108 | Unit | Output layer | Quiz setup lines explain the hint and the suggestion | Pass |
| TC-109 | Unit | Output layer | Result md says what the score changes [easy-medium-trending_up] | Pass |
| TC-110 | Unit | Output layer | Result md says what the score changes [hard-hard-trending_flat] | Pass |
| TC-111 | Unit | Output layer | Result md says what the score changes [hard-medium-trending_down] | Pass |
| TC-112 | Unit | Output layer | Md escape shows text literally [*p-\\*p] | Pass |
| TC-113 | Unit | Output layer | Md escape shows text literally [__init__-\\_\\_init\\_\\_] | Pass |
| TC-114 | Unit | Output layer | Md escape shows text literally [![x](http://example.com/a.png)-\\!\\[x\\]\\(http://example\\.com/a\\.png\\)] | Pass |
| TC-115 | Unit | Output layer | Md escape shows text literally [<script>alert(1)</script>-\\<script\\>alert\\(1\\)\\</script\\>] | Pass |
| TC-116 | Unit | Output layer | Md escape shows text literally [Costs $5 to $10-Costs \\$5 to \\$10] | Pass |
| TC-117 | Unit | Output layer | Md escape shows text literally [# 1. ----\\# 1\\. \\-\\-\\-] | Pass |
| TC-118 | Unit | Output layer | Md escape keeps code readable | Pass |
| TC-119 | Unit | Output layer | Topic chip follows the scheme and escapes its name | Pass |
| TC-120 | Unit | Output layer | Status pairs an icon with escaped words | Pass |
| TC-121 | Unit | Output layer | Critic text numbers questions like the quiz [critic rejected quiz: question 0: options are not distinct-critic rejected quiz: Q1:] | Pass |
| TC-122 | Unit | Output layer | Critic text numbers questions like the quiz [quiz: rejected after retries: question 3: a; question 11: b-Q4: a; Q12: b] | Pass |
| TC-123 | Unit | Output layer | Critic text numbers questions like the quiz [critic rejected interviewer: question already asked: "x"-question already asked] | Pass |
| TC-124 | Unit | Output layer | Critic text is escaped | Pass |
| TC-125 | Unit | Output layer | Markdown builders escape every dynamic value [*p] | Pass |
| TC-126 | Unit | Output layer | Markdown builders escape every dynamic value [__init__] | Pass |
| TC-127 | Unit | Output layer | Markdown builders escape every dynamic value [![x](http://example.com/a.png)] | Pass |
| TC-128 | Unit | Output layer | Markdown builders escape every dynamic value [<script>alert(1)</script>] | Pass |
| TC-129 | Unit | Output layer | Criteria html escapes criterion names [<script>alert(1)</script>] | Pass |
| TC-130 | Unit | Output layer | Criteria html escapes criterion names ["><img src=x onerror=alert(1)>] | Pass |
| TC-131 | Unit | Output layer | Quiz notes are plain markdown with every question | Pass |
| TC-132 | Unit | Output layer | Interview notes quote answers and list feedback | Pass |
| TC-133 | Unit | Output layer | Notes escape every dynamic value [*p] | Pass |
| TC-134 | Unit | Output layer | Notes escape every dynamic value [__init__] | Pass |
| TC-135 | Unit | Output layer | Notes escape every dynamic value [![x](http://example.com/a.png)] | Pass |
| TC-136 | Unit | Output layer | Notes escape every dynamic value [<script>alert(1)</script>] | Pass |
| TC-137 | Unit | Output layer | Quiz review requires one answer per question | Pass |
| TC-138 | Unit | Output layer | Feedback shows the overall score then each criterion | Pass |
| TC-139 | Unit | Output layer | A multi line model answer keeps its lines in the quote | Pass |
| TC-140 | Unit | Output layer | Session summary pieces show averages and tips | Pass |
| TC-141 | Unit | Output layer | Interview questions say whether they follow up | Pass |
| TC-142 | Unit | Output layer | Interview progress counts questions [0-True-shown0] | Pass |
| TC-143 | Unit | Output layer | Interview progress counts questions [1-False-shown1] | Pass |
| TC-144 | Unit | Output layer | Interview progress counts questions [4-True-shown2] | Pass |
| TC-145 | Unit | Output layer | Interview progress counts questions [5-False-shown3] | Pass |
| TC-146 | Unit | Output layer | Mastery words pair every trend with an icon and words | Pass |
| TC-147 | Unit | Output layer | Topic scores headline names the biggest move [scores0-OS is up from 30% to 70%] | Pass |
| TC-148 | Unit | Output layer | Topic scores headline names the biggest move [scores1-OS is down from 70% to 30%] | Pass |
| TC-149 | Unit | Output layer | Topic scores headline names the biggest move [scores2-Scores are level since your first quizzes] | Pass |
| TC-150 | Unit | Output layer | Topic scores headline names the biggest move [scores3-Take a second quiz on a topic to see it move] | Pass |
| TC-151 | Unit | Output layer | Dashboard headlines and alt text | Pass |
| TC-152 | Unit | Output layer | Telemetry tables are ready to read | Pass |
| TC-153 | Unit | Output layer | Readiness change and headline never invent a trend | Pass |
| TC-154 | Unit | Output layer | Streak and activity words | Pass |
| TC-155 | Unit | Output layer | Critic plain renumbers without escaping | Pass |
| TC-156 | Unit | Output layer | Results table includes only measured metrics | Pass |
| TC-157 | Unit | Output layer | Results markdown and caption | Pass |
| TC-158 | Unit | Output layer | Results note names the duplicate rate only with that row | Pass |
| TC-159 | Unit | Output layer | Results metrics define each rate and its direction | Pass |
| TC-160 | Unit | Output layer | Compare html draws both systems in their colours | Pass |
| TC-161 | Unit | Output layer | Results svg is well formed with one bar per measured value | Pass |
| TC-162 | Unit | Output layer | Trail tells the critic loop in order | Pass |
| TC-163 | Unit | Output layer | Trail collapses repeats and explains a stop | Pass |
| TC-164 | Unit | Output layer | Relative day uses the students calendar | Pass |
| TC-165 | Unit | Output layer | Weakness headline and alt text state the takeaway | Pass |
| TC-166 | Integration | Agents through the critic loop | Role map uses only syllabus topics | Pass |
| TC-167 | Integration | Agents through the critic loop | Profile scores are computed in code | Pass |
| TC-168 | Integration | Agents through the critic loop | Profile regenerates when a skill is invented | Pass |
| TC-169 | Integration | Agents through the critic loop | Replan shifts minutes toward low scores | Pass |
| TC-170 | Integration | Agents through the critic loop | Planner inputs carry previous week | Pass |
| TC-171 | Integration | Agents through the critic loop | Quiz avoids previous questions and records scores | Pass |
| TC-172 | Integration | Agents through the critic loop | Mock quiz demonstrates one critic rejection | Pass |
| TC-173 | Integration | Agents through the critic loop | Llm critic rejection triggers regeneration | Pass |
| TC-174 | Integration | Agents through the critic loop | Suggest difficulty [None-medium-medium] | Pass |
| TC-175 | Integration | Agents through the critic loop | Suggest difficulty [85-medium-hard] | Pass |
| TC-176 | Integration | Agents through the critic loop | Suggest difficulty [100-hard-hard] | Pass |
| TC-177 | Integration | Agents through the critic loop | Suggest difficulty [30-medium-easy] | Pass |
| TC-178 | Integration | Agents through the critic loop | Suggest difficulty [30-easy-easy] | Pass |
| TC-179 | Integration | Agents through the critic loop | Suggest difficulty [60-medium-medium] | Pass |
| TC-180 | Integration | Agents through the critic loop | Suggest difficulty [80-easy-medium] | Pass |
| TC-181 | Integration | Agents through the critic loop | Suggest difficulty [49.9-hard-medium] | Pass |
| TC-182 | Integration | Agents through the critic loop | Interview follows up on vague answers | Pass |
| TC-183 | Integration | Agents through the critic loop | Mock interview never repeats a follow up | Pass |
| TC-184 | Integration | Agents through the critic loop | Mock follow up quotes answers cleanly | Pass |
| TC-185 | Integration | Agents through the critic loop | Interview memory avoids past questions | Pass |
| TC-186 | Integration | Agents through the critic loop | Interview final turn is enforced in code | Pass |
| TC-187 | Integration | Agents through the critic loop | Answer evaluation overall is mean | Pass |
| TC-188 | Integration | Agents through the critic loop | Only flagged questions are regenerated | Pass |
| TC-189 | Integration | Agents through the critic loop | Critic judges each question once | Pass |
| TC-190 | Integration | Agents through the critic loop | Critic with one based indices is understood | Pass |
| TC-191 | Integration | Agents through the critic loop | Critic verdicts count only when their numbering is unambiguous [indices0-5] | Pass |
| TC-192 | Integration | Agents through the critic loop | Critic verdicts count only when their numbering is unambiguous [indices1-5] | Pass |
| TC-193 | Integration | Agents through the critic loop | Critic verdicts count only when their numbering is unambiguous [indices2-0] | Pass |
| TC-194 | Integration | Agents through the critic loop | Critic verdicts count only when their numbering is unambiguous [indices3-0] | Pass |
| TC-195 | Integration | Agents through the critic loop | Critic verdicts count only when their numbering is unambiguous [indices4-0] | Pass |
| TC-196 | Integration | Agents through the critic loop | Critic verdicts count only when their numbering is unambiguous [indices5-0] | Pass |
| TC-197 | Integration | Agents through the critic loop | Critic verdicts count only when their numbering is unambiguous [indices6-0] | Pass |
| TC-198 | Integration | Agents through the critic loop | Missing critic verdict counts as rejection | Pass |
| TC-199 | Integration | Agents through the critic loop | Unknown role is rejected before any llm call | Pass |
| TC-200 | Integration | User flows through the service layer | Onboard creates student and profile | Pass |
| TC-201 | Integration | User flows through the service layer | Invalid usn is rejected [] | Pass |
| TC-202 | Integration | User flows through the service layer | Invalid usn is rejected [   ] | Pass |
| TC-203 | Integration | User flows through the service layer | Invalid usn is rejected [AB1] | Pass |
| TC-204 | Integration | User flows through the service layer | Invalid usn is rejected [AB 123] | Pass |
| TC-205 | Integration | User flows through the service layer | Invalid usn is rejected [AB-123] | Pass |
| TC-206 | Integration | User flows through the service layer | Invalid usn is rejected [xxxxxxxxxxxxxxxxxxxxx] | Pass |
| TC-207 | Integration | User flows through the service layer | Invalid usn is rejected [None] | Pass |
| TC-208 | Integration | User flows through the service layer | Usn is normalised | Pass |
| TC-209 | Integration | User flows through the service layer | Onboard rejects unknown role and empty resume | Pass |
| TC-210 | Integration | User flows through the service layer | Sample list is read once | Pass |
| TC-211 | Integration | User flows through the service layer | Samples load only from the listed files | Pass |
| TC-212 | Integration | User flows through the service layer | Read resume surfaces parser errors | Pass |
| TC-213 | Integration | User flows through the service layer | Operations require an onboarded student | Pass |
| TC-214 | Integration | User flows through the service layer | Plans are numbered and adapt to quiz scores | Pass |
| TC-215 | Integration | User flows through the service layer | Quiz round trip and adaptive difficulty | Pass |
| TC-216 | Integration | User flows through the service layer | Quiz setup ranks topics and suggests from the latest attempt | Pass |
| TC-217 | Integration | User flows through the service layer | Quiz result counts correct answers and quiz key is stable | Pass |
| TC-218 | Integration | User flows through the service layer | Start quiz validates parameters [Maths-easy] | Pass |
| TC-219 | Integration | User flows through the service layer | Start quiz validates parameters [OS-extreme] | Pass |
| TC-220 | Integration | User flows through the service layer | Submit quiz validates answers | Pass |
| TC-221 | Integration | User flows through the service layer | Interview runs to completion and persists turns | Pass |
| TC-222 | Integration | User flows through the service layer | Interview answer validation | Pass |
| TC-223 | Integration | User flows through the service layer | Failed follow up can be retried without reanswering | Pass |
| TC-224 | Integration | User flows through the service layer | New session remembers earlier questions | Pass |
| TC-225 | Integration | User flows through the service layer | Unknown interview type | Pass |
| TC-226 | Integration | User flows through the service layer | Dashboard aggregates everything | Pass |
| TC-227 | Integration | User flows through the service layer | Evaluation summary | Pass |
| TC-228 | Integration | User flows through the service layer | Next action without a profile is onboarding | Pass |
| TC-229 | Integration | User flows through the service layer | Next action without a plan is week 1 | Pass |
| TC-230 | Integration | User flows through the service layer | Next action quizzes the weakest unpractised topic first | Pass |
| TC-231 | Integration | User flows through the service layer | Next action returns to a weak topic after a week at the suggested level | Pass |
| TC-232 | Integration | User flows through the service layer | Next action suggests an interview once weak topics are practised | Pass |
| TC-233 | Integration | User flows through the service layer | Next action adapts the plan when it is a week old with new scores | Pass |
| TC-234 | Integration | User flows through the service layer | Next action otherwise practises the weakest topic | Pass |
| TC-235 | Integration | User flows through the service layer | Home gathers focus checklist and recent activity | Pass |
| TC-236 | Integration | User flows through the service layer | Home for a new student starts with a plan | Pass |
| TC-237 | Integration | User flows through the service layer | Home reports an unreadable database safely | Pass |
| TC-238 | Integration | User flows through the service layer | Usn owner finds the student behind a usn | Pass |
| TC-239 | Integration | User flows through the service layer | Delete student needs the matching usn | Pass |
| TC-240 | Integration | User flows through the service layer | Interview summary averages each criterion and tips the weak ones | Pass |
| TC-241 | Integration | User flows through the service layer | Streaks count consecutive days [active0-20-expected0] | Pass |
| TC-242 | Integration | User flows through the service layer | Streaks count consecutive days [active1-20-expected1] | Pass |
| TC-243 | Integration | User flows through the service layer | Streaks count consecutive days [active2-20-expected2] | Pass |
| TC-244 | Integration | User flows through the service layer | Streaks count consecutive days [active3-20-expected3] | Pass |
| TC-245 | Integration | User flows through the service layer | Streaks count consecutive days [active4-20-expected4] | Pass |
| TC-246 | Integration | User flows through the service layer | Streaks count consecutive days [active5-20-expected5] | Pass |
| TC-247 | Integration | User flows through the service layer | Activity days use the students calendar not utc | Pass |
| TC-248 | Integration | User flows through the service layer | Study streak combines quizzes and interview sessions | Pass |
| TC-249 | Integration | User flows through the service layer | Score trend compares the latest quiz with the ones before [scores0-new] | Pass |
| TC-250 | Integration | User flows through the service layer | Score trend compares the latest quiz with the ones before [scores1-new] | Pass |
| TC-251 | Integration | User flows through the service layer | Score trend compares the latest quiz with the ones before [scores2-improving] | Pass |
| TC-252 | Integration | User flows through the service layer | Score trend compares the latest quiz with the ones before [scores3-steady] | Pass |
| TC-253 | Integration | User flows through the service layer | Score trend compares the latest quiz with the ones before [scores4-slipping] | Pass |
| TC-254 | Integration | User flows through the service layer | Score trend compares the latest quiz with the ones before [scores5-steady] | Pass |
| TC-255 | Integration | User flows through the service layer | Topic mastery matches the planners weakness and ranks weakest first | Pass |
| TC-256 | Integration | User flows through the service layer | Days done are validated and reach the overviews | Pass |
| TC-257 | Integration | Demo seed data | Seed builds four weeks of history | Pass |
| TC-258 | Integration | Demo seed data | Seeded plans follow the scores | Pass |
| TC-259 | Integration | Demo seed data | Seed is idempotent | Pass |
| TC-260 | Integration | Evaluation harness | Refuses mock mode without flag | Pass |
| TC-261 | Integration | Evaluation harness | Mock smoke run writes all outputs | Pass |
| TC-262 | Integration | Evaluation harness | Each run starts with a fresh eval db | Pass |
| TC-263 | Integration | Evaluation harness | Csv writer handles error rows first | Pass |
| TC-264 | Integration | Evaluation harness | Rate limit stops the run but keeps partial results | Pass |
| TC-265 | Integration | Evaluation harness | Resume continues after a rate limit without redoing cases | Pass |
| TC-266 | Integration | Evaluation harness | Resume refuses to mix mock and live | Pass |
| TC-267 | Integration | Evaluation harness | Consecutive quizzes measure memory | Pass |
| TC-268 | Integration | Evaluation harness | Interview probe measures follow up relevance | Pass |
| TC-269 | Integration | Evaluation harness | Progress is saved even when a case crashes | Pass |
| TC-270 | Integration | Evaluation harness | Consecutive quizzes resume per topic | Pass |
| TC-271 | Integration | Evaluation harness | Every case is checkpointed | Pass |
| TC-272 | Integration | Results report | Report writes markdown and svg | Pass |
| TC-273 | Integration | Results report | Report requires a summary | Pass |
| TC-274 | Integration | Results report | Report from a real mock run | Pass |
| TC-275 | Integration | Model availability check | Mock mode has nothing to check | Pass |
| TC-276 | Integration | Model availability check | Missing configuration exits 2 | Pass |
| TC-277 | Integration | Model availability check | Served models pass and report quota | Pass |
| TC-278 | Integration | Model availability check | Retired model fails | Pass |
| TC-279 | Integration | Model availability check | Non json reply fails | Pass |
| TC-280 | Integration | Graph export | Export writes raw and github renderable mermaid | Pass |
| TC-281 | Integration | Graph export | Docs copy is up to date | Pass |
| TC-282 | Integration | Test report generator | Table is built from junit results | Pass |
| TC-283 | Integration | Test report generator | Every test module has a layer | Pass |
| TC-284 | Unit | Screenshot tool helpers | Page list matches the app navigation | Pass |
| TC-285 | Unit | Screenshot tool helpers | Every capture is checked by a marker | Pass |
| TC-286 | Unit | Screenshot tool helpers | Interview answers are detailed and distinct | Pass |
| TC-287 | Unit | Screenshot tool helpers | Shot names follow the convention | Pass |
| TC-288 | Unit | Screenshot tool helpers | Planned shots cover pages states flows widths and schemes | Pass |
| TC-289 | Unit | Screenshot tool helpers | Unknown widths are rejected [] | Pass |
| TC-290 | Unit | Screenshot tool helpers | Unknown widths are rejected [1440,800] | Pass |
| TC-291 | Unit | Screenshot tool helpers | Unknown widths are rejected [1024] | Pass |
| TC-292 | Unit | Screenshot tool helpers | Widths and schemes parse | Pass |
| TC-293 | Unit | Screenshot tool helpers | Isolated env never reaches groq or the real env | Pass |
| TC-294 | Unit | Screenshot tool helpers | Compress png shrinks and keeps the size | Pass |
| TC-295 | Unit | Screenshot tool helpers | Pages filter parses known slugs only | Pass |
| TC-296 | Unit | Performance tool helpers | Percentile is nearest rank [values0-50-3] | Pass |
| TC-297 | Unit | Performance tool helpers | Percentile is nearest rank [values1-90-7] | Pass |
| TC-298 | Unit | Performance tool helpers | Percentile is nearest rank [values2-90-10] | Pass |
| TC-299 | Unit | Performance tool helpers | Percentile is nearest rank [values3-50-4] | Pass |
| TC-300 | Unit | Performance tool helpers | Dir size | Pass |
| TC-301 | Unit | Performance tool helpers | Query counter counts calls and statements and restores tx | Pass |
| TC-302 | Unit | Performance tool helpers | Markdown table | Pass |
| TC-303 | Unit | Performance tool helpers | Modes default to fresh and rerun is available | Pass |
| TC-304 | Unit | Design tokens: contrast and distinctness | Config toml mirrors the tokens [light] | Pass |
| TC-305 | Unit | Design tokens: contrast and distinctness | Config toml mirrors the tokens [dark] | Pass |
| TC-306 | Unit | Design tokens: contrast and distinctness | Text reaches 4 5 to 1 on every layer [light] | Pass |
| TC-307 | Unit | Design tokens: contrast and distinctness | Text reaches 4 5 to 1 on every layer [dark] | Pass |
| TC-308 | Unit | Design tokens: contrast and distinctness | Alert text reaches 4 5 to 1 on its tint [light] | Pass |
| TC-309 | Unit | Design tokens: contrast and distinctness | Alert text reaches 4 5 to 1 on its tint [dark] | Pass |
| TC-310 | Unit | Design tokens: contrast and distinctness | Buttons edges and chart marks reach 3 to 1 [light] | Pass |
| TC-311 | Unit | Design tokens: contrast and distinctness | Buttons edges and chart marks reach 3 to 1 [dark] | Pass |
| TC-312 | Unit | Design tokens: contrast and distinctness | Every topic has its own colour [light] | Pass |
| TC-313 | Unit | Design tokens: contrast and distinctness | Every topic has its own colour [dark] | Pass |
| TC-314 | Unit | Design tokens: contrast and distinctness | Status and primary colours stay away from topic colours [light] | Pass |
| TC-315 | Unit | Design tokens: contrast and distinctness | Status and primary colours stay away from topic colours [dark] | Pass |
| TC-316 | Unit | Design tokens: contrast and distinctness | Neutral chart marks read in both schemes | Pass |
| TC-317 | Unit | Design tokens: contrast and distinctness | The threshold rejects the old amber accent | Pass |
| TC-318 | Unit | Design tokens: contrast and distinctness | Fonts are self hosted woff2 files with their licences | Pass |
| TC-319 | Unit | Design tokens: contrast and distinctness | Type scale keeps text legible at a distance | Pass |
| TC-320 | Unit | Design tokens: contrast and distinctness | Sequential ramp runs away from the background [light] | Pass |
| TC-321 | Unit | Design tokens: contrast and distinctness | Sequential ramp runs away from the background [dark] | Pass |
| TC-322 | Unit | Design tokens: contrast and distinctness | Stylesheet is small and targets only data testids | Pass |
| TC-323 | Unit | Design tokens: contrast and distinctness | Brand svgs are self contained and on palette [mark.svg] | Pass |
| TC-324 | Unit | Design tokens: contrast and distinctness | Brand svgs are self contained and on palette [wordmark.svg] | Pass |
| TC-325 | Unit | Design tokens: contrast and distinctness | Brand colour reads on every background | Pass |
| TC-326 | Unit | Design tokens: contrast and distinctness | A selected pill uses the readable teal text | Pass |
| TC-327 | Unit | Chart builders: encodings and theme | Weakness bars run weakest first in topic colours | Pass |
| TC-328 | Unit | Chart builders: encodings and theme | Weakness bars take an optional takeaway title | Pass |
| TC-329 | Unit | Chart builders: encodings and theme | Minutes shift is a dumbbell from grey to topic colour | Pass |
| TC-330 | Unit | Chart builders: encodings and theme | Readiness ring fills the score in the brand teal | Pass |
| TC-331 | Unit | Chart builders: encodings and theme | Shared theme sets fonts and drops the frame | Pass |
| TC-332 | Unit | Chart builders: encodings and theme | View specs are the charts as plain vega lite without altairs size default | Pass |
| TC-333 | Unit | Chart builders: encodings and theme | Cached specs hand out fresh copies | Pass |
| TC-334 | Unit | Chart builders: encodings and theme | Score spark draws one topic in its colour without axes | Pass |
| TC-335 | Unit | Chart builders: encodings and theme | Week mix stacks topics in order per week | Pass |
| TC-336 | Unit | Chart builders: encodings and theme | Interview trend is a 0 to 5 line in the brand teal | Pass |
| TC-337 | Unit | Chart builders: encodings and theme | Readiness trend is a 0 to 100 line per profile | Pass |
| TC-338 | Unit | Chart builders: encodings and theme | Dashboard specs match their charts | Pass |
| TC-339 | Unit | Chart builders: encodings and theme | Activity heatmap is a 12 week calendar with neutral empty days | Pass |
| TC-340 | Unit | CI workflow settings | Ci token can only read the repository | Pass |
| TC-341 | Unit | Demo tunnel settings | Config toml keeps cors and xsrf protection on | Pass |
| TC-342 | Unit | Demo tunnel settings | Tunnel script lifts the checks on the command line | Pass |
| TC-343 | Unit | Demo tunnel settings | Tunnel bat runs the powershell script | Pass |
| TC-344 | System (UI) | Streamlit pages, headless | A page render never repeats a query [views/onboard.py] | Pass |
| TC-345 | System (UI) | Streamlit pages, headless | A page render never repeats a query [views/plan.py] | Pass |
| TC-346 | System (UI) | Streamlit pages, headless | A page render never repeats a query [views/quiz.py] | Pass |
| TC-347 | System (UI) | Streamlit pages, headless | A page render never repeats a query [views/interview.py] | Pass |
| TC-348 | System (UI) | Streamlit pages, headless | A page render never repeats a query [views/dashboard.py] | Pass |
| TC-349 | System (UI) | Streamlit pages, headless | A page render never repeats a query [views/results.py] | Pass |
| TC-350 | System (UI) | Streamlit pages, headless | Onboard prefills the selected students usn | Pass |
| TC-351 | System (UI) | Streamlit pages, headless | Design system components render | Pass |
| TC-352 | System (UI) | Streamlit pages, headless | Navigation groups pages with material icons | Pass |
| TC-353 | System (UI) | Streamlit pages, headless | Sidebar shows readiness and a quiet mock badge | Pass |
| TC-354 | System (UI) | Streamlit pages, headless | Onboard with sample resume | Pass |
| TC-355 | System (UI) | Streamlit pages, headless | Onboard without a student explains what happens next | Pass |
| TC-356 | System (UI) | Streamlit pages, headless | Onboard profile shows readiness skills and fixes | Pass |
| TC-357 | System (UI) | Streamlit pages, headless | Onboard reprofile without a resume shows the error | Pass |
| TC-358 | System (UI) | Streamlit pages, headless | Onboarding a usn that is taken asks before replacing that student | Pass |
| TC-359 | System (UI) | Streamlit pages, headless | Reprofiling the selected student closes their open quiz and interview | Pass |
| TC-360 | System (UI) | Streamlit pages, headless | Reprofiling the selected student needs no confirmation | Pass |
| TC-361 | System (UI) | Streamlit pages, headless | Deleting a student needs their usn then returns home | Pass |
| TC-362 | System (UI) | Streamlit pages, headless | Onboard rejects missing usn | Pass |
| TC-363 | System (UI) | Streamlit pages, headless | Pages require a student [views/plan.py] | Pass |
| TC-364 | System (UI) | Streamlit pages, headless | Pages require a student [views/quiz.py] | Pass |
| TC-365 | System (UI) | Streamlit pages, headless | Pages require a student [views/interview.py] | Pass |
| TC-366 | System (UI) | Streamlit pages, headless | Pages require a student [views/dashboard.py] | Pass |
| TC-367 | System (UI) | Streamlit pages, headless | The empty state points to the sidebar when students exist | Pass |
| TC-368 | System (UI) | Streamlit pages, headless | Plan generates next week and compares | Pass |
| TC-369 | System (UI) | Streamlit pages, headless | Plan shows the latest week day by day with why and the shift | Pass |
| TC-370 | System (UI) | Streamlit pages, headless | Plan week one has no shift and table view shows the table | Pass |
| TC-371 | System (UI) | Streamlit pages, headless | Plan days marked done are saved and counted on home and dashboard | Pass |
| TC-372 | System (UI) | Streamlit pages, headless | Plan week exports as calendar and table | Pass |
| TC-373 | System (UI) | Streamlit pages, headless | Plan export files are built only when downloaded | Pass |
| TC-374 | System (UI) | Streamlit pages, headless | Plan without a plan yet invites week one | Pass |
| TC-375 | System (UI) | Streamlit pages, headless | Quiz generate answer and review | Pass |
| TC-376 | System (UI) | Streamlit pages, headless | Quiz setup hints weakness and explains the suggestion | Pass |
| TC-377 | System (UI) | Streamlit pages, headless | Quiz review shows a score card marks and next steps | Pass |
| TC-378 | System (UI) | Streamlit pages, headless | Quiz with blank answers asks before submitting | Pass |
| TC-379 | System (UI) | Streamlit pages, headless | Critic log numbers questions like the quiz | Pass |
| TC-380 | System (UI) | Streamlit pages, headless | Quiz text and options are shown literally | Pass |
| TC-381 | System (UI) | Streamlit pages, headless | Interview answer is shown literally | Pass |
| TC-382 | System (UI) | Streamlit pages, headless | Interview session runs to completion | Pass |
| TC-383 | System (UI) | Streamlit pages, headless | Interview setup describes each type | Pass |
| TC-384 | System (UI) | Streamlit pages, headless | Interview shows progress scored feedback and the critic trail | Pass |
| TC-385 | System (UI) | Streamlit pages, headless | Dashboard renders | Pass |
| TC-386 | System (UI) | Streamlit pages, headless | Dashboard readiness shows a delta and trend only after a second profile | Pass |
| TC-387 | System (UI) | Streamlit pages, headless | Dashboard keeps system telemetry in its own section | Pass |
| TC-388 | System (UI) | Streamlit pages, headless | Dashboard for a new student explains each empty section | Pass |
| TC-389 | System (UI) | Streamlit pages, headless | Dashboard error state offers a retry | Pass |
| TC-390 | System (UI) | Streamlit pages, headless | Onboard requires a resume or sample | Pass |
| TC-391 | System (UI) | Streamlit pages, headless | Onboarding another student drops the previous students session | Pass |
| TC-392 | System (UI) | Streamlit pages, headless | Failed follow up offers retry without reanswering | Pass |
| TC-393 | System (UI) | Streamlit pages, headless | Failed quiz generation stays visible | Pass |
| TC-394 | System (UI) | Streamlit pages, headless | Results page without and with results | Pass |
| TC-395 | System (UI) | Streamlit pages, headless | Results note mentions the duplicate rate only when it is shown | Pass |
| TC-396 | System (UI) | Streamlit pages, headless | Seed demo fills an empty database on start | Pass |
| TC-397 | System (UI) | Streamlit pages, headless | Home without a student explains the loop | Pass |
| TC-398 | System (UI) | Streamlit pages, headless | Home quick start opens onboard with a sample | Pass |
| TC-399 | System (UI) | Streamlit pages, headless | Home shows todays focus for the demo student | Pass |
| TC-400 | System (UI) | Streamlit pages, headless | Todays focus opens the page it names | Pass |
| TC-401 | System (UI) | Streamlit pages, headless | Todays focus preselects the quiz topic | Pass |
| TC-402 | System (UI) | Streamlit pages, headless | Home error state offers a retry | Pass |
