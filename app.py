import os
import json
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore, auth

app = Flask(__name__)

# Load Firebase key from Render Environment Variable
firebase_key = json.loads(os.environ["FIREBASE_KEY"])
cred = credentials.Certificate(firebase_key)
firebase_admin.initialize_app(cred)

db = firestore.client()

@app.route("/export-data", methods=["GET"])
def export_data():
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401

        id_token = auth_header.split("Bearer ")[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token["uid"]

        # Optional: allow only IT role
        user_doc = db.collection("users_auth").document(uid).get()
        if not user_doc.exists:
            return jsonify({"error": "User not found"}), 403

        role = user_doc.to_dict().get("role")
        if role != "IT":
            return jsonify({"error": "Not authorized"}), 403

        users_ref = db.collection("users").stream()
        devices_ref = db.collection("devices").stream()

        users = {doc.id: doc.to_dict() for doc in users_ref}

        devices = []
        for doc in devices_ref:
            d = doc.to_dict()

            if "date_added" in d and d["date_added"]:
                d["date_added"] = d["date_added"].isoformat()
    
            device_id = doc.id
            user_id = d.get("user_id")

            user = users.get(user_id, {})

            device_data = d.get("device_info") or d

            devices.append({
                "device_id": device_id,
                "user_id": user_id,
                "user": user,
                "device_data": device_data
            })
        return jsonify(devices)

    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route("/")
def home():
    return "Backend is running"

@app.route("/secure-data", methods=["POST"])
def secure_data():
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401

        id_token = auth_header.split("Bearer ")[1]
        decoded_token = auth.verify_id_token(id_token)

        uid = decoded_token["uid"]

        user_doc = db.collection("users_auth").document(uid).get()

        if not user_doc.exists:
            return jsonify({"error": "User not found"}), 403

        role = user_doc.to_dict().get("role")

        return jsonify({
            "message": "Access granted",
            "uid": uid,
            "role": role
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route("/submit-device", methods=["POST"])
def submit_device():
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401

        id_token = auth_header.split("Bearer ")[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token["uid"]

        user_doc = db.collection("users_auth").document(uid).get()

        if not user_doc.exists:
            return jsonify({"error": "User not found"}), 403

        role = user_doc.to_dict().get("role")

        if role != "EMPLOYEE":
            return jsonify({"error": "Only employees can submit"}), 403

        data = request.json

        # Create user record
        user_ref = db.collection("users").document()
        user_ref.set({
            "firstname": data.get("firstname"),
            "middlename": data.get("middlename"),
            "lastname": data.get("lastname"),
            "contactnum": data.get("contactnum"),
            "department": data.get("department"),
            "created_at": firestore.SERVER_TIMESTAMP
        })

        # Save device info
        device_info = data.get("device_info") or {}
        serial = device_info.get("serial_number")

        if not serial:
            return jsonify({"error": "Missing serial number"}), 400

        device_ref = db.collection("devices").document(serial)

        existing_device = device_ref.get()

        if existing_device.exists:
            # Update existing device
            device_ref.update({
                "user_id": user_ref.id,
                "device_info": device_info,
                "date_updated": firestore.SERVER_TIMESTAMP
            })
        else:
            # Create new device
            device_ref.set({
                "user_id": user_ref.id,
                "device_info": device_info,
                "date_added": firestore.SERVER_TIMESTAMP
            })
        return jsonify({"status": "success"})

    except Exception as e:
        return jsonify({"error": str(e)}), 401
    
# ================= DEPARTMENT ROUTING (START) =================

@app.route("/departments", methods=["GET"])
def get_departments():
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401

        id_token = auth_header.split("Bearer ")[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token["uid"]

        user_doc = db.collection("users_auth").document(uid).get()
        if not user_doc.exists:
            return jsonify({"error": "User not found"}), 403

        role = user_doc.to_dict().get("role")
        if role != "IT":
            return jsonify({"error": "Not authorized"}), 403

        departments = []
        docs = db.collection("departments").stream()

        for doc in docs:
            d = doc.to_dict()
            departments.append({
                "id": doc.id,
                "name": d.get("name"),
                "acronym": d.get("acronym")
            })

        return jsonify(departments)

    except Exception as e:
        return jsonify({"error": str(e)}), 401
    
@app.route("/departments", methods=["POST"])
def add_department():
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401

        id_token = auth_header.split("Bearer ")[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token["uid"]

        user_doc = db.collection("users_auth").document(uid).get()
        if not user_doc.exists:
            return jsonify({"error": "User not found"}), 403

        role = user_doc.to_dict().get("role")
        if role != "IT":
            return jsonify({"error": "Not authorized"}), 403

        data = request.json
        name = data.get("name")
        acronym = data.get("acronym")

        if not name or not acronym:
            return jsonify({"error": "Missing fields"}), 400

        # Prevent duplicates
        existing = db.collection("departments")\
            .where("name", "==", name)\
            .stream()

        for _ in existing:
            return jsonify({"error": "Department already exists"}), 400

        db.collection("departments").add({
            "name": name,
            "acronym": acronym
        })

        return jsonify({"status": "success"})

    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route("/departments/<dept_id>", methods=["DELETE"])
def delete_department(dept_id):
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401

        id_token = auth_header.split("Bearer ")[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token["uid"]

        user_doc = db.collection("users_auth").document(uid).get()
        if not user_doc.exists:
            return jsonify({"error": "User not found"}), 403

        role = user_doc.to_dict().get("role")
        if role != "IT":
            return jsonify({"error": "Not authorized"}), 403

        db.collection("departments").document(dept_id).delete()

        return jsonify({"status": "deleted"})

    except Exception as e:
        return jsonify({"error": str(e)}), 401
    
# ================= DEPARTMENT ROUTING (END) =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)