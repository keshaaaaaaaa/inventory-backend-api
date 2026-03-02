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
        db.collection("devices").add({
            "user_id": user_ref.id,
            "device_info": data.get("device_info"),
            "date_added": firestore.SERVER_TIMESTAMP
        })

        return jsonify({"status": "success"})

    except Exception as e:
        return jsonify({"error": str(e)}), 401

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)