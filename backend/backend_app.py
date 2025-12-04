from flask import Flask, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity, JWTManager
from flask_cors import CORS
import database as db
import os
from functools import wraps 
import subprocess # NEW: To run the training script
import sys # NEW: To find the python executable

# --- 1. App Initialization ---
app = Flask(__name__)
CORS(app) 
app.config["JWT_SECRET_KEY"] = "your-super-secret-key-change-this" 
jwt = JWTManager(app)

# --- 4. Helper Function ---
@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    username = jwt_data["sub"]
    user = db.get_user(username)
    return user 

# --- 5. Authentication API Endpoints ---
@app.route("/api", methods=["GET"])
def hello():
    return "Hello! The Backend API is running."

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    if db.get_user(username):
        return jsonify({"error": "Username already exists"}), 400
    if db.add_user(username, password):
        return jsonify({"message": "User registered successfully"}), 201
    else:
        return jsonify({"error": "Failed to register user"}), 500

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    user = db.get_user(username)
    if user and db.verify_password(password, user['password']):
        access_token = create_access_token(
            identity=username, 
            additional_claims={"role": user['role']}
        )
        return jsonify(access_token=access_token, role=user['role']), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

# --- 6. User API Endpoints (MODIFIED) ---
@app.route("/save_prediction", methods=["POST"])
@jwt_required() 
def save_prediction():
    current_user = get_jwt_identity() 
    user = db.get_user(current_user) 
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = request.json
    skill_1 = data.get('skill_1')
    skill_2 = data.get('skill_2')
    education = data.get('education')
    p1 = data.get('prediction_1')
    p2 = data.get('prediction_2')
    p3 = data.get('prediction_3')
    
    if not all([skill_1, skill_2, education, p1, p2, p3]):
        return jsonify({"error": "Missing prediction data"}), 400
    
    # --- MODIFIED: Get the new ID ---
    new_prediction_id = db.save_prediction(user['id'], skill_1, skill_2, education, p1, p2, p3)
    
    if new_prediction_id:
        return jsonify({"message": "Prediction saved successfully", "prediction_id": new_prediction_id}), 201
    else:
        return jsonify({"error": "Failed to save prediction"}), 500

@app.route("/get_history", methods=["GET"])
@jwt_required()
def get_history():
    current_user = get_jwt_identity()
    user = db.get_user(current_user)
    if not user:
        return jsonify({"error": "User not found"}), 404
    history_rows = db.get_prediction_history(user['id'])
    history_list = [dict(row) for row in history_rows]
    return jsonify(history=history_list), 200

@app.route("/get_similar_users", methods=["POST"])
@jwt_required()
def get_similar_users():
    current_user = get_jwt_identity()
    user = db.get_user(current_user)
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = request.json
    skill_1 = data.get('skill_1')
    skill_2 = data.get('skill_2')
    education = data.get('education')
    if not all([skill_1, skill_2, education]):
        return jsonify({"error": "Missing skills or education"}), 400
    similar_users_rows = db.get_similar_users(skill_1, skill_2, education, user['id'])
    similar_users_list = [dict(row) for row in similar_users_rows]
    return jsonify(similar_users=similar_users_list), 200

# --- MODIFIED: Feedback Endpoint ---
@app.route("/save_feedback", methods=["POST"])
@jwt_required()
def save_feedback():
    """Saves a user's feedback."""
    current_user = get_jwt_identity()
    user = db.get_user(current_user)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    data = request.json
    prediction_id = data.get('prediction_id') # Get the new ID
    rating = data.get('rating')
    comment = data.get('comment')
    is_accurate = data.get('is_accurate')

    if not rating or not prediction_id:
        return jsonify({"error": "Rating and Prediction ID are required"}), 400
    
    if db.save_feedback(user['id'], prediction_id, rating, comment, is_accurate): # Pass new field
        return jsonify({"message": "Feedback saved successfully"}), 201
    else:
        return jsonify({"error": "Failed to save feedback"}), 500

# --- 7. Admin API Endpoints ---
def admin_required():
    def wrapper(fn):
        @wraps(fn) 
        @jwt_required()
        def decorator(*args, **kwargs):
            claims = get_jwt()
            if claims.get('role') != 'admin':
                return jsonify({"error": "Admin access required"}), 403
            else:
                return fn(*args, **kwargs)
        return decorator
    return wrapper

@app.route("/admin/stats", methods=["GET"])
@admin_required()
def get_admin_stats():
    total_users = db.get_total_user_count()
    total_predictions = db.get_total_prediction_count()
    avg_rating = db.get_average_feedback_rating()
    top_jobs_rows = db.get_top_predicted_jobs()
    top_skills_rows = db.get_top_searched_skills()
    top_edu_rows = db.get_top_searched_education()
    
    stats = {
        "total_users": total_users,
        "total_predictions": total_predictions,
        "average_rating": avg_rating,
        "model_name": "Random Forest",
        "model_accuracy": "93%", 
        "top_predicted_jobs": [dict(row) for row in top_jobs_rows],
        "top_searched_skills": [dict(row) for row in top_skills_rows],
        "top_searched_education": [dict(row) for row in top_edu_rows]
    }
    return jsonify(stats=stats), 200

@app.route("/admin/all_users", methods=["GET"])
@admin_required()
def get_admin_all_users():
    users_rows = db.get_all_users()
    users_list = [dict(row) for row in users_rows]
    return jsonify(users=users_list), 200

@app.route("/admin/delete_user/<int:user_id>", methods=["DELETE"])
@admin_required()
def delete_user(user_id):
    current_user = get_jwt_identity()
    admin_user = db.get_user(current_user)
    if admin_user and admin_user['id'] == user_id:
        return jsonify({"error": "Admin cannot delete their own account"}), 400
        
    if db.delete_user(user_id):
        return jsonify({"message": "User deleted successfully"}), 200
    else:
        return jsonify({"error": "Failed to delete user"}), 500

@app.route("/admin/all_predictions", methods=["GET"])
@admin_required()
def get_admin_all_predictions():
    predictions_rows = db.get_all_predictions_with_username()
    predictions_list = [dict(row) for row in predictions_rows]
    return jsonify(predictions=predictions_list), 200

@app.route("/admin/all_feedback", methods=["GET"])
@admin_required()
def get_admin_all_feedback():
    feedback_rows = db.get_all_feedback()
    feedback_list = [dict(row) for row in feedback_rows]
    return jsonify(feedback=feedback_list), 200

# --- NEW: Re-Training Endpoint ---
@app.route("/admin/retrain", methods=["POST"])
@admin_required()
def retrain_model():
    """
    Receives a new CSV file, saves it,
    and runs the train_model.py script.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and file.filename.endswith('.csv'):
        # Save the new dataset in the backend folder
        save_path = os.path.join(db.BASE_DIR, "new_training_data.csv")
        file.save(save_path)
        
        # Run the training script in the background
        try:
            python_exe = sys.executable # Path to current python
            script_path = os.path.join(db.BASE_DIR, "train_model.py")
            
            # This runs the script and WAITS for it to finish
            result = subprocess.run(
                [python_exe, script_path],
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
            
            # Return the log from the training script
            return jsonify({
                "message": "Model retrained successfully!",
                "log": result.stdout
            }), 200
        
        except subprocess.CalledProcessError as e:
            # If training fails (script returns an error)
            return jsonify({
                "error": "Model training failed.",
                "log": e.stderr
            }), 500
        except Exception as e:
            return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
            
    return jsonify({"error": "Invalid file type, please upload a .csv"}), 400

# --- 8. Run the App ---
if __name__ == '__main__':
    # We run create_tables() here to ensure tables exist
    # It's safe because of "CREATE TABLE IF NOT EXISTS"
    db.create_tables() 
    app.run(port=5000, debug=True)