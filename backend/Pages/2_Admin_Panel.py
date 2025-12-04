import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time

# --- 0. CHECK LOGIN & ADMIN STATUS ---
if not st.session_state.get('token'):
    st.error("Please log in first to access this page.")
    st.stop()
if st.session_state.get('role') != 'admin':
    st.error("You do not have permission to access this page. This page is for admins only.")
    st.stop()

# --- 1. Page Config ---
st.set_page_config(page_title="Edu2Job Admin Panel", layout="wide")
st.title("Admin Panel 👑")

# --- 2. Define API URL & Headers ---
BACKEND_URL = "http://127.0.0.1:5000"
AUTH_HEADERS = {"Authorization": f"Bearer {st.session_state['token']}"}

# --- 3. API Call Functions ---
@st.cache_data
def get_admin_stats():
    """Fetches dashboard stats from the backend."""
    try:
        response = requests.get(f"{BACKEND_URL}/admin/stats", headers=AUTH_HEADERS)
        if response.status_code == 200:
            return response.json().get("stats")
        else:
            st.error(f"Failed to fetch stats: {response.json().get('error')}")
            return None
    except Exception as e:
        st.error(f"Error connecting to backend: {e}")
        return None

@st.cache_data
def get_all_users():
    """Fetches all users for the management table."""
    try:
        response = requests.get(f"{BACKEND_URL}/admin/all_users", headers=AUTH_HEADERS)
        if response.status_code == 200:
            return response.json().get("users")
        else:
            return None
    except Exception:
        return None

@st.cache_data
def get_all_predictions():
    """Fetches all predictions for the log."""
    try:
        response = requests.get(f"{BACKEND_URL}/admin/all_predictions", headers=AUTH_HEADERS)
        if response.status_code == 200:
            return response.json().get("predictions")
        else:
            return None
    except Exception:
        return None

@st.cache_data
def get_all_feedback():
    """Fetches all feedback for the log."""
    try:
        response = requests.get(f"{BACKEND_URL}/admin/all_feedback", headers=AUTH_HEADERS)
        if response.status_code == 200:
            return response.json().get("feedback")
        else:
            return None
    except Exception:
        return None

# --- 4. Load Data ---
stats = get_admin_stats()
if not stats:
    st.error("Could not load admin statistics. Is the backend running?")
    st.stop()

# --- 5. Admin Dashboard ---
st.markdown("---")
st.header("Application Dashboard")

# --- Top Stats Metrics ---
st.subheader("At-a-Glance Statistics")
col1, col2, col3, col4 = st.columns(4)
col1.metric(label="Total Registered Users", value=stats.get("total_users", 0))
col2.metric(label="Total Predictions Made", value=stats.get("total_predictions", 0))
col3.metric(label="Average User Rating", value=f"{stats.get('average_rating', 0)} / 5.0")
col4.metric(label="Current Model Accuracy", value=stats.get("model_accuracy", "N/A"))

st.markdown("---")
st.header("App Analytics 📊")

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.subheader("Top 5 Most Predicted Jobs")
    top_jobs_data = stats.get("top_predicted_jobs", [])
    if top_jobs_data:
        job_df = pd.DataFrame(top_jobs_data)
        fig_bar = px.bar(job_df, x='prediction_1', y='count',
                         title="Top 5 Predictions (All Users)",
                         labels={'prediction_1': 'Job Role', 'count': 'Total Predictions'},
                         color='prediction_1')
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No prediction data available to display.")

with chart_col2:
    st.subheader("Top 5 Most Searched Skills")
    top_skills_data = stats.get("top_searched_skills", [])
    if top_skills_data:
        skill_df = pd.DataFrame(top_skills_data)
        fig_pie = px.pie(skill_df, names='Skill', values='total_count',
                         title="Top 5 Skills (All Users)",
                         color_discrete_sequence=px.colors.sequential.RdBu)
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No skill data available to display.")

st.subheader("Top 5 Most Searched Qualifications")
top_edu_data = stats.get("top_searched_education", [])
if top_edu_data:
    edu_df = pd.DataFrame(top_edu_data)
    fig_bar_edu = px.bar(edu_df, x='education', y='count',
                         title="Top 5 Qualifications (All Users)",
                         labels={'education': 'Qualification', 'count': 'Total Searches'},
                         color='education')
    st.plotly_chart(fig_bar_edu, use_container_width=True)
else:
    st.info("No qualification data available to display.")


st.markdown("---")
st.header("App Data Logs 📝")

tab1, tab2, tab3, tab4 = st.tabs([
    "👥 User Management", 
    "📜 Full Prediction Log", 
    "📬 All Feedback Log", 
    "🚩 Incorrect Predictions"
])

with tab1:
    st.subheader("User Profile Management")
    all_users = get_all_users()
    if all_users:
        users_df = pd.DataFrame(all_users)
        users_df['delete'] = False
        edited_df = st.data_editor(
            users_df,
            column_config={
                "delete": st.column_config.CheckboxColumn("Delete User?", default=False),
                "id": st.column_config.NumberColumn("User ID"),
                "username": st.column_config.TextColumn("Username"),
                "role": st.column_config.TextColumn("Role")
            },
            disabled=["id", "username", "role"], 
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("Confirm Deletions", type="primary"):
            users_to_delete = edited_df[edited_df['delete'] == True]
            if users_to_delete.empty:
                st.warning("No users selected for deletion.")
            else:
                for index, row in users_to_delete.iterrows():
                    user_id = row['id']
                    if row['username'] == st.session_state['username']:
                        st.error("You cannot delete your own admin account.")
                        continue
                    try:
                        response = requests.delete(f"{BACKEND_URL}/admin/delete_user/{user_id}", headers=AUTH_HEADERS)
                        if response.status_code == 200:
                            st.success(f"Successfully deleted user: {row['username']}")
                        else:
                            st.error(f"Failed to delete user {row['username']}: {response.json().get('error')}")
                    except Exception as e:
                        st.error(f"An error occurred while deleting {row['username']}: {e}")
                st.cache_data.clear()
                st.rerun()
    else:
        st.info("No users found.")

with tab2:
    st.subheader("Full Prediction History (All Users)")
    all_predictions = get_all_predictions()
    if all_predictions:
        pred_df = pd.DataFrame(all_predictions)
        pred_df['timestamp'] = pd.to_datetime(pred_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        st.dataframe(pred_df, use_container_width=True)
    else:
        st.info("No predictions have been made yet.")
        
with tab3:
    st.subheader("All User Feedback Log")
    all_feedback = get_all_feedback()
    if all_feedback:
        feedback_df = pd.DataFrame(all_feedback)
        feedback_df['timestamp'] = pd.to_datetime(feedback_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        st.dataframe(feedback_df[['timestamp', 'username', 'rating', 'is_accurate', 'comment', 'skill_1', 'skill_2', 'education', 'prediction_1']], use_container_width=True)
    else:
        st.info("No user feedback has been submitted yet.")

with tab4:
    st.subheader("Incorrect Prediction Log")
    st.info("This log shows all feedback where a user reported the prediction as 'No'. This is your guide for what to fix in the next training dataset.")
    all_feedback = get_all_feedback() 
    if all_feedback:
        feedback_df = pd.DataFrame(all_feedback)
        
        # --- Filter the DataFrame ---
        incorrect_df = feedback_df[feedback_df['is_accurate'] == 'No']
        
        if incorrect_df.empty:
            st.success("No incorrect predictions have been reported by users!")
        else:
            incorrect_df['timestamp'] = pd.to_datetime(incorrect_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
            # Show the new, complete data
            st.dataframe(incorrect_df[['timestamp', 'username', 'comment', 'skill_1', 'skill_2', 'education', 'prediction_1']], use_container_width=True)
    else:
        st.info("No user feedback has been submitted yet.")

# --- 6. NEW: Model Management Section ---
st.markdown("---")
st.header("🧠 Model Management")
st.info("Upload a new, pre-encoded CSV file (like your original `encoded_jobs_dataset.csv`) to retrain the model.")
st.warning("Warning: This will overwrite your current model. This action is irreversible.")

uploaded_file = st.file_uploader("Upload new training data (CSV)", type=["csv"])

if uploaded_file is not None:
    if st.button("Re-Train Model", type="primary"):
        with st.spinner("Training in progress... This may take several minutes. Please do not close this window."):
            try:
                # Send the file to the backend
                files = {'file': (uploaded_file.name, uploaded_file.getvalue(), 'text/csv')}
                response = requests.post(
                    f"{BACKEND_URL}/admin/retrain", 
                    files=files, 
                    headers=AUTH_HEADERS
                )
                
                if response.status_code == 200:
                    st.success("Model retrained successfully!")
                    st.subheader("Training Log:")
                    st.text(response.json().get("log", ""))
                    # IMPORTANT: Clear all caches so the app loads the new model
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Training Failed: {response.json().get('error')}")
                    st.subheader("Error Log:")
                    st.text(response.json().get("log", "No log available."))
            except Exception as e:
                st.error(f"An error occurred: {e}")