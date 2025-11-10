"""
utils/mark_attendance.py
---------------------------------
LBPH Face Recognition & Attendance Marking System

✅ Uses OpenCV DNN for detection + LBPH for recognition
✅ Fully works offline (no dlib required)
✅ Auto Check-In / Re-Entry / Check-Out logic
✅ Displays live confidence & model accuracy
✅ Stores attendance in MongoDB
"""

import os
import cv2
import pickle
import numpy as np
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from utils.db import mongo

# ==============================
# GLOBAL CONFIGURATION
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PROTO = os.path.join(BASE_DIR, "deploy.prototxt")
MODEL_WEIGHTS = os.path.join(BASE_DIR, "res10_300x300_ssd_iter_140000.caffemodel")
MODEL_FILE = os.path.join(BASE_DIR, "..", "lbph_model.yml")
LABELS_FILE = os.path.join(BASE_DIR, "..", "labels.pkl")

# ✅ MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client["AttendanceSystem"]

# Load DNN Model
if not (os.path.exists(MODEL_PROTO) and os.path.exists(MODEL_WEIGHTS)):
    raise FileNotFoundError("❌ Missing DNN model files (deploy.prototxt / caffemodel).")

FACE_NET = cv2.dnn.readNetFromCaffe(MODEL_PROTO, MODEL_WEIGHTS)
CONFIDENCE_THRESHOLD = 0.6


# -------------------------------------------------------------
# DNN FACE DETECTION
# -------------------------------------------------------------
def detect_faces_dnn(frame, conf_threshold=CONFIDENCE_THRESHOLD):
    """Detects faces using OpenCV DNN and returns bounding boxes."""
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
            boxes.append((x1, y1, x2 - x1, y2 - y1, confidence))
    return boxes


# -------------------------------------------------------------
# MARK ATTENDANCE IN DATABASE
# -------------------------------------------------------------
def mark_attendance_in_db(user_id, user_name, institute_id="Unknown"):
    """
    Marks attendance for a recognized user.
    Supports multiple entries per day (Check-In, Re-Entry, Check-Out)
    """
    try:
        # ✅ Ensure MongoDB connection
        client = MongoClient("mongodb://localhost:27017/")
        db = client["AttendanceSystem"]

        now = datetime.utcnow()
        today = now.strftime("%Y-%m-%d")

        # Find last entry for this user today
        last_entry = db.attendances.find_one(
            {"user_id": user_id, "date": today},
            sort=[("created_at", -1)]
        )

        status = "Check-In"
        if last_entry:
            diff = (now - last_entry["created_at"]).seconds
            if diff > 7200:  # >2 hours
                status = "Check-Out"
            elif diff > 300:  # >5 minutes
                status = "Re-Entry"
            else:
                print(f"[SKIP] Recent attendance exists for {user_name}")
                return False

        record = {
            "user_id": user_id,
            "institute_id": institute_id,
            "date": today,
            "time": now.strftime("%H:%M:%S"),
            "marked_by": "LBPH System",
            "status": status,
            "remarks": "",
            "correction": None,
            "created_at": now,
            "updated_at": now
        }

        db.attendances.insert_one(record)
        print(f"[✅ ATTENDANCE] {user_name} | {status} | {today} {now.strftime('%H:%M:%S')}")
        return True

    except Exception as e:
        print(f"[ERROR] mark_attendance_in_db failed: {e}")
        return False


# -------------------------------------------------------------
# MAIN FACE RECOGNITION + LIVE ACCURACY
# -------------------------------------------------------------
def mark_face_recognition():
    """
    Recognize faces using LBPH and mark attendance automatically.
    Works with label format: username_userid (e.g. Priysami_690ccb9e56acb5814051c4f7)
    """
    try:
        if not os.path.exists(MODEL_FILE):
            print("[❌ ERROR] LBPH model not found. Please train first.")
            return

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(MODEL_FILE)
        with open(LABELS_FILE, "rb") as f:
            labels = pickle.load(f)
        rev_labels = {v: k for k, v in labels.items()}

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("[❌ ERROR] Cannot access camera.")
            return

        print("[INFO] Starting LBPH Attendance Recognition (Press ESC to exit)...")
        recognized_today = set()
        total_tests = 0
        correct_matches = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detect_faces_dnn(frame)

            for (x, y, w, h, conf) in faces:
                face = gray[y:y + h, x:x + w]
                if face.size == 0:
                    continue

                label_id, confidence = recognizer.predict(face)
                total_tests += 1

                if confidence < 70:
                    full_label = rev_labels[label_id]
                    if "_" in full_label:
                        name, user_id_str = full_label.rsplit("_", 1)
                    else:
                        name, user_id_str = full_label, None

                    # Convert safely to ObjectId
                    try:
                        user_oid = ObjectId(user_id_str)
                    except Exception:
                        print(f"[WARN] Invalid ObjectId for {full_label}")
                        continue

                    # Lookup user in DB
                    user_record = db.users.find_one({"_id": user_oid})
                    if not user_record:
                        print(f"[WARN] User '{full_label}' not found in database.")
                        continue

                    correct_matches += 1
                    color = (0, 255, 0)
                    label = f"{name} ({round(100 - confidence, 2)}%)"

                    # Mark attendance only once per session
                    if str(user_oid) not in recognized_today:
                        institute_id = str(user_record.get("institute_id", "Unknown"))
                        mark_attendance_in_db(
                            user_id=str(user_oid),
                            user_name=name,
                            institute_id=institute_id
                        )
                        recognized_today.add(str(user_oid))

                else:
                    name = "Unknown"
                    color = (0, 0, 255)
                    label = f"{name} ({round(100 - confidence, 2)}%)"

                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, label, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            accuracy = (correct_matches / total_tests * 100) if total_tests > 0 else 0
            print(f"[LIVE ACCURACY] {accuracy:.2f}% ({correct_matches}/{total_tests})", end="\r")

            cv2.imshow("LBPH Attendance Recognition", frame)
            if cv2.waitKey(1) == 27:  # ESC key
                break

        cap.release()
        cv2.destroyAllWindows()
        print(f"\n[FINAL ACCURACY] {accuracy:.2f}% ({correct_matches}/{total_tests})")

    except Exception as e:
        print(f"[ERROR] mark_face_recognition failed: {e}")


# -------------------------------------------------------------
# MAIN ENTRY POINT
# -------------------------------------------------------------
if __name__ == "__main__":
    mark_face_recognition()
