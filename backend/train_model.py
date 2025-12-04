import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib
import os
import sys

# This script is designed to be run from the command line by your Flask app.

# --- 1. Define File Paths ---
# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# This is the new, temporary dataset the admin just uploaded
DATA_PATH = os.path.join(BASE_DIR, "new_training_data.csv")

# Go "up" one level to the main 'infosys_project' folder
MODEL_DIR = os.path.abspath(os.path.join(BASE_DIR, '..')) 

# Define the paths to save the new model files, OVERWRITING the old ones
MODEL_PATH = os.path.join(MODEL_DIR, 'random_forest_model.joblib')
COLUMNS_PATH = os.path.join(MODEL_DIR, 'model_columns.joblib')
ENCODER_PATH = os.path.join(MODEL_DIR, 'label_encoder.joblib')

def train():
    """
    Loads the new CSV, trains a new model, and overwrites the old .joblib files.
    """
    try:
        print(f"--- [Trainer] Loading new dataset from {DATA_PATH}...")
        df = pd.read_csv(DATA_PATH)
    except FileNotFoundError:
        print(f"--- [Trainer] ERROR: new_training_data.csv not found. Aborting.")
        sys.exit(1) # Exit with an error
    except Exception as e:
        print(f"--- [Trainer] ERROR: Failed to load CSV. {e}")
        sys.exit(1)

    print(f"--- [Trainer] Data loaded. Shape: {df.shape}")

    # --- 2. Model Training Logic (from your Colab notebook) ---
    target_column = 'Job_Role'
    if target_column not in df.columns:
        print(f"--- [Trainer] ERROR: Target column '{target_column}' not found in new dataset.")
        sys.exit(1)
        
    X = df.drop(columns=[target_column])
    y_categorical = df[target_column]
    
    print("--- [Trainer] Encoding target variable 'Job_Role'...")
    encoder = LabelEncoder()
    y = encoder.fit_transform(y_categorical)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"--- [Trainer] Data split into {len(X_train)} train and {len(X_test)} test samples.")
    
    print("--- [Trainer] Training new Random Forest model...")
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf_model.fit(X_train, y_train)
    
    # --- 3. Evaluate and Print New Accuracy ---
    try:
        y_pred = rf_model.predict(X_test)
        new_accuracy = accuracy_score(y_test, y_pred)
        print(f"--- [Trainer] NEW MODEL ACCURACY: {new_accuracy * 100:.2f}% ---")
    except Exception as e:
        print(f"--- [Trainer] Warning: Could not calculate accuracy. {e}")

    # --- 4. Save (Overwrite) Model Files ---
    print(f"--- [Trainer] Saving new model to {MODEL_PATH}")
    joblib.dump(rf_model, MODEL_PATH)
    
    print(f"--- [Trainer] Saving new columns to {COLUMNS_PATH}")
    joblib.dump(X.columns.tolist(), COLUMNS_PATH)
    
    print(f"--- [Trainer] Saving new encoder to {ENCODER_PATH}")
    joblib.dump(encoder, ENCODER_PATH)
    
    print("--- [Trainer] Retraining complete. All model files have been overwritten.")

if __name__ == "__main__":
    train()