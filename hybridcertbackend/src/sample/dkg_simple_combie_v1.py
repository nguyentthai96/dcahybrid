import base64
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature, decode_dss_signature

import nacl
from ecdsa import SECP256k1, ellipticcurve, numbertheory
from ecdsa.ellipticcurve import INFINITY, Point
import hashlib
import secrets

curve = SECP256k1
G = curve.generator
n = curve.order

# ----------------------------------------------------
# 1. DKG: mỗi party tự sinh secret share riêng s_i
t = 2
n_parties = 3
# ----------------------------------------------------
shares = [secrets.randbelow(n) for _ in range(n_parties)]
print("Private shares:", shares)
"""
    s1 = secrets.randbelow(n)
    s3 = secrets.randbelow(n)
    print("Party shares:", s1, s2, s3)
"""

# Public key chung Q (không bao giờ có private key chung s)
#    Q = (s1 * G) + (s2 * G) + (s3 * G)
#    print("\nJoint Public Key Q = (s1+s2+s3)*G  Q =", Q)
# --------------------------
# 2. Tính joint public key Q
# --------------------------
"""
Q = INFINITY
for s in shares:
    Q = Q + s * G  # cộng từng point, luôn hợp lệ
"""
Q = sum([s * G for s in shares], INFINITY)  # cộng các điểm  # khởi tạo bằng point vô cực
print("Joint public key Q:", Q)

# ----------------------------------------------------
# 2. Mỗi party tạo nonce riêng r_i (nonce = key tạm)
"""
    r1 = secrets.randbelow(n)
    r3 = secrets.randbelow(n)
    
    R = (r1 * G) + (r2 * G) + (r3 * G)
    print("\nJoint Nonce R = (r1+r2+r3)*G")
    print("R =", R)
"""
# ----------------------------------------------------
nonces = [secrets.randbelow(n) for _ in range(n_parties)]
# Linear addition → phù hợp với Schnorr/EdDSA.  sum([r*G for r in nonces], INFINITY)
R = sum([r * G for r in nonces], INFINITY)  # Point(curve.curve, Q.x(), Q.y()) # khởi tạo bằng point Q = INFINITY vô cực
r = R.x() % n
print("Joint nonce R:", R)

# ----------------------------------------------------
# 3. Hash message + R + Q
# ----------------------------------------------------
# --------- Hash file PDF hoặc ảnh ---------
file_path = "sample.pdf"  # có thể thay bằng .jpg, .png
file_data = file_path.encode("utf-8")  # simulate file data
# Hash = SHA256(R.x + Q.x + file_data)  ========================
msg_hash = hashlib.sha256(
    R.x().to_bytes(32, "big") +
    Q.x().to_bytes(32, "big") +
    hashlib.sha256(file_data).digest()
                          ).digest()
# msg_hash = hashlib.sha256(file_data).digest()  # h hash data for z1 = (r1 + h * s1) % n
h = int.from_bytes(msg_hash, "big") % n  # message as integer

# ----------------------------------------------------
# 4. Mỗi party tạo partial signature z_i = r_i + h*s_i
"""
    z1 = (r1 + h * s1) % n
    z2 = (r2 + h * s2) % n
    z3 = (r3 + h * s3) % n
"""
# ----------------------------------------------------
partials = [(r + h * s) % n for r, s in zip(nonces, shares)]  # get (r,s) public shares --> s is sk
print("Partial Schnorr signatures:", partials)


# ----------------------------------------------------
# 5. Combine partial signatures (không cần private key)
# ----------------------------------------------------
z = sum(partials) % n
"""S = 0
for z in partials:
    S = (S + z) % L"""
print("Final signature z:", z)





# region -------- FORMAT ECDSA-style threshold   -- khong nen dung ECDSA threshold khó hơn Schnorr
# r = R.x % n (ECDSA-style)
s = z % n
signatureECDSA = (r, s)
print("ECDSA signature:", signatureECDSA)
print("ECDSA signature:", base64.b64encode(encode_dss_signature(r, s)).decode())

# -------------------- Signature standard to verify easy than
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from nacl.signing import VerifyKey
from cryptography.exceptions import InvalidSignature

signatureECDSA_easy_verify = encode_dss_signature(r, s)
#
# 1) Tạo public_key (cryptography) từ  combie public key
pub_numbers = ec.EllipticCurvePublicNumbers(Q.x(), Q.y(), ec.SECP256K1())
public_key = pub_numbers.public_key(default_backend())

from cryptography.hazmat.primitives import hashes
# 2) Verify ECDSA (signature_der phải là encode_dss_signature(r, s))
try:
    r, s = decode_dss_signature(signatureECDSA_easy_verify)
    msg_hash = hashlib.sha256(
        R.x().to_bytes(32, "big") +
        Q.x().to_bytes(32, "big") +
        hashlib.sha256(file_data).digest()
    ).digest()
    h = int.from_bytes(msg_hash, "big") % n
    print("Verification result:", s*G == R + h*Q)

except InvalidSignature as exception:
    print(exception)
    print("ECDSA verify: INVALID")
except Exception as exception:
    print(exception)
    print("ECDSA verify: Exception")

# VerifyKey(public_key).verify(msg_hash, signatureECDSA_easy_verify)
# --------- 6. Verification ---------
# Verify: s*G == R + h*Q (Schnorr verification)
left = s * G
right = R + h * Q
print("Verification result:", left == right)
"""
r là x-coordinate của joint nonce R modulo n
s là tổng partial signature modulo n
Kiểm tra vẫn dựa trên Schnorr-style vì đây là threshold ECDSA approximation

Save stored signature in TBSCertificate:
TBSCertificate["signature"] = {
    "alg": "ECDSA-threshold",
    "r": r,
    "s": s
}
"""
# endregion -------- FORMAT ECDSA-style threshold   -- khong nen dung ECDSA threshold khó hơn Schnorr

# -------- FORMAT EdDSA-style (Ed25519, 64-byte signature)  NEN DUNG
# EdDSA chuẩn (Ed25519) khác:
# Private key: 32 bytes
# Public key: 32 bytes
# Signature: 64 bytes (R 32 bytes + S 32 bytes)
# R: 32-byte nonce point
R_bytes = R.x().to_bytes(32, "big")
# S: aggregated partial signature
S_bytes = z.to_bytes(32, "big")
signatureEdDSA = R_bytes + S_bytes
print("EdDSA-style signature (64 bytes) hex:", signatureEdDSA.hex())
print("EdDSA-style signature (64 bytes):", base64.b64encode(signatureEdDSA).decode())
"""
TBSCertificate["signature"] = {
    "alg": "EdDSA-threshold",
    "signatureAlg": "EdDSA-threshold",
    "subjectPublicKeyInfo": {
        "signatureAlg": "ed25519",
        "publicKey": base64.b64encode(S_bytes).decode()
    }
    "signature": eddsa_signature.hex()
}
"""


# --------- 6. Verification ---------
print("\nVerification\n Final Schnorr signature:")
print("R.x =", R.x())
print("z   =", z)

# ----------------------------------------------------
# 6. Verify: z*G == R + h*Q ?
# ----------------------------------------------------
left = z * G
right = R + h * Q
print("Verification result:", left == right)

# --------- 7. TBSCertificate mockup (bản khai public key) ---------
TBSCertificate = {
    "version": 3,
    "serialNumber": 1,
    "signatureAlg": "Schnorr-MP",
    "issuer": {
        "CN": "Decentralized CA",
        "O": "ConsortiumOrg",
    },
    "validity": {
        "notBefore": "2025-01-01T00:00:00Z",
        "notAfter": "2030-01-01T00:00:00Z"
    },
    "subject": {
        "CN": "User or File Signer",
        "O": "Client Org",
    },
    "subjectPublicKeyInfo": {
        "curve": "SECP256k1",
        "Qx": Q.x(),
        "Qy": Q.y()
    },
    # "issuerUniqueID": None,
    # "subjectUniqueID": None,
}


print("TBSCertificate (public key info only) : ", TBSCertificate)
#
TBSCertificate_EdSA = TBSCertificate
TBSCertificate_EdSA["signatureAlg"] = "ed25519-sha256"
TBSCertificate_EdSA["subjectPublicKeyInfo"] = {
    "signatureAlg": "ed25519",
    "publicKey": base64.b64encode(S_bytes).decode(),
    "Q": {  # joint public key
        "x": str(Q.x()),
        "y": str(Q.y())
    },
    "R": {  # joint nonce
        "x": str(R.x()),
        "y": str(R.y())
    },
}
TBSCertificate_EdSA["signature"] = base64.b64encode(signatureEdDSA).decode()
print("TBSCertificate EdDSA-style : ", TBSCertificate_EdSA)

#
#
TBSCertificate_ECDSA = TBSCertificate
TBSCertificate_ECDSA["signatureAlg"] = "ecdsa-secp256k1-sha256"
TBSCertificate_ECDSA["subjectPublicKeyInfo"] = {
    "algorithm": "ecdsa-secp256k1",
    "curve": "secp256k1",
    "publicKey": {
        "x": R.x(),  # 32-byte hex x coordinate
        "y": R.y()   # 32-byte hex y coordinate
    }
}
print("TBSCertificate ECDSA-style threshold : ", TBSCertificate_EdSA)




from ecdsa import SigningKey, NIST256p, VerifyingKey, BadSignatureError
pubkey = base64.b64decode("vvAfV6nL+BQ72ljdTgOw5pirIWcXza2zIH1LtN6R8J4=")
signature = base64.b64decode("z5dnWIUU7+UcBIFEEqeoQFtdCx8ep0rwESu75bXQQIzQSCOhIVt708EsvjjIxYhX6+1DZmOAvnxx22pO62aeBA==")
file_hash = base64.b64decode("En8X3SLDOUqn38gfiUbUqgBbaMP0qIlmryjj1pXkYYQ=")

# pubkey = base64.b64decode(base64.b64encode(S_bytes).decode())
# signatureECDSA = base64.b64decode(base64.b64encode(signatureEdDSA).decode())
# file_hash = base64.b64decode(base64.b64encode(msg_hash).decode())
# file_hash = msg_hash
try:
    valid = VerifyKey(pubkey).verify(file_hash, signature)
    print("Valid signature:", valid)
except BadSignatureError:
    print("Invalid signature")
