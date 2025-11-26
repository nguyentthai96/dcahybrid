from datetime import datetime, timezone
import hashlib
import os
import json
import hashlib
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from ecdsa import SECP256k1, numbertheory
from ecdsa.util import sigencode_string, sigdecode_string
from ecdsa import VerifyingKey, SECP256k1
from cryptography.hazmat.primitives.asymmetric.utils import (
    encode_dss_signature, decode_dss_signature
)
from LevelDBMerkleTree import LevelDBMerkleTree
from LevelDBMerkleTreePymerkle import LevelDBMerkleTreePymerkle
from MPCNode import MPCNode
from ecdsa import SECP256k1

from blockchain_manager import HardhatClient

CURVE = SECP256k1
G = CURVE.generator
ORDER = G.order()

import subprocess
import json
import os


# Thêm hàm tiện ích convert Hex/String sang BigInt String cho Circom
def to_bigint_string(val):
    if isinstance(val, str):
        # Nếu là hex (0x...)
        if val.startswith("0x"):
            return str(int(val, 16))
        # Nếu là string thường, convert sang int từ bytes
        else:
            return str(int.from_bytes(val.encode(), 'big'))
    elif isinstance(val, bytes):
        return str(int.from_bytes(val, 'big'))
    return str(val)


def hash_sha256(data_bytes):
    return hashlib.sha256(data_bytes).digest()

def canonicalize_tbs(tbs: dict) -> bytes:
    # Deterministic JSON serialization: sort keys, ensure separators, utf-8
    return json.dumps(tbs, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

def build_cert_full_bytes(tbs_bytes: bytes, signature_der: bytes) -> bytes:
    # domain separators: 0x10 for tbs, 0x30 for cert concat (example)
    return b'\x10' + tbs_bytes + b'\xFF' + signature_der

def compute_cert_full_hash(tbs_bytes: bytes, signature_der: bytes) -> str:
    return hash_sha256(build_cert_full_bytes(tbs_bytes, signature_der)).hex()


class DecentralizedCA:
    def __init__(self):
        # 1. Init MPC Nodes
        self.node_a = MPCNode("NodeA")
        self.node_b = MPCNode("NodeB")
        self.node_c = MPCNode("NodeC")
        # Joint PK = pkA + pkB
        self.joint_pk_point = self.node_a.pk_share + self.node_b.pk_share

        # Convert to VerifyingKey
        self.joint_vk = VerifyingKey.from_public_point(self.joint_pk_point, curve=SECP256k1)
        print(f"[SYSTEM] CA Initialized. Public Key: {self.joint_vk.to_string('compressed').hex()}")
        # 2. Khởi tạo Storage (Thay thế List RAM bằng LevelDB)
        # Dữ liệu sẽ được lưu bền vững vào thư mục './merkle_db'
        self.merkle_tree = LevelDBMerkleTree("./merkle_db")
        print(f"[Storage] LevelDB loaded. Current Root: {self.merkle_tree.get_root()}")
        self.merkle_root = self.merkle_tree.get_root()

        # 3. Khởi tạo Blockchain Interface (Hardhat)
        self.chain_client = None
        try:
            self.chain_client = HardhatClient()
            # Tự động deploy contract nếu chưa có (hoặc load address từ config)
            if not self.chain_client.contract_address:
                self.chain_client.deploy_contract()
            print("[Blockchain] Connected to Hardhat.")
        except Exception as e:
            print(f"[WARNING] Không thể kết nối Blockchain (Hardhat): {e}")
            print("Hệ thống sẽ chạy ở chế độ Offline (chỉ lưu DB, không commit on-chain).")

    def get_public_key_hex(self):
        return self.joint_vk.to_string("compressed").hex()

    def build_merkle_root(self):
        if not self.merkle_leaves: return None
        current_level = [bytes.fromhex(x) for x in self.merkle_leaves]
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                n1 = current_level[i]
                n2 = current_level[i + 1] if i + 1 < len(current_level) else n1
                next_level.append(hash_sha256(n1 + n2))
            current_level = next_level
        self.merkle_root = current_level[0].hex()
        return self.merkle_root

    def generate_real_zk_proof(self, secret_data):
        """
        Gọi snarkjs để tạo bằng chứng sự thật.
        secret_data: Dữ liệu bí mật (filehash: nội dung chứng chỉ)
        """
        print("[ZK] Đang sinh bằng chứng Zero-Knowledge...")

        # 1. Chuẩn bị Input cho Circuit (file input.json)
        # Poseidon hash trong Circom nhận số Decimal string
        secret_int_str = to_bigint_string(secret_data)

        # Ở bước này, tính Public Hash bằng Python logic tương tự Poseidon
        # NHƯNG để đơn giản cho demo, ta sẽ dùng Nodejs tính hash và tạo proof luôn.
        # Hoặc dùng thư viện python 'poseidon' (nhưng khó cài).
        # Cách dễ nhất: Để Circom tự tính hash, ta chỉ cần đưa secret vào.

        # Trong thực tế, public_hash phải lấy từ Blockchain về.
        # Để demo chạy được mạch, ta cần một con số khớp.
        # Mẹo: Ta chạy script nodejs để tính hash Poseidon của secret trước.

        input_data = {
            "secret": secret_int_str,
            "public_hash": "0"  # Placeholder, lát nữa script JS sẽ tính lại cho khớp để pass constraint
        }

        # Đường dẫn (Path)
        zk_dir = "../../hybridzkcircuit"
        input_path = os.path.join(zk_dir, "input.json")
        witness_path = os.path.join(zk_dir, "witness.wtns")
        proof_path = os.path.join(zk_dir, "proof.json")
        public_path = os.path.join(zk_dir, "public.json")

        # Ghi file input
        with open(input_path, "w") as f:
            json.dump(input_data, f)

        try:
            # 2. Tính Witness (nhờ Nodejs script wrapper cho tiện)
            # 'generate_proof.js' Vì ta cần tính Hash Poseidon(secret) để điền vào public_hash cho đúng logic
            script_path =os.path.join(zk_dir, "generate_proof_wrapper.js")
            assert os.path.exists(script_path), "File JS không tồn tại!"
            cmd = ["/home/nguyentthai96/.nvm/versions/node/v22.21.0/bin/node", script_path, secret_int_str]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print("Lỗi sinh proof:", result.stderr)
                return None

            # 3. Đọc kết quả JSON
            with open(proof_path, "r") as f:
                proof_json = json.load(f)

            with open(public_path, "r") as f:
                public_signals = json.load(f)  # Chứa hash poseidon

            print(f"[ZK] Proof sinh thành công! Hash (Poseidon): {public_signals[0]}")

            return {
                "proof": proof_json,
                "public_hash": public_signals[0]  # Đây chính là giá trị cần ghi lên chain
            }

        except Exception as e:
            print(f"Exception ZK: {e}")
            return None

    def sign_file(self, file_bytes, metadata):
        """
        Quy trình: Hash File -> MPC Sign -> LevelDB Store -> ZK Proof -> Blockchain Commit
        """
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 1. Hash file content
        file_hash = hash_sha256(file_bytes)
        # 2. Create TBS (To-Be-Signed) Structure
        tbs_data = {
            "file_hash": file_hash.hex(),
            "subject": "CN=NTT, O=DecentralizedOrg",
            "version": 3,
            "serialNumber": 1,
            "signatureAlg": "ecdsa-secp256k1-sha256",
            "issuer": {
                "CN": "Decentralized CA",
                "O": "ConsortiumOrg",
            },
            "validity": {
                "notBefore": current_time,
                "notAfter": "2025-01-01T00:00:00Z"
            },
            "metadata": metadata,
            "timestamp": current_time
        }
        tbs_json = json.dumps(tbs_data, sort_keys=True)
        z = int.from_bytes(hash_sha256(tbs_json.encode()), 'big')

        # 3. MPC Signing Logic (Tính toán phân tán r, s)
        # k = kA + kB
        k_a = self.node_a.generate_k_share()
        k_b = self.node_b.generate_k_share()
        k_total = (k_a + k_b) % ORDER

        # R point
        R_point = k_total * G
        r = R_point.x() % ORDER

        # s = k^-1 * (z + r*sk_total)
        sk_total = (self.node_a._sk_share + self.node_b._sk_share) % ORDER
        inv_k = numbertheory.inverse_mod(k_total, ORDER)
        s = (inv_k * (z + r * sk_total)) % ORDER

        signature = {"r": hex(r), "s": hex(s)}
        signature_der = encode_dss_signature(r, s)

        # 4. Update Merkle Tree (Sử dụng LevelDB)
        # Hash toàn bộ chứng chỉ (TBS + Signature) để tạo lá
        cert_full_hash = hash_sha256((tbs_json + json.dumps(signature)).encode()).hex()
        # Thêm vào DB và lấy Root mới ngay lập tức
        self.root_merkle = self.merkle_tree.add_leaf(cert_full_hash)

        # 5. Generate ZK Proof (Simplified) & Blockchain Commit
        # Secret ở đây ta lấy ví dụ là file_hash (dạng số)
        # Chứng minh: "Tôi biết file gốc có hash SHA256 này, tương ứng với hash Poseidon trên chain"
        tx_hash = None
        #  gọi snarkjs
        zk_result = self.generate_real_zk_proof(file_hash)
        zk_proof_json_data = "ZK_FAIL"
        zk_public_signals = None
        if zk_result:
            """"
            zk_result -> {
                "proof": proof_json,
                "public_hash": public_signals[0]  # Đây chính là giá trị cần ghi lên chain
            }
            """
            zk_proof_json_data = json.dumps(zk_result['proof'])
            zk_public_signals = zk_result['public_hash']
            # Poseidon dùng cho ZK Verification riêng
        zk_proof = {
            "root": self.root_merkle,
            "status": "VALID_ON_CHAIN" if self.chain_client else "INVALID_ON_CHAIN",
            "proof_data": zk_proof_json_data
        }

        if self.chain_client:
            try:
                # Gửi Root mới lên Blockchain
                tx_hash = self.chain_client.submit_root_on_chain(self.root_merkle, zk_public_signals.encode())
            except Exception as e:
                print(f"Lỗi submit blockchain: {e}")

        return {
            "tbs_data": tbs_data,
            "signature": signature,
            "certificate_hash": cert_full_hash,
            "blockchain_tx": tx_hash,  # Transaction hash để client tra cứu explorer
            "zk_proof":  zk_proof,
            # Privacy-Preserving: Có thể verify chứng chỉ (thông qua Y) mà không cần lộ nội dung chứng chỉ (X) cho người xác thực (Verifier) cho đến khi cần thiết.
        }

    def verify_file(self, file_bytes, cert_json):
        client_tbs_data = cert_json['tbs_data']
        signature = cert_json['signature']
        """
        Verify: Hash File -> Verify ECDSA -> Verify Integrity (LevelDB + Blockchain)
        """
        # 1. Re-construct TBS Check from file and provided metadata
        # Client gửi file lên, server hash file đó để so khớp với hash trong tbs_data
        server_file_hash = hash_sha256(file_bytes).hex()
        if server_file_hash != client_tbs_data["file_hash"]:
            return False, "Nội dung file không khớp với chứng chỉ."

        # 2. Verify ECDSA Signature
        tbs_json = json.dumps(client_tbs_data, sort_keys=True)
        z = int.from_bytes(hash_sha256(tbs_json.encode()), 'big')

        cert_full_hash = hash_sha256((tbs_json + json.dumps(signature)).encode()).hex()
        if (cert_full_hash != cert_json["certificate_hash"]):
            return False, "Nội dung file không khớp với chứng chỉ."
        r = int(signature['r'], 16)
        s = int(signature['s'], 16)

        try:
            # ...  ...
            w = numbertheory.inverse_mod(s, ORDER)
            u1 = (z * w) % ORDER
            u2 = (r * w) % ORDER

            # Reconstruct Point P
            P = u1 * G + u2 * self.joint_pk_point

            if P.x() % ORDER != r:
                return False, "Chữ ký ECDSA không hợp lệ (Toán học sai)."

        except Exception as e:
            return False, f"Lỗi tính toán Verify: {str(e)}"

        # 3. Transparency Check (LevelDB & Blockchain)
        # Check 3.1: Có tồn tại trong DB Off-chain của CA không? Check Merkle Existence (Transparency)
        # Ở đây ta dùng hàm get_merkle_proof để kiểm tra sự tồn tại
        # Hash lại toàn bộ để xem có trong cây không
        merkle_path = self.merkle_tree.get_merkle_proof(cert_full_hash)
        if merkle_path is None: # signature valid, but hash of tbs_data and signal not in DB
            return False, "Chữ ký Hợp lệ nhưng KHÔNG tìm thấy trong Database (Cảnh báo: Có thể là chứng chỉ chui)."

        # Check 3.2: Root hiện tại trên Blockchain có khớp với Root tính từ DB không?
        # (Đây là bước đảm bảo CA không sửa DB sau khi công bố)
        current_db_root = self.merkle_tree.get_root()

        chain_msg = ""
        if self.chain_client and self.chain_client.contract:
            try:
                on_chain_root = self.chain_client.contract.functions.merkleRoot().call()
                # Chuyển bytes32 về hex string (bỏ 0x)
                on_chain_root_hex = on_chain_root.hex()

                # Hardhat thường trả về hex string, ta cần normalize để so sánh
                if on_chain_root_hex.startswith('0x'):
                    on_chain_root_hex = on_chain_root_hex[2:]

                if current_db_root == on_chain_root_hex: # root_merkle db and on-chain
                    chain_msg = " (Đã xác thực khớp với Blockchain)."
                else:
                    chain_msg = f" (CẢNH BÁO: Root trên Blockchain khác với DB. Chain: {on_chain_root_hex[:10]}...)"
            except Exception as e:
                chain_msg = " (Không thể kết nối Blockchain để check Root)."

        return True, f"Chứng chỉ Hợp lệ & Đã được lưu trữ minh bạch{chain_msg}"
