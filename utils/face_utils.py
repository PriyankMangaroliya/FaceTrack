"""
utils/face_utils.py
---------------------------------
Handles face registration, encoding, recognition, and automatic attendance marking.
Stores data in:
1️⃣ dataset/ (images)
2️⃣ encodings.pkl (binary encodings)
3️⃣ MongoDB (metadata + registered flag)
"""

import os
import cv2
import numpy as np
import pickle
from datetime import datetime
from bson import ObjectId
from utils.db import mongo

# ==============================
# GLOBAL CONFIG
# ==============================
DATASET_DIR = "dataset"
ENCODINGS_FILE = "encodings.pkl"
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


# -------------------------------------------------------------
# 1️⃣ Capture faces and save dataset
# -------------------------------------------------------------
def capture_faces_for_user(user_id, user_name, num_samples=5):
    """
    Captures multiple face images from the webcam,
    saves them in dataset/, and encodes & stores them.
    """
    try:
        os.makedirs(DATASET_DIR, exist_ok=True)
        user_folder = os.path.join(DATASET_DIR, f"{user_name}_{user_id}")
        os.makedirs(user_folder, exist_ok=True)

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] Camera not detected or cannot be opened.")
            return None

        count = 0
        print(f"[INFO] Starting capture for {user_name} ({user_id})...")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Frame capture failed.")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                count += 1
                face_crop = gray[y:y + h, x:x + w]
                img_name = f"{user_name}_{user_id}_{count}.jpg"
                img_path = os.path.join(user_folder, img_name)
                cv2.imwrite(img_path, face_crop)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"{count}/{num_samples}", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            cv2.imshow("Capture Faces - Press ESC to stop", frame)
            if cv2.waitKey(1) == 27 or count >= num_samples:
                break

        cap.release()
        cv2.destroyAllWindows()

        if count > 0:
            print(f"[SUCCESS] {count} images captured for {user_name}")
            encode_and_store_face(user_id, user_name, user_folder)
            return user_folder
        else:
            print("[WARN] No faces captured. Try again.")
            return None

    except Exception as e:
        print(f"[ERROR] capture_faces_for_user failed: {e}")
        return None


# -------------------------------------------------------------
# 2️⃣ Encode faces and store data in all 3 locations
# -------------------------------------------------------------
def encode_and_store_face(user_id, user_name, user_folder):
    """Encodes user's face data and stores in dataset, .pkl, and MongoDB."""
    try:
        all_faces = []
        image_paths = []

        print("[INFO] Encoding faces...")

        if not os.path.exists(user_folder):
            print(f"[ERROR] Folder not found: {user_folder}")
            return False

        for file in os.listdir(user_folder):
            if file.lower().endswith((".jpg", ".png")):
                path = os.path.join(user_folder, file)
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    # ✅ Resize to fixed 100x100 to standardize shape
                    img_resized = cv2.resize(img, (100, 100))
                    all_faces.append(img_resized.flatten())
                    image_paths.append(path)
                else:
                    print(f"[WARN] Could not read image: {path}")

        if not all_faces:
            print("[ERROR] No valid face images to encode.")
            return False

        # ✅ Compute average encoding vector (now uniform length)
        avg_encoding = np.mean(all_faces, axis=0)
        print(f"[SUCCESS] Face encoding generated (length={len(avg_encoding)}).")

        # Step 1️⃣ Save encoding to .pkl
        print("[INFO] Updating global encodings file...")
        encodings = load_encodings()
        encodings[user_id] = {
            "name": user_name,
            "encoding": avg_encoding
        }
        save_encodings(encodings)
        print(f"[SUCCESS] Encoding stored in {ENCODINGS_FILE}.")

        # Step 2️⃣ Store metadata in MongoDB
        print("[INFO] Updating MongoDB with face info...")
        face_info = {
            "dataset_path": user_folder,
            "encoding_file": ENCODINGS_FILE,
            "encoding_shape": avg_encoding.shape,
            "images": image_paths,
            "last_updated": datetime.utcnow()
        }

        result = mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "face_data": face_info,
                "face_registered": True,
                "updated_at": datetime.utcnow()
            }}
        )

        if result.modified_count > 0:
            print(f"[SUCCESS] MongoDB updated for user {user_name}.")
        else:
            print(f"[WARN] MongoDB update may have failed for {user_name}.")

        print(f"[INFO] All face data stored successfully for {user_name}.")
        return True

    except Exception as e:
        print(f"[ERROR] encode_and_store_face failed: {e}")
        return False


# -------------------------------------------------------------
# 3️⃣ Save and Load Encodings (.pkl)
# -------------------------------------------------------------
def save_encodings(encodings):
    """Save all user encodings to encodings.pkl"""
    try:
        with open(ENCODINGS_FILE, "wb") as f:
            pickle.dump(encodings, f)
        print(f"[SUCCESS] Encodings file saved: {ENCODINGS_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to save encodings.pkl: {e}")


def load_encodings():
    """Load all user encodings from encodings.pkl"""
    if not os.path.exists(ENCODINGS_FILE):
        print("[INFO] No encodings.pkl found. Creating new one.")
        return {}
    try:
        with open(ENCODINGS_FILE, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load encodings.pkl: {e}")
        return {}


# -------------------------------------------------------------
# 4️⃣ Check if user has registered face
# -------------------------------------------------------------
def is_face_registered(user_id):
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        return bool(user and user.get("face_registered", False))
    except Exception as e:
        print(f"[ERROR] is_face_registered failed: {e}")
        return False


# -------------------------------------------------------------
# 5️⃣ Recognize faces and mark attendance (fast from .pkl)
# -------------------------------------------------------------
def recognize_and_mark_attendance():
    """Open webcam, recognize registered users, and mark attendance."""
    try:
        encodings = load_encodings()
        if not encodings:
            print("[ERROR] No encodings found. Register faces first.")
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] Cannot open camera.")
            return

        print("[INFO] Starting real-time recognition (Press ESC to exit)...")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Frame capture failed.")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                face_crop = gray[y:y + h, x:x + w].flatten()

                matched_user = None
                min_dist = float("inf")
                threshold = 3500.0

                for uid, data in encodings.items():
                    dist = np.linalg.norm(data["encoding"] - face_crop)
                    if dist < threshold and dist < min_dist:
                        matched_user = (uid, data["name"])
                        min_dist = dist

                if matched_user:
                    user_id, name = matched_user
                    mark_attendance_in_db(user_id, name)
                    cv2.putText(frame, f"{name} (Present)", (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                else:
                    cv2.putText(frame, "Unknown", (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 0), 2)

            cv2.imshow("Attendance Recognition", frame)
            if cv2.waitKey(1) == 27:
                break

        cap.release()
        cv2.destroyAllWindows()
        print("[INFO] Attendance session ended successfully.")

    except Exception as e:
        print(f"[ERROR] recognize_and_mark_attendance failed: {e}")


# -------------------------------------------------------------
# 6️⃣ Mark attendance in MongoDB
# -------------------------------------------------------------
def mark_attendance_in_db(user_id, user_name):
    """Insert attendance record only once per day."""
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        existing = mongo.db.attendances.find_one({
            "user_id": user_id,
            "date": today
        })

        if existing:
            return  # Skip duplicates

        now = datetime.utcnow()
        mongo.db.attendances.insert_one({
            "user_id": user_id,
            "name": user_name,
            "date": today,
            "time": now.strftime("%H:%M:%S"),
            "marked_by": "System",
            "created_at": now,
            "updated_at": now
        })
        print(f"[SUCCESS] Attendance marked for {user_name}.")
    except Exception as e:
        print(f"[ERROR] mark_attendance_in_db failed: {e}")
