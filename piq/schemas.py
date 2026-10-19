"""Pydantic models for every LLM output and the objects derived from them.

LLM-facing models (`*Extraction`, `WeeklyPlan`, `QuizSet`, `InterviewTurn`,
`AnswerEvaluation`, `QuizCritique`) describe exactly what the model must return.
Anything computable (scores, missing skills) is added in code, never asked of the LLM.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

Topic = Literal["Aptitude", "DBMS", "OS", "CN", "DSA", "OOP"]
Difficulty = Literal["easy", "medium", "hard"]
Score05 = Annotated[int, Field(ge=0, le=5)]


class ProfileExtraction(BaseModel):
    name: str
    education: str
    skills: list[str]
    projects: list[str]
    internships: list[str]
    matched_skills: list[str] = Field(
        description="Subset of the required skills the resume evidences"
    )
    resume_feedback: list[str] = Field(min_length=1, max_length=5)


class StudentProfile(ProfileExtraction):
    target_role: str
    missing_skills: list[str]
    readiness_score: int = Field(ge=0, le=100)


class DayPlan(BaseModel):
    day: int = Field(ge=1, le=7)
    topic: Topic
    subtopics: list[str] = Field(min_length=2, max_length=3)
    duration_min: int = Field(ge=30, le=240)
    practice_goal: str


class WeeklyPlan(BaseModel):
    week_no: int = Field(ge=1)
    rationale: str
    days: list[DayPlan] = Field(min_length=7, max_length=7)

    def minutes_by_topic(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for d in self.days:
            out[d.topic] = out.get(d.topic, 0) + d.duration_min
        return out


class Question(BaseModel):
    text: str = Field(min_length=10)
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str
    bloom_level: Literal["remember", "understand", "apply", "analyze"]

    @field_validator("bloom_level", mode="before")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v


class QuizSet(BaseModel):
    topic: Topic
    difficulty: Difficulty
    questions: list[Question] = Field(min_length=1)


class QuestionVerdict(BaseModel):
    index: int
    valid: bool
    reason: str = ""


class QuizCritique(BaseModel):
    verdicts: list[QuestionVerdict]


class InterviewTurn(BaseModel):
    question: str = Field(min_length=5)
    intent: str
    is_followup: bool
    is_final: bool


class AnswerEvaluation(BaseModel):
    relevance: Score05
    depth: Score05
    structure: Score05
    clarity: Score05
    strengths: list[str]
    improvements: list[str]
    model_answer: str

    @property
    def scores(self) -> dict[str, int]:
        return {
            "relevance": self.relevance,
            "depth": self.depth,
            "structure": self.structure,
            "clarity": self.clarity,
        }

    @property
    def overall(self) -> float:
        return round(sum(self.scores.values()) / 4, 2)


class FollowUpJudgement(BaseModel):
    """Evaluation only: does an interview question actually follow up on the last answer?"""

    references_answer: bool
    reason: str


class BaselineOutput(BaseModel):
    """Single-prompt baseline used only by the evaluation harness."""

    plan: WeeklyPlan
    quiz: QuizSet
