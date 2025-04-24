# app.py
import streamlit as st
from openai import OpenAI
from docx import Document
import fitz
import csv
from datetime import datetime
import pandas as pd
import io

# ✅ First Streamlit command
st.set_page_config(page_title="Career Coach AI", page_icon="🧠")

# 🔐 Password protection
password = st.text_input("🔐 Enter access password", type="password")
if password != st.secrets["APP_PASSWORD"]:
    st.warning("This app is password protected. Enter the correct password to continue.")
    st.stop()

# 🎨 Welcome / background logic
if "started" not in st.session_state:
    st.session_state.started = False

if not st.session_state.started:
    st.title("Career Coach AI")
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

st.markdown("---")
st.markdown("## Job Application Tailoring")

# Inputs
with st.container():
    resume_file = st.file_uploader("📌 Upload your resume (.pdf or .docx)", type=["pdf", "docx"])
    job_description = st.text_area("📜 Paste job description here", height=250)
    model_choice = st.selectbox("🧠 Choose GPT model", ["gpt-3.5-turbo", "gpt-4"])
    col1, col2, col3 = st.columns(3)
    with col1:
        log_this = st.checkbox("Log this application", value=True)
    with col2:
        expand_bullets = st.checkbox("Generate more bullet options")
    with col3:
        refresh_section = st.checkbox("Refresh only resume bullets")
    custom_feedback = st.text_input("Optional: Enter tone/style instructions (e.g. friendly, persuasive)")
    st.caption("Need tone help? e.g. Professional, Friendly, Persuasive, Confident, Concise")

# --- Bulk JD ---
st.markdown("---")
st.markdown("## Bulk Job Descriptions")
st.caption("Download a CSV template and upload multiple job descriptions to process.")
sample_csv = """Job Description
JD #1
JD #2
"""
st.download_button("Download Template CSV", data=sample_csv, file_name="job_description_template.csv")
bulk_jd_file = st.file_uploader("Upload Bulk Job Descriptions CSV", type="csv")

# Helpers
def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    return "".join([page.get_text() for page in doc])

def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

# --- Generation Trigger ---
if st.button("Generate AI Career Materials"):
    # resume
    if not resume_file:
        st.error("Please upload a resume.")
        st.stop()
    resume_text = (extract_text_from_pdf(resume_file)
                   if resume_file.name.endswith('.pdf')
                   else extract_text_from_docx(resume_file))
    # jobs
    if bulk_jd_file:
        df = pd.read_csv(bulk_jd_file)
        jds = df['Job Description'].dropna().tolist()
    elif job_description:
        jds = [job_description]
    else:
        st.error("Please paste a job description or upload a CSV.")
        st.stop()

    # generate first JD only for session memory
    st.session_state['resume_text'] = resume_text
    st.session_state['job_description'] = jds[0]

    for jd in jds:
        # build prompt
        if refresh_section:
            bullet_prompt = "five"
        else:
            bullet_prompt = "five" if expand_bullets else "two"
        feedback = f"User feedback: {custom_feedback}" if custom_feedback else ""
        prompt = f"""
{feedback}
You are an expert career coach AI. Using the resume below and the job description provided, return:
1. {bullet_prompt.capitalize()} tailored resume bullet points.
2. A personalized cover letter (3 short paragraphs max).
3. A short outreach message to the hiring manager.

Resume:
{resume_text}

Job Description:
{jd}
"""
        resp = client.chat.completions.create(
            model=model_choice,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = resp.choices[0].message.content
        parts = content.split("\n\n")
        # strip any leading numbering
        bullets = parts[0].lstrip('0123456789. ').strip() if len(parts)>0 else ''
        cover   = parts[1].lstrip('0123456789. ').strip() if len(parts)>1 else ''
        outreach= parts[2].lstrip('0123456789. ').strip() if len(parts)>2 else ''

        # store in session
        st.session_state['resume_bullets'] = bullets
        if not refresh_section:
            st.session_state['cover_letter'] = cover
            st.session_state['outreach'] = outreach

        st.success("✅ Generated Successfully!")

# --- Display & Download Section ---
if 'resume_bullets' in st.session_state:
    st.markdown("---")
    st.subheader("📌 Resume Bullets")
    st.markdown(st.session_state['resume_bullets'])
    buf = io.BytesIO()
    doc = Document()
    doc.add_heading('Resume Bullets', 0)
    doc.add_paragraph(st.session_state['resume_bullets'])
    doc.save(buf)
    st.download_button("Download Resume Bullets", buf.getvalue(), file_name="Updated_Resume.docx")

if 'cover_letter' in st.session_state:
    st.markdown("---")
    st.subheader("📜 Cover Letter")
    st.markdown(st.session_state['cover_letter'])
    buf = io.BytesIO()
    doc = Document()
    doc.add_heading('Cover Letter', 0)
    doc.add_paragraph(st.session_state['cover_letter'])
    doc.save(buf)
    st.download_button("Download Cover Letter", buf.getvalue(), file_name="Cover_Letter.docx")

if 'outreach' in st.session_state:
    st.markdown("---")
    st.subheader("💬 Outreach Message")
    st.markdown(st.session_state['outreach'])
    buf = io.BytesIO()
    doc = Document()
    doc.add_heading('Outreach Message', 0)
    doc.add_paragraph(st.session_state['outreach'])
    doc.save(buf)
    st.download_button("Download Outreach Message", buf.getvalue(), file_name="Outreach_Message.docx")

# --- Admin Log Viewer ---
st.markdown("---")
st.subheader("📊 Application Tracker & Log")
admin_key = st.text_input("🔑 Admin key (leave blank if not admin)", type="password")
is_admin = admin_key == st.secrets["ADMIN_KEY"]

if st.checkbox("Show Application Log"):
    try:
        df = pd.read_csv("application_log.csv", names=["Time","User","Job","Model","Preview"])
        df['Time'] = pd.to_datetime(df['Time'])
        if not is_admin:
            df = df[df['User'].str.lower()==user_id]
        else:
            st.success("🔓 Admin access enabled — viewing all logs.")
            sel = st.selectbox("Filter by user", ["All"] + sorted(df['User'].str.lower().unique()))
            if sel!='All': df=df[df['User'].str.lower()==sel]
        st.dataframe(df.sort_values('Time', ascending=False), use_container_width=True)
        st.download_button("Download Log as CSV", df.to_csv(index=False).encode('utf-8'), file_name="career_applications_log.csv")
    except FileNotFoundError:
        st.warning("No application log found yet.")
