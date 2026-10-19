"""Streamlit entry point: `streamlit run app.py`."""

import logging

import streamlit as st

from piq import db
from piq.config import ConfigError, settings
from piq.ui import student_selector
from scripts.seed import main as seed_demo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
st.set_page_config(page_title="PlacementIQ", page_icon="🎯", layout="wide")

try:
    cfg = settings()
except ConfigError as e:
    st.error(str(e))
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

st.sidebar.title("🎯 PlacementIQ")
if cfg.mock_mode:
    st.sidebar.warning("MOCK_MODE: canned responses, no API calls.")
student_selector()

st.navigation(
    [
        st.Page("views/onboard.py", title="Onboard", icon="📄", default=True),
        st.Page("views/plan.py", title="Weekly plan", icon="🗓️"),
        st.Page("views/quiz.py", title="Quiz", icon="📝"),
        st.Page("views/interview.py", title="Mock interview", icon="🎤"),
        st.Page("views/dashboard.py", title="Dashboard", icon="📈"),
        st.Page("views/results.py", title="Results", icon="🧪"),
    ]
).run()
