"""The multi-stream data: the four placement streams in degrees.json, the commerce, law and
management roles with their tools and benchmarks, the committed question bank's columns, the
bank's header upgrade, and the sample resumes of each stream."""

import csv
import json

import pytest

from piq import checks, degrees, question_bank, syllabus
from piq.config import DATA_DIR
from scripts import verify_and_ingest_mcq as ingest

STREAMS = ("Engineering", "Commerce", "Law", "Management")
NEW_ROLES = {
    "Tax Consultant": "commerce",
    "Audit Executive": "commerce",
    "Financial Analyst": "commerce",
    "Corporate Legal Associate": "law",
    "Contract Analyst": "law",
    "HR Talent Specialist": "corp",
}
SAMPLES = {
    "commerce_accountant.txt": "Tax Consultant",
    "law_corporate_fresher.txt": "Corporate Legal Associate",
    "management_hr_trainee.txt": "HR Talent Specialist",
}
BANK = DATA_DIR / "questions" / "mcq_bank.csv"


def _roles() -> dict[str, dict]:
    return {r["name"]: r for d in syllabus.catalog()["domains"] for r in d["roles"]}


def test_each_stream_names_real_degrees_specialisations_and_domains():
    streams = json.loads((DATA_DIR / "degrees.json").read_text(encoding="utf-8"))["streams"]
    assert tuple(streams) == STREAMS
    by_id = {d.id: d for d in syllabus.domains()}
    stream_of = {d["id"]: d["stream"] for d in syllabus.catalog()["domains"]}
    for name, s in streams.items():
        assert set(s["degrees"]) <= set(degrees.codes()), name
        assert len(s["specializations"]) >= 3, name
        assert len(set(s["specializations"])) == len(s["specializations"]), name
        assert s["domains"] and set(s["domains"]) <= set(by_id), name
        assert all(stream_of[d] == name for d in s["domains"]), name


def test_every_domain_names_its_stream():
    stream_of = {d["id"]: d.get("stream") for d in syllabus.catalog()["domains"]}
    assert set(stream_of.values()) == {*STREAMS, "Healthcare", "Government"}
    assert stream_of["commerce"] == "Commerce" and stream_of["law"] == "Law"
    assert stream_of["corp"] == "Management"


@pytest.mark.parametrize(("role", "domain_id"), NEW_ROLES.items())
def test_a_stream_role_lists_skills_tools_and_benchmarks(role, domain_id):
    assert syllabus.domain_of_role(role).id == domain_id
    info = _roles()[role]
    for key in ("tools", "benchmarks"):
        assert len(info[key]) >= 4 and len(set(info[key])) == len(info[key]), (role, key)
        assert all(isinstance(x, str) and x.strip() for x in info[key]), (role, key)
    skills = syllabus.role_skills()[role]
    assert any(t is None for t in skills.values()), "tools count as required skills too"
    assert sum(t is not None for t in skills.values()) >= 5, "core skills map to topics"


def test_hr_and_operations_are_separate_management_topics():
    corp = syllabus.domain("corp")
    assert {"Human Resources", "Operations & Supply Chain"} <= set(corp.topics)
    assert "HR & Operations" not in syllabus.all_topics()
    assert "Human Resources" in syllabus.focus_topics("HR Talent Specialist")
    assert "Operations & Supply Chain" in syllabus.focus_topics(
        "Supply Chain & Logistics Specialist"
    )


def test_the_committed_bank_has_one_header_and_consistent_rows():
    with BANK.open(encoding="utf-8", newline="") as f:
        lines = list(csv.reader(f))
    assert lines[0] == ingest.HEADER
    assert {len(row) for row in lines} == {len(ingest.HEADER)}
    homes = ingest.role_homes()
    rows = [dict(zip(lines[0], r, strict=True)) for r in lines[1:]]
    assert all(homes[r["role"]] == (r["stream"], r["domain"]) for r in rows)
    topics = question_bank.topic_map()
    assert {r["topic"] for r in rows} <= set(topics)
    for stream in ("Commerce", "Law", "Management"):
        assert sum(r["stream"] == stream for r in rows) >= 15, stream


def test_normalise_upgrades_the_older_header(tmp_path):
    old = tmp_path / "bank.csv"
    old.write_text(
        "category,role_or_stream,topic,difficulty,question,option_a,option_b,option_c,"
        "option_d,correct_option,explanation,bloom_level\n"
        "Corporate Management,Financial Analyst & Investment Associate,Corporate_Finance_WACC,"
        "easy,What does WACC weigh?,Costs of capital,Tax rates,Dividends,Sales,A,Why.,remember\n",
        encoding="utf-8",
    )
    changes = ingest.normalise_bank(old)
    assert changes["header upgraded"] == 1 and changes["role renamed"] == 1
    [row] = list(csv.DictReader(old.open(encoding="utf-8", newline="")))
    assert list(row) == ingest.HEADER
    assert (row["stream"], row["domain"], row["role"]) == (
        "Commerce",
        "Commerce, Accounting & Tax",
        "Financial Analyst",
    )
    assert b"\r\n" not in old.read_bytes()
    assert ingest.normalise_bank(old) == {}  # a second pass changes nothing


@pytest.mark.parametrize(("name", "role"), SAMPLES.items())
def test_a_stream_sample_resume_names_every_skill_its_role_requires(name, role):
    text = (DATA_DIR / "sample_resumes" / name).read_text(encoding="utf-8")
    words, aliases = checks.tokens(text), syllabus.skill_aliases()
    missing = [
        s
        for s in syllabus.role_skills()[role]
        if not checks.evidenced(s, words, aliases.get(s, ()))
    ]
    assert not missing, missing
    parsed = degrees.parse(text.splitlines()[1])
    assert parsed is not None
    entry = {"degree": parsed.code, "specialization": text.splitlines()[1], "status": "Completed"}
    assert degrees.qualifies(_roles()[role]["eligibility"], entry)
