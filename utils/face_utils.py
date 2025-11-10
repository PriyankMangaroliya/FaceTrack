"""
utils/face_utils.py
---------------------------------
Final Face Utilities Integration

✅ Fast camera startup (cv2.CAP_DSHOW)
✅ DNN-based face detection (no dlib)
✅ LBPH model training (lightweight + accurate)
✅ Dataset + .pkl + .yml + MongoDB integration
✅ All data stored inside user's face_data
✅ Auto-delete folder if DB update fails
"""

import os
import cv2
import numpy as np
import pickle
import shutil
from datetime import datetime
from bson import ObjectId
from utils.db import mongo

# ==============================
# GLOBAL CONFIG
# ==============================
DATASET_DIR = os.path.join("static", "dataset")
MODEL_FILE = "lbph_model.yml"
LABELS_FILE = "labels.pkl"

MODEL_PROTO = os.path.join("utils", "deploy.prototxt")
MODEL_WEIGHTS = os.path.join("utils", "res10_300x300_ssd_iter_140000.caffemodel")

if not (os.path.exists(MODEL_PROTO) and os.path.exists(MODEL_WEIGHTS)):
    raise FileNotFoundError(f"❌ Missing DNN model files: {MODEL_PROTO}, {MODEL_WEIGHTS}")

FACE_NET = cv2.dnn.readNetFromCaffe(MODEL_PROTO, MODEL_WEIGHTS)
CONFIDENCE_THRESHOLD = 0.6


# -------------------------------------------------------------
# DNN FACE DETECTION
# -------------------------------------------------------------
def detect_faces_dnn(frame, conf_threshold=CONFIDENCE_THRESHOLD):
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
# 1️⃣ CAPTURE FACE IMAGES + STORE IN DB
# -------------------------------------------------------------
def capture_faces_for_user(user_id, user_name, num_samples=5):
    """Capture multiple face images from webcam, train model, and update DB."""
    safe_name = user_name.replace(" ", "_")
    user_folder = os.path.join(DATASET_DIR, f"{safe_name}_{user_id}")

    try:
        os.makedirs(user_folder, exist_ok=True)
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("[ERROR] Camera not found.")
            return None

        count = 0
        image_paths = []
        print(f"[INFO] Capturing faces for {user_name}...")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            faces = detect_faces_dnn(frame)
            for (x, y, w, h, conf) in faces:
                face_crop = frame[y:y + h, x:x + w]
                if face_crop.size == 0:
                    continue
                gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                count += 1
                img_path = os.path.join(user_folder, f"{safe_name}_{count}.jpg")
                cv2.imwrite(img_path, gray)
                image_paths.append(img_path.replace("\\", "/"))

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"{count}/{num_samples}", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.imshow("Capture Faces (ESC to stop)", frame)
            if cv2.waitKey(1) == 27 or count >= num_samples:
                break

        cap.release()
        cv2.destroyAllWindows()

        print(f"[DONE] Captured {count} samples for {user_name}.")

        if count == 0:
            print("[WARNING] No images captured.")
            shutil.rmtree(user_folder, ignore_errors=True)
            return None

        # Train LBPH model and store locally
        model_binary, labels_binary, label_map = train_lbph_model()

        # ✅ Store everything inside face_data of the same user
        update_result = mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "face_registered": True,
                "face_data": {
                    "images": image_paths,
                    "lbph_model_yml": model_binary,
                    "labels_pkl": labels_binary,
                    "label_map": label_map,
                    "updated_at": datetime.utcnow().isoformat()
                }
            }}
        )

        if update_result.modified_count == 0:
            print("[DB ERROR] MongoDB update failed — deleting dataset folder.")
            shutil.rmtree(user_folder, ignore_errors=True)
            return None

        print(f"[DB] ✅ Face data stored in MongoDB for user {user_name}.")
        return user_folder

    except Exception as e:
        print(f"[ERROR] capture_faces_for_user failed: {e}")
        shutil.rmtree(user_folder, ignore_errors=True)
        return None


# -------------------------------------------------------------
# 2️⃣ TRAIN LBPH MODEL (Return Binary)
# -------------------------------------------------------------
def train_lbph_model():
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces, labels = [], []
    label_map, label_id = {}, 0

    for person in os.listdir(DATASET_DIR):
        person_dir = os.path.join(DATASET_DIR, person)
        if not os.path.isdir(person_dir):
            continue
        label_map[person] = label_id
        for img in os.listdir(person_dir):
            path = os.path.join(person_dir, img)
            gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if gray is not None:
                faces.append(gray)
                labels.append(label_id)
        label_id += 1

    if not faces:
        print("[WARNING] No faces found for training.")
        return None, None, {}

    recognizer.train(faces, np.array(labels))
    recognizer.save(MODEL_FILE)
    with open(LABELS_FILE, "wb") as f:
        pickle.dump(label_map, f)

    print(f"[TRAINED] LBPH Model saved → {MODEL_FILE}")

    # Read binary content for DB storage
    with open(MODEL_FILE, "rb") as f:
        model_binary = f.read()
    with open(LABELS_FILE, "rb") as f:
        labels_binary = f.read()

    return model_binary, labels_binary, label_map


# -------------------------------------------------------------
# 3️⃣ GENERATE CAMERA FRAMES (for live preview)
# -------------------------------------------------------------
def generate_camera_frames():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] Cannot open camera.")
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
# 4️⃣ CHECK IF FACE REGISTERED
# -------------------------------------------------------------
def is_face_registered(user_id):
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        return bool(user and user.get("face_registered", False))
    except Exception as e:
        print(f"[ERROR] is_face_registered failed: {e}")
        return False


__all__ = [
    "detect_faces_dnn",
    "capture_faces_for_user",
    "train_lbph_model",
    "generate_camera_frames",
    "is_face_registered"
]
