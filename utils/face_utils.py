"""
utils/face_utils.py
---------------------------------
Handles face registration, encoding, recognition, and automatic attendance marking.
Stores data in:
1️⃣ static/dataset/ (raw face images)
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
DATASET_DIR = os.path.join("static", "dataset")
ENCODINGS_FILE = "encodings.pkl"
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


# -------------------------------------------------------------
# 1️⃣ Capture faces and save dataset
# -------------------------------------------------------------
def capture_faces_for_user(user_id, user_name, num_samples=5):
    """
    Captures multiple face images from webcam and saves them in static/dataset/.
    Then encodes and stores data in all formats.
    """
    try:
        # ✅ Save inside static/dataset/
        DATASET_DIR = os.path.join("static", "dataset")
        os.makedirs(DATASET_DIR, exist_ok=True)

        # ✅ Safe folder name (no spaces)
        safe_name = user_name.replace(" ", "_")
        user_folder = os.path.join(DATASET_DIR, f"{safe_name}_{user_id}")

        os.makedirs(user_folder, exist_ok=True)

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] Camera not found or cannot be opened.")
            return None

        count = 0
        print(f"[INFO] Starting capture for {user_name} ({user_id})...")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Failed to capture frame.")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                count += 1
                face_crop = gray[y:y + h, x:x + w]
                img_path = os.path.join(user_folder, f"{user_name}_{user_id}_{count}.jpg")
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
            print("[WARN] No faces captured.")
            return None

    except Exception as e:
        print(f"[ERROR] capture_faces_for_user failed: {e}")
        return None


# -------------------------------------------------------------
# 2️⃣ Encode faces and store data in 3 locations
# -------------------------------------------------------------
def encode_and_store_face(user_id, user_name, user_folder):
    """Encodes user's face data and stores in dataset, .pkl, and MongoDB with duplicate-face check."""
    try:
        if not os.path.exists(user_folder):
            print(f"[ERROR] Folder not found: {user_folder}")
            return False

        all_faces = []
        image_paths = []

        print("[INFO] Processing and encoding images...")

        for file in os.listdir(user_folder):
            if file.lower().endswith((".jpg", ".png")):
                path = os.path.join(user_folder, file)
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    img_resized = cv2.resize(img, (100, 100))
                    all_faces.append(img_resized.flatten())
                    web_path = path.replace("\\", "/")
                    image_paths.append(web_path)

        if not all_faces:
            print("[ERROR] No valid images found for encoding.")
            return False

        # ✅ Compute new encoding (average vector)
        avg_encoding = np.mean(all_faces, axis=0)
        print(f"[SUCCESS] Encoding generated for {user_name} (length={len(avg_encoding)})")

        # ✅ Load existing encodings for duplicate check
        encodings = load_encodings()
        threshold = 2500.0  # smaller = stricter similarity threshold

        for existing_uid, data in encodings.items():
            if existing_uid == user_id:
                continue  # Skip self (update case)

            existing_encoding = np.array(data["encoding"])
            dist = np.linalg.norm(existing_encoding - avg_encoding)
            if dist < threshold:
                print(f"[DUPLICATE] Similar face found! User: {data['name']} | Distance={dist}")
                print("[ACTION] Registration aborted due to duplicate face.")
                return "duplicate"

        # ✅ If not duplicate, save normally
        encodings[user_id] = {"name": user_name, "encoding": avg_encoding}
        save_encodings(encodings)
        print(f"[SUCCESS] Stored encoding in {ENCODINGS_FILE}")

        # ✅ Store in MongoDB
        relative_folder = os.path.relpath(user_folder, "static").replace("\\", "/")
        face_info = {
            "dataset_path": relative_folder,
            "encoding_data": avg_encoding.tolist(),
            "encoding_shape": list(avg_encoding.shape),
            "images": image_paths,
            "last_updated": datetime.utcnow()
        }

        mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "face_data": face_info,
                "face_registered": True,
                "updated_at": datetime.utcnow()
            }}
        )

        print(f"[INFO] Face data stored successfully for {user_name}.")
        return True

    except Exception as e:
        print(f"[ERROR] encode_and_store_face failed: {e}")
        return False


# -------------------------------------------------------------
# 3️⃣ Save and Load Encodings (.pkl)
# -------------------------------------------------------------
def save_encodings(encodings):
    try:
        with open(ENCODINGS_FILE, "wb") as f:
            pickle.dump(encodings, f)
        print(f"[SUCCESS] Encodings saved to {ENCODINGS_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to save encodings.pkl: {e}")


def load_encodings():
    try:
        if not os.path.exists(ENCODINGS_FILE):
            return {}
        with open(ENCODINGS_FILE, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load encodings.pkl: {e}")
        return {}


# -------------------------------------------------------------
# 4️⃣ Stream Camera Feed (for live preview)
# -------------------------------------------------------------
def generate_camera_frames():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Cannot open camera for streaming.")
        return

    while True:
        success, frame = cap.read()
        if not success:
            break

        _, buffer = cv2.imencode(".jpg", frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()

# -------------------------------------------------------------
# 5️⃣ Check if user has registered face
# -------------------------------------------------------------
def is_face_registered(user_id):
    """Check from MongoDB if user has registered a face."""
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        return bool(user and user.get("face_registered", False))
    except Exception as e:
        print(f"[ERROR] is_face_registered failed: {e}")
        return False


# -------------------------------------------------------------
# 6️⃣ Recognize faces and mark attendance (from .pkl)
# -------------------------------------------------------------
def recognize_and_mark_attendance():
    """Opens webcam, compares live faces against stored encodings, and marks attendance."""
    try:
        encodings = load_encodings()
        if not encodings:
            print("[ERROR] No encodings found. Register faces first.")
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] Camera could not be opened.")
            return

        print("[INFO] Starting live recognition (Press ESC to exit)...")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Failed to read frame from camera.")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                face_crop = cv2.resize(gray[y:y + h, x:x + w], (100, 100)).flatten()

                matched_user = None
                min_dist = float("inf")
                threshold = 3500.0  # tune based on dataset

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
        print("[INFO] Attendance session completed.")

    except Exception as e:
        print(f"[ERROR] recognize_and_mark_attendance failed: {e}")


# -------------------------------------------------------------
# 7️⃣ Mark attendance in MongoDB
# -------------------------------------------------------------
def mark_attendance_in_db(user_id, user_name):
    """Inserts attendance record only once per day."""
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

        print(f"[SUCCESS] Attendance marked for {user_name} on {today}.")
    except Exception as e:
        print(f"[ERROR] mark_attendance_in_db failed: {e}")
