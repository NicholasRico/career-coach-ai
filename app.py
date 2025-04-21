import streamlit as st  # ✅ import first
from openai import OpenAI
from docx import Document
import fitz
import csv
from datetime import datetime
import pandas as pd

# ✅ FIRST Streamlit command – do NOT move this below anything
st.set_page_config(page_title="Career Coach AI", page_icon="🧠")

# 🔐 Password protection comes next
password = st.text_input("Enter access password", type="password")
if password != st.secrets["APP_PASSWORD"]:
    st.warning("🔒 This app is password protected. Enter the correct password to continue.")
    st.stop()

# ✅ Then everything else like setting up OpenAI client, UI, etc.
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- UI Layout ---
st.title("🎯 Career Coach AI")
st.markdown("Upload your resume and paste a job description to generate tailored bullets, a cover letter, and a recruiter message.")

# --- Inputs ---
resume_file = st.file_uploader("Upload your resume (.pdf or .docx)", type=["pdf", "docx"])
job_description = st.text_area("Paste job description here", height=250)
model_choice = st.selectbox("Choose GPT model", ["gpt-3.5-turbo", "gpt-4"], help="GPT-3.5 is cheaper; GPT-4 is more advanced.")
log_this = st.checkbox("Log this application", value=True)

# --- Resume Text Extraction ---
def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    return "".join([page.get_text() for page in doc])

def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

# --- Main Action ---
if st.button("Generate AI Career Materials") and resume_file and job_description:
    if resume_file.name.endswith(".pdf"):
        resume_text = extract_text_from_pdf(resume_file)
    else:
        resume_text = extract_text_from_docx(resume_file)

    prompt = f"""
You are an expert career coach AI. Using the resume below and the job description provided, return:

1. Two tailored resume bullet points.
2. A personalized cover letter (3 short paragraphs max).
3. A short outreach message to the hiring manager.

Resume:
{resume_text}

Job Description:
{job_description}
"""

    with st.spinner("Generating tailored materials..."):
        response = client.chat.completions.create(
            model=model_choice,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        output = response.choices[0].message.content
        st.success("✅ Generated Successfully!")

        # --- Output Tabs ---
        tabs = st.tabs(["📌 Resume Bullets", "📄 Cover Letter", "💬 Outreach Message"])
        sections = output.split("\n\n")
        if len(sections) >= 3:
            tabs[0].markdown(sections[0])
            tabs[1].markdown(sections[1])
            tabs[2].markdown(sections[2])
        else:
            st.text_area("Results", value=output, height=600)

        # --- Download as Word File ---
        doc_out = Document()
        doc_out.add_heading("Career Coach AI Output", 0)
        doc_out.add_paragraph(output)
        doc_out.save("CareerCoachOutput.docx")
        with open("CareerCoachOutput.docx", "rb") as f:
            st.download_button("📄 Download as Word File", f, file_name="CareerCoachOutput.docx")

        # --- Logging ---
        if log_this:
            job_title = job_description.splitlines()[0][:80] if job_description else "Unknown Role"
            with open("application_log.csv", mode="a", newline="") as log_file:
                writer = csv.writer(log_file)
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    job_title,
                    model_choice,
                    output[:300].replace("\n", " ")
                ])

# --- Application Log Viewer ---
st.markdown("---")
st.subheader("📊 Application Tracker & Log")

if st.checkbox("Show My Application Log"):
    try:
        df = pd.read_csv("application_log.csv", names=["Timestamp", "Job Title", "Model Used", "Output Preview"])
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        df = df.sort_values("Timestamp", ascending=False)

        search_term = st.text_input("🔍 Search job title or keywords")
        if search_term:
            df = df[df["Job Title"].str.contains(search_term, case=False, na=False)]

        st.dataframe(df, use_container_width=True)

        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Log as CSV", data=csv_data, file_name="career_applications_log.csv", mime="text/csv")
    except FileNotFoundError:
        st.warning("No application log found yet. Generate your first application to start logging!")
