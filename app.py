# app.py
import streamlit as st
from openai import OpenAI
from docx import Document
import fitz
import csv
from datetime import datetime
import pandas as pd
import io

# 👉 First Streamlit command
st.set_page_config(page_title="Career Coach AI", page_icon="🧠")

# 🎨 Background CSS (hero / content)
if "started" not in st.session_state:
    st.session_state.started = False
bg = "hero" if not st.session_state.started else "content"
bg_url = f"https://raw.githubusercontent.com/NicholasRico/career-coach-ai/main/.streamlit/assets/career-coach-{bg}-ng.jpg"
st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url('{bg_url}');
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position: center top;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# 🔐 Password protection
password = st.text_input("🔐 Enter access password", type="password")
if password != st.secrets["APP_PASSWORD"]:
    st.warning("This app is password protected. Enter the correct password to continue.")
    st.stop()

# 🎨 Branded Welcome (landing)
if not st.session_state.started:
    st.title("Career Coach AI")
    st.image(bg_url, use_column_width=True)
    st.markdown("Tailor your resume, cover letter, and recruiter message for **any job** in seconds.")
    st.markdown("Built by [Nicholas Gauthier](mailto:NickRGauthier@gmail.com)")
    if st.button("Get Started"):
        st.session_state.started = True
    st.stop()

# 👤 User ID (normalized)
user_id = st.text_input("👤 Enter your name or email to track your applications").strip().lower()
if not user_id:
    st.warning("Please enter your name or email to continue.")
    st.stop()

# 🔌 OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Main Inputs + Instructions ---
st.markdown("---")
st.markdown("## Job Application Tailoring")
col_main, col_help = st.columns([3, 1])
with col_main:
    resume_file = st.file_uploader("📌 Upload your resume (.pdf or .docx)", type=["pdf", "docx"])
    job_desc = st.text_area("📜 Paste job description here", height=250)
    model = st.selectbox("🧠 Choose GPT model", ["gpt-3.5-turbo", "gpt-4"] )
    c1, c2, c3 = st.columns(3)
    with c1:
        log_app = st.checkbox("Log this application", value=True)
    with c2:
        more_bullets = st.checkbox("Generate more bullet options")
    with c3:
        refresh_bullets = st.checkbox("Refresh only resume bullets")
    feedback = st.text_input("Optional: feedback or tone (e.g. friendly, persuasive)")
    st.caption("Tip: Professional, Friendly, Persuasive, Confident, Concise")

with col_help:
    st.markdown("**Quick Steps**")
    steps = [
        "Upload your current resume — drag & drop or browse.",
        "Paste the job description you want to apply to.",
        "Select options & hit **Generate AI Career Materials**.",
        "Not satisfied? Use feedback, expand bullets, or refresh.",
        "Download your personalized bullets, cover letter & message!"
    ]
    for i, step in enumerate(steps, 1):
        st.write(f"{i}. {step}")

# --- Bulk Job Descriptions ---
st.markdown("---")
st.markdown("## Bulk Job Descriptions")
st.caption("Download a CSV template and optionally upload multiple job descriptions.")
template = "Job Description\nJD #1\nJD #2\n"
st.download_button("Download Template CSV", data=template, file_name="job_description_template.csv")
bulk_file = st.file_uploader("Upload Bulk Job Descriptions CSV", type="csv")

# ✂️ Helpers
def extract_pdf(f):
    d = fitz.open(stream=f.read(), filetype="pdf")
    return "".join([p.get_text() for p in d])

def extract_docx(f):
    d = Document(f)
    return "\n".join([p.text for p in d.paragraphs])

# --- Generate Action ---
if st.button("Generate AI Career Materials"):
    if not resume_file:
        st.error("Please upload a resume.")
        st.stop()
    text = extract_pdf(resume_file) if resume_file.name.endswith('.pdf') else extract_docx(resume_file)
    # collect job descriptions
    if bulk_file:
        dfj = pd.read_csv(bulk_file)
        jobs = dfj['Job Description'].dropna().tolist()
    elif job_desc:
        jobs = [job_desc]
    else:
        st.error("Please paste a job description or upload a CSV.")
        st.stop()
    jd0 = jobs[0]

    # build strict-format prompt
    count = "five" if (more_bullets or refresh_bullets) else "two"
    fb = f"Feedback: {feedback}\n" if feedback else ""
    strict_instruct = (
        "Please format your reply exactly as follows, with no extra text:\n"
        "1. bullet points separated by new lines\n\n"
        "2. cover letter (3 paragraphs)\n\n"
        "3. outreach message"
    )
    prompt = f"""
{strict_instruct}
{fb}
You are an expert career coach AI. Using the resume below and the job description provided, return:
1. {count.capitalize()} tailored resume bullet points.
2. A personalized cover letter (3 short paragraphs max).
3. A short outreach message to the hiring manager.

Resume:
{text}

Job Description:
{jd0}
"""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    out = response.choices[0].message.content.strip()

    # insert raw output for debugging
    st.code(out, language='text')

    # split on double newlines for sections
    sections = out.split("\n\n")
    bullets = sections[0].strip() if len(sections) > 0 else ""
    cover = sections[1].strip() if len(sections) > 1 else ""
    outreach = sections[2].strip() if len(sections) > 2 else ""

    # store in session state
    st.session_state['bullets'] = bullets
    if not refresh_bullets:
        st.session_state['cover'] = cover
        st.session_state['outreach'] = outreach
    st.success("✅ Generated Successfully!")

# --- Display & Download ---
if 'bullets' in st.session_state:
    st.markdown("---")
    st.subheader("📌 Resume Bullets")
    st.markdown(st.session_state['bullets'])
    buf1 = io.BytesIO(); d1 = Document(); d1.add_heading("Resume Bullets", 0); d1.add_paragraph(st.session_state['bullets']); d1.save(buf1)
    st.download_button("Download Resume Bullets", buf1.getvalue(), file_name="ResumeBullets.docx")

if 'cover' in st.session_state:
    st.markdown("---")
    st.subheader("📜 Cover Letter")
    st.markdown(st.session_state['cover'])
    buf2 = io.BytesIO(); d2 = Document(); d2.add_heading("Cover Letter", 0); d2.add_paragraph(st.session_state['cover']); d2.save(buf2)
    st.download_button("Download Cover Letter", buf2.getvalue(), file_name="CoverLetter.docx")

if 'outreach' in st.session_state:
    st.markdown("---")
    st.subheader("💬 Outreach Message")
    st.markdown(st.session_state['outreach'])
    buf3 = io.BytesIO(); d3 = Document(); d3.add_heading("Outreach Message", 0); d3.add_paragraph(st.session_state['outreach']); d3.save(buf3)
    st.download_button("Download Outreach Message", buf3.getvalue(), file_name="OutreachMessage.docx")

# --- Admin Log Viewer ---
st.markdown("---")
st.subheader("📊 Application Tracker & Log")
admin = st.text_input("🔑 Admin key (leave blank if not admin)", type="password")
is_admin = admin == st.secrets['ADMIN_KEY']
if st.checkbox("Show Application Log"):
    try:
        df = pd.read_csv("application_log.csv", names=["Time","User","Job","Model","Preview"])
        df['Time'] = pd.to_datetime(df['Time'])
        if not is_admin:
            df = df[df['User'].str.lower() == user_id]
        else:
            st.success("🔓 Admin view enabled")
            sel = st.selectbox("Filter by user", ["All"] + sorted(df['User'].str.lower().unique().tolist()))
            if sel != "All": df = df[df['User'].str.lower() == sel]
        st.dataframe(df.sort_values('Time', False), use_container_width=True)
        st.download_button("Download Log as CSV", df.to_csv(index=False).encode('utf-8'), file_name="application_log.csv")
    except FileNotFoundError:
        st.warning("No application log found yet.")
