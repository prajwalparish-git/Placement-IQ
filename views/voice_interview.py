"""Live Voice Mock Interview: Step 5 interactive voice simulation.

Features:
- Stream-tailored scenario questions:
  * Engineering: System design & coding logic
  * Commerce: Financial audit & GST filing dispute
  * Law: Moot court & contractual breach interpretation
  * Management: HR grievance & marketing case study
- Speech Synthesis via ElevenLabs API (with automatic fallback to browser HTML5 / Web Speech API)
- Student Voice Input with audio recording (st.audio_input / HTML5) + Whisper transcription
- Comprehensive 0-15 Rubric Evaluation:
  * Content Knowledge & Technical Relevancy (0-5)
  * Verbal Clarity & Structure (STAR format) (0-5)
  * Confidence & Professional Demeanor (0-5)
- Automated detection of suspicious gaps, pauses, or off-topic hallucinations.
"""

from __future__ import annotations

import base64
import os

import streamlit as st

from agents.rubric_evaluator_agent import evaluate_rubric_answer, transcribe_audio_with_whisper
from agents.voice_interview_agent import (
    VoiceInterviewQuestion,
    generate_voice_interview_question,
    get_stream_from_role_or_domain,
)
from piq.ui import empty_state, page_header, require_profile

VOICE_AVATAR = ":material/graphic_eq:"
EVAL_AVATAR = ":material/analytics:"

page_header(
    "Live Voice Mock Interview",
    (
        "Practice oral interviews with realistic voice synthesis, scenario simulations across "
        "disciplines, and instant 0-15 point rubric scoring."
    ),
)

profile = require_profile()
if not profile:
    st.stop()

sid = (
    profile.student_id
    if hasattr(profile, "student_id")
    else st.session_state.get("student_id", "DEMO")
)
role = profile.target_role
default_stream = get_stream_from_role_or_domain(role)

# Session state initialization
if "voice_session_question" not in st.session_state:
    st.session_state["voice_session_question"] = None
if "voice_session_evaluation" not in st.session_state:
    st.session_state["voice_session_evaluation"] = None
if "voice_transcribed_text" not in st.session_state:
    st.session_state["voice_transcribed_text"] = ""

# Sidebar config / Session Setup
setup_col, preview_col = st.columns([1, 1], gap="large")

with setup_col, st.container(border=True):
    st.subheader("Interview Configuration", anchor=False)
    selected_stream = st.selectbox(
        "Discipline Stream",
        ["Engineering", "Commerce", "Law", "Management"],
        index=["Engineering", "Commerce", "Law", "Management"].index(default_stream)
        if default_stream in ["Engineering", "Commerce", "Law", "Management"]
        else 0,
        help="Select the discipline track to target role-specific situational scenarios.",
    )
    selected_category = st.radio(
        "Question Type",
        ["technical", "situational", "behavioral"],
        index=1,
        format_func=lambda c: c.capitalize(),
        horizontal=True,
    )

    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not elevenlabs_key:
        st.caption(
            "ℹ️ *Using browser HTML5 speech fallback. Set `ELEVENLABS_API_KEY` for "
            "high-definition neural voices.*"
        )

    if st.button("Generate Interview Scenario", type="primary", icon=":material/play_circle:"):
        q = generate_voice_interview_question(
            target_role=role,
            stream=selected_stream,
            category=selected_category,
            include_audio=bool(elevenlabs_key),
            elevenlabs_key=elevenlabs_key,
        )
        st.session_state["voice_session_question"] = q
        st.session_state["voice_session_evaluation"] = None
        st.session_state["voice_transcribed_text"] = ""
        st.rerun()

with preview_col, st.container(border=True):
    st.subheader("Evaluation Standards (0-15 Rubric)", anchor=False)
    st.markdown(
        """
            - **Content Knowledge & Domain Relevancy (0–5 pts):** Accuracy, technical depth,
              operational mechanics.
            - **Verbal Clarity & Structure (STAR) (0–5 pts):** Situation, Task, Action, Result
              methodology.
            - **Confidence & Professional Demeanor (0–5 pts):** Composure, articulate phrasing,
              absence of deflection.
            - **Suspicious Gap Flags:** Identifies terse responses (<20 words), off-topic drift,
              or buzzword clustering.
            """
    )

current_q: VoiceInterviewQuestion | None = st.session_state["voice_session_question"]

if not current_q:
    empty_state(
        "Ready for your voice interview",
        (
            "Choose your discipline stream and question category above, then click 'Generate "
            "Interview Scenario' to begin."
        ),
        ":material/mic:",
    )
    st.stop()

st.divider()

# --- Active Scenario Display ---
with st.container(border=True):
    col_badge, col_type = st.columns([3, 1])
    with col_badge:
        st.caption(f"Stream: **{current_q.stream}** | Scenario: **{current_q.scenario_context}**")
    with col_type:
        st.caption(f"Category: **{current_q.category.upper()}**")

    st.markdown(f"### 🎙️ {current_q.question_text}")
    st.info(f"**Interviewer Focus:** {current_q.intent}", icon=":material/info:")

    # Audio playback: ElevenLabs MP3 or HTML5 Web Speech Synthesis
    if current_q.audio_base64:
        st.audio(base64.b64decode(current_q.audio_base64), format="audio/mp3")
    else:
        # Browser-based speech synthesis fallback
        clean_text_js = current_q.question_text.replace("'", "\\'").replace('"', '\\"')
        tts_html = f"""
        <div style="margin-top: 8px;">
            <button onclick="speakQuestion()"
                style="background-color: #4F46E5; color: white; border: none;
                padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500;">
                🔊 Read Aloud (Browser TTS)
            </button>
            <script>
            function speakQuestion() {{
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    var msg = new SpeechSynthesisUtterance('{clean_text_js}');
                    msg.rate = 1.0;
                    msg.pitch = 1.0;
                    window.speechSynthesis.speak(msg);
                }} else {{
                    alert('Web Speech API is not supported in this browser.');
                }}
            }}
            </script>
        </div>
        """
        st.components.v1.html(tts_html, height=50)

# --- Student Response & Recording ---
st.subheader("Your Response", anchor=False)

record_tab, text_tab = st.tabs(["🎤 Voice Recording", "✍️ Written Transcript Mode"])
student_audio_bytes: bytes | None = None
student_text_input: str = ""

with record_tab:
    recorded_audio = st.audio_input("Record your spoken answer")
    if recorded_audio:
        student_audio_bytes = recorded_audio.read()
        st.audio(student_audio_bytes)

with text_tab:
    student_text_input = st.text_area(
        "Type your answer directly or paste an external transcript:",
        value=st.session_state.get("voice_transcribed_text", ""),
        placeholder=(
            "Structure your answer with the STAR format (Situation, Task, Action, Result)..."
        ),
        height=140,
    )

submit_col, reset_col = st.columns([1, 4])
with submit_col:
    eval_clicked = st.button("Submit & Evaluate", type="primary", icon=":material/grading:")

if eval_clicked:
    final_answer = student_text_input.strip()

    # If audio was recorded, transcribe it with Whisper
    if student_audio_bytes and not final_answer:
        with st.spinner("Transcribing audio via Whisper..."):
            final_answer = transcribe_audio_with_whisper(student_audio_bytes)
            st.session_state["voice_transcribed_text"] = final_answer

    if not final_answer:
        st.warning("Please record your voice or provide a written response before submitting.")
        st.stop()

    with st.spinner("Rubric Evaluator Agent analyzing response..."):
        evaluation = evaluate_rubric_answer(
            question=current_q.question_text,
            answer_text=final_answer,
            stream=current_q.stream,
            target_role=current_q.role,
            student_id=sid,
        )
        st.session_state["voice_session_evaluation"] = evaluation

# --- Rubric Feedback Display ---
eval_res = st.session_state["voice_session_evaluation"]
if eval_res:
    st.divider()
    st.subheader("Rubric Evaluation Breakdown (0–15 Score)", anchor=False)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Score", f"{eval_res.rubric.total_score} / 15", eval_res.performance_tier)
    with col2:
        st.metric("Content Knowledge", f"{eval_res.rubric.content_knowledge} / 5")
    with col3:
        st.metric("STAR Structure", f"{eval_res.rubric.verbal_clarity_star} / 5")
    with col4:
        st.metric("Confidence & Demeanor", f"{eval_res.rubric.confidence_demeanor} / 5")

    # Gap flags if any triggered
    if eval_res.gap_flags.flag_details:
        with st.container(border=True):
            st.markdown("⚠️ **Suspicious Delivery Patterns Detected:**")
            for flag in eval_res.gap_flags.flag_details:
                st.caption(f"• {flag}")

    st.markdown("#### Candidate Transcribed Response")
    st.write(eval_res.transcribed_response)

    col_str, col_imp = st.columns(2, gap="medium")
    with col_str, st.container(border=True):
        st.markdown("**:primary[:material/check_circle:] Key Strengths**")
        for s in eval_res.strengths:
            st.markdown(f"- {s}")

    with col_imp, st.container(border=True):
        st.markdown("**:primary[:material/warning:] Areas for Improvement**")
        for a in eval_res.areas_for_improvement:
            st.markdown(f"- {a}")

    with st.expander("Exemplary Model Answer (STAR Benchmark)", icon=":material/star:"):
        st.markdown(eval_res.exemplary_model_answer)
