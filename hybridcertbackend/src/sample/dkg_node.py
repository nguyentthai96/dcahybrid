import hashlib
import base64
from flask import Flask, request, jsonify
# from threshold_lib import DKGNode, ThresholdSigner

app = Flask(__name__)


"""
# ======================
# Step 1: DKG setup (run once)
# ======================
# Node A và Node B chạy DKG để tạo shared key
dkg_a = DKG(node_id="A", nodes=["A","B"], threshold=2)
dkg_b = DKG(node_id="B", nodes=["A","B"], threshold=2)

# Exchange DKG messages (over network)
dkg_a_messages = dkg_a.generate_messages()
dkg_b_messages = dkg_b.generate_messages()
dkg_a.receive_messages([dkg_b_messages])
dkg_b.receive_messages([dkg_a_messages])

# Node A và B có private shares riêng, public key chung
pubkey = dkg_a.get_public_key()  # same as dkg_b.get_public_key()

# ======================
# Step 2: Signing flow (file submitted by A, approved by B)
# ======================
file_data = open("image.png","rb").read()
file_hash = hash(file_data)  # e.g., SHA256

# Node A: sign share
sig_share_a = dkg_a.sign_share(file_hash)

# Node B: sign share
sig_share_b = dkg_b.sign_share(file_hash)

# Combine signatures to full threshold signature
threshold_signature = dkg_a.combine_shares([sig_share_a, sig_share_b])

# ======================
"""

# Initialize node
NODE_ID = "A"   # hoặc B
PEERS = ["A", "B"]  # full list
THRESHOLD = 2

dkg = DKGNode(node_id=NODE_ID, nodes=PEERS, threshold=THRESHOLD)
signer = None  # chỉ tạo sau khi DKG xong


# =========================
# 1. Receive DKG message
# =========================
@app.route("/dkg/message", methods=["POST"])
def dkg_message():
    msg = request.json
    dkg.receive_message(msg)
    return jsonify({"status": "ok"})


# =========================
# 2. Start DKG rounds
# =========================
@app.route("/dkg/start", methods=["POST"])
def dkg_start():
    msgs = dkg.generate_round_messages()
    # Caller phải gửi messages này sang các peer
    return jsonify({"messages": msgs})


# =========================
# 3. Query DKG status
# =========================
@app.route("/dkg/status", methods=["GET"])
def dkg_status():
    if dkg.is_finished():
        global signer
        if signer is None:
            signer = ThresholdSigner(dkg.private_share, dkg.public_key)
        return jsonify({
            "status": "done",
            "pubkey": dkg.public_key
        })
    return jsonify({"status": "in-progress"})


# =========================
# 4. Generate signing share
# =========================
@app.route("/sign/share", methods=["POST"])
def sign_share():
    content = request.json
    file_hash_b64 = content["hash"]
    file_hash = base64.b64decode(file_hash_b64)

    if signer is None:
        return jsonify({"error": "DKG not completed"}), 400

    # Generate threshold signature share
    sig_share = signer.sign_share(file_hash)

    return jsonify({
        "node": NODE_ID,
        "hash": file_hash_b64,
        "sig_share": base64.b64encode(sig_share).decode()
    })
