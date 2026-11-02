"""The HTTP API (server.py) over the services, offline in MOCK_MODE, with a small test bank."""

import json

import pytest
from fastapi.testclient import TestClient

from piq import checks, db, services
from server import app

ECE_RESUME = "Asha Rao\nB.E in Electronics\nSkills: Embedded C, I2C\nProject: STM32 logger"


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def cs() -> str:
    sid, _ = services.onboard(
        "CS0001", "Java Backend Developer", services.load_sample("java_backend_fresher.txt")
    )
    return sid


def _events(text: str) -> list[tuple[str, dict | str]]:
    out = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_catalog_lists_every_domain_role_and_degree(client):
    body = client.get("/api/catalog").json()
    assert len(body["domains"]) == 10
    assert sum(len(d["roles"]) for d in body["domains"]) == 60
    cs = body["domains"][0]
    assert cs["topics"][0]["name"] == "Aptitude" and "ats_keywords" in cs["roles"][0]
    assert {"code": "MCA", "name": "MCA (Master of Computer Applications)"} in body["degrees"]
    assert body["statuses"] == ["Completed", "Pursuing"]


def test_roles_for_degree(client):
    fits = client.get(
        "/api/roles-for-degree", params={"degree": "B.E", "specialization": "Civil"}
    ).json()
    assert any(f["role"] == "Structural Design Engineer" and f["eligible_now"] for f in fits)
    assert client.get("/api/roles-for-degree", params={"degree": "Nope"}).status_code == 400


def test_a_quiz_comes_from_the_bank_without_answers_and_is_graded_on_submit(client, bank):
    r = client.get("/api/quiz", params={"topic": "DBMS", "difficulty": "easy"})
    assert r.status_code == 200
    quiz = r.json()
    assert len(quiz["questions"]) == 5
    assert all("correct_index" not in q and len(q["options"]) == 4 for q in quiz["questions"])
    answers = [{"id": q["id"], "choice": 2} for q in quiz["questions"]]  # "C" in the test bank
    answers[0]["choice"] = 0
    graded = client.post(
        "/api/quiz/submit", json={"topic": "DBMS", "difficulty": "easy", "answers": answers}
    ).json()
    assert graded["correct"] == 4 and graded["total"] == 5 and graded["score_pct"] == 80.0
    assert graded["review"][0] == {
        "id": answers[0]["id"],
        "chosen": 0,
        "correct_index": 2,
        "is_correct": False,
        "explanation": "Because.",
    }
    assert graded["weakness"] is None  # a guest's score is not saved


def test_a_candidates_quiz_is_saved_and_moves_their_weakness(client, bank, cs):
    before = services.weakness_for(services.current_profile(cs), db.topic_performance(cs))
    quiz = client.get(
        "/api/quiz",
        params={"topic": "DBMS", "difficulty": "easy", "count": 3, "candidate_id": cs},
    ).json()
    answers = [{"id": q["id"], "choice": 2} for q in quiz["questions"]]
    body = client.post(
        "/api/quiz/submit",
        json={"candidate_id": cs, "topic": "DBMS", "difficulty": "easy", "answers": answers},
    ).json()
    assert body["score_pct"] == 100.0 and body["next_difficulty"] == "medium"
    assert body["weakness"]["DBMS"] == 0.0 < before["DBMS"]
    again = client.get(
        "/api/quiz",
        params={"topic": "DBMS", "difficulty": "easy", "count": 10, "candidate_id": cs},
    ).json()
    assert not {q["id"] for q in again["questions"]} & {a["id"] for a in answers}  # unseen


def test_quiz_errors_are_400s(client, bank, cs):
    bad = client.get("/api/quiz", params={"topic": "Embedded C", "candidate_id": cs})
    assert bad.status_code == 400 and "not in your domain" in bad.json()["detail"]
    assert client.get("/api/quiz", params={"topic": "Nope"}).status_code == 400
    assert client.get("/api/quiz", params={"topic": "DBMS", "difficulty": "hard"}).status_code == (
        400
    )  # none at this difficulty in the test bank
    forged = client.post(
        "/api/quiz/submit",
        json={"topic": "DBMS", "difficulty": "easy", "answers": [{"id": "x", "choice": 0}]},
    )
    assert forged.status_code == 400


def test_plan_and_dashboard(client, cs):
    assert client.get("/api/plan/nobody").status_code == 404
    empty = client.get(f"/api/plan/{cs}").json()
    assert empty["plan"] is None and empty["next_week"] == 1 and "OS" in empty["weakness"]
    made = client.post(f"/api/plan/{cs}/next").json()
    assert made["plan"]["week_no"] == 1 and len(made["plan"]["days"]) == 7
    done = client.post(f"/api/plan/{cs}/done", json={"week_no": 1, "days": [1, 2]}).json()
    assert done["done"] == [1, 2]
    dash = client.get(f"/api/dashboard/{cs}").json()
    assert dash["profile"]["target_role"] == "Java Backend Developer"
    assert dash["readiness"][0]["readiness_score"] == dash["profile"]["readiness_score"]
    assert {m["topic"] for m in dash["mastery"]} >= {"OS", "DBMS"}


def test_interview_tracks_follow_the_domain_and_the_degree(client, cs):
    names = [t["name"] for t in client.get(f"/api/interview/tracks/{cs}").json()]
    assert names[:5] == [
        "System Design",
        "Algorithm Walkthrough",
        "Frameworks",
        "Behavioral STAR",
        "Project Defense",
    ]
    assert names[-3:] == ["HR", "Technical", "Project"]
    ece, _ = services.onboard("ECE001", "Embedded Systems & Firmware Engineer", ECE_RESUME)
    assert "VLSI" in [t["name"] for t in client.get(f"/api/interview/tracks/{ece}").json()]
    mca, _ = services.onboard("MCA001", "Software Engineer", "Ravi\nMCA, 2025\nSkills: Java, SQL")
    groups = {t["group"] for t in client.get(f"/api/interview/tracks/{mca}").json()}
    assert "Applied Sciences & Computing (BCA / MCA / MSc / MSE)" in groups


def test_an_interview_streams_steps_then_the_approved_question(client, cs):
    r = client.post("/api/interview/turn", json={"candidate_id": cs, "track": "System Design"})
    assert r.headers["content-type"].startswith("text/event-stream")
    events = _events(r.text)
    assert events[-1][0] == "result" and all(e == "step" for e, _ in events[:-1])
    session = events[-1][1]["session"]
    assert session["interview_type"] == "System Design" and session["current"]["question"]
    r = client.post(
        "/api/interview/turn",
        json={"candidate_id": cs, "session": session, "answer": "I would add a cache " * 10},
    )
    kind, result = _events(r.text)[-1]
    assert kind == "result"
    assert len(result["session"]["history"]) == 1 and result["session"]["current"]["question"]
    assert result["average"] is not None


def test_an_interview_error_arrives_as_an_event(client, cs):
    r = client.post("/api/interview/turn", json={"candidate_id": cs, "track": "Underwater"})
    [(kind, data)] = _events(r.text)
    assert kind == "error" and data["status"] == 400 and "Unknown interview" in data["detail"]


RESUME = {
    "full_name": "Asha Rao",
    "email": "asha@example.com",
    "role_name": "VLSI & Chip Design Engineer",
    "skills": ["Verilog", "Static Timing Analysis"],
    "education": [{"degree": "B.E", "specialization": "Electronics", "institution": "A college"}],
    "experience": [
        {
            "title": "Intern",
            "company": "Chips",
            "type": "Internship",
            "start": "Jan 2025",
            "end": "Jun 2025",
            "highlights": "Built a UART in Verilog\nCut area by 12%",
        }
    ],
}


def test_resume_ats_and_pdf(client):
    body = client.post("/api/resume/ats", json=RESUME).json()
    assert 0 < body["ats"]["score"] <= 100 and body["ats"]["degree_fit"] == "now"
    assert "Verilog" in body["ats"]["matched_keywords"]
    pdf = client.post("/api/resume/build-pdf", json=RESUME)
    assert pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")
    assert "asha_rao" in pdf.headers["content-disposition"]
    bad = client.post(
        "/api/resume/build-pdf",
        json={**RESUME, "experience": [{**RESUME["experience"][0], "end": "someday"}]},
    )
    assert bad.status_code == 400
    assert client.post("/api/resume/ats", json={**RESUME, "role_name": "Wizard"}).status_code == (
        400
    )


def test_enhance_bullet_rewrites_without_inventing_numbers(client):
    r = client.post(
        "/api/resume/enhance-bullet",
        json={"text": "made the build faster by 30%", "role": "Software Engineer"},
    )
    bullet = r.json()["bullet"]
    assert "30" in bullet and "[metric]" in bullet
    assert not checks.check_bullet("made the build faster by 30%", bullet)
    assert (
        client.post(
            "/api/resume/enhance-bullet", json={"text": "x", "role": "Software Engineer"}
        ).status_code
        == 400
    )


def test_check_bullet_rejects_invented_numbers():
    assert checks.check_bullet("Fixed bugs", "Fixed 40 bugs, cutting crashes by 25%")
    assert not checks.check_bullet("Fixed 40 bugs", "Resolved 40 bugs, measured by [metric]")
    assert checks.check_bullet("Fixed bugs", "Fixed bugs")  # unchanged
