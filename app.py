from __future__ import annotations

from pathlib import Path

import streamlit as st

from clipper.config import load_config
from clipper.jobs import JobManager
from clipper.source import SourceError


st.set_page_config(
    page_title="MyClip — Local AI Clipper",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: #0b0d12; color: #e7eaf0; }
    [data-testid="stSidebar"] { background: #11141c; border-right: 1px solid #252a36; }
    .hero { padding: 1.3rem 0 0.5rem; }
    .hero h1 { letter-spacing: -0.04em; margin-bottom: .2rem; }
    .hero p { color: #9aa4b2; font-size: 1.05rem; }
    div[data-testid="stMetric"] { background: #141923; padding: 1rem; border-radius: 12px; }
    div.stButton > button[kind="primary"] { background: #8b5cf6; border: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_manager() -> JobManager:
    return JobManager()


manager = get_manager()
config = load_config()

with st.sidebar:
    st.title("✂️ MyClip")
    st.caption("Private, local-first video clipping")
    output_dir_value = st.text_input(
        "Output folder",
        value=str(config.output_dir),
        help="Downloaded source videos and finished clips stay in this folder.",
    )
    st.caption(f"Local model: `{config.ollama_model}`")
    st.caption(f"Speech model: `{config.whisper_model}`")
    st.divider()
    st.markdown(
        "**Local services required**\n\n"
        "- FFmpeg + FFprobe\n"
        "- Ollama running with the selected model\n"
        "- First transcription downloads the Whisper model"
    )
    st.caption("No accounts, paid APIs, quotas, or automatic clip deletion.")

st.markdown(
    '<div class="hero"><h1>Make the moments worth sharing.</h1>'
    "<p>Describe the clips you want. MyClip finds, captions, and exports them "
    "on this Mac.</p></div>",
    unsafe_allow_html=True,
)

with st.form("new_job", clear_on_submit=False):
    youtube_url = st.text_input(
        "YouTube video URL",
        placeholder="https://www.youtube.com/watch?v=...",
    )
    instruction = st.text_area(
        "What should the clips capture?",
        value=(
            "Find the funniest moments from this gaming livestream. Prioritize "
            "unexpected reactions, clutch situations, and funny conversations. "
            "Choose moments that make sense without watching the entire stream."
        ),
        height=115,
    )
    first, second, third = st.columns(3)
    with first:
        clip_count = st.number_input(
            "Number of clips", min_value=1, value=5, step=1
        )
        min_duration = st.number_input(
            "Minimum duration (seconds)", min_value=1, value=30, step=1
        )
    with second:
        max_duration = st.number_input(
            "Maximum duration (seconds)", min_value=1, value=60, step=1
        )
        aspect_ratio = st.selectbox(
            "Output aspect ratio", ["9:16", "original", "16:9"]
        )
    with third:
        caption_style = st.selectbox(
         "Caption style",
         ["None", "Standard", "Bold"],
    index=0,
    )
    permission = st.checkbox(
        "I have permission to download and process this video. I understand "
        "MyClip only handles publicly accessible videos and does not bypass access controls."
    )
    submitted = st.form_submit_button(
        "✨  Find and create clips", type="primary", use_container_width=True
    )

if submitted:
    if not permission:
        st.error("Confirm that you have permission to process this video.")
    elif not youtube_url.strip():
        st.error("Enter a YouTube video URL.")
    elif not instruction.strip():
        st.error("Describe the kind of moments you want.")
    elif not output_dir_value.strip():
        st.error("Choose a local output folder.")
    elif min_duration > max_duration:
        st.error("Minimum duration must not exceed maximum duration.")
    else:
        settings = {
            "clip_count": int(clip_count),
            "min_duration": float(min_duration),
            "max_duration": float(max_duration),
            "aspect_ratio": aspect_ratio,
            "caption_style": caption_style,
            "output_dir": str(Path(output_dir_value).expanduser()),
        }
        try:
            job_id, created = manager.submit(youtube_url, instruction, settings)
            if created:
                st.session_state["selected_job_id"] = job_id
                st.success("Job started. Progress and results update below.")
            else:
                st.session_state["selected_job_id"] = job_id
                st.info("An identical job is already processing; showing its progress.")
        except SourceError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Could not start the background job: {exc}")

st.divider()

jobs = manager.database.list_jobs(limit=100)
selected_job_id = st.session_state.get("selected_job_id")
if selected_job_id:
    selected_job = manager.database.get(selected_job_id)
    if selected_job:
        st.subheader("Current job")
        st.caption(selected_job["url"])
        st.progress(
            selected_job["progress"],
            text=selected_job["message"] or selected_job["stage"],
        )
        if selected_job["status"] == "failed":
            st.error(selected_job["error"] or "Processing failed.")
        elif selected_job["status"] == "completed":
            st.success(selected_job["message"])
        for clip in selected_job["clips"]:
            st.markdown(f"**{clip['title']}** · {clip['start']:.1f}s–{clip['end']:.1f}s · score {clip['score']:.0f}")
            clip_path = Path(clip["output_path"])
            if clip_path.is_file():
                st.video(str(clip_path))
                st.download_button(
                    f"Download {clip_path.name}",
                    data=clip_path.read_bytes(),
                    file_name=clip_path.name,
                    mime="video/mp4",
                    key=f"download-{selected_job_id}-{clip_path.name}",
                )
            st.caption(f"Why this moment: {clip['reason']}")
        if selected_job["status"] in {"queued", "running"}:
            st.caption("This page refreshes automatically while processing.")
            from streamlit_autorefresh import st_autorefresh

            st_autorefresh(interval=3000, key=f"refresh-{selected_job_id}")

with st.expander("Job history", expanded=not bool(selected_job_id)):
    if not jobs:
        st.caption("Your completed and previous jobs will appear here.")
    else:
        for job in jobs:
            left, right = st.columns([5, 1])
            with left:
                st.markdown(
                    f"**{job['status'].upper()}** · "
                    f"{job['created_at'][:19].replace('T', ' ')} · {job['url']}"
                )
                st.caption(job["message"])
            with right:
                if st.button("Open", key=f"open-{job['id']}"):
                    st.session_state["selected_job_id"] = job["id"]
                    st.rerun()
            st.progress(job["progress"])
