# backend/app_extended.py
import base64
import datetime
import hashlib
import json
import os

import requests
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    encode_dss_signature, decode_dss_signature
)
from cryptography.x509.oid import NameOID
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # This allows all origins by default

# ---------- Config ----------
IPFS_API = os.environ.get("IPFS_API", "http://127.0.0.1:5001/api/v0")  # local ipfs daemon
# If you want to use Infura/Pinata, use their HTTP API and auth headers (need credentials).
ETH_ENABLED = os.environ.get("ETH_ENABLED", "false").lower() == "true"
# If ETH_ENABLED True, set WEB3_PROVIDER and PRIVATE_KEY env vars for later optional function.
# ----------------------------

# For demo: generate an ephemeral ECDSA key (replace by calling DCA binary)
private_key = ec.generate_private_key(ec.SECP256R1())  # NIST P-256 for demo
public_key = private_key.public_key()


def sha256_bytes(data: bytes) -> bytes:
    h = hashlib.sha256()
    h.update(data)
    return h.digest()


def b64(x: bytes) -> str:
    return base64.b64encode(x).decode()


def from_b64(s: str) -> bytes:
    return base64.b64decode(s.encode())


# ---------------------------
# 1) Sign endpoint (demo or call DCA binary here)
# ---------------------------
@app.route("/sign", methods=["POST"])
def sign_file():
    f = request.files.get("file")
    if f is None:
        return jsonify({"error": "no file"}), 400
    data = f.read()
    file_hash = sha256_bytes(data)
    # sign using private_key (demo). Replace: call DCA binary & parse (r,s) if needed.
    signature_der = private_key.sign(file_hash, ec.ECDSA(hashes.SHA256()))
    # decode signature DER to (r,s)
    r, s = decode_dss_signature(signature_der)
    signature_obj = {"r": str(r), "s": str(s)}  # send as strings (big ints)
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # For identity demo: create a self-signed certificate (or load certificate produced by DCA)
    cert_pem = generate_self_signed_cert_pem(public_key)

    return jsonify({
        "hash_b64": b64(file_hash),
        "signature": signature_obj,
        "pubkey_b64": b64(pub_bytes),
        "certificate_pem": cert_pem.decode()  # text PEM
    })


# ---------------------------
# 2) Verify endpoint + extract identity + store metadata to IPFS
# ---------------------------
@app.route("/verify_and_store", methods=["POST"])
def verify_and_store():
    """
    Expect multipart/form-data:
      - file: uploaded file
      - signature: JSON string {"r": "...", "s": "..."} OR base64 DER (optional)
      - pubkey_b64: base64 of SubjectPublicKeyInfo DER OR certificate_pem optionally
      - certificate_pem: optional: PEM certificate (string)
      - store_ipfs: optional 'true'/'false'
      - store_chain: optional 'true'/'false' (if you want to write CID to blockchain)
    """
    file = request.files.get("file")
    if file is None:
        return jsonify({"error": "no file"}), 400
    data = file.read()
    file_hash = sha256_bytes(data)

    # parse signature
    sig_field = request.form.get("signature")
    if not sig_field:
        return jsonify({"error": "no signature provided"}), 400

    # allow either JSON or base64 DER
    try:
        sig_json = json.loads(sig_field)
        r = int(sig_json["r"])
        s = int(sig_json["s"])
        signature_der = encode_dss_signature(r, s)
    except Exception:
        # fallback: assume base64 DER
        signature_der = base64.b64decode(sig_field)

    # parse certificate or public key
    cert_pem = request.form.get("certificate_pem")
    pubkey_b64 = request.form.get("pubkey_b64")

    identity = {}
    verifier_public_key = None
    if cert_pem:
        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode())
            # extract subject fields (CN, O, email, etc)
            subj = cert.subject

            def get_attr(name):
                try:
                    return ", ".join([attr.value for attr in subj.get_attributes_for_oid(name)])
                except Exception:
                    return None

            from cryptography.x509.oid import NameOID
            identity = {
                "common_name": get_attr(NameOID.COMMON_NAME),
                "organization": get_attr(NameOID.ORGANIZATION_NAME),
                "organizational_unit": get_attr(NameOID.ORGANIZATIONAL_UNIT_NAME),
                "email": get_attr(NameOID.EMAIL_ADDRESS),
                "country": get_attr(NameOID.COUNTRY_NAME),
            }
            verifier_public_key = cert.public_key()
        except Exception as e:
            return jsonify({"error": "invalid certificate_pem", "detail": str(e)}), 400
    elif pubkey_b64:
        try:
            pub_der = base64.b64decode(pubkey_b64)
            verifier_public_key = serialization.load_der_public_key(pub_der)
            identity = {"note": "no certificate provided; only public key available"}
        except Exception as e:
            return jsonify({"error": "invalid pubkey_b64", "detail": str(e)}), 400
    else:
        return jsonify({"error": "no pubkey or certificate provided"}), 400

    # verify signature against file_hash
    try:
        verifier_public_key.verify(signature_der, file_hash, ec.ECDSA(hashes.SHA256()))
        valid = True
    except InvalidSignature:
        valid = False
    except Exception as ex:
        return jsonify({"error": "verification_error", "detail": str(ex)}), 500

    response = {
        "valid": valid,
        "identity": identity,
        "file_hash_b64": b64(file_hash),
    }

    # If store to IPFS requested
    store_ipfs = request.form.get("store_ipfs", "false").lower() == "true"
    if store_ipfs:
        metadata = {
            "file_hash_hex": file_hash.hex(),
            "file_hash_b64": b64(file_hash),
            "signature": sig_json if isinstance(sig_json, dict) else {"der_b64": b64(signature_der)},
            "pubkey_b64": pubkey_b64,
            "identity": identity
        }
        try:
            cid = ipfs_add_json(metadata)
            response["ipfs_cid"] = cid
            response["ipfs_url"] = f"https://ipfs.io/ipfs/{cid}"
            # optional: store cid on-chain
            store_chain = request.form.get("store_chain", "false").lower() == "true"
            if store_chain and ETH_ENABLED:
                tx_receipt = eth_store_cid(cid)
                response["eth_tx"] = tx_receipt
        except Exception as e:
            response["ipfs_error"] = str(e)

    return jsonify(response)


# ---------------------------
# Helper: create a self-signed certificate (demo)
# ---------------------------
def generate_self_signed_cert_pem(pubkey):
    # NOTE: This function uses the demo private_key to sign a self-signed cert containing a subject
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"demo.example.org"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Demo Org"),
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"VN"),
        x509.NameAttribute(NameOID.EMAIL_ADDRESS, u"demo@example.org"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(pubkey)
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )
    pem = cert.public_bytes(serialization.Encoding.PEM)
    return pem


# ---------------------------
# Helper: IPFS add JSON metadata (local daemon)
# ---------------------------
def ipfs_add_json(obj) -> str:
    # requires local ipfs daemon running (ipfs init && ipfs daemon)
    url = f"{IPFS_API}/add"
    data = json.dumps(obj).encode()
    files = {
        'file': ('metadata.json', data)
    }
    # stream: false to get single response
    r = requests.post(url, files=files)
    if r.status_code != 200:
        raise Exception(f"IPFS add failed: {r.status_code} {r.text}")
    # response is like: {"Name":"metadata.json","Hash":"Qm...","Size":"..."}
    j = r.json()
    return j.get("Hash")


# ---------------------------
# Helper: optional Ethereum storage (very minimal)
# ---------------------------
def eth_store_cid(cid: str):
    # This is a placeholder. Implementing requires web3, provider, private key and a smart contract.
    # For demo, we will return a fake tx id. In production implement with web3.py or ethers.js.
    return {"status": "not_implemented", "cid": cid}


# ---------------------------
# Run app
# ---------------------------
if __name__ == "__main__":
    app.run(port=5000, debug=True)

#
# pip install flask cryptography requests web3

# IPFS: cách chạy (local) hoặc dùng Infura/Pinata
#
# Local: cài go-ipfs hoặc ipfs package, khởi daemon:
# install ipfs (instructions: https://docs.ipfs.tech/install/)
# ipfs init
# ipfs daemon

# Start IPFS local
# ipfs init
# ipfs daemon &
