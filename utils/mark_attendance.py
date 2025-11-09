"""
utils/mark_attendance.py
---------------------------------
Manual Face Recognition & Attendance Marking System

✅ Uses pre-saved encodings.pkl and MongoDB (direct connection)
✅ Allows multiple Check-Ins, Re-Entries, and Check-Outs per day
✅ Shows model accuracy live in CMD
✅ Press ESC to exit camera manually
"""

import os
import cv2
import pickle
import numpy as np
from datetime import datetime
from pymongo import MongoClient

# ==============================
# GLOBAL CONFIG
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "..", "static", "dataset")
ENCODINGS_FILE = os.path.join(BASE_DIR, "..", "encodings.pkl")

MODEL_PROTO = os.path.join(BASE_DIR, "deploy.prototxt")
MODEL_WEIGHTS = os.path.join(BASE_DIR, "res10_300x300_ssd_iter_140000.caffemodel")

# ✅ MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["AttendanceSystem"]

# ==============================
# DNN MODEL LOAD
# ==============================
if not (os.path.exists(MODEL_PROTO) and os.path.exists(MODEL_WEIGHTS)):
    raise FileNotFoundError(
        f"❌ Missing model files.\nExpected:\n- {MODEL_PROTO}\n- {MODEL_WEIGHTS}"
    )

FACE_NET = cv2.dnn.readNetFromCaffe(MODEL_PROTO, MODEL_WEIGHTS)
CONFIDENCE_THRESHOLD = 0.6


# -------------------------------------------------------------
# FACE DETECTION (DNN)
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
# LOAD ENCODINGS
# -------------------------------------------------------------
def load_encodings():
    if not os.path.exists(ENCODINGS_FILE):
        print("[INFO] No encodings.pkl found.")
        return {}
    with open(ENCODINGS_FILE, "rb") as f:
        return pickle.load(f)


# -------------------------------------------------------------
# ATTENDANCE DB HANDLER
# -------------------------------------------------------------
def mark_attendance_in_db(user_id, user_name, gap_seconds=7200):
    """
    Marks attendance:
    - First → Check-In
    - After 2+ hours → Check-Out
    - After 5+ minutes → Re-Entry
    - Within 5 minutes → skip
    """
    try:
        now = datetime.utcnow()
        today = now.strftime("%Y-%m-%d")

        last_entry = db.attendances.find_one(
            {"user_id": user_id, "date": today},
            sort=[("created_at", -1)]
        )

        status = "Check-In"
        if last_entry:
            diff = (now - last_entry["created_at"]).seconds
            if diff > gap_seconds:
                status = "Check-Out"
            elif diff > 300:
                status = "Re-Entry"
            else:
                return False

        db.attendances.insert_one({
            "user_id": user_id,
            "name": user_name,
            "date": today,
            "time": now.strftime("%H:%M:%S"),
            "status": status,
            "marked_by": "System",
            "created_at": now,
            "updated_at": now
        })

        print(f"[✅ MARKED] {user_name} | {status} | {today} {now.strftime('%H:%M:%S')}")
        return True

    except Exception as e:
        print(f"[ERROR] mark_attendance_in_db failed: {e}")
        return False


# -------------------------------------------------------------
# MAIN FACE RECOGNITION WITH ACCURACY DISPLAY
# -------------------------------------------------------------
def mark_face_recognition():
    try:
        encodings = load_encodings()
        if not encodings:
            print("[❌ ERROR] No encodings found. Please register at least one user.")
            return

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("[❌ ERROR] Could not access the camera.")
            return

        print("\n[🎥 INFO] Starting Manual Attendance Recognition...")
        print("[ℹ️ INFO] Press ESC to stop.\n")

        total_tests = 0
        correct_matches = 0
        recognized_users = set()

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[⚠️ WARN] Failed to capture frame from camera.")
                break

            faces = detect_faces_dnn(frame)
            for (x, y, w, h, conf) in faces:
                face_crop = frame[y:y + h, x:x + w]
                if face_crop.size == 0:
                    continue

                gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                face_enc = cv2.resize(gray, (100, 100)).flatten()

                matched_user, min_dist = None, float("inf")
                threshold = 3500.0

                for uid, data in encodings.items():
                    dist = np.linalg.norm(data["encoding"] - face_enc)
                    if dist < threshold and dist < min_dist:
                        matched_user = (uid, data["name"])
                        min_dist = dist

                total_tests += 1
                color, label = (0, 0, 255), f"Unknown ({int(conf * 100)}%)"

                if matched_user:
                    uid, name = matched_user
                    mark_attendance_in_db(uid, name)
                    correct_matches += 1
                    label, color = f"{name} ({int(conf * 100)}%)", (0, 255, 0)

                    if uid not in recognized_users:
                        print(f"[🎯 RECOGNIZED] {name} | Distance={min_dist:.2f}")
                        recognized_users.add(uid)

                # ✅ Display accuracy in CMD live
                accuracy = (correct_matches / total_tests) * 100 if total_tests > 0 else 0
                print(f"[📊 Accuracy Update] {accuracy:.2f}% ({correct_matches}/{total_tests})", end="\r")

                # Draw bounding box
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, label, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            cv2.imshow("Mark Attendance - Press ESC to Stop", frame)
            if cv2.waitKey(1) == 27:  # ESC
                break

        cap.release()
        cv2.destroyAllWindows()
        print("\n\n[ℹ️ INFO] Attendance marking session ended.")
        if total_tests > 0:
            final_acc = (correct_matches / total_tests) * 100
            print(f"[✅ Final Accuracy] {final_acc:.2f}% ({correct_matches}/{total_tests})")

    except Exception as e:
        print(f"[❌ ERROR] mark_face_recognition failed: {e}")


# -------------------------------------------------------------
# MAIN ENTRY POINT
# -------------------------------------------------------------
if __name__ == "__main__":
    mark_face_recognition()
