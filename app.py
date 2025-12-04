import streamlit as st
import requests
import time
import streamlit.components.v1 as components

# --- 1. Page Configuration ---
# Set as the very first command
st.set_page_config(
    page_title="Job Role Predictor",
    page_icon="✨",
    layout="wide"
)

BACKEND_URL = "http://127.0.0.1:5000"

# --- 3. Initialize Session State ---
# This is the "memory" of your app
if 'token' not in st.session_state:
    st.session_state['token'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = ""
if 'role' not in st.session_state:
    st.session_state['role'] = ""

# --- 4. Function to Clear Session (for Logout) ---
def logout():
    """Clears all session data and reruns the app to go to lobby."""
    st.session_state['token'] = None
    st.session_state['username'] = ""
    st.session_state['role'] = ""
    # Clear all cached data for all users
    st.cache_data.clear()
    # --- THIS IS THE FIX ---
    # We must also clear the leftover prediction results and balloons
    if 'last_prediction_results' in st.session_state:
        st.session_state['last_prediction_results'] = None
    if 'run_balloons' in st.session_state:
        st.session_state['run_balloons'] = False

# --- 5. NEW: CSS to Hide/Show Sidebar ---
def configure_sidebar():
    """
    Applies CSS to hide the sidebar on the lobby page,
    and show/hide specific pages based on user role.
    """
    if not st.session_state.get('token'):
        # --- LOGGED OUT (Homepage) ---
        # Hide the entire sidebar component
        st.markdown("""
            <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            </style>
        """, unsafe_allow_html=True)
    
    else:
        # --- LOGGED IN ---
        # Show the sidebar, but customize its contents
        
        # (First, add the welcome message and logout button)
        st.sidebar.write(f"Welcome, **{st.session_state['username']}**!")
        st.sidebar.button("Logout", on_click=logout, use_container_width=True, type="primary")

        # --- THIS IS THE NEW, MORE POWERFUL CSS ---
        if st.session_state.get('role') == 'user':
            # If user, find the list item (li) that contains the admin link and hide it.
            # This is more robust than hiding the link (a) itself.
            st.markdown("""
                <style>
                [data-testid="stSidebarNav"] ul > li:has(a[href*="2_Admin_Panel"]) {
                    display: none !important;
                }
                </style>
            """, unsafe_allow_html=True)
        
        # (If admin, we add no CSS, so all pages will show by default)

# Call the new function
configure_sidebar()

# --- 6. Custom CSS ---
page_bg_css = f"""
<style>
/* --- Hides the "Made with Streamlit" footer --- */
footer {{visibility: hidden;}}
/* --- Sets a clean font --- */
html, body, [class*="st-"] {{font-family: 'sans-serif';}}
/* --- Custom blue button color --- */
[data-testid="stFormSubmitButton"] button {{
    background-color: #0068C9; color: white; border: none;
}}
[data-testid="stFormSubmitButton"] button:hover {{
    background-color: #004F9A; color: white; border: none;
}}
/* --- Style for the logout button --- */
[data-testid="stSidebar"] button {{
    background-color: #FF4B4B; /* Red color for logout */
    color: white;
}}
[data-testid="stSidebar"] button:hover {{
    background-color: #CC3C3C; /* Darker red on hover */
    color: white;
}}
</style>
"""
st.markdown(page_bg_css, unsafe_allow_html=True)


# --- 7. Main Lobby Page Content ---
st.markdown("<h1 style='text-align: center; font-family: sans-serif;'>✨ Welcome to the Edu2Job : Predicting job roles from Educational Background  ✨</h1>", unsafe_allow_html=True)

if st.session_state['token']:
    st.success("You are logged in!")
    st.markdown(f"<p style='text-align: center;'>Please select a page from the sidebar on the left to get started, <b>{st.session_state['username']}</b>.</p>", unsafe_allow_html=True)

else:
    # --- Show General Info ---
    st.markdown("---")
    st.subheader("Bridging gap between Education and Employment")
    st.markdown("""
    In today's dynamic job market, students and professionals often struggle to identify career paths that align with their educational background. 
    This project aims to bridge that gap by analyzing a user's academic history and suggesting suitable job roles.
    
    Leveraging a Random Forest model, this system predicts the job roles that best match your qualifications, enabling informed career planning.
    """)
    st.markdown("---")
    
    st.header("Get Started")
    st.markdown("<p style='text-align: center;'>Please log in to get your prediction or register as a new user.</p>", unsafe_allow_html=True)

    _col1, mid_col, _col3 = st.columns([1, 1, 1]) 
    with mid_col:
        user_tab, admin_tab = st.tabs(["User Portal", "Admin Login"])

        # --- User Tab (Login & Register) ---
        with user_tab:
            sub_login, sub_register = st.tabs(["User Login", "User Register"])
            
            with sub_login:
                with st.form("user_login_form"):
                    st.subheader("User Login")
                    username = st.text_input("Username", key="user_login_username")
                    password = st.text_input("Password", type="password", key="user_login_pass")
                    login_button = st.form_submit_button("Login")

                    if login_button:
                        try:
                            response = requests.post(f"{BACKEND_URL}/login", json={"username": username, "password": password})
                            if response.status_code == 200:
                                data = response.json()
                                st.session_state['token'] = data['access_token']
                                st.session_state['username'] = username
                                st.session_state['role'] = data['role']
                                st.success("Login Successful!")
                                time.sleep(1) # Brief pause so user sees the message
                                st.rerun() 
                            else:
                                st.error(response.json().get("error", "Invalid username or password"))
                        except requests.exceptions.ConnectionError:
                            st.error("Could not connect to the backend. Is it running?")
            
            with sub_register:
                with st.form("user_register_form"):
                    st.subheader("Register New User")
                    new_username = st.text_input("Choose a Username", key="user_reg_username")
                    new_password = st.text_input("Choose a Password", type="password", key="user_reg_pass")
                    new_password_confirm = st.text_input("Confirm Password", type="password", key="user_reg_pass_confirm")
                    register_button = st.form_submit_button("Register")

                    if register_button:
                        if not new_username or not new_password:
                            st.error("Please fill out all fields.")
                        elif new_password != new_password_confirm:
                            st.error("Passwords do not match.")
                        else:
                            try:
                                # --- Auto-Login Flow ---
                                response_reg = requests.post(f"{BACKEND_URL}/register", json={"username": new_username, "password": new_password})
                                if response_reg.status_code == 201:
                                    st.success("Registration successful! Logging you in...")
                                    response_login = requests.post(f"{BACKEND_URL}/login", json={"username": new_username, "password": new_password})
                                    if response_login.status_code == 200:
                                        data = response_login.json()
                                        st.session_state['token'] = data['access_token']
                                        st.session_state['username'] = new_username
                                        st.session_state['role'] = data['role']
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("Auto-login failed. Please go to the Login tab.")
                                else:
                                    st.error(response_reg.json().get("error", "Registration failed"))
                            except requests.exceptions.ConnectionError:
                                st.error("Could not connect to the backend. Is it running?")

        # --- Admin Tab (Login Only) ---
        with admin_tab:
            with st.form("admin_login_form"):
                st.subheader("Admin Login")
                username = st.text_input("Admin Username", key="admin_login_username")
                password = st.text_input("Admin Password", type="password", key="admin_login_pass")
                login_button = st.form_submit_button("Login")

                if login_button:
                    try:
                        response = requests.post(f"{BACKEND_URL}/login", json={"username": username, "password": password})
                        if response.status_code == 200:
                            data = response.json()
                            if data['role'] == 'admin':
                                st.session_state['token'] = data['access_token']
                                st.session_state['username'] = username
                                st.session_state['role'] = data['role']
                                st.success("Admin Login Successful!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("This user is not an admin.")
                        else:
                            st.error(response.json().get("error", "Invalid username or password"))
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to the backend. Is it running?")
                        # --- 8. JAVASCRIPT HACK TO HIDE TOOLTIP ---
# This script finds the sidebar button and removes its "title" attribute.
js_hack = """
<script>
window.addEventListener('load',function() {
    // We target the button by its data-testid
    const sidebarButton = window.parent.document.querySelector('[data-testid="stSidebarCollapseButton"]');
    
    if (sidebarButton) {
        // Removing the 'title' attribute kills the tooltip
        sidebarButton.removeAttribute('title');
    }
    
    // Also try to find the label just in case
  const sidebarLabel = window.parent.document.querySelector('[data-testid="stSidebarCollapseButton-label"]');
   if (sidebarLabel) {
    sidebarLabel.removeAttribute('title');
}

});
</script>
""" 
# This component injects the JavaScript into the app
components.html(js_hack, height=0, width=0)