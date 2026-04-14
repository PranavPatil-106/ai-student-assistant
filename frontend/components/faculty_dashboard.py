import streamlit as st
import requests
import os

API_URL = "http://localhost:8000"

def faculty_dashboard():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"👩‍🏫 Faculty Dashboard - {st.session_state.full_name}")
    with col2:
        if st.button("🚪 Sign Out", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
            
    st.markdown("---")
    tab1, tab2 = st.tabs(["📤 Upload Materials", "📊 Preview Content"])
    
    with tab1:
        st.subheader("📤 Upload Study Materials")
        try:
            response = requests.get(f"{API_URL}/faculty/subjects", headers=st.session_state.get_auth_headers())
            existing_subjects = response.json().get("subjects", []) if response.status_code == 200 else []
        except:
            existing_subjects = []
            
        col1, col2 = st.columns(2)
        with col1:
            use_existing = st.checkbox("📂 Use existing subject", key="use_existing_subject")
            if use_existing and existing_subjects:
                subject = st.selectbox("Select Subject", existing_subjects, key="upload_subject_select")
            else:
                subject = st.text_input("Subject Name", key="upload_subject", placeholder="e.g., Physics, Edge AI")
                
        with col2:
            if subject and use_existing:
                try:
                    response = requests.get(f"{API_URL}/faculty/units/{subject}", headers=st.session_state.get_auth_headers())
                    existing_units = response.json().get("units", []) if response.status_code == 200 else []
                except:
                    existing_units = []
                use_existing_unit = st.checkbox("📁 Use existing unit (will replace files)", key="use_existing_unit")
                if use_existing_unit and existing_units:
                    unit = st.selectbox("Select Unit", existing_units, key="upload_unit_select")
                    st.warning("⚠️ Warning: Uploading to existing unit will REPLACE all current files!")
                else:
                    unit = st.text_input("New Unit Name", key="upload_unit", placeholder="e.g., Unit 1, Chapter 2")
            else:
                unit = st.text_input("Unit Name", key="upload_unit", placeholder="e.g., Unit 1, Chapter 2")
                
        uploaded_file = st.file_uploader("Choose a file (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"], key="file_upload")
        
        if st.button("Upload File", key="upload_btn", use_container_width=True):
            if not subject or not unit:
                st.error("Please provide both subject and unit names")
            elif not uploaded_file:
                st.error("Please select a file to upload")
            else:
                with st.spinner("Uploading file..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        replace_mode = use_existing and subject in existing_subjects and 'use_existing_unit' in st.session_state and st.session_state.use_existing_unit
                        data = {"subject": subject, "unit": unit, "replace": "true" if replace_mode else "false"}
                        
                        response = requests.post(
                            f"{API_URL}/faculty/upload",
                            files=files, data=data, headers=st.session_state.get_auth_headers()
                        )
                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"✅ File uploaded successfully!")
                        else:
                            st.error(response.json().get("detail", "Upload failed"))
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    with tab2:
        st.subheader("📊 Preview Generated Content")
        try:
            response = requests.get(f"{API_URL}/faculty/subjects", headers=st.session_state.get_auth_headers())
            subjects = response.json().get("subjects", []) if response.status_code == 200 else []
        except:
            subjects = []
            
        if not subjects:
            st.info("No subjects found.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                subject = st.selectbox("Select Subject", subjects, key="select_preview_subject")
            if subject:
                try:
                    response = requests.get(f"{API_URL}/faculty/units/{subject}", headers=st.session_state.get_auth_headers())
                    units = response.json().get("units", []) if response.status_code == 200 else []
                except:
                    units = []
                with col2:
                    unit = st.selectbox("Select Unit", units if units else ["No units"], key="select_preview_unit")
                    
            if subject and unit and unit != "No units":
                st.markdown("---")
                if "preview_mcqs" not in st.session_state: st.session_state.preview_mcqs = []
                if "preview_flashcards" not in st.session_state: st.session_state.preview_flashcards = []
                if "preview_generating" not in st.session_state: st.session_state.preview_generating = False
                if "preview_gen_type" not in st.session_state: st.session_state.preview_gen_type = None
                if "preview_gen_count" not in st.session_state: st.session_state.preview_gen_count = 0
                if "preview_gen_total" not in st.session_state: st.session_state.preview_gen_total = 10
                
                preview_tabs = st.tabs(["📝 Summary", "❓ MCQs", "🧠 Flashcards"])
                
                with preview_tabs[0]:
                    if st.button("📝 Generate Summary", use_container_width=True):
                        if not st.session_state.llm_api_key:
                            st.error("Please configure API Key in settings.")
                        else:
                            with st.spinner("Generating summary..."):
                                try:
                                    response = requests.post(
                                        f"{API_URL}/faculty/generate-content",
                                        data={"subject": subject, "unit": unit, "content_type": "summary"},
                                        headers=st.session_state.get_auth_headers()
                                    )
                                    if response.status_code == 200:
                                        data = response.json()
                                        if data.get("status") == "success":
                                            st.markdown(data["summary"])
                                        else:
                                            st.error(data.get("message", "Error"))
                                    else:
                                        st.error(response.json().get("detail", "Error"))
                                except Exception as e:
                                    st.error(str(e))
                # Add basic MCQ and Flashcard UI without interactive step-by-step for brevity
                with preview_tabs[1]:
                    if st.button("❓ Generate 1 MCQ", use_container_width=True):
                        if not st.session_state.llm_api_key:
                            st.error("Please configure API Key.")
                        else:
                            with st.spinner("Generating..."):
                                try:
                                    response = requests.post(f"{API_URL}/faculty/generate-content", data={"subject": subject, "unit": unit, "content_type": "mcq"}, headers=st.session_state.get_auth_headers())
                                    if response.status_code == 200:
                                        data = response.json()
                                        if data.get("status") == "success" and data.get("mcqs"):
                                            mcq = data["mcqs"][0]
                                            st.write(mcq['question'])
                                            for k, v in mcq['options'].items(): st.write(f"{k}) {v}")
                                            st.write(f"Answer: {mcq['correct_answer']} - {mcq['explanation']}")
                                    else:
                                        st.error("Error generating")
                                except Exception as e:
                                    st.error(str(e))
                with preview_tabs[2]:
                    if st.button("🧠 Generate 1 Flashcard", use_container_width=True):
                        if not st.session_state.llm_api_key:
                            st.error("Please configure API Key.")
                        else:
                            with st.spinner("Generating..."):
                                try:
                                    response = requests.post(f"{API_URL}/faculty/generate-content", data={"subject": subject, "unit": unit, "content_type": "flashcards"}, headers=st.session_state.get_auth_headers())
                                    if response.status_code == 200:
                                        data = response.json()
                                        if data.get("status") == "success" and data.get("flashcards"):
                                            card = data["flashcards"][0]
                                            st.write(f"Front: {card['front']}\nBack: {card['back']}")
                                    else:
                                        st.error("Error generating")
                                except Exception as e:
                                    st.error(str(e))
