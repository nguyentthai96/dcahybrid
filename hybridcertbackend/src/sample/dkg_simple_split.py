from ecdsa import SigningKey, VerifyingKey, NIST256p
from secretsharing import SecretSharer
import hashlib

# ----------------------------
# 1. DKG: tạo key và chia secret
# ----------------------------

# tạo master private key
sk = SigningKey.generate(curve=NIST256p)
private_key_int = sk.privkey.secret_multiplier

# chuyển private key thành hex string
secret_hex = hex(private_key_int)[2:]

# chia thành 3 phần, threshold t=2
shares = SecretSharer.split_secret(secret_hex, 2, 3)
print("Secret shares for 3 parties:")
for i, s in enumerate(shares):
    print(f"Party {i+1}: {s}")

# ----------------------------
# 2. Threshold Signing: combine t=2 shares để ký
# ----------------------------

# giả sử Party 1 và Party 2 hợp tác để ký
subset_shares = shares[:2]

# reconstruct private key
reconstructed_secret = SecretSharer.recover_secret(subset_shares)
reconstructed_int = int(reconstructed_secret, 16)
assert reconstructed_int == private_key_int

# tạo SigningKey từ reconstructed_int
sk_reconstructed = SigningKey.from_secret_exponent(reconstructed_int, curve=NIST256p)

# ----------------------------
# 3. Tạo TBSCertificate và ký
# ----------------------------
tbs_certificate = b"""
-----BEGIN CERTIFICATE-----
MIIB...example certificate...
-----END CERTIFICATE-----
"""

# hash TBSCertificate
digest = hashlib.sha256(tbs_certificate).digest()

# tạo signature
signature = sk_reconstructed.sign_digest(digest)
print("\nThreshold ECDSA signature (simulated) for TBSCertificate:")
print(signature.hex())

# ----------------------------
# 4. Verify
# ----------------------------
vk = sk.get_verifying_key()
assert vk.verify_digest(signature, digest)
print("\nSignature verified!")




















""" 

Threshold Signature Scheme, for ECDSA and EDDSA
https://github.com/bnb-chain/tss-lib
Rust implementation of {t,n}-threshold ECDSA (elliptic curve digital signature algorithm).
https://github.com/ZenGo-X/multi-party-ecdsa



KHONG THANH CONG

from petre_tss import DKG, ThresholdSigner, ThresholdVerifier
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
# Step 3: Verification (anyone)
# ======================
verifier = ThresholdVerifier(pubkey)
assert verifier.verify(file_hash, threshold_signature)
print("Signature valid")



# ======================
# ======================
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
sudo apt install build-essential rustup pkg-config

sudo apt install python3 python3-pip python3-venv
sudo apt install libssl-dev

curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env


Check 
rustc --version
cargo --version


export CARGO_BUILD_JOBS=$(nproc)
pip install petre-tss

python3 -c "import petre_tss; print('petre-tss OK')"



# Fix error SSL
sudo apt install -y libssl3 libssl-dev
export OPENSSL_DIR="/usr/lib/ssl"
export OPENSSL_INCLUDE_DIR="/usr/include/openssl"

# Error Rust nightly
rustup default stable
"""