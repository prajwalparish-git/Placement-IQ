"""Layer 2 Multi-Agent Orchestration Layer package for Skill Scout Nexus.

Modular sub-agents:
- resume_parser_agent: extracts candidate skills, degree/stream, match % and missing gaps.
- study_planner_agent: generates adaptive 7-day roadmaps with objectives, links, and micro-tasks.
- critic_quiz_agent: Generator-Critic loop with factual/ambiguity validation and question bank fallback.
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
from agents.study_planner_agent import (
    DailyRoadmap,
    ResourceLink,
    SevenDayRoadmap,
    generate_study_roadmap,
)

__all__ = [
    "CandidateDegree",
    "CriticEvaluation",
    "DailyRoadmap",
    "GeneratedMCQ",
    "QuizBatch",
    "ResourceLink",
    "ResumeAnalysisResult",
    "SevenDayRoadmap",
    "generate_critic_quiz",
    "generate_study_roadmap",
    "parse_resume",
]
