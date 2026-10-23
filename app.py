"""Streamlit entry point: `streamlit run app.py`."""

import logging

import streamlit as st

from piq import db, formatter
from piq.config import BRAND_DIR, ConfigError, settings
from piq.ui import load_css, sidebar_context, student_selector
from scripts.seed import main as seed_demo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
st.set_page_config(page_title="PlacementIQ", page_icon=str(BRAND_DIR / "mark.svg"), layout="wide")
st.logo(str(BRAND_DIR / "wordmark.svg"), icon_image=str(BRAND_DIR / "mark.svg"), size="large")
load_css()

try:
    cfg = settings()
except ConfigError as e:
    st.error(formatter.md_escape(str(e)))
    st.stop()


@st.cache_resource
def _startup() -> None:
    db.init_db()
    if cfg.seed_demo and not db.list_students():  # hosted disks reset on every restart
        seed_demo()
    logging.getLogger("piq").info(
        "mock_mode=%s large=%s small=%s db=%s",
        cfg.mock_mode,
        cfg.model_large or "-",
        cfg.model_small or "-",
        cfg.db_path,
    )


_startup()

student_selector()
sidebar_context(mock_mode=cfg.mock_mode)

# Sidebar navigation keeps every page visible with the student context beneath it; a top
# bar would fold the sections into menus, which is worse on a projector (docs/design).
st.navigation(
    {
        "Prepare": [
            st.Page("views/home.py", title="Home", icon=":material/home:", default=True),
            st.Page("views/onboard.py", title="Onboard", icon=":material/upload_file:"),
            st.Page("views/plan.py", title="Weekly plan", icon=":material/calendar_month:"),
            st.Page("views/quiz.py", title="Quiz", icon=":material/quiz:"),
            st.Page(
                "views/interview.py", title="Mock interview", icon=":material/record_voice_over:"
            ),
        ],
        "Insights": [
            st.Page("views/dashboard.py", title="Dashboard", icon=":material/monitoring:"),
            st.Page("views/results.py", title="Results", icon=":material/fact_check:"),
        ],
    },
    position="sidebar",
).run()
