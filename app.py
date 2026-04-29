"""LinkedIn Job & Skills Analyzer — main Streamlit application.

Tabs:
  1. 🔍 Job Role Research   — search jobs, view companies & skills
  2. 📊 Skills Analysis     — AI-generated skill trends
  3. 🎯 Skill Gap Analysis  — compare your skills against a job posting
  4. 📚 Learning Path       — personalised recommendations
  5. 📄 Resume Analyzer     — upload resume → matching jobs / gap + training
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.ai_engine import AIEngine
from src.config import Config
from src.job_searcher import JobPosting, JobSearcher
from src.learning_recommender import LearningRecommender
from src.resume_parser import parse_resume
from src.skill_analyzer import frequency_map, normalize_skills

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="LinkedIn Job & Skills Analyzer",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": "https://github.com/arunsuthar98/linkedin-job-analyzer-tool/issues",
        "Report a bug": "https://github.com/arunsuthar98/linkedin-job-analyzer-tool/issues/new",
        "About": (
            "**LinkedIn Job & Skills Analyzer** v1.2.0  \n"
            "Open-source AI career assistant — built by [Arun Suthar](https://github.com/arunsuthar98).  \n"
            "Licensed under MIT."
        ),
    },
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

_css_path = Path(__file__).parent / "assets" / "style.css"
if _css_path.exists():
    st.markdown(f"<style>{_css_path.read_text()}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session-state defaults
# ---------------------------------------------------------------------------

DEFAULTS = {
    "postings": [],
    "is_mock": True,
    "skills_analysis": None,
    "role_overview": None,
    "selected_job_idx": None,
    "gap_analysis": None,
    "learning_path": None,
    "user_skills": [],
    "search_done": False,
    "job_role": "",
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------------------------------------------------------
# Sidebar — API keys
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("⚙️ Configuration")
    st.success("✅ App is pre-configured and ready to use!")
    st.markdown(
        "The app works out of the box with default API keys.  \n"
        "You can optionally enter **your own keys** below to use your personal quota."
    )
    st.divider()

    cfg = Config()  # loads from .env / Streamlit secrets if present

    with st.expander("🔑 Use my own API keys (optional)"):
        groq_key_input = st.text_input(
            "Groq API Key (FREE)",
            value="",
            type="password",
            placeholder="gsk_... (get free at console.groq.com)",
        )
        openai_key_input = st.text_input(
            "OpenAI API Key (optional)",
            value="",
            type="password",
            placeholder="sk-...",
        )
        jsearch_key_input = st.text_input(
            "JSearch API Key (RapidAPI)",
            value="",
            type="password",
            placeholder="Your RapidAPI key",
        )
        youtube_key_input = st.text_input(
            "YouTube Data API Key",
            value="",
            type="password",
            placeholder="AIza...",
        )
        cfg.update_from_ui(
            groq_key=groq_key_input or None,
            openai_key=openai_key_input or None,
            jsearch_key=jsearch_key_input or None,
            youtube_key=youtube_key_input or None,
        )

    st.divider()
    st.markdown("**Status**")
    if cfg.has_groq:
        st.markdown("✅ Groq AI — active (FREE)")
    elif cfg.has_openai:
        st.markdown("✅ OpenAI — active")
    else:
        st.markdown("⚠️ No AI key found")
    st.markdown(f"{'✅' if cfg.has_jsearch else '🔶'} JSearch — {'live data' if cfg.has_jsearch else 'demo mode'}")
    st.markdown(f"{'✅' if cfg.has_youtube else '🔶'} YouTube — {'connected' if cfg.has_youtube else 'URL fallback'}")

    st.divider()
    st.caption(
        "💡 **Get your own free keys:**\n"
        "- [Groq (FREE)](https://console.groq.com)\n"
        "- [RapidAPI / JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)\n"
        "- [YouTube Data API](https://console.cloud.google.com/apis/library/youtube.googleapis.com)\n"
        "- [OpenAI](https://platform.openai.com/api-keys)"
    )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="hero">
        <h1>💼 LinkedIn Job & Skills Analyzer</h1>
        <p>Your AI-powered career copilot — discover jobs, analyse skills, close gaps, and build a personalised learning roadmap.</p>
        <div class="badges">
            <span class="badge">🤖 Powered by Free AI (Groq)</span>
            <span class="badge">🆓 100% Open Source</span>
            <span class="badge">⚡ Instant Insights</span>
            <span class="badge">📄 Resume Analyzer</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Feature cards (only shown when user hasn't searched yet — keeps UI clean later)
if not st.session_state.get("search_done") and not st.session_state.get("resume_analysis"):
    fc1, fc2, fc3, fc4, fc5 = st.columns(5)
    cards = [
        (fc1, "🔍", "Job Search", "Real-time postings from LinkedIn, Indeed & Glassdoor"),
        (fc2, "📊", "AI Skills", "Trending skills extracted from real job descriptions"),
        (fc3, "🎯", "Skill Gap", "Honest readiness score against any job"),
        (fc4, "📚", "Learning Path", "Personalised roadmap with videos & courses"),
        (fc5, "📄", "Resume Match", "Upload resume → AI finds your best-fit roles"),
    ]
    for col, icon, title, desc in cards:
        with col:
            st.markdown(
                f"""<div class="feature-card">
                    <div class="icon">{icon}</div>
                    <h4>{title}</h4>
                    <p>{desc}</p>
                </div>""",
                unsafe_allow_html=True,
            )

if not cfg.has_any_ai:
    st.warning(
        "⚠️ No AI key configured. If you're running locally, add a free Groq key to your `.env` file.  \n"
        "See [docs/API_KEYS.md](docs/API_KEYS.md) for instructions."
    )

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["🔍 Job Research", "📊 Skills Trends", "🎯 Skill Gap", "📚 Learning Path", "📄 Resume Match", "✍️ Resume Coach"]
)

# ============================================================
# TAB 1 — Job Role Research
# ============================================================

with tab1:
    st.header("🔍 Job Role Research")
    st.markdown("Search for jobs and discover which companies are hiring and what skills they need.")

    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        job_role = st.text_input(
            "Job Role",
            value=st.session_state.job_role or "",
            placeholder="e.g. Data Scientist, Backend Engineer, Product Manager",
        )
    with col2:
        location = st.text_input("Location (optional)", placeholder="e.g. London, Remote, New York")
    with col3:
        remote_only = st.checkbox("Remote only")

    max_results = st.slider("Max job postings to fetch", 5, 50, 20, step=5)

    search_clicked = st.button("🔍 Search Jobs", type="primary", use_container_width=True)

    if search_clicked and job_role.strip():
        st.session_state.job_role = job_role.strip()
        # Reset downstream state
        for key in ["postings", "skills_analysis", "role_overview",
                    "selected_job_idx", "gap_analysis", "learning_path", "search_done"]:
            st.session_state[key] = DEFAULTS[key]

        searcher = JobSearcher(
            api_key=cfg.jsearch_api_key,
            cache_ttl=cfg.cache_ttl_seconds,
        )
        with st.spinner("Searching job postings…"):
            try:
                postings, is_mock = searcher.search(
                    job_role=job_role.strip(),
                    location=location,
                    remote_only=remote_only,
                    max_results=max_results,
                )
                st.session_state.postings = postings
                st.session_state.is_mock = is_mock
                st.session_state.search_done = True
            except RuntimeError as e:
                st.error(f"Search failed: {e}")

    if st.session_state.search_done:
        postings: list[JobPosting] = st.session_state.postings
        is_mock: bool = st.session_state.is_mock

        if is_mock:
            st.info(
                "🔶 **Demo mode** — showing sample data.  \n"
                "Add a JSearch API key in the sidebar to fetch live postings."
            )

        if not postings:
            st.warning("No job postings found. Try a different role or location.")
        else:
            import pandas as pd
            import plotly.express as px

            st.success(f"Found **{len(postings)}** job postings for **{st.session_state.job_role}**")

            # Build DataFrame for tables/charts
            df_jobs = pd.DataFrame([{
                "Title": p.title,
                "Company": p.company,
                "Location": p.location,
                "Type": p.employment_type or "—",
                "Remote": "🌐" if p.is_remote else "",
                "Posted": (p.date_posted or "")[:10] or "—",
                "Source": p.source or "—",
                "Apply": p.url or "",
            } for p in postings])

            # ── KPI metrics ──
            searcher_tmp = JobSearcher(api_key=None)
            companies = searcher_tmp.top_companies(postings)
            remote_count = sum(1 for p in postings if p.is_remote)
            unique_locations = len({p.location for p in postings if p.location})

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📋 Jobs", len(postings))
            m2.metric("🏢 Companies", len(companies))
            m3.metric("🌐 Remote", remote_count)
            m4.metric("📍 Locations", unique_locations)

            st.markdown('<hr class="gradient-divider">', unsafe_allow_html=True)

            # ── Charts ──
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                top_co_df = pd.DataFrame(companies[:10], columns=["Company", "Postings"])
                if not top_co_df.empty:
                    fig = px.bar(
                        top_co_df, x="Postings", y="Company", orientation="h",
                        title="🏢 Top Companies Hiring",
                        color="Postings", color_continuous_scale="Blues",
                    )
                    fig.update_layout(height=380, yaxis={"categoryorder": "total ascending"},
                                      showlegend=False, margin=dict(l=0, r=0, t=40, b=0),
                                      template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                                      plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True)

            with chart_col2:
                all_skills = [p.skills_raw for p in postings if p.skills_raw]
                if all_skills:
                    freq = frequency_map(all_skills)
                    skill_df = pd.DataFrame(list(freq.items())[:12], columns=["Skill", "Count"])
                    fig = px.bar(
                        skill_df, x="Count", y="Skill", orientation="h",
                        title="🛠️ Top Skills (from job tags)",
                        color="Count", color_continuous_scale="Greens",
                    )
                    fig.update_layout(height=380, yaxis={"categoryorder": "total ascending"},
                                      showlegend=False, margin=dict(l=0, r=0, t=40, b=0),
                                      template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                                      plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    # Remote vs Onsite pie
                    remote_pie_df = pd.DataFrame({
                        "Mode": ["Remote", "On-site / Hybrid"],
                        "Count": [remote_count, len(postings) - remote_count],
                    })
                    fig = px.pie(remote_pie_df, names="Mode", values="Count",
                                 title="🌐 Work Mode Distribution",
                                 color_discrete_sequence=["#0077b5", "#7fc15e"])
                    fig.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0),
                                      template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                                      plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True)

            st.markdown('<hr class="gradient-divider">', unsafe_allow_html=True)

            # ── Sortable table with direct Apply links ──
            st.subheader("📋 All Jobs — Sortable Table")
            st.caption("💡 Click column headers to sort. Click **Apply** to open the job posting.")

            st.dataframe(
                df_jobs,
                use_container_width=True,
                hide_index=True,
                height=420,
                column_config={
                    "Apply": st.column_config.LinkColumn(
                        "Apply →",
                        display_text="🚀 Apply",
                        help="Click to open the job posting",
                    ),
                    "Title": st.column_config.TextColumn("Title", width="large"),
                    "Company": st.column_config.TextColumn("Company", width="medium"),
                    "Remote": st.column_config.TextColumn("Remote", width="small"),
                    "Posted": st.column_config.TextColumn("Posted", width="small"),
                },
            )

            # CSV export
            st.download_button(
                "⬇️ Download as CSV",
                data=df_jobs.to_csv(index=False).encode(),
                file_name=f"jobs_{st.session_state.job_role.replace(' ', '_')}.csv",
                mime="text/csv",
            )

            # ── Detailed expandable cards ──
            with st.expander("👁️ View detailed job descriptions"):
                for i, p in enumerate(postings):
                    remote_badge = " 🌐 Remote" if p.is_remote else ""
                    st.markdown(f"### {p.title} — *{p.company}*{remote_badge}")
                    st.markdown(f"📍 {p.location} · 🏷️ {p.source} · 📅 {(p.date_posted or '—')[:10]}")
                    st.text(p.description[:600] + ("…" if len(p.description) > 600 else ""))
                    btn_cols = st.columns([1, 1, 4])
                    with btn_cols[0]:
                        if p.url:
                            st.link_button("🚀 Apply", p.url)
                    with btn_cols[1]:
                        if st.button("🎯 Analyse Gap", key=f"select_{i}"):
                            st.session_state.selected_job_idx = i
                            st.session_state.gap_analysis = None
                            st.success(f"Selected — go to **Skill Gap Analysis** tab")
                    st.divider()

# ============================================================
# TAB 2 — Skills Analysis
# ============================================================

with tab2:
    st.header("📊 Skills Analysis")
    st.markdown("AI-powered analysis of skills and trends across all fetched job postings.")

    if not st.session_state.search_done or not st.session_state.postings:
        st.info("👆 Run a job search in the **Job Role Research** tab first.")
    else:
        postings = st.session_state.postings
        job_role = st.session_state.job_role

        if st.button("🤖 Analyse Skills with AI", type="primary", disabled=not cfg.has_any_ai):
            if not cfg.has_any_ai:
                st.warning("Add a free Groq API key in the sidebar.")
            else:
                descriptions = [p.description for p in postings if p.description]
                ai = AIEngine(api_key=cfg.active_ai_key, provider=cfg.active_ai_provider, model=cfg.active_model)

                with st.spinner("Analysing skills across all job postings…"):
                    try:
                        analysis = ai.extract_skills_from_postings(job_role, descriptions)
                        st.session_state.skills_analysis = analysis
                    except Exception as e:
                        st.error(f"AI analysis failed: {e}")

                with st.spinner("Generating role overview…"):
                    try:
                        overview = ai.analyze_role_overview(job_role, analysis)
                        st.session_state.role_overview = overview
                    except Exception as e:
                        st.warning(f"Role overview unavailable: {e}")

        if not cfg.has_any_ai:
            st.warning("Add your free Groq API key to enable AI analysis.")

        analysis = st.session_state.skills_analysis
        overview = st.session_state.role_overview

        if overview:
            st.subheader("🌍 Role Overview")
            st.markdown(f"**{overview.get('headline', '')}**")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Career levels:**")
                st.write(overview.get("career_level_breakdown", ""))
                st.markdown("**Market demand:**")
                st.write(overview.get("market_demand", ""))
            with col2:
                trending = overview.get("trending_skills", [])
                if trending:
                    st.markdown("**Trending skills right now:**")
                    for s in trending:
                        st.markdown(f"- 🔥 {s}")

        if analysis:
            st.subheader("🏆 Top Skills Required")
            top_skills = analysis.get("top_skills", [])
            if top_skills:
                for skill_info in top_skills[:15]:
                    skill = skill_info.get("skill", "")
                    freq = skill_info.get("frequency_pct", 0)
                    cat = skill_info.get("category", "")
                    st.progress(freq / 100, text=f"**{skill}** ({cat}) — {freq}%")

            categories = analysis.get("categories", {})
            if categories:
                st.subheader("📂 Skills by Category")
                cols = st.columns(min(len(categories), 3))
                for idx, (cat, skills) in enumerate(categories.items()):
                    with cols[idx % 3]:
                        st.markdown(f"**{cat}**")
                        for s in skills:
                            st.markdown(f"- {s}")

            summary = analysis.get("summary", "")
            if summary:
                st.subheader("💡 AI Summary")
                st.info(summary)

        elif not analysis and st.session_state.search_done:
            # Show basic frequency without AI
            all_skills = [p.skills_raw for p in postings if p.skills_raw]
            if all_skills:
                st.subheader("📊 Skill Frequency (from posting tags)")
                freq = frequency_map(all_skills)
                for skill, count in list(freq.items())[:15]:
                    pct = int(count / len(postings) * 100)
                    st.progress(pct / 100, text=f"**{skill}** — {pct}%")

# ============================================================
# TAB 3 — Skill Gap Analysis
# ============================================================

with tab3:
    st.header("🎯 Skill Gap Analysis")
    st.markdown("Compare your current skills against a specific job posting.")

    if not st.session_state.search_done or not st.session_state.postings:
        st.info("👆 Run a job search first, then select a job posting to analyse.")
    else:
        postings = st.session_state.postings
        job_role = st.session_state.job_role

        # Job selector
        posting_options = {
            f"{p.title} — {p.company}": i for i, p in enumerate(postings)
        }
        selected_label = st.selectbox(
            "Select a job posting to analyse",
            options=list(posting_options.keys()),
            index=st.session_state.selected_job_idx or 0,
        )
        selected_idx = posting_options[selected_label]
        selected_job = postings[selected_idx]

        st.markdown(f"**Role:** {selected_job.title}  \n**Company:** {selected_job.company}  \n**Location:** {selected_job.location}")

        # User skills input
        st.subheader("🛠️ Your Current Skills")
        skills_text = st.text_area(
            "Enter your skills (one per line or comma-separated)",
            value="\n".join(st.session_state.user_skills) if st.session_state.user_skills else "",
            placeholder="Python\nSQL\nMachine Learning\nDocker",
            height=150,
        )

        background = st.text_input(
            "Your background (optional)",
            placeholder="e.g. 2 years as data analyst, BSc in Computer Science",
        )

        analyse_btn = st.button(
            "🤖 Analyse My Skill Gap",
            type="primary",
            disabled=not cfg.has_any_ai,
        )

        if not cfg.has_any_ai:
            st.warning("Add your free Groq API key to enable skill gap analysis.")

        if analyse_btn:
            if not skills_text.strip():
                st.warning("Please enter your skills first.")
            elif not cfg.has_any_ai:
                st.warning("Add a free Groq API key in the sidebar.")
            else:
                # Parse skills from textarea
                raw_skills = [
                    s.strip()
                    for line in skills_text.replace(",", "\n").splitlines()
                    for s in [line.strip()]
                    if s.strip()
                ]
                user_skills = normalize_skills(raw_skills)
                st.session_state.user_skills = user_skills

                ai = AIEngine(api_key=cfg.active_ai_key, provider=cfg.active_ai_provider, model=cfg.active_model)
                with st.spinner("Analysing your skill gap…"):
                    try:
                        gap = ai.perform_skill_gap_analysis(
                            job_role=selected_job.title,
                            job_description=selected_job.description,
                            user_skills=user_skills,
                        )
                        st.session_state.gap_analysis = gap
                        st.session_state.selected_job_idx = selected_idx
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")

        gap = st.session_state.gap_analysis
        if gap:
            score = gap.get("readiness_score", 0)
            colour = "🟢" if score >= 70 else "🟡" if score >= 40 else "🔴"

            st.divider()
            st.subheader(f"{colour} Readiness Score: {score}/100")
            st.progress(score / 100)

            col1, col2, col3 = st.columns(3)
            with col1:
                matched = gap.get("matched_skills", [])
                st.markdown(f"**✅ Skills You Have ({len(matched)})**")
                for s in matched:
                    st.markdown(f"- ✅ {s}")
            with col2:
                critical = gap.get("missing_critical", [])
                st.markdown(f"**🚨 Critical Gaps ({len(critical)})**")
                for s in critical:
                    st.markdown(f"- 🚨 {s}")
            with col3:
                nice = gap.get("missing_nice_to_have", [])
                st.markdown(f"**💡 Nice-to-Have ({len(nice)})**")
                for s in nice:
                    st.markdown(f"- 💡 {s}")

            summary = gap.get("summary", "")
            if summary:
                st.info(f"💬 **AI Coach:** {summary}")

            all_missing = gap.get("missing_critical", []) + gap.get("missing_nice_to_have", [])
            if all_missing:
                if st.button("📚 Generate Learning Path for These Gaps", type="primary"):
                    st.session_state.learning_path = None
                    st.session_state["_pending_learning"] = {
                        "skills": all_missing,
                        "background": background,
                    }
                    st.success("Go to the **Learning Path** tab to see your roadmap!")

# ============================================================
# TAB 4 — Learning Path
# ============================================================

with tab4:
    st.header("📚 Learning Path")
    st.markdown("A personalised roadmap to acquire the skills you need for your target role.")

    pending = st.session_state.get("_pending_learning")
    gap = st.session_state.gap_analysis
    job_role = st.session_state.job_role

    # Allow manual skill entry if arriving directly
    if not gap and not pending:
        st.info("Complete the **Skill Gap Analysis** tab first to auto-populate your missing skills, or enter them manually below.")

    # Manual entry fallback
    manual_skills = st.text_area(
        "Skills to learn (one per line, or filled automatically from Skill Gap Analysis)",
        value="\n".join(pending["skills"] if pending else (
            (gap.get("missing_critical", []) + gap.get("missing_nice_to_have", [])) if gap else []
        )),
        height=120,
    )
    manual_background = st.text_input(
        "Your background",
        value=pending.get("background", "") if pending else "",
        placeholder="e.g. 1 year of Python experience, transitioning from data analyst",
    )
    manual_role = st.text_input("Target job role", value=job_role or "", placeholder="Data Scientist")

    generate_btn = st.button(
        "🗺️ Generate Learning Path",
        type="primary",
        disabled=not cfg.has_any_ai,
    )
    if not cfg.has_any_ai:
        st.warning("Add your free Groq API key to generate a learning path.")

    if generate_btn:
        skills_to_learn = [
            s.strip()
            for line in manual_skills.splitlines()
            for s in [line.strip()]
            if s.strip()
        ]
        target_role = manual_role.strip() or job_role or "target role"

        if not skills_to_learn:
            st.warning("Please enter at least one skill to learn.")
        elif not cfg.has_any_ai:
            st.warning("Add a free Groq API key in the sidebar.")
        else:
            ai = AIEngine(api_key=cfg.active_ai_key, provider=cfg.active_ai_provider, model=cfg.active_model)
            with st.spinner("Generating your personalised learning path…"):
                try:
                    path = ai.generate_learning_path(
                        job_role=target_role,
                        missing_skills=skills_to_learn,
                        user_background=manual_background,
                    )
                    st.session_state.learning_path = {
                        "path": path,
                        "skills": skills_to_learn,
                        "role": target_role,
                    }
                    st.session_state["_pending_learning"] = None
                except Exception as e:
                    st.error(f"Could not generate learning path: {e}")

    lp_data = st.session_state.learning_path
    if lp_data:
        path = lp_data["path"]
        skills = lp_data["skills"]
        role = lp_data["role"]

        total_weeks = path.get("total_duration_weeks", "?")
        st.success(f"🗺️ Your learning roadmap — estimated **{total_weeks} weeks** to job-ready for **{role}**")

        phases = path.get("phases", [])
        for phase in phases:
            with st.expander(
                f"Phase {phase.get('phase', '')}: {phase.get('title', '')} "
                f"({phase.get('duration_weeks', '?')} weeks)",
                expanded=phase.get("phase", 1) == 1,
            ):
                st.markdown(phase.get("description", ""))
                phase_skills = phase.get("skills", [])
                if phase_skills:
                    st.markdown("**Skills covered:** " + ", ".join(phase_skills))

        tips = path.get("tips", [])
        if tips:
            st.subheader("💡 Study Tips")
            for tip in tips:
                st.markdown(f"- {tip}")

        # Learning resources
        st.subheader("🎥 Learning Resources")
        st.markdown("Find tutorials and courses for each skill:")

        recommender = LearningRecommender(youtube_api_key=cfg.youtube_api_key)
        search_queries = path.get("search_queries", {})

        with st.spinner("Fetching learning resources…"):
            resources_list = recommender.get_resources_for_skills(
                skills=skills[:8],
                job_role=role,
                search_queries=search_queries,
                max_videos_per_skill=2,
            )

        for resources in resources_list:
            with st.expander(f"📖 {resources.skill}"):
                col_v, col_c = st.columns(2)
                with col_v:
                    st.markdown("**📺 YouTube**")
                    for v in resources.videos:
                        if v.thumbnail:
                            st.image(v.thumbnail, width=180)
                        st.markdown(f"[{v.title}]({v.url})")
                        if v.channel and v.channel != "YouTube":
                            st.caption(f"Channel: {v.channel}")
                with col_c:
                    st.markdown("**🎓 Online Courses**")
                    for course in resources.courses:
                        st.markdown(f"{course.icon} [{course.title}]({course.url})")

        # Export
        st.divider()
        st.subheader("📤 Export")
        import json as _json
        export = {
            "role": role,
            "skills_to_learn": skills,
            "learning_path": path,
        }
        st.download_button(
            "⬇️ Download Learning Path (JSON)",
            data=_json.dumps(export, indent=2),
            file_name=f"learning_path_{role.replace(' ', '_').lower()}.json",
            mime="application/json",
        )

        # ── Certifications recommender ──
        from src.certifications import recommend_for_role
        st.divider()
        st.subheader("🎓 Recommended Certifications")
        st.caption("Industry-recognised certifications that boost your credibility for this role")
        certs = recommend_for_role(role, max_results=6)
        if certs:
            cert_cols = st.columns(2)
            for i, cert in enumerate(certs):
                with cert_cols[i % 2]:
                    level_color = {"Beginner": "🟢", "Intermediate": "🟡", "Advanced": "🔴"}.get(cert.level, "⚪")
                    st.markdown(
                        f"""**{level_color} [{cert.name}]({cert.url})**
                        \n*{cert.provider}* · `{cert.category}` · {cert.level}"""
                    )

# ============================================================
# TAB 5 — Resume Analyzer
# ============================================================

with tab5:
    st.header("📄 Resume Analyzer")
    st.markdown(
        "Upload your resume to discover matching job roles, "
        "or compare it against a specific job to see your skill gaps and training plan."
    )

    if not cfg.has_any_ai:
        st.warning("⚠️ Add a free Groq API key in the sidebar to use Resume Analyzer.")
    else:
        # Privacy notice
        st.info(
            "🔒 **Privacy notice:** Your resume text is sent to the AI provider (Groq/OpenAI) "
            "for analysis. It is **not stored** by this app. "
            "Consider removing personal contact details before uploading if you prefer."
        )

        # Resume upload
        st.subheader("📤 Upload Your Resume")
        uploaded_file = st.file_uploader(
            "Upload PDF or DOCX (max 5 MB)",
            type=["pdf", "docx"],
            help="Supported formats: PDF, DOCX. Max size: 5 MB.",
        )

        # Also allow pasting as fallback
        with st.expander("📝 Or paste resume text manually"):
            pasted_resume = st.text_area(
                "Paste your resume text here",
                height=200,
                placeholder="Paste the full text of your resume...",
            )

        resume_text = ""

        if uploaded_file is not None:
            file_bytes = uploaded_file.read()
            try:
                with st.spinner("Parsing resume..."):
                    result = parse_resume(uploaded_file.name, file_bytes)
                if result.warning:
                    st.warning(f"⚠️ {result.warning}")
                else:
                    st.success(f"✅ Resume parsed ({result.file_type}, {len(result.text)} characters extracted)")
                resume_text = result.text
                with st.expander("👁️ Preview extracted text"):
                    st.text(resume_text[:1500] + ("..." if len(resume_text) > 1500 else ""))
            except ValueError as e:
                st.error(f"❌ {e}")
        elif pasted_resume.strip():
            resume_text = pasted_resume.strip()
            st.success(f"✅ Resume text received ({len(resume_text)} characters)")

        if resume_text:
            st.divider()

            # ── Mode selector ──────────────────────────────────────
            mode = st.radio(
                "What would you like to do?",
                options=[
                    "🔍 Find jobs I can apply for (resume → job matches)",
                    "🎯 Compare resume to a specific job (gap analysis + training)",
                ],
                horizontal=True,
            )

            # ============================================================
            # MODE 1: Resume → Job Matches
            # ============================================================
            if mode.startswith("🔍"):
                st.subheader("🔍 Jobs You Can Apply For")

                if st.button("🤖 Analyse My Resume", type="primary"):
                    ai = AIEngine(
                        api_key=cfg.active_ai_key,
                        provider=cfg.active_ai_provider,
                        model=cfg.active_model,
                    )
                    with st.spinner("Analysing your resume... (10–20 seconds)"):
                        try:
                            analysis = ai.analyze_resume(resume_text)
                            st.session_state["resume_analysis"] = analysis
                        except Exception as e:
                            st.error(f"Analysis failed: {e}")

                analysis = st.session_state.get("resume_analysis")
                if analysis:
                    # Profile summary
                    st.subheader("👤 Your Profile")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Career Level", analysis.get("career_level", "—"))
                    with col2:
                        st.metric("Experience", f"{analysis.get('experience_years', '?')} years")
                    with col3:
                        st.metric("Education", analysis.get("education", "—"))

                    summary = analysis.get("summary", "")
                    if summary:
                        st.info(f"💼 **{summary}**")

                    # Skills
                    skills = analysis.get("skills", [])
                    if skills:
                        st.markdown("**🛠️ Skills found in your resume:**")
                        st.markdown(" • ".join(f"`{s}`" for s in skills))

                    # Job matches
                    matches = analysis.get("top_job_matches", [])
                    if matches:
                        st.subheader("✅ Jobs You Can Apply For")
                        st.markdown("Based on your resume, here are your best-fit roles:")

                        for match in matches:
                            role = match.get("role", "")
                            pct = match.get("match_pct", 0)
                            color = "🟢" if pct >= 70 else "🟡" if pct >= 40 else "🔴"

                            with st.expander(f"{color} {role} — {pct}% match"):
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    strengths = match.get("strengths", [])
                                    if strengths:
                                        st.markdown("**✅ Your strengths for this role:**")
                                        for s in strengths:
                                            st.markdown(f"- ✅ {s}")
                                with col_b:
                                    gaps = match.get("gaps", [])
                                    if gaps:
                                        st.markdown("**📚 What you'd need to learn:**")
                                        for g in gaps:
                                            st.markdown(f"- 📚 {g}")

                                # Quick search button
                                encoded = role.replace(" ", "+")
                                st.markdown(
                                    f"[🔍 Search '{role}' jobs on LinkedIn](https://www.linkedin.com/jobs/search/?keywords={encoded})  |  "
                                    f"[Search on Indeed](https://indeed.com/jobs?q={encoded})"
                                )

            # ============================================================
            # MODE 2: Resume vs Job → Gap Analysis
            # ============================================================
            else:
                st.subheader("🎯 Compare Resume to a Job")

                # Job input options
                job_input_method = st.radio(
                    "How would you like to provide the job?",
                    options=[
                        "📋 Paste job description",
                        "📌 Pick from my search results",
                    ],
                    horizontal=True,
                )

                job_description = ""
                job_title = ""

                if job_input_method.startswith("📋"):
                    job_title = st.text_input(
                        "Job title (optional)",
                        placeholder="e.g. Senior Data Scientist at Google",
                    )
                    job_description = st.text_area(
                        "Paste the full job description here",
                        height=200,
                        placeholder="Copy and paste the job description from any job board...",
                    )

                else:
                    if not st.session_state.search_done or not st.session_state.postings:
                        st.info("👆 Run a job search in the **Job Role Research** tab first, then come back here.")
                    else:
                        postings = st.session_state.postings
                        options = {f"{p.title} — {p.company}": i for i, p in enumerate(postings)}
                        selected_label = st.selectbox("Select a job from your search results", list(options.keys()))
                        selected_job = postings[options[selected_label]]
                        job_title = f"{selected_job.title} at {selected_job.company}"
                        job_description = selected_job.description
                        st.markdown(f"**Selected:** {job_title}")

                if job_description.strip():
                    if st.button("🤖 Compare Resume to This Job", type="primary"):
                        ai = AIEngine(
                            api_key=cfg.active_ai_key,
                            provider=cfg.active_ai_provider,
                            model=cfg.active_model,
                        )
                        with st.spinner("Comparing your resume to the job... (10–20 seconds)"):
                            try:
                                gap = ai.match_resume_to_job(
                                    resume_text=resume_text,
                                    job_description=job_description,
                                    job_title=job_title,
                                )
                                st.session_state["resume_gap"] = gap
                                st.session_state["resume_gap_role"] = job_title
                            except Exception as e:
                                st.error(f"Analysis failed: {e}")

                gap = st.session_state.get("resume_gap")
                if gap:
                    score = gap.get("readiness_score", 0)
                    color = "🟢" if score >= 70 else "🟡" if score >= 40 else "🔴"

                    st.divider()
                    st.subheader(f"{color} Resume Match Score: {score}/100")
                    st.progress(score / 100)

                    headline = gap.get("suggested_headline", "")
                    if headline:
                        st.success(f"✏️ **Suggested resume headline for this role:**  \n_{headline}_")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        matched = gap.get("matched_skills", [])
                        st.markdown(f"**✅ Matched Skills ({len(matched)})**")
                        for s in matched:
                            st.markdown(f"- ✅ {s}")
                    with col2:
                        critical = gap.get("missing_critical", [])
                        st.markdown(f"**🚨 Critical Gaps ({len(critical)})**")
                        for s in critical:
                            st.markdown(f"- 🚨 {s}")
                    with col3:
                        nice = gap.get("missing_nice_to_have", [])
                        st.markdown(f"**💡 Nice-to-Have ({len(nice)})**")
                        for s in nice:
                            st.markdown(f"- 💡 {s}")

                    strengths = gap.get("resume_strengths", [])
                    if strengths:
                        st.subheader("🌟 Your Resume Strengths for This Role")
                        for s in strengths:
                            st.markdown(f"- ⭐ {s}")

                    summary = gap.get("summary", "")
                    if summary:
                        st.info(f"💬 **AI Coach:** {summary}")

                    # Generate learning path for gaps
                    all_missing = gap.get("missing_critical", []) + gap.get("missing_nice_to_have", [])
                    if all_missing:
                        st.divider()
                        st.subheader("📚 Get the Missing Skills")

                        role_for_path = st.session_state.get("resume_gap_role", "target role")

                        if st.button("🗺️ Generate Training Plan for My Gaps", type="primary"):
                            ai = AIEngine(
                                api_key=cfg.active_ai_key,
                                provider=cfg.active_ai_provider,
                                model=cfg.active_model,
                            )
                            with st.spinner("Generating your personalised training plan..."):
                                try:
                                    path = ai.generate_learning_path(
                                        job_role=role_for_path,
                                        missing_skills=all_missing,
                                    )
                                    st.session_state["resume_learning_path"] = {
                                        "path": path,
                                        "skills": all_missing,
                                        "role": role_for_path,
                                    }
                                except Exception as e:
                                    st.error(f"Could not generate training plan: {e}")

                        lp = st.session_state.get("resume_learning_path")
                        if lp:
                            path = lp["path"]
                            total = path.get("total_duration_weeks", "?")
                            st.success(f"🗺️ Training plan: **{total} weeks** to close your skill gaps")

                            for phase in path.get("phases", []):
                                with st.expander(
                                    f"Phase {phase.get('phase','')}: {phase.get('title','')} ({phase.get('duration_weeks','?')} weeks)",
                                    expanded=phase.get("phase", 1) == 1,
                                ):
                                    st.markdown(phase.get("description", ""))
                                    if phase.get("skills"):
                                        st.markdown("**Skills:** " + ", ".join(phase["skills"]))

                            # Resources
                            st.subheader("🎥 Learning Resources")
                            recommender = LearningRecommender(youtube_api_key=cfg.youtube_api_key)
                            with st.spinner("Fetching resources..."):
                                resources_list = recommender.get_resources_for_skills(
                                    skills=all_missing[:8],
                                    job_role=role_for_path,
                                    search_queries=path.get("search_queries"),
                                    max_videos_per_skill=2,
                                )
                            for resources in resources_list:
                                with st.expander(f"📖 {resources.skill}"):
                                    col_v, col_c = st.columns(2)
                                    with col_v:
                                        st.markdown("**📺 YouTube**")
                                        for v in resources.videos:
                                            if v.thumbnail:
                                                st.image(v.thumbnail, width=160)
                                            st.markdown(f"[{v.title}]({v.url})")
                                    with col_c:
                                        st.markdown("**🎓 Courses**")
                                        for course in resources.courses:
                                            st.markdown(f"{course.icon} [{course.title}]({course.url})")

                            # Export
                            import json as _json
                            st.download_button(
                                "⬇️ Download Training Plan (JSON)",
                                data=_json.dumps(lp, indent=2),
                                file_name="training_plan.json",
                                mime="application/json",
                            )

# ============================================================
# TAB 6 — Resume Coach (tailored bullets + LinkedIn copy)
# ============================================================
with tab6:
    st.header("✍️ Resume Coach — AI Rewriter")
    st.caption("Get tailored resume bullets, LinkedIn headline & About section optimized for a target job.")

    if not cfg.has_any_ai:
        st.warning("⚠️ AI provider required. Add a Groq or OpenAI key in the sidebar.")
    else:
        coach_col1, coach_col2 = st.columns(2)
        with coach_col1:
            coach_resume_text = st.text_area(
                "📄 Paste your current resume",
                height=260,
                placeholder="Paste resume text here…",
                key="coach_resume_input",
            )
        with coach_col2:
            coach_job_title = st.text_input("🎯 Target Job Title", placeholder="e.g. Senior Data Scientist")
            coach_jd = st.text_area(
                "📋 Target Job Description",
                height=200,
                placeholder="Paste the job description…",
                key="coach_jd_input",
            )

        if st.button("✨ Generate Coach Output", type="primary", use_container_width=True):
            if not coach_resume_text.strip() or not coach_jd.strip() or not coach_job_title.strip():
                st.error("Please fill all three fields.")
            else:
                with st.spinner("AI is crafting your tailored content…"):
                    try:
                        ai_coach = AIEngine(
                            provider=cfg.active_ai_provider,
                            api_key=cfg.active_ai_key,
                            model=cfg.active_model,
                        )
                        result = ai_coach.coach_resume(
                            resume_text=coach_resume_text,
                            job_description=coach_jd,
                            job_title=coach_job_title,
                        )
                        st.session_state["coach_result"] = result
                    except Exception as e:
                        st.error(f"AI failed: {e}")

        coach_result = st.session_state.get("coach_result")
        if coach_result:
            st.success("✅ Tailored content ready!")

            st.subheader("🎯 Tailored Resume Bullets")
            for b in coach_result.get("tailored_bullets", []):
                st.markdown(f"- {b}")

            st.subheader("💼 LinkedIn Headline")
            st.code(coach_result.get("linkedin_headline", ""), language=None)

            st.subheader("📝 LinkedIn About Section")
            st.text_area(
                "Copy this to your LinkedIn About section",
                value=coach_result.get("linkedin_about", ""),
                height=180,
                key="coach_about_out",
            )

            missing = coach_result.get("missing_keywords", [])
            if missing:
                st.subheader("⚠️ Missing Keywords (add these!)")
                st.markdown(" ".join(f'<span class="pill">{k}</span>' for k in missing), unsafe_allow_html=True)

            iq = coach_result.get("interview_questions", [])
            if iq:
                st.subheader("🎤 Likely Interview Questions")
                for i, q in enumerate(iq, 1):
                    st.markdown(f"**{i}.** {q}")

            import json as _json
            st.download_button(
                "⬇️ Download Coach Output (JSON)",
                data=_json.dumps(coach_result, indent=2),
                file_name="resume_coach_output.json",
                mime="application/json",
            )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="footer">
        Built with 💙 by <a href="https://github.com/arunsuthar98" target="_blank">Arun Suthar</a>
        · <a href="https://github.com/arunsuthar98/linkedin-job-analyzer-tool" target="_blank">⭐ Star on GitHub</a>
        · <a href="https://github.com/arunsuthar98/linkedin-job-analyzer-tool/issues" target="_blank">🐛 Report a bug</a>
        · MIT License<br>
        <small>Powered by Groq · JSearch · YouTube Data API · Streamlit</small>
    </div>
    """,
    unsafe_allow_html=True,
)
