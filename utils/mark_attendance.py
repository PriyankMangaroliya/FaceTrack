import os
import cv2
import pickle
import numpy as np
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from bson import ObjectId

# ============================
# CONFIG
# ============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PROTO = os.path.join(BASE_DIR, "deploy.prototxt")
MODEL_WEIGHTS = os.path.join(BASE_DIR, "res10_300x300_ssd_iter_140000.caffemodel")
MODEL_FILE = os.path.join(BASE_DIR, "..", "lbph_model.yml")
LABELS_FILE = os.path.join(BASE_DIR, "..", "labels.pkl")

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "AttendanceSystem"

MIN_DURATION_MINUTES = 5
CONFIDENCE_THRESHOLD = 0.4

# Proper timezone-aware IST
IST = timezone(timedelta(hours=5, minutes=30))

FACE_NET = cv2.dnn.readNetFromCaffe(MODEL_PROTO, MODEL_WEIGHTS)


# ============================
# UTILITIES
# ============================
def _parse_time_str(tstr):
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(tstr, fmt)
        except ValueError:
            continue
    raise ValueError(f"Bad time: {tstr}")


def _minutes_between(t1, t2):
    # Convert string times to datetime objects (same day)
    d1 = _parse_time_str(t1)
    d2 = _parse_time_str(t2)

    today = datetime.now(IST).date()
    d1 = d1.replace(year=today.year, month=today.month, day=today.day)
    d2 = d2.replace(year=today.year, month=today.month, day=today.day)

    # Midnight wrap
    if d2 < d1:
        d2 += timedelta(days=1)

    return int((d2 - d1).total_seconds() / 60)


def _format_dur(m):
    h, mm = divmod(int(m), 60)
    return f"{h}h {mm}m"


# ============================
# FACE DETECTION (DNN)
# ============================
def detect_faces_dnn(frame, conf_threshold=CONFIDENCE_THRESHOLD):
    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(
        cv2.resize(frame, (300, 300)),
        1.0,
        (300, 300),
        (104.0, 177.0, 123.0)
    )
    FACE_NET.setInput(blob)
    detections = FACE_NET.forward()

    boxes = []
    for i in range(detections.shape[2]):
        confidence = float(detections[0, 0, i, 2])
        if confidence > conf_threshold:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (x1, y1, x2, y2) = box.astype("int")
            boxes.append((x1, y1, x2-x1, y2-y1, confidence))

    return boxes


# ============================
# MARK ATTENDANCE
# ============================
def mark_attendance_in_db(user_id, user_name):
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]

        # ---------------------------
        # GET USER & INSTITUTE FROM DB
        # ---------------------------
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            print("[ERROR] User not found in DB")
            return "Error"

        # Get institute_id as STRING
        institute_id = str(user.get("institute_id", ""))

        # ---------------------------
        # DATE / TIME
        # ---------------------------
        now_ist = datetime.now(IST)
        today = now_ist.strftime("%Y-%m-%d")
        current_time = now_ist.strftime("%H:%M")

        # ATTENDANCE EXIST?
        rec = db.attendances.find_one({
            "user_id": str(user_id),
            "date": today
        })

        # ---------------------------
        # FIRST ENTRY → CHECK-IN
        # ---------------------------
        if not rec:
            entry = {
                "time_in": current_time,
                "time_out": None,
                "duration": None,
                "label": "Check-In"
            }

            db.attendances.insert_one({
                "user_id": str(user_id),
                "institute_id": institute_id,
                "date": today,
                "entries": [entry],
                "status": "present",
                "marked_by": "LBPH System",
                "created_at": now_ist,
                "updated_at": now_ist
            })

            print(f"[NEW] {user_name} | Check-In {current_time}")
            return "Check-In"

        # ---------------------------
        # OTHER ENTRIES
        # ---------------------------
        entries = rec.get("entries", [])
        last = entries[-1] if entries else None

        # No last entry → add check-in
        if not last:
            entries.append({
                "time_in": current_time,
                "time_out": None,
                "duration": None,
                "label": "Check-In"
            })
            db.attendances.update_one(
                {"_id": rec["_id"]},
                {"$set": {"entries": entries, "updated_at": now_ist}}
            )
            print(f"[ADD] {user_name} | Check-In {current_time}")
            return "Check-In"

        # Last entry has no time_out → CHECK-OUT
        if last.get("time_out") is None:
            diff = _minutes_between(last["time_in"], current_time)

            if diff < MIN_DURATION_MINUTES:
                print(f"[REPEAT] {user_name} | Already Present ({diff}m)")
                return f"Already Present ({diff}m)"

            last["time_out"] = current_time
            last["duration"] = _format_dur(diff)
            last["label"] = "Check-Out"

            entries[-1] = last
            db.attendances.update_one(
                {"_id": rec["_id"]},
                {"$set": {"entries": entries, "updated_at": now_ist}}
            )
            print(f"[OUT] {user_name} | Check-Out {current_time}")
            return "Check-Out"

        # Last entry closed → NEW CHECK-IN
        last_out = last.get("time_out")
        diff = _minutes_between(last_out, current_time)

        if diff < MIN_DURATION_MINUTES:
            print(f"[REPEAT] {user_name} | Already Present ({diff}m)")
            return f"Already Present ({diff}m)"

        entries.append({
            "time_in": current_time,
            "time_out": None,
            "duration": None,
            "label": "Check-In"
        })

        db.attendances.update_one(
            {"_id": rec["_id"]},
            {"$set": {"entries": entries, "updated_at": now_ist}}
        )

        print(f"[IN] {user_name} | New Check-In {current_time}")
        return "Check-In"

    except Exception as e:
        print("DB Error:", e)
        return "Error"


# ============================
# FACE RECOGNITION LOOP
# ============================
def mark_face_recognition():
    try:
        if not os.path.exists(MODEL_FILE):
            print("[ERROR] No LBPH model found.")
            return

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(MODEL_FILE)

        with open(LABELS_FILE, "rb") as f:
            labels = pickle.load(f)

        rev = {v: k for k, v in labels.items()}

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("[ERROR] Cannot open camera.")
            return

        print("[INFO] LBPH Recognition Started (ESC to exit)")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detect_faces_dnn(frame)

            for (x, y, w, h, conf) in faces:
                roi = gray[y:y+h, x:x+w]
                if roi.size == 0:
                    continue

                predicted_id, confv = recognizer.predict(roi)

                # KNOWN USER
                if confv < 70:
                    full = rev.get(predicted_id)
                    if not full:
                        continue

                    name, uid = (full.rsplit("_", 1) + [None])[:2]
                    uid = str(ObjectId(uid)) if uid else None

                    action = mark_attendance_in_db(uid, name)
                    color = (0, 255, 0)
                    label = f"{name} - {action}"

                # UNKNOWN USER
                else:
                    label = "Unknown"
                    color = (0, 0, 255)

                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                cv2.putText(
                    frame,
                    label,
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2
                )

            cv2.imshow("LBPH Attendance", frame)

            if cv2.waitKey(1) == 27:
                break

        cap.release()
        cv2.destroyAllWindows()

    except Exception as e:
        print("[ERROR] Recognition:", e)


if __name__ == "__main__":
    mark_face_recognition()
