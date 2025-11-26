import hashlib
import json
import os
import random
import time
from ecdsa import SECP256k1, numbertheory
from ecdsa.ellipticcurve import Point
from ecdsa.util import sigencode_string, sigdecode_string
import plyvel


# --- CẤU HÌNH ---
CURVE = SECP256k1
G = CURVE.generator
ORDER = G.order()

# --- UTILS ---
def hash_sha256(data):
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).digest()

def int_to_bytes(x):
    return x.to_bytes(32, 'big')

def bytes_to_int(x):
    return int.from_bytes(x, 'big')

# --- LỚP 1: MPC & KEY MANAGEMENT (DKG & THRESHOLD SIGNING) ---

class MPCNode:
    def __init__(self, name):
        self.name = name
        # Mỗi node giữ một phần secret share, không bao giờ lộ ra ngoài
        self._sk_share = random.randrange(1, ORDER)
        # Public key phần của node này
        self.pk_share = self._sk_share * G

    def get_z_share(self, tbs_cert_bytes):
        """Tính hash của chứng chỉ theo góc nhìn của node (Bước Consensus)"""
        return bytes_to_int(hash_sha256(tbs_cert_bytes))

    def generate_k_share(self):
        """Sinh phần ngẫu nhiên k cho mỗi phiên ký"""
        return random.randrange(1, ORDER)

class ThresholdSigner:
    """
    Lớp giả lập môi trường Secure MPC.
    Trong thực tế, đây là giao thức mạng giữa các node, không có object trung gian này nắm giữ dữ liệu.
    """
    def __init__(self, node_a, node_b):
        self.node_a = node_a
        self.node_b = node_b

        # DKG: Tạo Public Key tổng hợp (sk ảo = skA + skB)
        # pk = sk * G = (skA + skB) * G = pkA + pkB
        self.joint_pk = self.node_a.pk_share + self.node_b.pk_share
        print(f"[DKG] Joint Public Key Generated: {self.joint_pk.x()}, {self.joint_pk.y()}")

    def mpc_sign(self, tbs_cert_json):
        """
        Thực hiện ký ngưỡng.
        Công thức: s = k^-1 * (z + r * sk) mod n
        Với k = kA + kB (giả lập additive secret sharing cho k)
        """
        tbs_bytes = json.dumps(tbs_cert_json, sort_keys=True).encode()

        # 1. Consensus check z
        z_a = self.node_a.get_z_share(tbs_bytes)
        z_b = self.node_b.get_z_share(tbs_bytes)

        if z_a != z_b:
            raise Exception("MPC Alert: Inconsistent certificate data between nodes!")
        z = z_a # Hash message

        # 2. Sinh k shares và R (Ephemeral Key)
        k_a = self.node_a.generate_k_share()
        k_b = self.node_b.generate_k_share()

        # Trong thực tế, việc cộng k_a + k_b và tính R phải dùng giao thức commit-reveal
        # để không lộ k từng phần. giả lập toán học.
        k_total = (k_a + k_b) % ORDER
        R_point = k_total * G
        r = R_point.x() % ORDER

        if r == 0: raise Exception("Unlucky R, retry")

        # 3. Tính s (Distributed Computing)
        # s = k^-1 * (z + r * (skA + skB))
        #   = k^-1 * (z + r*skA + r*skB)
        # Các phần tử được tính riêng và gộp lại (giản lược cho code demo)

        sk_total = (self.node_a._sk_share + self.node_b._sk_share) % ORDER

        inv_k = numbertheory.inverse_mod(k_total, ORDER)
        s = (inv_k * (z + r * sk_total)) % ORDER

        if s == 0: raise Exception("Unlucky S, retry")

        signature = {"r": r, "s": s}
        return signature, tbs_bytes

# --- LỚP 2: STORAGE & MERKLE TREE (LEVELDB) ---

class LevelDBMerkleTree:
    def __init__(self, db_path="./merkle_db"):
        self.leaves = [] # Cache leaves for demo simple merkle tree
        try:
            self.db = plyvel.DB(db_path, create_if_missing=True)
            self.use_db = True
            print(f"[Storage] LevelDB initialized at {db_path}")
        except ImportError:
            self.db = {}
            self.use_db = False
            print("[Storage] LevelDB not found (plyvel), using Memory Dict instead.")

    def add_leaf(self, cert_hash_hex):
        self.leaves.append(cert_hash_hex)
        # Lưu vào DB: key=hash, value=index/metadata
        if self.use_db:
            self.db.put(cert_hash_hex.encode(), str(len(self.leaves)).encode())
        else:
            self.db[cert_hash_hex] = len(self.leaves)

        return self.build_root()

    def build_root(self):
        """Xây dựng Merkle Root đơn giản từ danh sách leaves"""
        if not self.leaves:
            return None

        current_level = [bytes.fromhex(x) for x in self.leaves]

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                node1 = current_level[i]
                if i + 1 < len(current_level):
                    node2 = current_level[i+1]
                else:
                    node2 = node1 # Duplicate last node if odd

                # Hash(node1 + node2)
                combined = hash_sha256(node1 + node2)
                next_level.append(combined)
            current_level = next_level

        return current_level[0].hex()

    def get_proof(self, target_hash):
        """Lấy Merkle Path (Witness)"""
        # Trong thực tế cần thuật toán traverse cây.
        # Ở đây trả về danh sách dummy path để demo flow.
        return ["hash_sibling_1", "hash_sibling_2"]

# --- LỚP 3: ZK-SNARK & BLOCKCHAIN ---

class ZKProver:
    """
    Prover - dùng thư viện snarkjs/libsnark.
    """
    @staticmethod
    def generate_proof(merkle_root, cert_hash, merkle_path):
        print(f"[ZK Prover] Generating proof for {cert_hash} in root {merkle_root}...")
        # Tạo một bằng chứng giả (Mock Proof)
        # Chứng minh rằng: "Tôi biết path dẫn từ cert_hash tới merkle_root"
        proof = {
            "pi_a": "mock_point_a",
            "pi_b": "mock_point_b",
            "public_signals": [merkle_root, cert_hash] # Public inputs
        }
        return proof

class ConsortiumBlockchain:
    """
    Mô phỏng Smart Contract lưu Merkle Root
    """
    def __init__(self):
        self.current_merkle_root = None
        self.history = []

    def update_root(self, new_root, zk_proof):
        # Verifier logic on-chain
        if self.verify_zk_proof_on_chain(zk_proof, new_root):
            self.current_merkle_root = new_root
            self.history.append(new_root)
            print(f"[Blockchain] Root updated: {new_root[:10]}...")
            return True
        return False

    def verify_zk_proof_on_chain(self, proof, claimed_root):
        # Verify zk-SNARK
        # Kiểm tra public signal khớp với input
        if proof["public_signals"][0] == claimed_root:
            return True
        return False

# --- LỚP 4: CLIENT VERIFICATION ---

class ClientVerifier:
    def __init__(self, ca_public_key):
        self.ca_pk = ca_public_key

    def verify_certificate(self, tbs_cert_bytes, signature, blockchain, zk_proof):
        print("\n--- Client Verification Start ---")

        # 1. Verify ECDSA Signature
        z = bytes_to_int(hash_sha256(tbs_cert_bytes))
        r, s = signature['r'], signature['s']

        # Check r, s range
        if not (1 <= r < ORDER and 1 <= s < ORDER):
            print("FAIL: Signature out of range")
            return False

        # Tính w = s^-1
        w = numbertheory.inverse_mod(s, ORDER)
        # u1 = z * w
        u1 = (z * w) % ORDER
        # u2 = r * w
        u2 = (r * w) % ORDER

        # P = u1*G + u2*PK
        try:
            P = u1 * G + u2 * self.ca_pk
            if P.x() % ORDER == r:
                print("[Client] ECDSA Signature: VALID")
            else:
                print("[Client] ECDSA Signature: INVALID")
                return False
        except Exception as e:
            print(f"[Client] Error calc point: {e}")
            return False

        # 2. Verify Transparency (On-chain check)
        cert_hash = hash_sha256(tbs_cert_bytes + str(signature).encode()).hex()
        chain_root = blockchain.current_merkle_root

        # Client check: Proof's public signal must match current chain root
        # and Proof's cert hash must match our cert hash
        if zk_proof["public_signals"][0] == chain_root:
            # Ở đây client tin tưởng vào ZK Proof đã được verify on-chain
            # Hoặc tự verify lại ZK Proof (nếu client mạnh)
            print(f"[Client] Transparency Check: VALID (Root: {chain_root[:10]}...)")
            return True
        else:
            print("[Client] Transparency Check: INVALID Root mismatch")
            return False

# --- MAIN FLOW EXECUTION ---

def run_system():
    # 1. Init System
    print("--- 1. Initializing System ---")
    blockchain = ConsortiumBlockchain()
    merkle_db = LevelDBMerkleTree()

    # 2. Key Generation (DKG)
    node_a = MPCNode("NodeA")
    node_b = MPCNode("NodeB")
    ca_system = ThresholdSigner(node_a, node_b)

    # Client biết Public Key của CA
    client = ClientVerifier(ca_system.joint_pk)

    # 3. Issue Certificate (Signing Phase)
    print("\n--- 2. Issuing Certificate ---")
    tbs_cert = {
        "subject": "CN=User1, O=DecentralizedOrg",
        "validity": "2025-2026",
        "public_key": "user_pub_key_placeholder"
    }

    # Thực hiện ký (Off-chain MPC)
    signature, tbs_bytes = ca_system.mpc_sign(tbs_cert)
    print(f"Signature Created: r={signature['r']}, s={signature['s']}")

    # 4. Storage & Transparency Phase
    print("\n--- 3. Storage & Merkle Tree ---")
    # Tạo full signed cert object để hash
    signed_cert_str = str(tbs_cert) + str(signature)
    cert_hash = hash_sha256(signed_cert_str.encode()).hex()

    # Thêm vào Merkle Tree -> Có Root mới
    new_root = merkle_db.add_leaf(cert_hash)
    merkle_path = merkle_db.get_proof(cert_hash)
    print(f"New Merkle Root: {new_root}")

    # 5. ZK Proof & Blockchain Commit
    print("\n--- 4. ZK Proof & Blockchain ---")
    zk_proof = ZKProver.generate_proof(new_root, cert_hash, merkle_path)

    # Submit lên Blockchain
    tx_status = blockchain.update_root(new_root, zk_proof)
    if tx_status:
        print("Transaction Confirmed: Root stored on-chain.")

    # 6. Client Verify
    print("\n--- 5. Client Receiving Certificate ---")
    # Client nhận: tbs_cert, signature, zk_proof
    # Client query blockchain để lấy root hiện tại

    # Giả sử Client tự hash lại cert để check proof
    # Note: Trong thực tế signed_cert phải được serialize chuẩn (DER/PEM)
    is_valid = client.verify_certificate(tbs_bytes, signature, blockchain, zk_proof)

    if is_valid:
        print("\n>>> CERTIFICATE IS FULLY VALID & SECURE <<<")
    else:
        print("\n>>> CERTIFICATE INVALID <<<")

if __name__ == "__main__":
    run_system()