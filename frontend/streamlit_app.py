import streamlit as st
from components.login_signup import login_signup_page
from components.student_dashboard import student_dashboard
from components.faculty_dashboard import faculty_dashboard

st.set_page_config(
    page_title="AI Student Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { padding: 2rem; }
    .stButton>button {
        background-color: #4CAF50;
        color: white; border-radius: 5px;
        padding: 0.5rem 1rem; font-weight: 500;
    }
    .stButton>button:hover { background-color: #45a049; }
    h1 { color: #2c3e50; }
    h2, h3 { color: #34495e; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6; border-radius: 5px 5px 0 0; padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #4CAF50; color: white; }
</style>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "token" not in st.session_state:
    st.session_state.token = None
if "llm_provider" not in st.session_state:
    st.session_state.llm_provider = "Gemini"
if "llm_api_key" not in st.session_state:
    st.session_state.llm_api_key = ""

def get_auth_headers():
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    if st.session_state.llm_provider and st.session_state.llm_api_key:
        headers["llm-provider"] = st.session_state.llm_provider.lower()
        headers["llm-api-key"] = st.session_state.llm_api_key
    return headers

st.session_state.get_auth_headers = get_auth_headers

def main():
    if not st.session_state.logged_in:
        login_signup_page()
    else:
        with st.sidebar:
            st.header("⚙️ AI Configuration")
            st.markdown("Configure your Bring-Your-Own-Key details.")
            provider = st.selectbox("LLM Provider", ["Gemini", "OpenAI", "Groq", "Claude"], index=["Gemini", "OpenAI", "Groq", "Claude"].index(st.session_state.llm_provider))
            api_key = st.text_input("API Key", type="password", value=st.session_state.llm_api_key)
            if st.button("Save Configuration", use_container_width=True):
                st.session_state.llm_provider = provider
                st.session_state.llm_api_key = api_key
                st.success("Configuration saved!")
            st.markdown("---")
            st.markdown(f"**Logged in as:** {st.session_state.full_name}")
            st.markdown(f"**Role:** {st.session_state.role.capitalize()}")

        if not st.session_state.llm_api_key:
            st.warning("⚠️ Please configure your API key in the sidebar to use AI features.")

        if st.session_state.role == "student":
            student_dashboard()
        elif st.session_state.role == "faculty":
            faculty_dashboard()
        else:
            st.error("Invalid user role")
            if st.button("Back to Login"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

if __name__ == "__main__":
    main()
