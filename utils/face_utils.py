"""
utils/face_utils.py
---------------------------------
Optimized Face Utilities for:
1️⃣ Fast camera startup (cv2.CAP_DSHOW)
2️⃣ DNN-based face detection (no dlib)
3️⃣ Accurate encoding + duplicate detection
4️⃣ Reliable MongoDB + .pkl integration
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

MODEL_PROTO = os.path.join("utils", "deploy.prototxt")
MODEL_WEIGHTS = os.path.join("utils", "res10_300x300_ssd_iter_140000.caffemodel")

# Load DNN model safely
if not (os.path.exists(MODEL_PROTO) and os.path.exists(MODEL_WEIGHTS)):
    raise FileNotFoundError(
        f"❌ Missing DNN model files.\nExpected:\n- {MODEL_PROTO}\n- {MODEL_WEIGHTS}"
    )

FACE_NET = cv2.dnn.readNetFromCaffe(MODEL_PROTO, MODEL_WEIGHTS)
CONFIDENCE_THRESHOLD = 0.6


# -------------------------------------------------------------
# FAST DNN FACE DETECTION
# -------------------------------------------------------------
def detect_faces_dnn(frame, conf_threshold=CONFIDENCE_THRESHOLD):
    """Detect faces using OpenCV DNN and return bounding boxes."""
    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0,
                                 (300, 300), (104.0, 177.0, 123.0))
    FACE_NET.setInput(blob)
    detections = FACE_NET.forward()

    boxes = []
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > conf_threshold:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (x1, y1, x2, y2) = box.astype("int")
            x1, y1 = max(0, x1), max(0, y1)
            boxes.append((x1, y1, x2 - x1, y2 - y1, confidence))
    return boxes


# -------------------------------------------------------------
# 1️⃣ CAPTURE FACE IMAGES
# -------------------------------------------------------------
def capture_faces_for_user(user_id, user_name, num_samples=5):
    """Capture multiple face images from webcam and store dataset."""
    try:
        os.makedirs(DATASET_DIR, exist_ok=True)
        safe_name = user_name.replace(" ", "_")
        user_folder = os.path.join(DATASET_DIR, f"{safe_name}_{user_id}")
        os.makedirs(user_folder, exist_ok=True)

        # ✅ Use CAP_DSHOW for faster camera open (Windows)
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("[ERROR] Camera not found or cannot be opened.")
            return None

        count = 0
        print(f"[INFO] Starting capture for {user_name} ({user_id})...")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            faces = detect_faces_dnn(frame)
            for (x, y, w, h, conf) in faces:
                if w < 50 or h < 50:
                    continue

                face_crop = frame[y:y + h, x:x + w]
                if face_crop.size == 0:
                    continue

                count += 1
                gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                img_path = os.path.join(user_folder, f"{safe_name}_{user_id}_{count}.jpg")
                cv2.imwrite(img_path, gray)

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"{count}/{num_samples}", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            cv2.imshow("Capture Faces - ESC to stop", frame)
            if cv2.waitKey(1) == 27 or count >= num_samples:
                break

        cap.release()
        cv2.destroyAllWindows()

        if count > 0:
            result = encode_and_store_face(user_id, user_name, user_folder)
            if result == "duplicate":
                print("[⚠️] Duplicate face detected. Folder removed.")
                for f in os.listdir(user_folder):
                    os.remove(os.path.join(user_folder, f))
                os.rmdir(user_folder)
                return "duplicate"
            print(f"[SUCCESS] {count} images captured for {user_name}")
            return user_folder
        return None

    except Exception as e:
        print(f"[ERROR] capture_faces_for_user failed: {e}")
        return None


# -------------------------------------------------------------
# 2️⃣ ENCODE AND STORE FACE
# -------------------------------------------------------------
def encode_and_store_face(user_id, user_name, user_folder):
    """Encodes user's face data and stores in dataset + .pkl + MongoDB."""
    try:
        if not os.path.exists(user_folder):
            return False

        all_faces, image_paths = [], []
        for file in os.listdir(user_folder):
            if file.lower().endswith((".jpg", ".png")):
                path = os.path.join(user_folder, file)
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    img_resized = cv2.resize(img, (100, 100))
                    all_faces.append(img_resized.flatten())
                    image_paths.append(path.replace("\\", "/"))

        if not all_faces:
            return False

        avg_encoding = np.mean(all_faces, axis=0)
        encodings = load_encodings()
        threshold = 2500.0

        # Duplicate check
        for uid, data in encodings.items():
            if uid == user_id:
                continue
            dist = np.linalg.norm(np.array(data["encoding"]) - avg_encoding)
            if dist < threshold:
                print(f"[DUPLICATE] Already registered: {data['name']} (dist={dist:.2f})")
                return "duplicate"

        encodings[user_id] = {"name": user_name, "encoding": avg_encoding}
        save_encodings(encodings)

        rel_path = os.path.relpath(user_folder, "static").replace("\\", "/")
        face_info = {
            "dataset_path": rel_path,
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

        print(f"[INFO] Face data stored for {user_name}.")
        return True

    except Exception as e:
        print(f"[ERROR] encode_and_store_face failed: {e}")
        return False


# -------------------------------------------------------------
# 3️⃣ SAVE / LOAD ENCODINGS
# -------------------------------------------------------------
def save_encodings(encodings):
    try:
        with open(ENCODINGS_FILE, "wb") as f:
            pickle.dump(encodings, f)
        print(f"[SUCCESS] Saved encodings → {ENCODINGS_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to save encodings.pkl: {e}")


def load_encodings():
    if not os.path.exists(ENCODINGS_FILE):
        print("[INFO] No encodings.pkl found. Creating fresh one.")
        return {}
    try:
        with open(ENCODINGS_FILE, "rb") as f:
            return pickle.load(f)
    except EOFError:
        print("[WARN] encodings.pkl corrupted — resetting file.")
        return {}


# -------------------------------------------------------------
# 4️⃣ STREAM CAMERA PREVIEW (for web)
# -------------------------------------------------------------
def generate_camera_frames():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] Cannot open camera.")
        return

    frame_skip = 2
    frame_count = 0

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame_count += 1
        if frame_count % frame_skip != 0:
            continue

        _, buffer = cv2.imencode(".jpg", frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()


# -------------------------------------------------------------
# 5️⃣ CHECK FACE REGISTERED
# -------------------------------------------------------------
def is_face_registered(user_id):
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        return bool(user and user.get("face_registered", False))
    except Exception as e:
        print(f"[ERROR] is_face_registered failed: {e}")
        return False


# -------------------------------------------------------------
# EXPORTS (used by mark_attendance.py and HR module)
# -------------------------------------------------------------
__all__ = [
    "detect_faces_dnn",
    "capture_faces_for_user",
    "encode_and_store_face",
    "save_encodings",
    "load_encodings",
    "generate_camera_frames",
    "is_face_registered"
]
