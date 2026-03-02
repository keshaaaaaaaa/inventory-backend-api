import os
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore, auth

app = Flask(__name__)

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

@app.route("/")
def home():
    return "Backend is running"

@app.route("/secure-data", methods=["POST"])
def secure_data():
    try:
        id_token = request.headers.get("Authorization").split("Bearer ")[1]
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)