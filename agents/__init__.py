"""Layer 2 & Layer 5 Multi-Agent Orchestration Layer package for Skill Scout Nexus.

Modular sub-agents:
- resume_parser_agent: extracts candidate skills, degree/stream, match % and missing gaps.
- study_planner_agent: generates adaptive 7-day roadmaps with objectives, links, and micro-tasks.
- critic_quiz_agent: Generator-Critic loop with factual/ambiguity validation and question bank fallback.
- voice_interview_agent: ElevenLabs speech synthesis and stream-specific behavioral/scenario questions.
- rubric_evaluator_agent: 0-15 point rubric evaluation (Knowledge, STAR Clarity, Confidence) & gap flags.
"""

from agents.critic_quiz_agent import (
    CriticEvaluation,
    GeneratedMCQ,
    QuizBatch,
    generate_critic_quiz,
)
from agents.resume_parser_agent import (
    CandidateDegree,
    ResumeAnalysisResult,
    parse_resume,
)
from agents.rubric_evaluator_agent import (
    RubricBreakdown,
    RubricEvaluationResult,
    SuspiciousGapFlags,
    evaluate_rubric_answer,
    transcribe_audio_with_whisper,
)
from agents.study_planner_agent import (
    DailyRoadmap,
    ResourceLink,
    SevenDayRoadmap,
    generate_study_roadmap,
)
from agents.voice_interview_agent import (
    VoiceInterviewQuestion,
    generate_voice_interview_question,
    synthesize_speech_elevenlabs,
)

__all__ = [
    "CandidateDegree",
    "CriticEvaluation",
    "DailyRoadmap",
    "GeneratedMCQ",
    "QuizBatch",
    "ResourceLink",
    "ResumeAnalysisResult",
    "RubricBreakdown",
    "RubricEvaluationResult",
    "SevenDayRoadmap",
    "SuspiciousGapFlags",
    "VoiceInterviewQuestion",
    "evaluate_rubric_answer",
    "generate_critic_quiz",
    "generate_study_roadmap",
    "generate_voice_interview_question",
    "parse_resume",
    "synthesize_speech_elevenlabs",
    "transcribe_audio_with_whisper",
]
