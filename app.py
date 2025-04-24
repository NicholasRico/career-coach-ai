# app.py
import streamlit as st
from openai import OpenAI
from docx import Document
import fitz
import csv
from datetime import datetime
import pandas as pd
import io

# --- Initial Setup ---
st.set_page_config(page_title="Career Coach AI", page_icon="🧠")

# --- Access Control ---
password = st.text_input("🔐 Enter access password", type="password")
if password != st.secrets["APP_PASSWORD"]:
    st.warning("This app is password protected. Enter the correct password to continue.")
    st.stop()

# --- Session State for Background ---
if "started" not in st.session_state:
    st.session_state.started = False

# --- Background Styling ---
background_image = "hero" if not st.session_state.started else "content"
background_url = (
    f"https://raw.githubusercontent.com/NicholasRico/career-coach-ai/main/.streamlit/assets/career-coach-{background_image}-ng.jpg"
)
st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url('{background_url}');
        background-size: cover;
        background-attachment: fixed;
        background-position: center top;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Welcome Screen ---
if not st.session_state.started:
    st.title("🧠 Career Coach AI")
    st.markdown("Tailor your resume, cover letter, and recruiter message for **any job** in seconds.")
    st.markdown("Built by [Nicholas Gauthier](mailto:NickRGauthier@gmail.com)")
    if st.button("🚀 Get Started"):
        st.session_state.started = True
    st.stop()

# --- User Identification ---
user_id = st.text_input("👤 Enter your name or email to track your applications").strip().lower()
if not user_id:
    st.warning("Please enter your name or email to continue.")
    st.stop()

# --- OpenAI Client ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Main Form ---
st.markdown("---")
st.markdown("## 📄 Job Application Tailoring")
with st.container():
    resume_file = st.file_uploader("📌 Upload your resume (.pdf or .docx)", type=["pdf", "docx"])
    job_description = st.text_area("📜 Paste job description here", height=250)
    model_choice = st.selectbox("🤖 Choose GPT model", ["gpt-3.5-turbo", "gpt-4"])
    col1, col2, col3 = st.columns(3)
    with col1:
        log_this = st.checkbox("📥 Log this application", value=True)
    with col2:
        expand_bullets = st.checkbox("➕ Generate more bullet options")
    with col3:
        refresh_bullets = st.checkbox("🔄 Refresh only resume bullets")
    custom_tone = st.text_input("🎨 Tone/style instructions (e.g., friendly, persuasive)")
    st.caption("Need ideas? Professional, Friendly, Persuasive, Confident, Concise")

# --- Bulk Upload ---
st.markdown("---")
st.markdown("## 📑 Bulk Job Descriptions")
st.caption("Download template or upload multiple JDs to process.")
sample_csv = """Job Description
Sample job description 1.
Sample job description 2.
"""
st.download_button("📥 Download Template CSV", data=sample_csv, file_name="job_desc_template.csv")
bulk_file = st.file_uploader("📤 Upload Bulk CSV", type="csv")

# --- Text Extraction Helpers ---
def extract_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    return "\n".join(p.get_text() for p in doc)

def extract_docx(file):
    doc = Document(file)
    return "\n".join(p.text for p in doc.paragraphs)

# --- Generate Button ---
if st.button("✨ Generate AI Materials"):
    # Validate inputs
    if not resume_file:
        st.error("Please upload your resume.")
        st.stop()
    if not job_description and not bulk_file:
        st.error("Please paste a job description or upload bulk CSV.")
        st.stop()

    # Extract resume text
    resume_text = extract_pdf(resume_file) if resume_file.name.endswith(".pdf") else extract_docx(resume_file)
    jd_list = []
    if bulk_file:
        df = pd.read_csv(bulk_file)
        jd_list = df["Job Description"].dropna().tolist()
    else:
        jd_list = [job_description]

    # For now, process only first JD
    jd = jd_list[0]

    # Build prompt
    bullet_count = 5 if expand_bullets else 2
    if refresh_bullets:
        prompt = (
            f"Generate {bullet_count} resume bullet points based on resume and JD below."
            + (f" Tone: {custom_tone}" if custom_tone else "")
            + f"\nResume:\n{resume_text}\nJD:\n{jd}"
        )
    else:
        prompt = (
            f"Use resume + JD below to output:\n1. {bullet_count} resume bullet points\n"
            + "2. Short cover letter (3 paragraphs max)\n3. Outreach message to hiring manager"
            + (f"\nTone: {custom_tone}" if custom_tone else "")
            + f"\nResume:\n{resume_text}\nJD:\n{jd}"
        )

    resp = client.chat.completions.create(
        model=model_choice,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    out = resp.choices[0].message.content.strip()

    # Parse numbered sections
    bullet_sec, _, rest = out.partition("\n2.")
    resume_bullets = bullet_sec.strip()
    cover_sec, _, outreach_sec = rest.partition("\n3.")
    cover_letter = ("2." + cover_sec).strip()
    outreach = ("3." + outreach_sec).strip()

    # Display sections
    st.markdown("---")
    st.subheader("📌 Resume Bullets")
    st.markdown(resume_bullets)
    if not refresh_bullets:
        st.subheader("💌 Cover Letter")
        st.markdown(cover_letter)
        st.subheader("💬 Outreach Message")
        st.markdown(outreach)

    # Download docs
    buf1 = io.BytesIO()
    d1 = Document()
    d1.add_heading("Resume Bullets", 0)
    d1.add_paragraph(resume_bullets)
    d1.save(buf1)
    st.download_button("Download Resume Bullets", buf1.getvalue(), file_name="Resume_Bullets.docx")

    if not refresh_bullets:
        buf2 = io.BytesIO()
        d2 = Document()
        d2.add_heading("Cover Letter", 0)
        d2.add_paragraph(cover_letter)
        d2.save(buf2)
        st.download_button("Download Cover Letter", buf2.getvalue(), file_name="Cover_Letter.docx")

        buf3 = io.BytesIO()
        d3 = Document()
        d3.add_heading("Outreach Message", 0)
        d3.add_paragraph(outreach)
        d3.save(buf3)
        st.download_button("Download Outreach Message", buf3.getvalue(), file_name="Outreach_Message.docx")

    # Logging
    if log_this:
        with open("application_log.csv", "a", newline="") as lf:
            writer = csv.writer(lf)
            writer.writerow([
                datetime.now().isoformat(),
                user_id,
                jd,
                model_choice,
                resume_bullets.replace("\n", " "),
            ])

# --- Admin Log Viewer ---
st.markdown("---")
st.header("📊 Application Tracker & Log")
if st.checkbox("Show Application Log"):
    df_log = pd.read_csv(
        "application_log.csv",
        names=["Timestamp", "User", "JD", "Model", "Bullets"],
    )
    df_log["Timestamp"] = pd.to_datetime(df_log["Timestamp"])
    admin_input = st.text_input("🔑 Admin key (leave blank if not admin)")
    if admin_input != st.secrets["ADMIN_KEY"]:
        df_log = df_log[df_log.User.str.lower() == user_id]
    else:
        st.success("🔓 Admin access enabled — showing all logs.")
        sel = st.selectbox("Filter by user", options=["All"] + df_log.User.str.lower().unique().tolist())
        if sel != "All":
            df_log = df_log[df_log.User.str.lower() == sel]
    st.dataframe(df_log.sort_values("Timestamp", False))
