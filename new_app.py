import streamlit as st
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
import os
import re
import requests
import google.generativeai as genai

# Configure the Gemini API key
genai.configure(api_key=os.getenv(genai_api_key))

def render_markdown_text(text):
    text = re.sub(r"^\s*-\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)  # Convert **bold** to <b>bold</b>
    text = text.replace("\n", "<br/>")  # Replace newline characters with <br/>
    return text

# Function to query Google Gemini API
def query_gpt(user_input):
    # Initialize the Gemini model
    model = genai.GenerativeModel("gemini-pro")
    
    # Generate a response from the model
    response = model.generate_content(user_input)
    
    # Extract and return the content
    return response.text if hasattr(response, 'text') else response.candidates[0].content

def render_skills(skills, layout_type):
    if layout_type in ["Modern", "Creative"]:
        skill_columns = [skills[i:i + 2] for i in range(0, len(skills), 2)]
        skills_html = ""
        for row in skill_columns:
            skills_html += '<div style="display: flex; justify-content: space-between;">'
            for skill in row:
                skills_html += f'<div style="width: 48%;"><b>{skill["name"]}</b><br>{"⭐" * skill["rating"]} ({skill["rating"]}/5)</div>'
            skills_html += "</div>"
        return skills_html
    else:
        return "".join([
            f'<p><b>{skill["name"]}</b><br>{"⭐" * skill["rating"]} ({skill["rating"]}/5)</p>'
            for skill in skills
        ])

def render_fresher_projects(projects, theme_color, text_color, font_family):
    if not projects:
        return "<p>No projects to display.</p>"

    projects_html = "<h3>Projects</h3>"
    for project in projects:
        projects_html += f"""
        <div style="margin-bottom: 15px; padding: 10px; border: 1px solid {text_color}; border-radius: 5px;">
            <h4 style="color: {text_color}; font-family: {font_family};">{project.get('project_name', '[Project Name]')}</h4>
            <p><b>Tools Used:</b> {project.get('tools_used', '[Tools Used]')}</p>
            <p>{project.get('description', '[Project Description]')}</p>
        </div>
        """
    return projects_html

def render_experienced_work(work_experiences, theme_color, text_color, font_family):
    if not work_experiences:
        return "<p>No work experiences to display.</p>"

    work_html = "<h3>Work Experience</h3>"
    for work in work_experiences:
        processed_description = render_markdown_text(work.get('description', ''))
        description_html = "".join(
            f"<li>{desc.strip()}</li>" for desc in processed_description.split("<br/>") if desc.strip()
        )
        # Generate the HTML for each work experience
        work_html += f"""
        <div style="background-color: {theme_color}; color: {text_color}; font-family: {font_family}; 
                    padding: 20px; border-radius: 10px; margin-bottom: 10px; text-align: left;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <div>
                    <b>{work.get('role', '[Role]')}</b>
                </div>
                <div>
                    <span>{work.get('start_date', '[Start Date]')} - {work.get('end_date', '[End Date]')}</span>
                </div>
            </div>
            <div>
                <b>{work.get('company_name', '[Company Name]')}</b>, <span>{work.get('location', '[Location]')}</span>
            </div>
            <ul style="margin-top: 5px; padding-left: 20px;">
                {description_html}
            </ul>
        </div>
        """
    return work_html

# Function to generate PDF using PDF.co API
def generate_pdf(data,font_family,text_color,theme_color):
    API_KEY = 'rakib.m@ivyproschool.com_TIxfVsy2h0LE7O5MUZvtgdJYCK0JtR5PN4QvBKD6DRoUKZVivtzlg2V87wEpsu4j'
    url = "https://api.pdf.co/v1/pdf/convert/from/html"

    html_content = f"""
    <html>
    <head>
        <style>
            @page {{
                margin: 0; /* Remove margins for the entire page */
            }}
            body {{
                margin: 0; 
                padding: 0; 
                font-family: {font_family}; 
                color: {text_color};
                background-color: {theme_color};
            }}
        </style>
    </head>
    <body>
        {data}
    </body>
    </html>
    """
    payload = {
        "html": html_content,
        "name": "resume.pdf"  # File name
    }
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        result = response.json()
        pdf_url = result.get("url")
        if pdf_url:
            # Download the PDF from the URL
            pdf_response = requests.get(pdf_url)
            if pdf_response.status_code == 200:
                return pdf_response.content  # Return PDF content for download
            else:
                st.error(f"Error downloading PDF: {pdf_response.status_code}")
                return None
        else:
            st.error("Error: PDF URL not found in API response.")
            return None
    else:
        st.error(f"Error generating PDF: {response.text}")
        return None

# Initialize session state for multi-page navigation
if "page" not in st.session_state:
    st.session_state.page = 1
if "resume_data" not in st.session_state:
    st.session_state.resume_data = {}

# Navigation Functions
def go_to_next_page():
    st.session_state.page += 1

def go_to_previous_page():
    st.session_state.page -= 1

def next_button_callback():
    st.session_state.resume_data.update({
        "first_name": st.session_state.first_name,
        "last_name": st.session_state.last_name,
        "job_title": st.session_state.job_title,
        "address": st.session_state.address,
        "phone": st.session_state.phone,
        "email": st.session_state.email,
    })
    go_to_next_page()

# Streamlit App Layout and Pages
st.set_page_config(page_title="Resume Builder", layout="wide")

# Page 1: Style Selection
if st.session_state.page == 1:
    st.title("📄 Resume Builder - Step 1: Select Style and Design")
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.header("Style and Design Options")
        theme_color = st.color_picker("Choose Background Color", st.session_state.resume_data.get("theme_color", "#FFFFFF"))
        text_color = st.color_picker("Choose Text Color", st.session_state.resume_data.get("text_color", "#000000"))
        font_family = st.selectbox(
            "Choose Font Style",
            ["Helvetica", "Arial", "Times New Roman", "Courier"],
            index=["Helvetica", "Arial", "Times New Roman", "Courier"].index(
                st.session_state.resume_data.get("font_family", "Helvetica")
            )
        )
        layout_type = st.selectbox(
            "Choose Resume Layout",
            ["Modern", "Classic", "Minimalist", "Creative"],
            index=["Modern", "Classic", "Minimalist", "Creative"].index(
                st.session_state.resume_data.get("layout_type", "Modern")
            )
        )

    with right_col:
        st.header("Live Layout Preview")
        # Placeholder data for preview
        name = "[Your Name]"
        job_title = "[Your Job Title]"
        phone = "[Your Phone]"
        email = "[Your Email]"
        skills = [
            {"name": "Python", "rating": 5},
            {"name": "JavaScript", "rating": 4},
            {"name": "Machine Learning", "rating": 5},
            {"name": "Django", "rating": 3},
        ]
        education = "B.Sc in Computer Science, XYZ University, 2023"
        experience_or_projects = (
            "<b>Software Engineer at ABC Corp</b><br>"
            "Worked on developing scalable web applications using modern technologies."
        )

        # Render preview based on layout
        if layout_type == "Modern":
            st.markdown(f"""
            <div style="background-color: {theme_color}; color: {text_color}; font-family: {font_family}; padding: 20px; border-radius: 10px;">
                <h1 style="text-align: center; font-size: 32px;">{name}</h1>
                <h3 style="text-align: center; font-size: 20px;">{job_title}</h3>
                <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                    <p style="text-align: left;">{phone}</p>
                    <p style="text-align: right;">{email}</p>
                </div>
                <h3>Skills</h3>
                {render_skills(skills, layout_type)}
                <h3>Education</h3>
                <p>{education}</p>
                <h3>Experience</h3>
                <p>{experience_or_projects}</p>
            </div>
            """, unsafe_allow_html=True)

        elif layout_type == "Classic":
            st.markdown(f"""
            <div style="background-color: {theme_color}; color: {text_color}; font-family: {font_family}; padding: 20px; border-radius: 10px;">
                <h1 style="text-align: left; font-size: 28px;">{name}</h1>
                <h3 style="text-align: left; font-size: 18px;">{job_title}</h3>
                <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                    <p style="text-align: left;">{phone}</p>
                    <p style="text-align: right;">{email}</p>
                </div>
                <h3>Skills</h3>
                {render_skills(skills, layout_type)}
                <h3>Education</h3>
                <p>{education}</p>
                <h3>Experience</h3>
                <p>{experience_or_projects}</p>
            </div>
            """, unsafe_allow_html=True)

        elif layout_type == "Minimalist":
            st.markdown(f"""
            <div style="background-color: {theme_color}; color: {text_color}; font-family: {font_family}; padding: 20px; border-radius: 10px;">
                <h1 style="text-align: center; font-size: 30px;">{name}</h1>
                <h3 style="text-align: center; font-size: 16px;">{job_title}</h3>
                <div style="margin-top: 10px;">
                    <p style="text-align: left;">{phone}</p>
                    <p style="text-align: right;">{email}</p>
                </div>
                <h3>Skills</h3>
                {render_skills(skills, layout_type)}
                <h3>Education</h3>
                <p>{education}</p>
                <h3>Experience</h3>
                <p>{experience_or_projects}</p>
            </div>
            """, unsafe_allow_html=True)

        elif layout_type == "Creative":
            st.markdown(f"""
            <div style="background-color: {theme_color}; color: {text_color}; font-family: {font_family}; padding: 20px; border-radius: 10px;">
                <h1 style="text-align: center; font-size: 34px; font-weight: bold;">{name}</h1>
                <h3 style="text-align: center; font-size: 22px; font-style: italic;">{job_title}</h3>
                <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                    <p style="text-align: left;">{phone}</p>
                    <p style="text-align: right;">{email}</p>
                </div>
                <h3>Skills</h3>
                {render_skills(skills, layout_type)}
                <h3>Education</h3>
                <p>{education}</p>
                <h3>Experience</h3>
                <p>{experience_or_projects}</p>
            </div>
            """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    if col2.button("Next", key="page1_next"):
        st.session_state.resume_data.update({
            "theme_color": theme_color,
            "text_color": text_color,
            "font_family": font_family,
            "layout_type": layout_type,
        })
        go_to_next_page()

# Page 2: Personal Details
elif st.session_state.page == 2:
    st.title("📄 Resume Builder - Step 2: Personal Details")

    # Use styling and layout options selected on Page 1
    layout_type = st.session_state.resume_data["layout_type"]
    theme_color = st.session_state.resume_data["theme_color"]
    text_color = st.session_state.resume_data["text_color"]
    font_family = st.session_state.resume_data["font_family"]

    # Initialize session state for personal information
    if "personal_info" not in st.session_state:
        st.session_state.personal_info = {
            "first_name": "",
            "last_name": "",
            "job_title": "",
            "phone": "",
            "email": "",
        }

    # Input Section: Collect Personal Details
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.header("Enter Your Personal Information")
        st.session_state.personal_info["first_name"] = st.text_input(
            "First Name", value=st.session_state.personal_info["first_name"]
        )
        st.session_state.personal_info["last_name"] = st.text_input(
            "Last Name", value=st.session_state.personal_info["last_name"]
        )
        st.session_state.personal_info["job_title"] = st.text_input(
            "Job Title", value=st.session_state.personal_info["job_title"]
        )
        st.session_state.personal_info["phone"] = st.text_input(
            "Phone", value=st.session_state.personal_info["phone"]
        )
        st.session_state.personal_info["email"] = st.text_input(
            "Email", value=st.session_state.personal_info["email"]
        )

    # Live Preview Section
    with right_col:
        st.header("Live Preview")

        # Fetch entered details or use placeholders
        name = f"{st.session_state.personal_info['first_name']} {st.session_state.personal_info['last_name']}".strip() or "[Your Name]"
        job_title = st.session_state.personal_info["job_title"] or "[Your Job Title]"
        phone = f"Phone - {st.session_state.personal_info['phone']}" if st.session_state.personal_info["phone"] else "Phone - [Your Phone]"
        email = f"Email - {st.session_state.personal_info['email']}" if st.session_state.personal_info["email"] else "Email - [Your Email]"

        # Preview based on layout type
        st.markdown(f"""
        <div style="background-color: {theme_color}; color: {text_color}; font-family: {font_family}; padding: 20px; border-radius: 10px;">
            <h1 style="text-align: {"center" if layout_type in ["Modern", "Creative"] else "left"};">{name}</h1>
            <h3 style="text-align: {"center" if layout_type in ["Modern", "Creative"] else "left"};">{job_title}</h3>
            <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                <p style="text-align: left;">{phone}</p>
                <p style="text-align: right;">{email}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Navigation Buttons
    col1, col2 = st.columns([1, 1])
    if col1.button("Back"):
        go_to_previous_page()
    if col2.button("Next"):
        st.session_state.resume_data["personal_info"] = st.session_state.personal_info
        go_to_next_page()

# Page 3: Summary with Langchain and gpt, skills
elif st.session_state.page == 3:
    st.title("📄 Resume Builder - Step 3: Summary and Skills")

    # Retrieve layout and styling options from session state
    layout_type = st.session_state.resume_data["layout_type"]
    theme_color = st.session_state.resume_data["theme_color"]
    text_color = st.session_state.resume_data["text_color"]
    font_family = st.session_state.resume_data["font_family"]

    # Fetch personal information from Page 2
    personal_info = st.session_state.resume_data.get("personal_info", {})
    name = f"{personal_info.get('first_name', '')} {personal_info.get('last_name', '')}".strip() or "[Your Name]"
    job_title = personal_info.get("job_title", "[Your Job Title]")
    phone = f"Phone - {personal_info.get('phone', '[Your Phone]')}"
    email = f"Email - {personal_info.get('email', '[Your Email]')}"

    # Initialize session state for summary and skills
    if "summary" not in st.session_state:
        st.session_state.summary = ""
    if "skills" not in st.session_state:
        st.session_state.skills = []

    # Two columns for input and live preview
    left_col, right_col = st.columns([1, 2])

    with left_col:
        # Job Description Input for GPT-based Summary Generation
        st.header("Job Description")
        job_description = st.text_area(
            "Paste the job description for the role you're applying for:",
            height=150,
        )
        # Store it in the session state for access outside the block
        if job_description:
            st.session_state["job_description"] = job_description

        # Job Profile Input
        st.header("Job Profile")
        job_profile = st.text_input("Describe the job profile in a sentence:")

        # Generate Summary using GPT
        if st.button("Generate Summary"):
            if job_description.strip() and job_profile.strip():
                try:
                    # Integrate the query_gpt function for summary generation
                    input_text = f"Create a 3-4 line summary about myself for my resume, emphasizing my personality, social skills, and interests outside of work based on the following Job Description:\n{job_description}\n\n and Job Profile:\n{job_profile}"
                    generated_summary = query_gpt(input_text)  # Use the LangChain GPT function
                    st.session_state.summary = generated_summary
                    st.success("Summary generated successfully!")
                except Exception as e:
                    st.error(f"Error generating summary: {e}")
            else:
                st.error("Please provide both job description and job profile.")

        # Summary Input
        st.session_state.summary = st.text_area(
            "Edit your professional summary:",
            value=st.session_state.summary,
            height=120,
        )

        # Skills Input
        st.header("Add Your Skills")
        with st.form("add_skills_form"):
            skill_name = st.text_input("Skill Name")
            skill_rating = st.slider("Skill Rating (1 to 5 Stars)", 1, 5, 3)
            if st.form_submit_button("Add Skill"):
                st.session_state.skills.append({"name": skill_name, "rating": skill_rating})

        # Display and Remove Skills
        st.markdown("### Your Skills")
        for i, skill in enumerate(st.session_state.skills):
            cols = st.columns([3, 1])  # Skill name and rating in one column, "Remove" button in the other
            with cols[0]:
                st.write(f"{skill['name']} - {'⭐' * skill['rating']} ({skill['rating']}/5)")
            with cols[1]:
                if st.button("Remove", key=f"remove_skill_{i}"):
                    st.session_state.skills.pop(i)

    with right_col:
        # Live Preview
        st.header("Live Preview")

        # Fetch summary and skills
        summary = st.session_state.summary or "[Your professional summary or career objective goes here.]"
        # Render Live Preview
        st.markdown(f"""
        <div style="background-color: {theme_color}; color: {text_color}; font-family: {font_family}; padding: 20px; border-radius: 10px;">
            <h1 style="text-align: {"center" if layout_type in ["Modern", "Creative"] else "left"};">{name}</h1>
            <h3 style="text-align: {"center" if layout_type in ["Modern", "Creative"] else "left"};">{job_title}</h3>
            <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                <p style="text-align: left;">{phone}</p>
                <p style="text-align: right;">{email}</p>
            </div>
            <p>{summary}</p>
            <h3>Skills</h3>
            {render_skills(st.session_state.skills, layout_type)}
        </div>
        """, unsafe_allow_html=True)

    # Navigation Buttons
    col1, col2 = st.columns([1, 1])
    if col1.button("Back", key="page3_back"):
        go_to_previous_page()
    if col2.button("Next", key="page3_next"):
        st.session_state.resume_data["summary"] = st.session_state.summary
        st.session_state.resume_data["skills"] = st.session_state.skills
        go_to_next_page()

# Page 4: Project/Workexperience with Langchain and gpt
elif st.session_state.page == 4:
    st.title("📄 Resume Builder - Step 4: Work Experience / Projects")

    # Retrieve layout and styling options from session state
    layout_type = st.session_state.resume_data["layout_type"]
    theme_color = st.session_state.resume_data["theme_color"]
    text_color = st.session_state.resume_data["text_color"]
    font_family = st.session_state.resume_data["font_family"]

    # Retrieve data from previous pages
    personal_info = st.session_state.resume_data.get("personal_info", {})
    name = f"{personal_info.get('first_name', '')} {personal_info.get('last_name', '')}".strip() or "[Your Name]"
    job_title = personal_info.get("job_title", "[Your Job Title]")
    phone = f"Phone - {personal_info.get('phone', '[Your Phone]')}"
    email = f"Email - {personal_info.get('email', '[Your Email]')}"
    professional_summary = st.session_state.resume_data.get("summary", "[Your professional summary or career objective goes here.]")
    skills = st.session_state.resume_data.get("skills", [])

    if "projects" not in st.session_state:
        st.session_state.projects = []
    if "work_experiences" not in st.session_state:
        st.session_state.work_experiences = []

    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.header("Are you a Fresher or Experienced?")
        experience_type = st.radio("Select your profile:", ["Fresher", "Experienced"], horizontal=True)

        # Get the job description
        if "job_description" in st.session_state:
            job_description_variable = st.session_state["job_description"]
        else:
            job_description_variable = None

        if experience_type == "Fresher":
            st.subheader("Add Project Details")
            project_name = st.text_input("Project Name")
            tools_used = st.text_input("Tools Used")
            project_info = st.text_area("Brief Description of the Project", height=150)

            # Generate Project Summary using GPT
            if st.button("Generate Project Summary"):
                if project_name.strip() and tools_used.strip() and project_info.strip():
                    try:
                        input_text = f"""
                                        Using the details provided below, create a concise project summary in three bullet points with the following format:
                                        **Objective:** Clearly state the project's goal or purpose.
                                        **Tools/Technologies Used:** Mention the tools and technologies applied in the project.
                                        **Outcome:** Summarize the key results or achievements, ensuring the outcome indirectly aligns with or hints at the job description {job_description_variable}.

                                        Details:
                                        - Project Name: {project_name}
                                        - Tools/Technologies Used: {tools_used}
                                        - Description: {project_info}
                                        """
                        generated_project_summary = query_gpt(input_text)
                        st.session_state.generated_project_summary = render_markdown_text(generated_project_summary)
                        st.success("Project summary generated successfully!")
                    except Exception as e:
                        st.error(f"Error generating project summary: {e}")
                else:
                    st.error("Please fill in all fields to generate the project summary.")

            project_summary = st.text_area(
                "Edit your Project Summary:",
                value=st.session_state.get("generated_project_summary", ""),
                height=120,
            )

            # Add Project
            if st.button("Add Project"):
                if project_name.strip() and tools_used.strip() and project_summary.strip():
                    st.session_state.projects.append({
                        "project_name": project_name,
                        "tools_used": tools_used,
                        "description": project_summary,
                    })
                    st.success("Project added successfully!")
            project_to_remove = None
            # Display and Remove Projects
            if st.session_state.projects:
                st.subheader("Your Projects")
                for i, project in enumerate(st.session_state.projects):
                    with st.expander(f"{project['project_name']}"):
                        st.markdown(f"**Tools Used:** {project['tools_used']}")
                        st.markdown(f"**Description:** {project['description']}")
                        if st.button(f"Remove Project {i + 1}", key=f"remove_project_{i}"):
                            project_to_remove = i
                            st.success(f"Marked project '{project['project_name']}' for removal.")
                            break  # Exit loop to avoid index issues
                if project_to_remove is not None:
                    st.session_state.projects.pop(project_to_remove)

        elif experience_type == "Experienced":
            st.subheader("Add Work Experience")
            company_name = st.text_input("Company Name")
            company_location = st.text_input("Location")
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date (Leave blank if current)", disabled=st.checkbox("Currently Working Here"))
            role_description = st.text_input("Description of Your Role")
            key_achievements = st.text_input("Key achievements and contributions")
            skills_expertise = st.text_input("Skills and expertise demonstrated")
            impact = st.text_area("Overall impact or value added",height=100)

            # Generate Work Experience Summary using GPT
            if st.button("Generate Work Experience Summary"):
                if company_name.strip() and company_location.strip() and role_description.strip():
                    try:
                        input_text = f"""
                                        Based on the following details, create a professional work experience summary in 3 to 4 concise bullet points:

                                        1. **Role Description:** {role_description}
                                        2. **Key Achievements:** {key_achievements}
                                        3. **Skills and Expertise:** {skills_expertise}
                                        4. **Impact:** {impact}

                                        Refine and present the information in a polished and professional manner, suitable for a resume or LinkedIn profile.
                                        """
                        generated_work_summary = query_gpt(input_text)
                        st.session_state.generated_work_summary = generated_work_summary
                        st.success("Work experience summary generated successfully!")
                    except Exception as e:
                        st.error(f"Error generating work experience summary: {e}")
                else:
                    st.error("Please fill in all fields to generate the work experience summary.")

            work_summary = st.text_area(
                "Edit your Work Experience Summary:",
                value=st.session_state.get("generated_work_summary", ""),
                height=120,
            )

            # Add Work Experience
            if st.button("Add Work Experience"):
                if company_name.strip() and company_location.strip() and work_summary.strip():
                    st.session_state.work_experiences.append({
                        "company_name": company_name,
                        "location": company_location,
                        "start_date": str(start_date),
                        "end_date": str(end_date) if end_date else "Present",
                        "role" : role_description,
                        "description": work_summary,
                    })
                    st.success("Work experience added successfully!")
            # Initialize workexp_to_remove in session state
            if "workexp_to_remove" not in st.session_state:
                st.session_state.workexp_to_remove = None

            # Display and Remove Work Experiences
            if st.session_state.work_experiences:
                st.subheader("Your Work Experiences")
                for i, work in enumerate(st.session_state.work_experiences):
                    with st.expander(f"{work['company_name']} - {work['location']}"):
                        st.markdown(f"**Start Date:** {work['start_date']}")
                        st.markdown(f"**End Date:** {work['end_date']}")
                        st.markdown(f"**Description:** {work['description']}")
                        # Button to remove the specific work experience
                        if st.button(f"Remove Work Experience {i + 1}", key=f"remove_work_{i}"):
                            st.session_state.workexp_to_remove = i
                            st.success(f"Marked Work Experience '{work['company_name']}' for removal.")
                            st.rerun()  # Trigger rerun to reflect changes

            # Remove the marked work experience
            if st.session_state.workexp_to_remove is not None:
                st.session_state.work_experiences.pop(st.session_state.workexp_to_remove)
                st.session_state.workexp_to_remove = None  # Reset after removal
                st.success("Work experience removed successfully.")

    with right_col:
        st.header("Live Preview")
        if experience_type == "Fresher" and st.session_state.projects:
            st.markdown(f"""
            <div style="background-color: {theme_color}; color: {text_color}; font-family: {font_family}; padding: 20px; border-radius: 10px;">
                <h1 style="text-align: center; font-size: 32px;">{name}</h1>
                <h3 style="text-align: center; font-size: 20px;">{job_title}</h3>
                <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                    <p style="text-align: left;">{phone}</p>
                    <p style="text-align: right;">{email}</p>
                </div>
                <p>{professional_summary}</p>
                <h3>Skills</h3>
                {render_skills(skills, layout_type)}
                {render_fresher_projects(st.session_state.projects, theme_color, text_color, font_family)}
            """, unsafe_allow_html=True)
        elif experience_type == "Experienced" and st.session_state.work_experiences:
            st.markdown(f"""
            <div style="background-color: {theme_color}; color: {text_color}; font-family: {font_family}; padding: 20px; border-radius: 10px;">
                <h1 style="text-align: center; font-size: 32px;">{name}</h1>
                <h3 style="text-align: center; font-size: 20px;">{job_title}</h3>
                <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                    <p style="text-align: left;">{phone}</p>
                    <p style="text-align: right;">{email}</p>
                </div>
                <p>{professional_summary}</p>
                <h3>Skills</h3>
                {render_skills(skills, layout_type)}
                {render_experienced_work(st.session_state.work_experiences, theme_color, text_color, font_family)}
            """, unsafe_allow_html=True)
            
        else:
            st.markdown(f"""
            <div style="background-color: {theme_color}; color: {text_color}; font-family: {font_family}; padding: 20px; border-radius: 10px;">
                <h1 style="text-align: center; font-size: 32px;">{name}</h1>
                <h3 style="text-align: center; font-size: 20px;">{job_title}</h3>
                <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                    <p style="text-align: left;">{phone}</p>
                    <p style="text-align: right;">{email}</p>
                </div>
                <p>{professional_summary}</p>
                <h3>Skills</h3>
                {render_skills(skills, layout_type)}
            """, unsafe_allow_html=True)

    # Navigation Buttons
    col1, col2 = st.columns([1, 1])
    if col1.button("Back", key="page4_back"):
        go_to_previous_page()
    if col2.button("Next", key="page4_next"):
        # Determine which Markdown to save based on experience type
        if experience_type == "Fresher":
            # Generate the Markdown for Fresher
            markdown_string = f"""
            <div style="background-color: {theme_color}; color: {text_color}; font-family: {font_family}; padding: 20px; border-radius: 10px;">
                <h1 style="text-align: center; font-size: 32px;">{name}</h1>
                <h3 style="text-align: center; font-size: 20px;">{job_title}</h3>
                <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                    <p style="text-align: left;">{phone}</p>
                    <p style="text-align: right;">{email}</p>
                </div>
                <p>{professional_summary}</p>
                <h3>Skills</h3>
                {render_skills(skills, layout_type)}
                {render_fresher_projects(st.session_state.projects, theme_color, text_color, font_family)}
            </div>
            """
        elif experience_type == "Experienced":
            # Generate the Markdown for Experienced
            markdown_string = f"""
            <div style="background-color: {theme_color}; color: {text_color}; font-family: {font_family}; padding: 20px; border-radius: 10px;">
                <h1 style="text-align: center; font-size: 32px;">{name}</h1>
                <h3 style="text-align: center; font-size: 20px;">{job_title}</h3>
                <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                    <p style="text-align: left;">{phone}</p>
                    <p style="text-align: right;">{email}</p>
                </div>
                <p>{professional_summary}</p>
                <h3>Skills</h3>
                {render_skills(skills, layout_type)}
                {render_experienced_work(st.session_state.work_experiences, theme_color, text_color, font_family)}
            </div>
            """
        else:
            markdown_string = ""  # Fallback if no valid type is set

        # Save the Markdown string in session state
        st.session_state.resume_preview_markdown = markdown_string
        st.session_state.resume_data.update({
            "projects": st.session_state.projects,
            "work_experiences": st.session_state.work_experiences,
            "experience_type": experience_type,
        })
        go_to_next_page()
    
# Page 5: Final Resume and Download
elif st.session_state.page == 5:
    st.title("📄 Resume Builder - Step 5: Download Your Resume")

    # Retrieve all resume data from session state
    resume_data = st.session_state.resume_data
    personal_info = resume_data.get("personal_info", {})
    name = f"{personal_info.get('first_name', '')} {personal_info.get('last_name', '')}".strip() or "[Your Name]"
    job_title = personal_info.get("job_title", "[Your Job Title]")
    phone = f"Phone - {personal_info.get('phone', '[Your Phone]')}"
    email = f"Email - {personal_info.get('email', '[Your Email]')}"
    summary = resume_data.get("summary", "[Your professional summary or career objective goes here.]")
    skills = resume_data.get("skills", [])
    projects = resume_data.get("projects", [])
    work_experiences = resume_data.get("work_experiences", [])

    # Styling options
    theme_color = resume_data["theme_color"]
    text_color = resume_data["text_color"]
    font_family = resume_data["font_family"]
    layout_type = resume_data["layout_type"]
    resume_preview_markdown = st.session_state.get("resume_preview_markdown", "")

    # Live Preview
    st.header("Live Preview")
    st.markdown(resume_preview_markdown, unsafe_allow_html=True)

    # Button to generate and download the PDF
    if st.button("Generate and Download Resume as PDF"):
        pdf_data = generate_pdf(resume_preview_markdown,font_family,text_color,theme_color)
        if pdf_data:
            st.download_button(
                label="Download PDF",
                data=pdf_data,
                file_name="resume.pdf",
                mime="application/pdf"
            )

    # Navigation Button
    if st.button("Back", key="page5_back"):
        go_to_previous_page()
