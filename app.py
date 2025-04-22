# app.py
import streamlit as st
from openai import OpenAI
from docx import Document
import fitz
import csv
from datetime import datetime
import pandas as pd
import io
import base64
import os

# ✅ First Streamlit command
st.set_page_config(page_title="Career Coach AI", page_icon="🧠")

# 🔐 Password protection
password = st.text_input("🔐 Enter access password", type="password")
if password != st.secrets["APP_PASSWORD"]:
    st.warning("This app is password protected. Enter the correct password to continue.")
    st.stop()

# 🎨 Set custom background based on session state
if "started" not in st.session_state:
    st.session_state.started = False

# Select appropriate background image
background_image = "hero" if not st.session_state.started else "content"
background_image_url = f"https://raw.githubusercontent.com/NicholasRico/career-coach-ai/main/.streamlit/assets/career-coach-{background_image}-ng.jpg"
st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url("{background_image_url}");
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position: center top;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# 🎨 Branded Welcome
if not st.session_state.started:
    st.title("Career Coach AI")
    st.markdown("Tailor your resume, cover letter, and recruiter message for **any job** in seconds.")
    st.markdown("Built by [Nicholas Gauthier](mailto:NickRGauthier@gmail.com)")

    if st.button("Get Started"):
        st.session_state.started = True

    st.stop()

# 👤 Track who is using it
user_id = st.text_input("👤 Enter your name or email to track your applications").strip().lower()
if not user_id:
    st.warning("Please enter your name or email to continue.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.markdown("---")
st.markdown("## Job Application Tailoring")

# Inputs
with st.container():
    resume_file = st.file_uploader("📌 Upload your resume (.pdf or .docx)", type=["pdf", "docx"])
    job_description = st.text_area("📝 Paste job description here", height=250)
    model_choice = st.selectbox("🤖 Choose GPT model", ["gpt-3.5-turbo", "gpt-4"])

    col1, col2, col3 = st.columns(3)
    with col1:
        log_this = st.checkbox("Log this application", value=True)
    with col2:
        expand_bullets = st.checkbox("Generate more bullet options")
    with col3:
        refresh_section = st.checkbox("Refresh only resume bullets")

custom_feedback = st.text_input("Optional: Enter tone/style instructions (e.g. confident, concise, persuasive)")
st.caption("Need ideas? Try: Professional, Friendly, Persuasive, Confident, Concise")

# --- Bulk JD ---
st.markdown("---")
st.markdown("## Bulk Job Descriptions")
st.caption("You can optionally download a CSV template and upload multiple job descriptions to process.")

sample_csv = """Job Description
This is where you'd paste job description #1.
This is job description #2.
"""
st.download_button("Download Template CSV", data=sample_csv, file_name="job_description_template.csv")
bulk_jd_file = st.file_uploader("Upload Bulk Job Descriptions CSV", type="csv")

# Helper functions
def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    return "".join([page.get_text() for page in doc])

def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

# Generation Trigger
if st.button("Generate AI Career Materials"):
    if resume_file:
        resume_text = extract_text_from_pdf(resume_file) if resume_file.name.endswith(".pdf") else extract_text_from_docx(resume_file)
    else:
        st.error("Please upload a resume.")
        st.stop()

    job_descriptions = []
    if bulk_jd_file:
        df_bulk = pd.read_csv(bulk_jd_file)
        job_descriptions = df_bulk["Job Description"].dropna().tolist()
    elif job_description:
        job_descriptions = [job_description]
    else:
        st.error("Please paste a job description or upload a CSV.")
        st.stop()

    for jd in job_descriptions:
        if refresh_section:
            prompt = f"""
You are an expert resume optimizer. Based only on the resume and job description below, generate five strong tailored resume bullet points.

Resume:
{resume_text}

Job Description:
{jd}
"""
        else:
            bullet_prompt = "five" if expand_bullets else "two"
            feedback_note = f"The user added this customization instruction: {custom_feedback}" if custom_feedback else ""
            prompt = f"""
You are an expert career coach AI. Using the resume below and the job description provided, return:
1. {bullet_prompt.capitalize()} tailored resume bullet points.
2. A personalized cover letter (3 short paragraphs max).
3. A short outreach message to the hiring manager.

{feedback_note}

Resume:
{resume_text}

Job Description:
{jd}
"""

        with st.spinner("Generating for a job..."):
            response = client.chat.completions.create(
                model=model_choice,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            output = response.choices[0].message.content
            st.success("✅ Generated Successfully!")

            st.markdown("---")
            st.subheader("📌 Resume Bullets")
            st.markdown(output.split("\n\n")[0])

            if not refresh_section:
                st.subheader("📄 Cover Letter")
                st.markdown(output.split("\n\n")[1])
                st.subheader("💬 Outreach Message")
                st.markdown(output.split("\n\n")[2])

            # Save to doc
            doc_out = Document()
            doc_out.add_heading("Career Coach AI Output", 0)
            doc_out.add_paragraph(output)
            doc_buffer = io.BytesIO()
            doc_out.save(doc_buffer)
            st.download_button("Download as Word File", doc_buffer.getvalue(), file_name="CareerCoachOutput.docx")

            # Logging
            if log_this:
                job_title = jd.splitlines()[0][:80] if jd else "Unknown Role"
                with open("application_log.csv", mode="a", newline="") as log_file:
                    writer = csv.writer(log_file)
                    writer.writerow([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        user_id,
                        job_title,
                        model_choice,
                        output[:300].replace("\n", " ")
                    ])

# --- Admin Log Viewer ---
st.markdown("---")
st.subheader("📊 Application Tracker & Log")

admin_key = st.text_input("🔑 Admin key (leave blank if not admin)", type="password")
is_admin = admin_key == st.secrets["ADMIN_KEY"]

if st.checkbox("📁 Show Application Log"):
    try:
        df = pd.read_csv("application_log.csv", names=["Timestamp", "User", "Job Title", "Model Used", "Output Preview"])
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])

        if not is_admin:
            df = df[df["User"].str.lower() == user_id]
        else:
            st.success("🔓 Admin access enabled — viewing all user logs.")
            filter_user = st.selectbox("Filter by user", options=["All"] + sorted(df["User"].str.lower().unique().tolist()))
            if filter_user != "All":
                df = df[df["User"].str.lower() == filter_user]

        df = df.sort_values("Timestamp", ascending=False)
        st.dataframe(df, use_container_width=True)

        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Log as CSV", data=csv_data, file_name="career_applications_log.csv", mime="text/csv")
    except FileNotFoundError:
        st.warning("No application log found yet. Generate your first application to start logging!")
