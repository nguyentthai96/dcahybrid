from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib, json, os, base64
from ecdsa import SigningKey, NIST256p, VerifyingKey, BadSignatureError
import subprocess, shlex
from nacl import signing
from nacl.signing import VerifyKey
from jwcrypto import jwk

app = Flask(__name__)
CORS(app)  # This allows all origins by default

# tạo key giả lập (có thể thay bằng gen từ decentralizedca)
# sk = SigningKey.generate(curve=NIST256p) # ECDSA
# vk = sk.get_verifying_key()
sk = signing.SigningKey.generate() # Ed25519
vk = sk.verify_key #  Ed25519

protocol_cert = "yao"
#
# subprocess.run(["./a.out", "7000", "--", protocol_cert, "signCert"], cwd="backend/dca")
# proc = subprocess.run(["./a.out", "7001", "localhost", protocol_cert, "signCert"],
#                       cwd="backend/dca",
#                       capture_output=True, text=True, timeout=120
#                       )
# out = proc.stdout


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


@app.route("/sign", methods=["POST"])
def sign_file():
    f = request.files["file"]
    data = f.read()
    file_hash = hashlib.sha256(data).digest()
    # Generate NEW keypair every signing
    # sk = SigningKey.generate(curve=NIST256p)   Ed25519
    # vk = sk.get_verifying_key()
    # Ed25519 keypair
    sk = signing.SigningKey.generate()
    vk = sk.verify_key
    # Sign hash
    # signature = sk.sign(file_hash) # Ed25519
    signature = sk.sign(file_hash).signature
    return jsonify({
        "hash": base64.b64encode(file_hash).decode(),
        "signature": base64.b64encode(signature).decode(),
        # "pubkey": base64.b64encode(vk.to_string()).decode() # Ed25519
        "pubkey": base64.b64encode(vk.encode()).decode()
    })

# JWK = JSON Web Key (chuẩn của IETF RFC 7517)
def vk_to_jwk(vk):
    x, y = vk.to_string()[:32], vk.to_string()[32:]
    return {
        "kty": "EC",
        "crv": "P-256",
        "x": base64.urlsafe_b64encode(x).decode().rstrip("="),
        "y": base64.urlsafe_b64encode(y).decode().rstrip("=")
    }

@app.route("/verify", methods=["POST"])
def verify_file():
    # pubkey = VerifyingKey.from_string(base64.b64decode(request.form["pubkey"]), curve=NIST256p) # Ed25519
    pubkey = base64.b64decode(request.form["pubkey"])
    signature = base64.b64decode(request.form["signature"])
    #
    f = request.files["file"]
    data = f.read()
    file_hash = hashlib.sha256(data).digest()
    try:
        # valid = pubkey.verify(signature, file_hash) # Ed25519
        valid = VerifyKey(pubkey).verify(file_hash, signature)
        return jsonify({"valid": True})
    except BadSignatureError:
        valid = False
    return jsonify({"valid": valid})

def encode_b64(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

@app.route("/did/ed25519")
def did_ed25519():
    sk = signing.SigningKey.generate()
    vk = sk.verify_key

    pub = vk.encode()

    # DID:key format (multibase, multicodec)
    did = "did:key:z" + base58.b58encode(b"\xed" + pub).decode()

    jwk = {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": encode_b64(pub)
    }

    did_doc = {
        "@context": "https://www.w3.org/ns/did/v1",
        "id": did,
        "verificationMethod": [{
            "id": did + "#key-1",
            "type": "JsonWebKey2020",
            "controller": did,
            "publicKeyJwk": jwk
        }]
    }

    return jsonify({
        "keypair": {
            "privateKey": encode_b64(sk.encode()),
            "publicKey": encode_b64(pub)
        },
        "jwk": jwk,
        "didDocument": did_doc
    })

if __name__ == "__main__":
    app.run(port=5000, debug=True)
