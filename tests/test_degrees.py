"""Degrees: the qualification list, reading a free-text degree, and which roles a degree
(completed or being pursued) qualifies for."""

import pytest

from piq import degrees, syllabus


def test_the_list_runs_from_school_to_doctorate_with_unique_codes():
    codes = degrees.codes()
    assert len(codes) == len(set(codes))
    assert codes[0] == "Class 10" and "PhD" in codes
    for wanted in ("B.E", "BBA", "BA", "M.Sc", "MCA", "BCA", "MBBS", "LL.B", "Diploma"):
        assert wanted in codes, wanted
    assert {d.level for d in degrees.degrees()} <= set(degrees.levels())


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("B.E. in Electronics & Communication, 2026", "B.E"),
        ("BTech CSE", "B.Tech"),
        ("Pursuing M.E in VLSI", "M.E"),
        ("Bachelor of Commerce", "B.Com"),
        ("II PUC (Science)", "Class 12"),
        ("BA LLB, 2024", "BA LL.B"),
        ("MCA", "MCA"),
    ],
)
def test_parse_reads_the_degree_a_line_names(text, code):
    assert degrees.parse(text).code == code


def test_two_letter_codes_count_only_in_capitals():
    assert degrees.parse("will be graduating next year") is None  # "be" is not a B.E
    assert degrees.parse("me and my team") is None
    assert degrees.parse("BE (Mechanical)").code == "B.E"


def test_groups_expand_and_any_graduate_skips_school_and_diplomas():
    assert degrees.expand(["@engineering_ug", "MCA"]) == {"B.E", "B.Tech", "MCA"}
    graduate = degrees.expand(["@any_graduate"])
    assert {"BA", "B.E", "MBBS", "PhD", "MBA"} <= graduate
    assert not graduate & {"Class 10", "Class 12", "Diploma", "ITI", "Other"}


def test_a_role_with_fields_needs_a_matching_branch():
    rule = {"degrees": ["@engineering_ug"], "fields": ["civil", "structural"]}
    civil = {"degree": "B.E", "specialization": "Civil Engineering", "status": "Completed"}
    mech = {"degree": "B.E", "specialization": "Mechanical", "status": "Completed"}
    assert degrees.qualifies(rule, civil) and not degrees.qualifies(rule, mech)
    assert not degrees.qualifies(rule, {**civil, "degree": "B.Sc"})  # wrong degree
    assert not degrees.qualifies(None, civil)


def test_a_degree_names_its_own_field():
    # MCA says "Computer Applications" itself: no branch needed for a computing role.
    rule = {"degrees": ["MCA"], "fields": ["computer"]}
    assert degrees.qualifies(rule, {"degree": "MCA", "specialization": ""})


def test_completed_beats_pursuing_and_pursuing_opens_on_completion():
    rule = {"degrees": ["@management"], "fields": ["human resources", "hr"]}
    pursuing = {"degree": "MBA", "specialization": "HR", "status": "Pursuing", "end": "2027"}
    assert degrees.fit(rule, [pursuing]) == (False, "MBA in HR (pursuing, 2027)")
    done = {"degree": "BBA", "specialization": "Human Resources", "status": "Completed"}
    assert degrees.fit(rule, [pursuing, done]) == (True, "BBA in Human Resources")
    assert degrees.fit(rule, []) is None


def test_roles_for_lists_open_roles_first_across_domains():
    cs = degrees.roles_for(
        [{"degree": "B.E", "specialization": "Computer Science", "status": "Completed"}]
    )
    names = [f.role for f in cs]
    assert "Software Engineer" in names and "UPSC Civil Services Aspirant" in names
    assert "Structural Design Engineer" not in names  # civil only
    assert "Railway Recruitment Board (RRB) SSE" not in names  # core branches only
    later = degrees.roles_for(
        [{"degree": "Diploma", "specialization": "Mechanical", "status": "Pursuing"}]
    )
    assert later and not any(f.eligible_now for f in later)
    mixed = degrees.roles_for(
        [
            {"degree": "BA", "specialization": "History", "status": "Completed"},
            {"degree": "LL.B", "specialization": "", "status": "Pursuing", "end": "2027"},
        ]
    )
    flags = [f.eligible_now for f in mixed]
    assert flags == sorted(flags, reverse=True)  # every open role before any later one
    assert any(f.role == "Corporate Legal Counsel" and not f.eligible_now for f in mixed)


def test_entry_label_reads_naturally():
    assert degrees.entry_label({"degree": "B.Tech", "specialization": "IT"}) == "B.Tech in IT"
    assert degrees.entry_label({"degree": "Other", "specialization": "CFA Level 1"}) == (
        "CFA Level 1"
    )
    assert degrees.entry_label({"degree": "B.E", "title": "B.E (ECE)"}) == "B.E (ECE)"
    assert degrees.entry_label({"degree": "PhD", "status": "Pursuing"}) == "PhD (pursuing)"


def test_every_catalog_role_has_a_valid_degree_rule():
    known = set(degrees.codes()) | {"@any_graduate", "@any_postgraduate"}
    known |= {f"@{g}" for g in degrees._data()["groups"]}
    for d in syllabus.catalog()["domains"]:
        for r in d["roles"]:
            rule = r.get("eligibility")
            assert rule and rule["degrees"], r["name"]
            assert set(rule["degrees"]) <= known, r["name"]
            assert degrees.expand(rule["degrees"]) <= set(degrees.codes()), r["name"]
