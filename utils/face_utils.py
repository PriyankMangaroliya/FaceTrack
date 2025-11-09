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

                # draw box
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

        # Store in DB
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

        # Skip every 2nd frame → smoother output
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


# # -------------------------------------------------------------
# # 6️⃣ AUTO FACE RECOGNITION & ATTENDANCE (STABLE VERSION)
# # -------------------------------------------------------------
# def recognize_and_mark_attendance(auto_start=True):
#     """
#     Runs a real-time loop for face recognition and marks attendance.
#     Allows multiple Check-Ins / Check-Outs per day.
#     ✅ Works reliably on Windows with CAP_DSHOW
#     ✅ Marks attendance automatically in MongoDB
#     """
#     try:
#         encodings = load_encodings()
#         if not encodings:
#             print("[ERROR] No face encodings found — please register at least one user.")
#             return
#
#         # Use CAP_DSHOW for faster and more reliable camera init (Windows)
#         cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
#         if not cap.isOpened():
#             print("[ERROR] Camera not accessible. Try another device index or restart system.")
#             return
#
#         print("[INFO] 🔍 Starting auto attendance system... (Press ESC to exit)")
#         mark_interval = 60  # avoid duplicate marking within 1 minute
#         check_gap_seconds = 7200  # 2 hours for Check-Out logic
#         last_marked = {}
#
#         while True:
#             ret, frame = cap.read()
#             if not ret:
#                 print("[WARN] Failed to read frame from camera.")
#                 break
#
#             # Detect faces
#             faces = detect_faces_dnn(frame)
#             for (x, y, w, h, conf) in faces:
#                 face_crop = frame[y:y + h, x:x + w]
#                 if face_crop.size == 0:
#                     continue
#
#                 gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
#                 face_enc = cv2.resize(gray, (100, 100)).flatten()
#
#                 matched_user, min_dist = None, float("inf")
#                 threshold = 3500.0
#
#                 for uid, data in encodings.items():
#                     dist = np.linalg.norm(data["encoding"] - face_enc)
#                     if dist < threshold and dist < min_dist:
#                         matched_user = (uid, data["name"])
#                         min_dist = dist
#
#                 color = (0, 0, 255)
#                 label = "Unknown"
#
#                 if matched_user:
#                     uid, name = matched_user
#                     now = datetime.utcnow()
#                     if uid not in last_marked or (now - last_marked[uid]).seconds > mark_interval:
#                         success = mark_attendance_in_db(uid, name, check_gap_seconds)
#                         if success:
#                             last_marked[uid] = now
#                     color = (0, 255, 0)
#                     label = f"{name} ({int(conf * 100)}%)"
#
#                 cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
#                 cv2.putText(frame, label, (x, y - 10),
#                             cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
#
#             cv2.imshow("Auto Attendance System", frame)
#             if cv2.waitKey(1) == 27:  # ESC key
#                 break
#
#         cap.release()
#         cv2.destroyAllWindows()
#         print("[INFO] Attendance session closed.")
#
#     except Exception as e:
#         print(f"[ERROR] recognize_and_mark_attendance failed: {e}")
#
#
# # -------------------------------------------------------------
# # 7️⃣ ATTENDANCE DATABASE HANDLER
# # -------------------------------------------------------------
# def mark_attendance_in_db(user_id, user_name, gap_seconds=7200):
#     """
#     Marks 'Check-In', 'Check-Out', or 'Re-Entry' based on time gap.
#     ✅ Multiple attendance entries per day supported
#     ✅ Returns True when new entry created
#     """
#     try:
#         now = datetime.utcnow()
#         today = now.strftime("%Y-%m-%d")
#
#         # Find last entry of the day for this user
#         last_entry = mongo.db.attendances.find_one(
#             {"user_id": user_id, "date": today},
#             sort=[("created_at", -1)]
#         )
#
#         status = "Check-In"
#         if last_entry:
#             diff = (now - last_entry["created_at"]).seconds
#             if diff > gap_seconds:
#                 status = "Check-Out"
#             elif diff > 300:  # seen again after 5+ mins
#                 status = "Re-Entry"
#             else:
#                 # Skip duplicates within 5 minutes
#                 return False
#
#         mongo.db.attendances.insert_one({
#             "user_id": user_id,
#             "name": user_name,
#             "date": today,
#             "time": now.strftime("%H:%M:%S"),
#             "status": status,
#             "marked_by": "System (Auto)",
#             "created_at": now,
#             "updated_at": now
#         })
#
#         print(f"[ATTENDANCE ✅] {user_name} | {status} | {today} {now.strftime('%H:%M:%S')}")
#         return True
#
#     except Exception as e:
#         print(f"[ERROR] mark_attendance_in_db failed: {e}")
#         return False
