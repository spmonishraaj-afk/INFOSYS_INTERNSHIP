import streamlit as st
import joblib
import pandas as pd
import numpy as np
import plotly.express as px
import requests 
from collections import Counter

# --- 0. CHECK LOGIN STATUS ---
if not st.session_state.get('token'):
    st.error("Please log in first to access this page.")
    st.stop() # Stop the page from loading

# --- 1. Page Configuration ---
st.set_page_config(page_title="Edu2Job Predictor", layout="wide")

# --- 2. Define API URL ---
BACKEND_URL = "http://127.0.0.1:5000"
AUTH_HEADERS = {"Authorization": f"Bearer {st.session_state['token']}"}

# --- 3. Initialize Session State for Predictions ---
if 'last_prediction_results' not in st.session_state:
    st.session_state['last_prediction_results'] = None
if 'last_prediction_id' not in st.session_state: # NEW: To link feedback
    st.session_state['last_prediction_id'] = None
if 'run_balloons' not in st.session_state:
    st.session_state['run_balloons'] = False
if 'feedback_submitted' not in st.session_state:
    st.session_state['feedback_submitted'] = False

# Check if the current user is an admin
is_admin = st.session_state.get('role') == 'admin'

# --- 4. Data Loading Functions (Cached) ---
@st.cache_data
def load_data(file):
    try:
        df = pd.read_csv(file)
        return df
    except FileNotFoundError:
        st.error(f"Error: Dataset '{file}' not found. Charts cannot be loaded.")
        return None

@st.cache_data
def load_model_files():
    try:
        model = joblib.load('random_forest_model.joblib')
        model_columns = joblib.load('model_columns.joblib')
        encoder = joblib.load('label_encoder.joblib')
        return model, model_columns, encoder
    except FileNotFoundError:
        st.error("Error: Model/column/encoder files not found.")
        return None, None, None

# --- 5. API Call Functions ---
@st.cache_data
def get_user_history(token):
    """Fetches the user's prediction history from the backend."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BACKEND_URL}/get_history", headers=headers)
        if response.status_code == 200:
            return response.json().get("history", [])
        else:
            st.error(f"Error fetching history: {response.json().get('error', 'Unknown')}")
            return []
    except Exception as e:
        st.error(f"Error connecting to backend: {e}")
        return []

@st.cache_data
def get_similar_users_for_combo(token, skill_1, skill_2, education):
    """Fetches similar users for a *single* combination."""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"skill_1": skill_1, "skill_2": skill_2, "education": education}
    try:
        response = requests.post(f"{BACKEND_URL}/get_similar_users", json=payload, headers=headers)
        if response.status_code == 200:
            return response.json().get("similar_users", [])
        else:
            return []
    except Exception as e:
        st.error(f"Error finding similar users: {e}")
        return []

# --- 6. Load Files ---
model, model_columns, encoder = load_model_files()
df = load_data("encoded_jobs_dataset.csv")
if not model or df is None:
    st.error("A critical file is missing. The app cannot continue.")
    st.stop()

# --- 7. Define Input Options ---
SKILL_1_OPTIONS = [
    'AI', 'Accounting', 'Adobe Photoshop', 'Anatomy', 'Attention to Detail', 'Behavioral Analysis', 'Biology', 'Brand Management', 'Budgeting', 'C++', 'CAD Design', 'Case Analysis', 'Chemistry', 'Circuit Design', 'Classroom Management', 'Clinical Practice', 'Cloud Computing', 'Communication', 'Conflict Resolution', 'Construction Planning', 'Counseling', 'Creative Thinking', 'Creativity', 'Curriculum Design', 'Cybersecurity', 'Data Analysis', 'Data Structures', 'Deep Learning', 'Documentation', 'Educational Research', 'Electronics', 'Embedded Systems', 'Emergency Handling', 'Ethical Hacking', 'Excel', 'Financial Analysis', 'Forecasting', 'Graphic Design', 'HR Management', 'Illustration', 'Java', 'Laboratory Skills', 'Leadership', 'Legal Research', 'Linux', 'Machine Learning', 'Marketing Strategy', 'Materials Science', 'Medical Diagnosis', 'Negotiation', 'Network Security', 'Networking', 'Nursing', 'Patient Care', 'Pharmacology', 'Problem Solving', 'Project Management', 'Project Planning', 'Public Speaking', 'Publication Writing', 'Python', 'Recruitment', 'Research', 'Risk Assessment', 'Routing', 'SEO', 'SQL', 'Scheduling', 'Social Media', 'Statistics', 'Structural Design', 'Subject Expertise', 'Surgery', 'Surveying', 'Switching', 'Teaching', 'Thermodynamics', 'Visualization'
]
SKILL_2_OPTIONS = SKILL_1_OPTIONS.copy()
EDUCATION_OPTIONS = [
    'Bachelor of Architecture', 'Bachelor of Arts', 'Bachelor of Commerce', 'Bachelor of Engineering', 'Bachelor of Law', 'Bachelor of Medicine and Surgery', 'Bachelor of Nursing', 'Bachelor of Science', 'MBA', 'Master of Architecture', 'Master of Arts', 'Master of Business Administration', 'Master of Engineering', 'Master of Law', 'Master of Medicine', 'Master of Nursing', 'Master of Science', 'PhD in Biology', 'PhD in Computer Science', 'PhD in Education', 'PhD in Psychology'
]

# --- 8. Main Predictor UI ---
st.markdown("<h1 style='text-align: center; font-family: sans-serif;'>✨ Edu2Job Predictor ✨</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>This app predicts your job role using a Random Forest model. Fill in the form below to get your prediction!</p>", unsafe_allow_html=True)

if is_admin:
    st.info("Admin Mode: Predictions will be shown but not saved to user history.")

with st.form(key="prediction_form"):
    st.subheader("Enter Your Details:")
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_skill_1 = st.selectbox("Select your Primary Skill:", options=SKILL_1_OPTIONS, index=None, placeholder="Choose a primary skill...")
    with col2:
        selected_skill_2 = st.selectbox("Select your Secondary Skill:", options=SKILL_2_OPTIONS, index=None, placeholder="Choose a secondary skill...")
    with col3:
        selected_education = st.selectbox("Select your Educational Qualification:", options=EDUCATION_OPTIONS, index=None, placeholder="Choose your qualification...")
    st.markdown("---") 
    submit_button = st.form_submit_button(label="Predict Job Role", type="primary", use_container_width=True)

# --- 9. Prediction Logic (MODIFIED) ---
if submit_button:
    if not selected_skill_1 or not selected_skill_2 or not selected_education:
        st.warning("Please fill in all three fields to make a prediction.")
    else:
        try:
            # --- Make Prediction (Same for all) ---
            input_data = pd.DataFrame(columns=model_columns)
            input_data.loc[0] = 0
            input_data[f"Skill_1_{selected_skill_1}"] = 1
            input_data[f"Skill_2_{selected_skill_2}"] = 1
            input_data[f"Educational_Qualifications_{selected_education}"] = 1
            probabilities = model.predict_proba(input_data)[0]
            top_3_indices = np.argsort(probabilities)[-3:][::-1]
            top_3_job_roles = encoder.inverse_transform(model.classes_[top_3_indices])
            top_3_probs = probabilities[top_3_indices]
            
            st.session_state['last_prediction_results'] = {
                "roles": top_3_job_roles,
                "probs": top_3_probs
            }
            st.session_state['run_balloons'] = True 
            
            if not is_admin:
                try:
                    payload = {
                        "skill_1": selected_skill_1, "skill_2": selected_skill_2, "education": selected_education,
                        "prediction_1": top_3_job_roles[0], "prediction_2": top_3_job_roles[1], "prediction_3": top_3_job_roles[2]
                    }
                    response = requests.post(f"{BACKEND_URL}/save_prediction", json=payload, headers=AUTH_HEADERS)
                    if response.status_code == 201:
                        st.success("Prediction saved to your history!")
                        # --- NEW: Save the ID of this prediction ---
                        st.session_state['last_prediction_id'] = response.json().get('prediction_id')
                        st.cache_data.clear() 
                    else:
                        st.warning("Could not save prediction to history.")
                        st.session_state['last_prediction_id'] = None
                except Exception as e:
                    st.warning(f"Error saving history: {e}")
            
            if not is_admin:
                st.rerun() 
            elif is_admin:
                st.rerun() 
        except Exception as e:
            st.error(f"An error occurred during prediction: {e}")

# --- 10. Display Last Prediction (Same for all) ---
if st.session_state['last_prediction_results']:
    if st.session_state.get('run_balloons', False):
        st.balloons()
        st.session_state['run_balloons'] = False 
        
    results = st.session_state['last_prediction_results']
    top_3_job_roles = results['roles']
    top_3_probs = results['probs']
    
    st.subheader("🚀 Your Top 3 Predictions")
    p_col1, p_col2, p_col3 = st.columns(3)
    with p_col1:
        st.success(f"🥇 **1. {top_3_job_roles[0]}**")
        st.metric(label="Confidence Score", value=f"{top_3_probs[0]:.1%}")
    with p_col2:
        st.info(f"🥈 **2. {top_3_job_roles[1]}**")
        st.metric(label="Confidence Score", value=f"{top_3_probs[1]:.1%}")
    with p_col3:
        st.info(f"🥉 **3. {top_3_job_roles[2]}**")
        st.metric(label="Confidence Score", value=f"{top_3_probs[2]:.1%}")

# --- 11. User's Personal Dashboard (Hidden from Admin) ---
if not is_admin:
    st.markdown("---") 
    st.header(f"Your Personal Dashboard, {st.session_state['username']} 📜")
    history = get_user_history(st.session_state['token'])

    if not history:
        st.info("You have no past predictions. Make a prediction above to see your history!")
    else:
        hist_col1, hist_col2 = st.columns(2)
        
        with hist_col1:
            st.subheader("Your Top Predicted Jobs")
            job_counts = Counter([record['prediction_1'] for record in history])
            job_df = pd.DataFrame(job_counts.items(), columns=['Job Role', 'Count']).sort_values(by='Count', ascending=False)
            fig_hist_bar = px.bar(job_df.head(5), x='Job Role', y='Count', color='Job Role', title="Your Most Common Predictions")
            st.plotly_chart(fig_hist_bar, use_container_width=True)

        with hist_col2:
            st.subheader("Your Most Used Skills")
            skill_counts = Counter([record['skill_1'] for record in history] + [record['skill_2'] for record in history])
            skill_df = pd.DataFrame(skill_counts.items(), columns=['Skill', 'Count']).sort_values(by='Count', ascending=False)
            fig_hist_pie = px.pie(skill_df.head(5), names='Skill', values='Count', title="Your Most Common Skills")
            st.plotly_chart(fig_hist_pie, use_container_width=True)
        
        with st.expander("View Full Prediction History (Table)"):
            history_df = pd.DataFrame(history)
            history_df['timestamp'] = pd.to_datetime(history_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(history_df[['timestamp', 'skill_1', 'skill_2', 'education', 'prediction_1']], use_container_width=True)

# --- 12. Similar Profiles Section (Hidden from Admin) ---
if not is_admin:
    st.markdown("---")
    st.header("👤 Similar Profiles")

    if not history:
        st.info("Make a prediction to see profiles similar to yours.")
    else:
        st.info("Showing profiles who have made similar searches to your *entire* history.")
        
        unique_searches = set()
        for record in history:
            unique_searches.add((record['skill_1'], record['skill_2'], record['education']))
        
        all_similar_users = []
        for s1, s2, edu in unique_searches:
            similar_users = get_similar_users_for_combo(st.session_state['token'], s1, s2, edu)
            all_similar_users.extend(similar_users) 

        if not all_similar_users:
            st.info("No similar profiles found based on your history.")
        else:
            similar_df = pd.DataFrame(all_similar_users)
            similar_df = similar_df.drop_duplicates(subset=['username'])
            
            st.subheader(f"Found {len(similar_df)} similar profiles:")
            
            sim_col1, sim_col2 = st.columns(2)
            for i, (index, row) in enumerate(similar_df.iterrows()):
                if i % 2 == 0:
                    with sim_col1:
                        with st.container(border=True): 
                            st.markdown(f"**👤 {row['username']}**")
                            st.write(f"Matched on: `{row['education']}` | `{row['skill_1']}` | `{row['skill_2']}`")
                else:
                    with sim_col2:
                        with st.container(border=True):
                            st.markdown(f"**👤 {row['username']}**")
                            st.write(f"Matched on: `{row['education']}` | `{row['skill_1']}` | `{row['skill_2']}`")


# --- 13. Feedback Form (MODIFIED) ---
if not is_admin:
    st.markdown("---")
    
    if st.session_state.get('feedback_submitted', False):
        st.success("Thank you for your feedback!")
        st.session_state['feedback_submitted'] = False # Reset it
    
    with st.form("feedback_form", clear_on_submit=True):
        st.header("Feedback 📝")
        
        # --- MODIFIED: Only show feedback if a prediction was just made ---
        if st.session_state.get('last_prediction_id') is None:
            st.info("Make a new prediction to leave feedback on it.")
        else:
            st.write("We'd love to hear your feedback on your *last prediction*!")
            
            st.write("Was your top prediction accurate or helpful?")
            is_accurate = st.radio(
                "Prediction Accuracy", 
                options=["Yes", "No", "Not Sure"], 
                index=2, # Default to "Not Sure"
                horizontal=True,
                key="feedback_accuracy" 
            )
            
            rating = st.slider("Rate your overall experience (1-5 Stars)", 1, 5, 5, key="feedback_rating")
            comment = st.text_area("Leave a comment (optional):", key="feedback_comment")
            feedback_button = st.form_submit_button("Submit Feedback", type="primary")

            if feedback_button:
                try:
                    payload = {
                        "prediction_id": st.session_state['last_prediction_id'], # Send the linked ID
                        "rating": rating, 
                        "comment": comment, 
                        "is_accurate": is_accurate
                    }
                    response = requests.post(f"{BACKEND_URL}/save_feedback", json=payload, headers=AUTH_HEADERS)
                    if response.status_code == 201:
                        st.session_state['feedback_submitted'] = True
                    else:
                        st.error("Could not submit feedback.")
                except Exception as e:
                    st.error(f"Error submitting feedback: {e}")
                
                st.rerun()

# --- 14. Global Charts ---
st.markdown("---") 
st.header("Global Job Market Insights 📊")
if df is not None:
    st.subheader("Top 5 Popular Job Roles (All Users)")
    job_counts = df['Job_Role'].value_counts().head(5)
    job_df = job_counts.reset_index(name='count').rename(columns={'Job_Role': 'Job Role'})
    fig_bar = px.bar(job_df, x='Job Role', y='count', title="Top 5 Most Common Job Roles")
    fig_bar.update_traces(marker_color='#FFB6C1') 
    chart_col1, _ = st.columns([2, 1]) 
    with chart_col1:
        st.plotly_chart(fig_bar, use_container_width=True)
    
    chart_col2, chart_col3 = st.columns(2)
    with chart_col2:
        st.subheader("Top 5 Primary Skills (All Users)")
        skill_cols = [col for col in df.columns if col.startswith('Skill_1_')]
        skill_counts = df[skill_cols].sum().sort_values(ascending=False).head(5)
        skill_counts.index = skill_counts.index.str.replace('Skill_1_', '')
        skill_df = skill_counts.reset_index(name='count').rename(columns={'index': 'Skill'})
        fig_pie = px.pie(skill_df, names='Skill', values='count', 
                         color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig_pie, use_container_width=True)
    with chart_col3:
        st.subheader("Top 5 Qualifications (All Users)")
        edu_cols = [col for col in df.columns if col.startswith('Educational_Qualifications_')]
        edu_counts = df[edu_cols].sum().sort_values(ascending=False).head(5)
        edu_counts.index = edu_counts.index.str.replace('Educational_Qualifications_', '')
        edu_df = edu_counts.reset_index(name='count').rename(columns={'index': 'Qualification'})
        st.area_chart(edu_df.set_index('Qualification'))
else:
    st.warning("`encoded_jobs_dataset.csv` not loaded. Charts are unavailable.")