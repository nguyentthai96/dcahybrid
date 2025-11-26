import hashlib
import secrets
from ecdsa import SECP256k1, numbertheory
from ecdsa.ellipticcurve import INFINITY

# --- Cấu hình Curve SECP256k1 ---
curve = SECP256k1
G = curve.generator
n = curve.order

# ==========================================
# 1. CÁC HÀM TOÁN HỌC BỔ TRỢ (LAGRANGE)
# ==========================================

def lagrange_coefficient(i, all_indices, x=0):
    """
    Tính hệ số Lagrange cho party i tại điểm x (mặc định x=0 để khôi phục secret tại 0)
    L_i(x) = product((x - j) / (i - j)) for j in all_indices if j != i
    """
    num, den = 1, 1
    for j in all_indices:
        if j != i:
            num = (num * (x - j)) % n
            den = (den * (i - j)) % n
    return (num * numbertheory.inverse_mod(den, n)) % n

# ==========================================
# 2. GIAI ĐOẠN DKG (SETUP)
# Trusted Dealer chia sẻ key (thực tế dùng giao thức Feldman VSS)
# ==========================================

print("--- 1. DKG SETUP ---")
threshold = 2
total_parties = 3
party_indices = [1, 2, 3] # ID của các node

# Secret polynomial f(x) = secret + a1*x. (bậc 1 cho threshold 2)
# Private key tổng (Master Secret) là f(0) - KHÔNG AI ĐƯỢC GIỮ CÁI NÀY
master_secret = secrets.randbelow(n)
poly_coeff_1 = secrets.randbelow(n)

def polynomial(x):
    return (master_secret + poly_coeff_1 * x) % n

# Mỗi party giữ một share (x, f(x))
shares = {i: polynomial(i) for i in party_indices}

print(f"Master Secret (Test only): {master_secret}")
print(f"Shares phân tán: {shares}")

# Tính Joint Public Key từ các Public Shares (minh bạch)
# Q = Sum( share_i * G * Lagrange_i )
# Giả sử party 1 và 2 tham gia tính Q (hoặc bất kỳ tập t node nào)
subset = [1, 2]
Q = INFINITY
for i in subset:
    lambda_i = lagrange_coefficient(i, subset)
    # Public share của party i
    pub_share_i = shares[i] * G
    Q = Q + lambda_i * pub_share_i

print(f"Joint Public Key Q: ({hex(Q.x())}, {hex(Q.y())})")

# Verify Q khớp với master secret
assert Q == master_secret * G
print(">> DKG Public Key khớp!")


# ==========================================
# 3. SIGNING PROCESS (THRESHOLD SCHNORR)
# Client gửi file hash cần ký
# ==========================================
print("\n--- 2. SIGNING ---")

msg_data = b"Certificate: User ID 12345 - Verified"
print(f"Message: {msg_data}")

# BƯỚC 3.1: Tạo Nonce phân tán
# Mỗi party tạo nonce random k_i và cam kết R_i = k_i * G
signers = [1, 3] # Giả sử node 1 và 3 thực hiện ký
nonces = {}
R_commitments = {}

for i in signers:
    k_i = secrets.randbelow(n)
    nonces[i] = k_i
    R_commitments[i] = k_i * G

# Tổng hợp Joint Nonce Commitment R
# R = R1 + R3
R_joint = sum(R_commitments.values(), INFINITY)
print(f"Joint Nonce R: ({hex(R_joint.x())}, {hex(R_joint.y())})")

# BƯỚC 3.2: Tính Challenge Hash (Schnorr Challenge)
# e = Hash(R_x || Q_x || Message)
def schnorr_hash(R_point, Q_point, msg):
    # Chỉ lấy tọa độ x để tối ưu storage (BIP340 optimization)
    data = (R_point.x().to_bytes(32, 'big') +
            Q_point.x().to_bytes(32, 'big') +
            msg)
    digest = hashlib.sha256(data).digest()
    return int.from_bytes(digest, 'big') % n

e = schnorr_hash(R_joint, Q, msg_data)
print(f"Challenge e: {hex(e)}")

# BƯỚC 3.3: Partial Signatures
# Mỗi node tính: s_i = k_i + e * share_i * Lagrange_coeff_i
partial_sigs = []

for i in signers:
    lambda_i = lagrange_coefficient(i, signers) # Hệ số nội suy cho tập signer hiện tại
    s_i = (nonces[i] + e * lambda_i * shares[i]) % n
    partial_sigs.append(s_i)
    print(f"Node {i} partial sig: {s_i}")

# BƯỚC 3.4: Combine Signature
# S = Sum(s_i)
S_final = sum(partial_sigs) % n
signature = (R_joint, S_final)

print(f"Final Signature (R, s): \nR_x: {hex(R_joint.x())}\ns: {hex(S_final)}")

# Định dạng Compressed Public Key (thường dùng trong blockchain):
# Prefix 02 (nếu y chẵn) hoặc 03 (nếu y lẻ) + 32 bytes x
prefix = b'\x02' if Q.y() % 2 == 0 else b'\x03'
pubkey_bytes = prefix + Q.x().to_bytes(32, 'big')
pubkey_hex = pubkey_bytes.hex()
print(f"Public Key (Hex): {pubkey_hex}")

# 2. Export Signature (R_x, s)
# Signature = R.x (32 bytes) + s (32 bytes) -> Tổng 64 bytes
r_bytes = R_joint.x().to_bytes(32, 'big')
s_bytes = S_final.to_bytes(32, 'big')
signature_hex = (r_bytes + s_bytes).hex()
print(f"Signature (Hex):  {signature_hex}")

# 3. Export Message
print(f"Message (Raw):    {msg_data.decode('utf-8')}")
print(f"Message (Hex):    {msg_data.hex()}")

# ==========================================
# 4. VERIFICATION (CLIENT SIDE)
# Client chỉ cần biết: Q, Message, Signature (R, s)
# ==========================================
print("\n--- 3. VERIFICATION ---")

def verify_schnorr(Q, R, s, msg):
    # 1. Recompute challenge e
    e = schnorr_hash(R, Q, msg)

    # 2. Check equation: s * G = R + e * Q
    P1 = s * G
    P2 = R + e * Q

    return P1 == P2

is_valid = verify_schnorr(Q, signature[0], signature[1], msg_data)
print(f"Signature Valid? -> {is_valid}")

if is_valid:
    print(">> Certificate hợp lệ, được ký bởi Threshold CA.")
else:
    print(">> Chữ ký giả mạo!")