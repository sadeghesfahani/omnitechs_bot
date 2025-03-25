import os
import pandas as pd
import numpy as np
import librosa
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# ---------- Step 1: Load and preprocess Kaggle training data ----------
print("Loading training data...")
df = pd.read_csv("train.csv")

# Drop non-feature columns if present
X = df.drop(columns=["label", "filename", "Id"], errors="ignore")
le = LabelEncoder()
y = le.fit_transform(df["label"])

# Train/test split
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

# ---------- Step 2: Train the model ----------
print("Training model...")
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

# Evaluate
y_pred = clf.predict(X_val)
acc = accuracy_score(y_val, y_pred)
print(f"Validation Accuracy: {acc:.2f}")

# ---------- Step 3: Save the model ----------
joblib.dump(clf, "gender_model.joblib")
joblib.dump(le, "label_encoder.joblib")
print("Model and label encoder saved.")

# ---------- Step 4: Function to extract features from new WAV ----------
def extract_features_from_wav(wav_path):
    y, sr = librosa.load(wav_path, sr=None)
    features = {
        "meanfreq": np.mean(librosa.yin(y, fmin=50, fmax=1100, sr=sr)),
        "sd": np.std(y),
        "median": np.median(y),
        "Q25": np.percentile(y, 25),
        "Q75": np.percentile(y, 75),
        "IQR": np.percentile(y, 75) - np.percentile(y, 25),
        "skew": pd.Series(y).skew(),
        "kurt": pd.Series(y).kurt(),
        "sp.ent": 0,  # optional fix if entropy doesn't exist
        "sfm": librosa.feature.spectral_flatness(y=y).mean(),
        "mode": pd.Series(y).mode()[0] if not pd.Series(y).mode().empty else 0,
        "centroid": librosa.feature.spectral_centroid(y=y, sr=sr).mean(),
        "meanfun": librosa.feature.rms(y=y).mean(),
        "minfun": librosa.feature.rms(y=y).min(),
        "maxfun": librosa.feature.rms(y=y).max(),
        "meandom": librosa.feature.spectral_bandwidth(y=y, sr=sr).mean(),
        "mindom": librosa.feature.spectral_bandwidth(y=y, sr=sr).min(),
        "maxdom": librosa.feature.spectral_bandwidth(y=y, sr=sr).max(),
        "dfrange": np.ptp(librosa.feature.spectral_bandwidth(y=y, sr=sr)),  # ✅ fixed
        "modindx": np.std(y) / np.mean(y) if np.mean(y) != 0 else 0
    }
    return pd.DataFrame([features])

# ---------- Step 5: Function to predict gender ----------
def predict_gender(wav_path):
    clf = joblib.load("gender_model.joblib")
    le = joblib.load("label_encoder.joblib")
    features = extract_features_from_wav(wav_path)
    prediction = clf.predict(features)
    return le.inverse_transform(prediction)[0]

# ---------- Example usage ----------
if __name__ == "__main__":
    test_file = "your_audio.wav"  # Replace with your actual file path
    if os.path.exists(test_file):
        gender = predict_gender(test_file)
        print(f"Predicted gender: {gender}")
    else:
        print("No test audio file found. Replace 'your_audio.wav' with your actual path.")