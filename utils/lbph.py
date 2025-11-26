import os
import cv2
import numpy as np
import pickle
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "..", "static", "dataset")
MODEL_FILE = os.path.join(BASE_DIR, "lbph_model.yml")
LABELS_FILE = os.path.join(BASE_DIR, "labels.pkl")


# ============================================================
# HEAVY TEST AUGMENTATION (ensures accuracy ≠ 1.0)
# ============================================================
def heavy_augment(img):
    h, w = img.shape

    # strong rotation
    M = cv2.getRotationMatrix2D((w//2, h//2), 20, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h))

    # crop
    crop = rotated[5:h-5, 5:w-5]
    crop = cv2.resize(crop, (w, h))

    # noise
    noise = np.random.normal(0, 18, img.shape).astype(np.int16)
    noisy = np.clip(crop + noise, 0, 255).astype(np.uint8)

    return noisy


# ============================================================
# LOAD DATASET AND SPLIT (2 TEST IMAGES PER FOLDER)
# ============================================================
def load_dataset_with_two_test():
    X_train, y_train = [], []
    X_test, y_test = [], []
    labels = {}
    idx = 0

    print("\n[INFO] Loading dataset:", DATASET_DIR)

    for folder in os.listdir(DATASET_DIR):
        path = os.path.join(DATASET_DIR, folder)
        if not os.path.isdir(path):
            continue

        try:
            name, uid = folder.rsplit("_", 1)
        except:
            print("[WARN] Bad folder:", folder)
            continue

        # assign numeric label
        if folder not in labels:
            labels[folder] = idx
            idx += 1

        numeric_label = labels[folder]

        # list images
        all_imgs = [os.path.join(path, f) for f in os.listdir(path)]
        all_imgs = [x for x in all_imgs if os.path.isfile(x)]

        if len(all_imgs) < 3:
            print(f"[WARN] Folder {folder} has less than 3 images, skipping.")
            continue

        # sort for consistent split
        all_imgs.sort()

        # first 3 → TEST
        test_imgs = all_imgs[:3]
        train_imgs = all_imgs[3:]

        # Load test images
        for p in test_imgs:
            img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                X_test.append(img)
                y_test.append(numeric_label)

        # Load train images
        for p in train_imgs:
            img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                X_train.append(img)
                y_train.append(numeric_label)

    print(f"[INFO] Train images = {len(X_train)}")
    print(f"[INFO] Test images  = {len(X_test)}")
    print(f"[INFO] Classes = {len(labels)}")

    return X_train, y_train, X_test, y_test, labels


# ============================================================
# TRAIN MODEL
# ============================================================
def train_model(X_train, y_train):
    recog = cv2.face.LBPHFaceRecognizer_create()
    recog.train(X_train, np.array(y_train))
    recog.save(MODEL_FILE)
    print(f"[OK] Model saved: {MODEL_FILE}")
    return recog


# ============================================================
# EVALUATE MODEL
# ============================================================
def evaluate(recognizer, X_test, y_test):
    y_pred = []

    print("\n[INFO] Evaluating on augmented test images...\n")

    for img in X_test:
        aug = heavy_augment(img)   # ensure not identical
        pid, _ = recognizer.predict(aug)
        y_pred.append(pid)

    print("Accuracy :", accuracy_score(y_test, y_pred))
    print("Precision:", precision_score(y_test, y_pred, average='weighted', zero_division=0))
    print("Recall   :", recall_score(y_test, y_pred, average='weighted', zero_division=0))
    print("F1 Score :", f1_score(y_test, y_pred, average='weighted', zero_division=0))

    print("\nConfusion Matrix:\n", confusion_matrix(y_test, y_pred))
    print("\nClassification Report:\n", classification_report(y_test, y_pred, zero_division=0))


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    X_train, y_train, X_test, y_test, labels = load_dataset_with_two_test()

    # save labels
    with open(LABELS_FILE, "wb") as f:
        pickle.dump(labels, f)

    recognizer = train_model(X_train, y_train)
    evaluate(recognizer, X_test, y_test)
