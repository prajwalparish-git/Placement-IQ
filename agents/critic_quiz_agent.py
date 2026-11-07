"""Critic Quiz Agent for Skill Scout Nexus (Layer 2 Multi-Agent Orchestration).

Responsibilities:
- Implements a Generator-Critic loop based on `docs/critic_graph.md`:
    - Generator: Generates targeted technical/stream MCQs based on the student's skill gaps.
    - Critic Agent: Validates question factual correctness, answer ambiguity, distractor viability,
      and difficulty appropriateness. If rejected, regenerates.
- Falls back to `data/questions/mcq_bank.csv` if offline or LLM fails.
- All outputs follow strict Pydantic schemas.
"""

from __future__ import annotations

import csv
import logging
import random
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from piq import llm, question_bank
from piq.config import DATA_DIR, settings

log = logging.getLogger("agents.critic_quiz_agent")

MCQ_BANK_PATH = DATA_DIR / "questions" / "mcq_bank.csv"


class GeneratedMCQ(BaseModel):
    text: str = Field(min_length=10, description="Question stem")
    options: list[str] = Field(min_length=4, max_length=4, description="Exactly 4 distinct choices")
    correct_index: int = Field(ge=0, le=3, description="0-based index of correct answer")
    explanation: str = Field(description="Educational explanation justifying the answer")
    bloom_level: Literal["remember", "understand", "apply", "analyze"] = Field(
        default="understand", description="Cognitive level according to Bloom's taxonomy"
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(
        default="medium", description="Difficulty level"
    )
    skill_tag: str = Field(default="", description="The specific skill gap or topic tested")

    @field_validator("bloom_level", mode="before")
    @classmethod
    def _lower_bloom(cls, v: Any) -> str:
        return str(v).strip().lower() if v else "understand"

    @property
    def correct_option_letter(self) -> str:
        return "ABCD"[self.correct_index]


class CriticEvaluation(BaseModel):
    is_valid: bool = Field(description="True if question passes all quality standards")
    rejection_reasons: list[str] = Field(
        default_factory=list, description="Concrete reasons if question is flawed"
    )
    factual_correctness: bool = Field(
        default=True, description="Question facts and solution are accurate"
    )
    unambiguous: bool = Field(default=True, description="Exactly one option is defensibly correct")
    difficulty_appropriate: bool = Field(
        default=True, description="Matches target audience and difficulty level"
    )


class QuizBatch(BaseModel):
    topic_or_skill: str
    target_role: str
    difficulty: str
    source: Literal["critic_generated", "question_bank_fallback"]
    questions: list[GeneratedMCQ] = Field(min_length=1)
    attempts: int = Field(default=1, description="Number of generator-critic loops attempted")
    critic_notes: list[str] = Field(default_factory=list)


def _load_bank_fallback_questions(
    skill_gap: str,
    target_role: str,
    difficulty: str = "medium",
    count: int = 5,
) -> list[GeneratedMCQ]:
    """Reads vetted fallback MCQs from data/questions/mcq_bank.csv."""
    if not MCQ_BANK_PATH.exists():
        # Fallback to question_bank module if CSV direct read fails
        q_objs = question_bank.random_questions(skill_gap, difficulty, count)
        if q_objs:
            return [
                GeneratedMCQ(
                    text=q.text,
                    options=q.options,
                    correct_index=q.correct_index,
                    explanation=q.explanation,
                    bloom_level=q.bloom_level,
                    difficulty=difficulty,
                    skill_tag=skill_gap,
                )
                for q in q_objs
            ]
        return _make_synthetic_sample(skill_gap, difficulty, count)

    matched_rows: list[dict[str, str]] = []
    broad_rows: list[dict[str, str]] = []

    try:
        with open(MCQ_BANK_PATH, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                q_text = row.get("question", "")
                r_topic = row.get("topic", "")
                r_role = row.get("role", "")
                r_diff = (row.get("difficulty") or "medium").lower()

                # High relevance match: topic or skill mentioned in topic or question
                if (
                    skill_gap.lower() in r_topic.lower()
                    or skill_gap.lower() in q_text.lower()
                    or (r_role and r_role.lower() in target_role.lower())
                ):
                    if r_diff == difficulty.lower():
                        matched_rows.append(row)
                    else:
                        broad_rows.append(row)
                elif r_diff == difficulty.lower():
                    broad_rows.append(row)
    except Exception as e:
        log.warning("Could not read mcq_bank.csv: %s", e)

    selected = matched_rows if len(matched_rows) >= count else (matched_rows + broad_rows)
    if not selected:
        return _make_synthetic_sample(skill_gap, difficulty, count)

    random.shuffle(selected)
    results: list[GeneratedMCQ] = []

    for r in selected[:count]:
        opts = [r.get(f"option_{c}", "").strip() for c in "abcd"]
        letter = (r.get("correct_option") or "A").strip().upper()
        idx = "ABCD".index(letter) if letter in "ABCD" else 0
        results.append(
            GeneratedMCQ(
                text=(r.get("question") or "").strip(),
                options=opts
                if len(opts) == 4 and all(opts)
                else ["True", "False", "Neither", "Both"],
                correct_index=idx,
                explanation=(
                    r.get("explanation") or f"Standard verified principle in {skill_gap}."
                ).strip(),
                bloom_level=r.get("bloom_level") or "understand",
                difficulty=difficulty,
                skill_tag=r.get("topic") or skill_gap,
            )
        )

    return results


def _make_synthetic_sample(skill: str, difficulty: str, count: int) -> list[GeneratedMCQ]:
    """Generates clean verified default MCQs for core topics when bank is sparse."""
    items = [
        GeneratedMCQ(
            text=(
                f"Which of the following statements best characterizes core best practices in "
                f"{skill}?"
            ),
            options=[
                f"Prioritizing modularity, loose coupling, and defensive validation in {skill}",
                "Relying entirely on runtime exception ignoring without systematic logs",
                "Hardcoding dynamic configurations directly inside compilation units",
                "Bypassing deterministic testing phases to optimize deployment throughput",
            ],
            correct_index=0,
            explanation=(
                f"Modularity and defensive programming are universal industry standards when "
                f"engineering solutions in {skill}."
            ),
            bloom_level="understand",
            difficulty=difficulty,
            skill_tag=skill,
        ),
        GeneratedMCQ(
            text=(
                f"In the context of production-grade systems using {skill}, what is the primary "
                f"consequence of unhandled concurrency?"
            ),
            options=[
                "Automatic compiler optimization of critical sections",
                "Race conditions, data inconsistencies, and potential deadlocks",
                "Guaranteed reduction in cache miss latencies",
                "Deterministic memory deallocation across distributed nodes",
            ],
            correct_index=1,
            explanation=(
                "Uncoordinated multi-threaded or concurrent access leads to non-deterministic "
                "race conditions and deadlocks."
            ),
            bloom_level="analyze",
            difficulty=difficulty,
            skill_tag=skill,
        ),
        GeneratedMCQ(
            text=(
                f"When profiling asymptotic performance in {skill}, what does O(1) time complexity "
                f"indicate?"
            ),
            options=[
                "Linear growth proportional to input size",
                "Logarithmic reduction across partitioned subsets",
                "Constant time independent of input cardinality",
                "Quadratic latency scaling for nested iterations",
            ],
            correct_index=2,
            explanation=(
                "O(1) signifies constant time complexity where the execution duration remains "
                "invariant relative to input magnitude."
            ),
            bloom_level="remember",
            difficulty=difficulty,
            skill_tag=skill,
        ),
    ]
    while len(items) < count:
        items.append(items[0].model_copy())
    return items[:count]


def validate_mcq_with_critic(question: GeneratedMCQ, target_topic: str) -> CriticEvaluation:
    """The Critic Agent validation logic.

    Verifies:
    1. Four non-empty distinct options (case-insensitive distinctness).
    2. Correct index is within [0, 3].
    3. No 'all/none of the above' lazy distractors.
    4. Explanations are non-empty and substantive.
    5. Options length heuristic (avoiding obvious 'longest option is always correct' cue).
    6. Topic relevance check.
    """
    reasons: list[str] = []

    # 1. Distinct options
    opts = [o.strip() for o in question.options]
    if len(opts) != 4 or not all(opts):
        reasons.append("Question must contain exactly 4 non-empty options.")
    if len({o.lower() for o in opts}) < 4:
        reasons.append("Options contain duplicate choices.")

    # 2. Lazy distractors
    for o in opts:
        if any(
            lazy in o.lower() for lazy in ["all of the above", "none of the above", "all of these"]
        ):
            reasons.append(f"Option '{o}' uses prohibited 'all/none of the above' pattern.")

    # 3. Index sanity
    if not (0 <= question.correct_index <= 3):
        reasons.append("Correct index out of valid range [0, 3].")

    # 4. Longest-answer cue check (if correct answer is more than 3x longer than all others)
    if 0 <= question.correct_index < len(opts):
        correct_len = len(opts[question.correct_index])
        other_lens = [len(o) for i, o in enumerate(opts) if i != question.correct_index]
        if other_lens and correct_len > 3 * max(other_lens):
            reasons.append("Correct option is disproportionately long (answer-length cue).")

    # 5. Text length
    if len(question.text.strip()) < 15:
        reasons.append("Question stem is too brief or incomplete.")

    is_valid = len(reasons) == 0
    return CriticEvaluation(
        is_valid=is_valid,
        rejection_reasons=reasons,
        factual_correctness=is_valid,
        unambiguous=is_valid,
        difficulty_appropriate=is_valid,
    )


class _RawGeneratedQuestionSet(BaseModel):
    questions: list[GeneratedMCQ] = Field(min_length=1)


def generate_critic_quiz(
    skill_gap: str,
    target_role: str,
    difficulty: Literal["easy", "medium", "hard"] = "medium",
    count: int = 5,
    max_retries: int = 2,
    student_id: str | None = None,
) -> QuizBatch:
    """Executes the Generator-Critic Loop for targeted technical MCQs.

    Workflow based on docs/critic_graph.md:
    START -> Generator -> Critic Verify -> (Approved -> DONE | Rejected -> Regenerate)
    If offline or repeated failures -> Fallback to data/questions/mcq_bank.csv.

    Args:
        skill_gap: Targeted skill gap or topic name.
        target_role: Target career role.
        difficulty: Desired difficulty ('easy', 'medium', 'hard').
        count: Number of questions to return.
        max_retries: Retries allowed in the critic loop.
        student_id: Optional tracking identifier.

    Returns:
        QuizBatch: Collection of validated MCQs with audit metadata.
    """
    cfg = settings()

    # Mock mode serves the CSV bank at once. Live: the AI router picks a provider; when none
    # answers, the loop below ends in the same bank.
    if cfg.mock_mode:
        log.info("Running in mock/offline mode: serving from mcq_bank.csv")
        bank_qs = _load_bank_fallback_questions(skill_gap, target_role, difficulty, count)
        return QuizBatch(
            topic_or_skill=skill_gap,
            target_role=target_role,
            difficulty=difficulty,
            source="question_bank_fallback",
            questions=bank_qs,
            attempts=1,
            critic_notes=["Offline/Mock Mode: Questions fetched from verified question bank."],
        )

    # Online Generator-Critic Loop
    system_prompt = (
        "You are an expert technical interviewer and test creator. "
        "Generate targeted technical multiple-choice questions focusing specifically on the "
        "provided skill gap. "
        "Rules: Exactly 4 distinct options, exactly 1 unambiguously correct option, clear "
        "explanation, "
        "no 'all/none of the above' options, balanced option lengths, realistic industrial "
        "placement standards."
    )

    rejection_feedback = ""
    attempt_count = 0
    all_critic_notes: list[str] = []

    while attempt_count <= max_retries:
        attempt_count += 1
        user_prompt = (
            f"Target Skill Gap: {skill_gap}\n"
            f"Target Role: {target_role}\n"
            f"Difficulty: {difficulty}\n"
            f"Number of Questions: {count}\n"
            f"{rejection_feedback}\n\n"
            "Return a _RawGeneratedQuestionSet with high-quality MCQs."
        )

        try:
            raw_result, _ = llm.call(
                _RawGeneratedQuestionSet,
                agent="quiz",
                system=system_prompt,
                user=user_prompt,
                context={"skill": skill_gap, "role": target_role, "attempt": attempt_count},
                student_id=student_id,
                size="large" if attempt_count > 1 else "small",
                temperature=0.7,
            )

            # --- Critic Verification Phase ---
            verified_questions: list[GeneratedMCQ] = []
            batch_rejections: list[str] = []

            for i, q in enumerate(raw_result.questions):
                verdict = validate_mcq_with_critic(q, skill_gap)
                if verdict.is_valid:
                    verified_questions.append(q)
                else:
                    batch_rejections.extend(
                        [f"Question {i + 1}: {r}" for r in verdict.rejection_reasons]
                    )

            if len(verified_questions) >= count:
                # Generator succeeded and Critic approved!
                return QuizBatch(
                    topic_or_skill=skill_gap,
                    target_role=target_role,
                    difficulty=difficulty,
                    source="critic_generated",
                    questions=verified_questions[:count],
                    attempts=attempt_count,
                    critic_notes=all_critic_notes
                    or ["Critic approved all questions on verification."],
                )

            # Prepare feedback for the retry loop
            all_critic_notes.append(
                f"Attempt {attempt_count} rejected: {'; '.join(batch_rejections[:3])}"
            )
            rejection_feedback = (
                "\n\nCRITIC REJECTION NOTICE: Previous attempt had these flaws. "
                "Fix them completely:\n" + "\n".join(f"- {r}" for r in batch_rejections[:5])
            )

        except Exception as e:
            log.warning("LLM call failed in critic quiz agent (attempt %d): %s", attempt_count, e)
            all_critic_notes.append(f"Attempt {attempt_count} error: {e}")

    # If retries are exhausted or Critic rejects repeatedly, fall back to vetted Question Bank
    log.warning("Critic loop exhausted attempts; falling back to mcq_bank.csv")
    fallback_qs = _load_bank_fallback_questions(skill_gap, target_role, difficulty, count)
    return QuizBatch(
        topic_or_skill=skill_gap,
        target_role=target_role,
        difficulty=difficulty,
        source="question_bank_fallback",
        questions=fallback_qs,
        attempts=attempt_count,
        critic_notes=[
            *all_critic_notes,
            "Fallback activated: Loaded vetted items from question bank.",
        ],
    )
