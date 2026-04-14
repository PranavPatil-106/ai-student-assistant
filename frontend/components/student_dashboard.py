import streamlit as st
import requests

import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

def student_dashboard():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"👨‍🎓 Welcome, {st.session_state.full_name}!")
    with col2:
        if st.button("🚪 Sign Out", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
            
    st.markdown("---")
    
    try:
        response = requests.get(f"{API_URL}/student/workspaces", headers=st.session_state.get_auth_headers())
        workspaces_data = response.json().get("workspaces", []) if response.status_code == 200 else []
    except:
        workspaces_data = []

    if not workspaces_data:
        st.info("📚 No study materials available yet.")
        return

    # Create mapping of readable names to owner_ids
    workspace_options = {}
    for w in workspaces_data:
        if not w["subjects"]: continue
        if w["type"] == "Personal":
            workspace_options["My Personal Workspace"] = w["owner_id"]
        else:
            workspace_options[f"Faculty: {w['owner_name']}"] = w["owner_id"]

    if not workspace_options:
        st.info("📚 No subjects found inside any workspace.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        selected_ws_name = st.selectbox("🏫 Select Workspace", list(workspace_options.keys()), key="student_ws")
        owner_id = workspace_options[selected_ws_name]

    # Find subjects for this owner
    subjects = []
    for w in workspaces_data:
        if w["owner_id"] == owner_id:
            subjects = w["subjects"]
            break

    with col2:
        subject = st.selectbox("📖 Select Subject", subjects if subjects else ["None"], key="student_subject")

    if subject and subject != "None":
        try:
            response = requests.get(f"{API_URL}/student/units/{owner_id}/{subject}", headers=st.session_state.get_auth_headers())
            units = response.json().get("units", []) if response.status_code == 200 else []
        except:
            units = []
            
        with col3:
            unit = st.selectbox("📑 Select Unit", units if units else ["No units available"], key="student_unit")
    else:
        unit = None

    if not subject or not unit or unit == "No units available":
        st.warning("Please select a subject and unit to continue")
        return

    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs(["📘 Summarize", "❓ MCQ Practice", "🧠 Flashcards", "💬 Ask Question"])

    with tab1:
        if st.button("Generate Summary", key="gen_summary", use_container_width=True):
            if not st.session_state.llm_api_key:
                st.error("Please configure your API Key in the side menu.")
            else:
                with st.spinner("Generating summary..."):
                    try:
                        response = requests.post(f"{API_URL}/student/summary", json={"subject": subject, "unit": unit, "owner_id": owner_id}, headers=st.session_state.get_auth_headers())
                        if response.status_code == 200:
                            data = response.json()
                            if data.get("status") == "success":
                                st.markdown(data["summary"])
                            else:
                                st.error(data.get("message", "Failed"))
                        else:
                            st.error("Error generating summary")
                    except Exception as e:
                        st.error(str(e))

    with tab2:
        if st.button("Generate 1 MCQ", key="gen_mcq", use_container_width=True):
            if not st.session_state.llm_api_key:
                st.error("Please configure API key.")
            else:
                with st.spinner("Generating MCQ..."):
                    try:
                        response = requests.post(f"{API_URL}/student/mcq", json={"subject": subject, "unit": unit, "owner_id": owner_id, "count": 1}, headers=st.session_state.get_auth_headers())
                        if response.status_code == 200 and response.json().get("status") == "success":
                            data = response.json()
                            mcq = data["mcqs"][0]
                            st.write(mcq['question'])
                            for k, v in mcq['options'].items(): st.write(f"{k}) {v}")
                            st.write(f"Answer: {mcq['correct_answer']} - {mcq['explanation']}")
                        else:
                            st.error("Error")
                    except Exception as e:
                        st.error(str(e))

    with tab3:
        if st.button("Generate 1 Flashcard", key="gen_fc", use_container_width=True):
            if not st.session_state.llm_api_key:
                st.error("Please configure API key.")
            else:
                with st.spinner("Generating flashcard..."):
                    try:
                        response = requests.post(f"{API_URL}/student/flashcards", json={"subject": subject, "unit": unit, "owner_id": owner_id, "count": 1}, headers=st.session_state.get_auth_headers())
                        if response.status_code == 200 and response.json().get("status") == "success":
                            data = response.json()
                            fc = data["flashcards"][0]
                            st.success("Front: " + fc['front'])
                            st.info("Back: " + fc['back'])
                        else:
                            st.error("Error")
                    except Exception as e:
                        st.error(str(e))

    with tab4:
        question = st.text_area("Enter your question:", key="student_question")
        if st.button("Ask", use_container_width=True):
            if not st.session_state.llm_api_key:
                st.error("Please configure API key.")
            elif question:
                with st.spinner("Thinking..."):
                    try:
                        response = requests.post(f"{API_URL}/student/ask", json={"subject": subject, "unit": unit, "owner_id": owner_id, "question": question}, headers=st.session_state.get_auth_headers())
                        if response.status_code == 200 and response.json().get("status") == "success":
                            data = response.json()
                            st.markdown(data["answer"])
                            st.caption(f"Sources: {', '.join(data.get('sources', []))}")
                        else:
                            st.error("Error finding answer")
                    except Exception as e:
                        st.error(str(e))
