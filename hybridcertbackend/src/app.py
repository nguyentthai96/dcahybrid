import logging
import traceback

from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib, json, os, base64
from ecdsa import SigningKey, NIST256p, VerifyingKey, BadSignatureError
from ecdsa import SECP256k1, numbertheory
import subprocess, shlex
from nacl import signing
from nacl.signing import VerifyKey
from jwcrypto import jwk

from DecentralizedCA import DecentralizedCA, parse_csr

app = Flask(__name__)
CORS(app)  # This allows all origins by default
#
app.logger.setLevel(logging.INFO)
# Nếu bạn muốn ghi ra file thay vì console
# handler = logging.FileHandler('app.log')
# app.logger.addHandler(handler)


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'



# Init Global System
ca_system = DecentralizedCA()

# --- API ROUTES ---

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "public_key": ca_system.get_public_key_hex(),
        "dca_certificate": ca_system.dca_crt,
        "merkle_root": ca_system.merkle_tree.get_root(),
        "total_certs": len(ca_system.merkle_tree.get_all_leaves())
    })

@app.route('/api/issue', methods=['POST'])
def sign_issue():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    file_bytes = file.read()
    metadata = request.form.get('metadata', 'User Document')


    try:
        parse_csr(file_bytes)
        result = ca_system.sign_issue(file_bytes, { "metadata": metadata, "filename": file.filename})
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/sign', methods=['POST'])
def sign_document():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    file_bytes = file.read()
    metadata = request.form.get('metadata', 'User Document')


    try:
        result = ca_system.sign_file(file_bytes, { "metadata": metadata, "filename": file.filename})
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/verify', methods=['POST'])
def verify_document():
    if 'file' not in request.files or 'certificate' not in request.form:
        return jsonify({"error": "Missing file or certificate JSON"}), 400

    file = request.files['file']
    file_bytes = file.read()

    # Parse Certificate JSON
    try:
        cert_json = json.loads(request.form['certificate'])


        is_valid, message = ca_system.verify_file(file_bytes, cert_json)
        return jsonify({"valid": is_valid, "message": message})
    except Exception as e:
        return jsonify({"error": "Invalid Certificate Format", "details": str(e)}), 400




if __name__ == "__main__":
    app.run(port=5000, debug=True, use_reloader=False)
