import pickle
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LABELS_FILE = os.path.join(BASE_DIR, "..", "labels.pkl")

# # View
with open(LABELS_FILE, "rb") as f:
    labels = pickle.load(f)

print("Labels File Content:")
for name, label_id in labels.items():
    print(f"{label_id} -> {name}")

# Update

# ================================
# Load current labels
# ================================
# with open(LABELS_FILE, "rb") as f:
#     labels = pickle.load(f)
#
# print("Current Labels:")
# for name, label_id in labels.items():
#     print(f"{label_id} -> {name}")
#
# print("\n=====================================")
# print(" UPDATE LABEL NAME SAFELY")
# print(" (Do NOT change numeric ID)")
# print("=====================================\n")
#
# # ================================
# # User input
# # ================================
# old_name = input("Enter OLD label name: ").strip()
# new_name = input("Enter NEW label name: ").strip()
#
# # ================================
# # Check existence
# # ================================
# if old_name not in labels:
#     print("\n❌ ERROR: Label does not exist.")
#     exit()
#
# # ================================
# # Get ID and update name
# # ================================
# label_id = labels[old_name]
# labels.pop(old_name)          # remove old
# labels[new_name] = label_id   # set new with same ID
#
# # ================================
# # Save updated file
# # ================================
# with open(LABELS_FILE, "wb") as f:
#     pickle.dump(labels, f)
#
# print("\n✔ Successfully updated label!")
# print("Updated Labels:")
# for name, label_id in labels.items():
#     print(f"{label_id} -> {name}")


