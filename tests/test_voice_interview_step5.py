"""Unit tests for Step 5: ElevenLabs Voice Mock Interview and Rubric Evaluator Agent."""

import pytest

from agents.voice_interview_agent import (
    DOMAIN_SCENARIOS,
    VoiceInterviewQuestion,
    generate_voice_interview_question,
    get_stream_from_role_or_domain,
    synthesize_speech_elevenlabs,
)
from agents.rubric_evaluator_agent import (
    RubricEvaluationResult,
    SuspiciousGapFlags,
    _detect_suspicious_gaps,
    evaluate_rubric_answer,
    transcribe_audio_with_whisper,
)


def test_get_stream_from_role_or_domain():
    assert get_stream_from_role_or_domain("Full Stack Developer") == "Engineering"
    assert get_stream_from_role_or_domain("Chartered Accountant", "commerce") == "Commerce"
    assert get_stream_from_role_or_domain("Corporate Lawyer", "law") == "Law"
    assert get_stream_from_role_or_domain("HR Manager", "corp") == "Management"


def test_generate_voice_interview_question_across_streams():
    for stream in ["Engineering", "Commerce", "Law", "Management"]:
        q = generate_voice_interview_question(
            target_role="Specialist",
            stream=stream,
            category="technical",
            include_audio=False,
        )
        assert isinstance(q, VoiceInterviewQuestion)
        assert q.stream == stream
        assert len(q.question_text) > 20
        assert q.intent != ""
        assert q.tts_source == "browser_fallback"


def test_voice_synthesis_fallback_without_key():
    audio, source = synthesize_speech_elevenlabs("Testing interview question", api_key="")
    assert audio is None
    assert source == "browser_fallback"


def test_suspicious_gap_detection():
    # Terse answer (< 20 words)
    gaps_terse = _detect_suspicious_gaps(
        question="How would you design a distributed caching layer?",
        answer_text="I will use redis for this.",
    )
    assert gaps_terse.excessive_silence_or_terse is True

    # Off-topic deflection
    gaps_offtopic = _detect_suspicious_gaps(
        question="Explain how you reconcile input tax credit discrepancies between GSTR-2B and GSTR-3B.",
        answer_text="The weather in Bengaluru is very pleasant today and cricket is my favorite sport to play on weekends.",
    )
    assert gaps_offtopic.off_topic_hallucination is True


def test_rubric_evaluator_agent_scoring():
    question = (
        "During a statutory year-end audit, you notice a material mismatch between vendor ledger balances "
        "and physical stock registers. How do you design your audit procedure?"
    )
    answer = (
        "In my audit internship at a mid-tier accounting firm, we encountered a similar 15% discrepancy in inventory. "
        "I first established a sampling threshold under SA 530 and vouched high-value purchase orders against goods "
        "received notes (GRNs) and e-way bills. Then, I cross-verified physical inventory counts with cutoff tests. "
        "As a result, we identified two duplicate invoices, reconciled the ledger discrepancy, and issued an unqualified audit opinion."
    )

    eval_result = evaluate_rubric_answer(
        question=question,
        answer_text=answer,
        stream="Commerce",
        target_role="Chartered Accountant",
    )

    assert isinstance(eval_result, RubricEvaluationResult)
    assert 0 <= eval_result.rubric.content_knowledge <= 5
    assert 0 <= eval_result.rubric.verbal_clarity_star <= 5
    assert 0 <= eval_result.rubric.confidence_demeanor <= 5
    assert 0 <= eval_result.rubric.total_score <= 15
    assert eval_result.rubric.total_score >= 8
    assert len(eval_result.strengths) >= 1
    assert len(eval_result.areas_for_improvement) >= 1
    assert eval_result.gap_flags.excessive_silence_or_terse is False


def test_whisper_transcription_fallback():
    text = transcribe_audio_with_whisper(b"fake_audio_bytes")
    assert isinstance(text, str)
    assert len(text) > 10
