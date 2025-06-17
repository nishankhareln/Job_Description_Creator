import streamlit as st
import requests
from dotenv import load_dotenv
import os
import json
import psycopg2
from datetime import date

# Load .env for local dev
load_dotenv()

# Unified secret getter
def get_secret(key):
    return os.getenv(key) or st.secrets.get(key)

# Load secrets
API_KEY = get_secret("GEMINI_API_KEY")
PG_HOST = get_secret("PG_HOST")
PG_PORT = get_secret("PG_PORT")
PG_DB = get_secret("PG_DB")
PG_USER = get_secret("PG_USER")
PG_PASSWORD = get_secret("PG_PASSWORD")

# Check API Key
if not API_KEY:
    st.error("❌ API key not found in .env or .streamlit/secrets.toml")
    st.stop()

# Configure the page
st.set_page_config(page_title="Job Description Generator", page_icon="💼", layout="centered")

# Custom CSS
st.markdown("""
<style>
.main-header { text-align: center; color: #1f77b4; margin-bottom: 30px; }
.job-description { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #1f77b4; margin-top: 20px; }
.stButton > button { width: 100%; background-color: #1f77b4; color: white; border: none; padding: 10px; border-radius: 5px; font-size: 16px; font-weight: bold; }
.stDownloadButton > button { background-color: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🚀 AI Job Description Generator</h1>', unsafe_allow_html=True)
st.markdown("Fill out the form below to generate a professional job description using Google Gemini AI.")

# Company Info
st.subheader("🏢 Company Information")
col_company1, col_company2 = st.columns(2)
with col_company1:
    company_name = st.text_input("Company Name")
    company_size = st.selectbox("Company Size", ["Small (0-200)", "Medium (201-1000)", "Large (1000+)", "Not specified"])
with col_company2:
    industry = st.text_input("Industry")
    company_website = st.text_input("Company Website (optional)")
company_description = st.text_area("Company Description (optional)")

# Job Info
st.subheader("💼 Job Information")
col1, col2 = st.columns(2)
with col1:
    position = st.text_input("Job Title / Position*")
    experience_level = st.selectbox("Experience Level*", ["Entry-level", "Mid-level", "Senior", "Lead/Principal", "Director/VP"])
    location = st.text_input("Location")
with col2:
    employment_type = st.selectbox("Employment Type", ["Full-time", "Part-time", "Contract", "Internship"])
    salary_range = st.text_input("Salary Range (optional)")
    remote_work = st.selectbox("Remote Work Policy", ["Not specified", "Fully remote", "Hybrid", "On-site"])
skills = st.text_area("Required Skills (comma-separated)")

# Application Info
st.subheader("📧 Application Information")
col_app1, col_app2 = st.columns(2)
with col_app1:
    application_email = st.text_input("Application Email")
    application_deadline = st.date_input("Application Deadline (optional)", value=None)
with col_app2:
    application_link = st.text_input("Application Link (optional)")
    contact_person = st.text_input("Contact Person (optional)")
application_instructions = st.text_area("Additional Application Instructions (optional)")

# Additional Options
st.subheader("⚙️ Additional Options")
col3, col4 = st.columns(2)
with col3:
    include_benefits = st.checkbox("Include benefits section", value=True)
    include_company_culture = st.checkbox("Include company culture section")
with col4:
    include_growth_opportunities = st.checkbox("Include growth opportunities")
    include_team_info = st.checkbox("Include team information")

# DB connection
def get_db_connection():
    try:
        st.write(f"🔌 Connecting to DB at {PG_HOST}:{PG_PORT} as {PG_USER}")
        conn = psycopg2.connect(
            host=PG_HOST,
            port=int(PG_PORT),
            dbname=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD,
            sslmode='require'
        )
        return conn
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        raise

def save_job_to_db(data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO job_submissions (
                company_name, company_size, industry, company_website, company_description,
                job_title, experience_level, location, employment_type, salary_range, remote_work,
                skills, include_benefits, include_company_culture, include_growth_opportunities,
                include_team_info, application_email, application_link, contact_person,
                application_deadline, application_instructions
            ) VALUES (
                %(company_name)s, %(company_size)s, %(industry)s, %(company_website)s, %(company_description)s,
                %(job_title)s, %(experience_level)s, %(location)s, %(employment_type)s, %(salary_range)s, %(remote_work)s,
                %(skills)s, %(include_benefits)s, %(include_company_culture)s, %(include_growth_opportunities)s,
                %(include_team_info)s, %(application_email)s, %(application_link)s, %(contact_person)s,
                %(application_deadline)s, %(application_instructions)s
            )
        """
        cursor.execute(insert_query, data)
        conn.commit()
        cursor.close()
        conn.close()
        st.success("✅ Job details saved to database.")
    except Exception as e:
        st.error(f"❌ Failed to save job to DB: {e}")

def generate_prompt(data):
    return f"""
Generate a job description for:
Job Title: {data['job_title']}
Company: {data['company_name']}
Experience Level: {data['experience_level']}
Industry: {data['industry']}
Location: {data['location']}
Type: {data['employment_type']}
Skills: {data['skills'] or 'Not specified'}
Salary: {data['salary_range'] or 'Competitive'}
Remote: {data['remote_work']}
Description: {data['company_description']}
Website: {data['company_website']}
Additional Instructions: {data['application_instructions']}
{"Include benefits." if data['include_benefits'] else ""}
{"Include company culture." if data['include_company_culture'] else ""}
{"Include growth opportunities." if data['include_growth_opportunities'] else ""}
{"Include team info." if data['include_team_info'] else ""}
"""

# Gemini API call
def call_gemini_api(prompt):
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7, "topK": 40, "topP": 0.95, "maxOutputTokens": 2048
        }
    }
    for model in ["gemini-1.5-flash", "gemini-1.5-pro"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        response = requests.post(url, headers=headers, json=data)
        if response.ok:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    return "Error: Could not generate content."

# Button handler
if st.button("🚀 Generate Job Description", type="primary"):
    if not position or not experience_level:
        st.warning("⚠️ Please fill required fields.")
    else:
        skills_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else []
        skills_str = ", ".join(skills_list)

        data = {
            "company_name": company_name,
            "company_description": company_description,
            "company_website": company_website,
            "job_title": position,
            "experience_level": experience_level,
            "industry": industry,
            "location": location,
            "employment_type": employment_type,
            "company_size": company_size,
            "skills": skills_str,
            "salary_range": salary_range,
            "remote_work": remote_work,
            "include_benefits": include_benefits,
            "include_company_culture": include_company_culture,
            "include_growth_opportunities": include_growth_opportunities,
            "include_team_info": include_team_info,
            "application_email": application_email,
            "application_link": application_link,
            "contact_person": contact_person,
            "application_deadline": application_deadline if application_deadline != date.today() else None,
            "application_instructions": application_instructions
        }

        prompt = generate_prompt(data)
        with st.spinner("🧐 Generating..."):
            description = call_gemini_api(prompt)

        if description.startswith("Error"):
            st.error(description)
        else:
            st.success("✅ Generated successfully!")
            st.markdown('<div class="job-description">', unsafe_allow_html=True)
            st.markdown("### 📄 Generated Job Description")
            st.markdown(description)
            st.markdown('</div>', unsafe_allow_html=True)

            save_job_to_db(data)

            filename = f"{company_name.replace(' ', '_')}_{position.replace(' ', '_')}_job_description.txt"
            st.download_button("Download Description", description, file_name=filename, mime="text/plain")

# Footer
st.markdown("---")
st.markdown("-------Recruit Nepal------")

