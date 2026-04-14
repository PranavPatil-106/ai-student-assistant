import streamlit as st
import requests

import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

def login_signup_page():
    st.title("🎓 AI-Powered Student Learning Assistant")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
    
    with tab1:
        st.subheader("Login to Your Account")
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if not email or not password:
                    st.error("Please fill in all fields")
                else:
                    try:
                        response = requests.post(f"{API_URL}/auth/login", json={"email": email, "password": password})
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.user_id = data["user_id"]
                            st.session_state.full_name = data["full_name"]
                            st.session_state.email = data["email"]
                            st.session_state.role = data["role"]
                            st.session_state.college = data["college"]
                            st.session_state.branch = data["branch"]
                            st.session_state.logged_in = True
                            st.success(f"Welcome back, {data['full_name']}!")
                            st.rerun()
                        else:
                            st.error(response.json().get("detail", "Login failed"))
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    with tab2:
        st.subheader("Create New Account")
        with st.form("signup_form"):
            full_name = st.text_input("Full Name", key="signup_name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            role = st.selectbox("I am a:", ["student", "faculty"], key="signup_role")
            college = st.text_input("College Name", key="signup_col")
            branch = st.text_input("Branch (e.g. Computer Science)", key="signup_branch")
            year_of_study = st.selectbox("Year of Study", ["1st Year", "2nd Year", "3rd Year", "4th Year", "N/A (Faculty)"], key="signup_year")
            
            submit = st.form_submit_button("Sign Up", use_container_width=True)
            if submit:
                if not full_name or not email or not password or not college or not branch:
                    st.error("Please fill in all required fields")
                else:
                    try:
                        response = requests.post(
                            f"{API_URL}/auth/signup",
                            json={"full_name": full_name, "email": email, "password": password, "role": role, "college": college, "branch": branch, "year_of_study": year_of_study}
                        )
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.user_id = data["user_id"]
                            st.session_state.full_name = data["full_name"]
                            st.session_state.role = data["role"]
                            st.session_state.college = data["college"]
                            st.session_state.branch = data["branch"]
                            st.session_state.logged_in = True
                            st.success(f"Account created! Welcome, {data['full_name']}!")
                            st.rerun()
                        else:
                            st.error(response.json().get("detail", "Signup failed"))
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
