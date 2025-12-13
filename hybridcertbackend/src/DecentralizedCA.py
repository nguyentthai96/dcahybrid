import base64
import traceback
import hashlib
import os
import json
import hashlib
import random
from flask import Flask, request, jsonify
from ecdsa import SECP256k1, numbertheory
from ecdsa.util import sigencode_string, sigdecode_string
from ecdsa import VerifyingKey, SECP256k1
from cryptography.hazmat.primitives.asymmetric.utils import (
    encode_dss_signature, decode_dss_signature
)
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec as _ec
from cryptography.hazmat.primitives import hashes as _hashes

from ecdsa import SECP256k1
import subprocess
import time
from datetime import datetime, timezone, timedelta
from cryptography.x509.oid import NameOID, SignatureAlgorithmOID
from pyasn1.type import univ, namedtype, tag
from pyasn1.codec.der.encoder import encode as der_encode
from pyasn1.codec.der.decoder import decode as der_decode
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import ec

from blockchain_manager import HardhatClient
from LevelDBMerkleTree import LevelDBMerkleTree
from LevelDBMerkleTreePymerkle import LevelDBMerkleTreePymerkle
from MPCNode import MPCNode

CURVE = SECP256k1
G = CURVE.generator
ORDER = G.order()


# ===== Custom ASN.1 Structures for X.509 =====
class AlgorithmIdentifier(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('algorithm', univ.ObjectIdentifier()),
        namedtype.OptionalNamedType('parameters', univ.Null()
                                    # namedtype.OptionalNamedType('parameters', univ.Null().subtype(
                                    #     explicitTag=tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 5)
                                    # )
                                    )
    )


class CertificateASN1(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('tbsCertificate', univ.Any()),
        namedtype.NamedType('signatureAlgorithm', AlgorithmIdentifier()),
        namedtype.NamedType('signatureValue', univ.BitString())
    )


def now_ms():
    return time.time() * 1000


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


def create_tbs_bytes(file_hash, metadata):
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tbs_data = {
        "file_hash": file_hash.hex(),
        "subject": "CN=NTT, O=IT",
        "version": 3,
        "serialNumber": 1,
        "signatureAlg": "ecdsa-secp256k1-sha256",
        "issuer": {
            "CN": "Decentralized CA",
            "O": "ConsortiumOrg",
        },
        "validity": {
            "notBefore": current_time,
            "notAfter": "2030-01-01T00:00:00Z"
        },
        "metadata": metadata,
        "timestamp": time.time()
    }
    tbs_json = json.dumps(tbs_data, sort_keys=True)
    return tbs_json, tbs_json.encode()


class DecentralizedCA:
    def __init__(self):
        self.issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ConsortiumOrg"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Hybrid DCA"),
        ])

        # 1. Init MPC Nodes
        self.node_a = MPCNode("NodeA")
        self.node_b = MPCNode("NodeB")
        self.node_c = MPCNode("NodeC")
        # Joint PK = pkA + pkB; public key of CA
        self.joint_pk_point = self.node_a.pk_share + self.node_b.pk_share

        # Convert to VerifyingKey
        self.joint_vk = VerifyingKey.from_public_point(self.joint_pk_point, curve=SECP256k1)
        print(f"[SYSTEM] CA Initialized. Public Key: {self.joint_vk.to_string('compressed').hex()}")
        self.dca_crt = self.self_signed_certificate()
        self.dca_cert_obj = x509.load_pem_x509_certificate(
            self.dca_crt.encode("utf-8")
        )

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

    def get_public_key_uncompressed_hex(self):
        x = format(self.joint_pk_point.x(), "064x")
        y = format(self.joint_pk_point.y(), "064x")

        return {
            "x963_uncompressed": "04" + x + y,
            # "x963_compressed": ("02" if self.joint_pk_point.y() % 2 == 0 else "03") + x,
            # "x": x,
            # "y": y
        }

    def create_tbs_self_signed_builder(self):
        # 1. Build X.509 TBS Certificate
        # Parse EC public key
        uncompressed_hex = self.get_public_key_uncompressed_hex()['x963_uncompressed']
        pub_bytes = bytes.fromhex(uncompressed_hex)
        public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256K1(), pub_bytes
        )
        builder = x509.CertificateBuilder()
        subject = self.issuer
        builder = builder.subject_name(self.issuer)
        builder = builder.issuer_name(self.issuer)
        issuance_date = datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
        builder = builder.not_valid_before(issuance_date)
        builder = builder.not_valid_after(issuance_date + timedelta(days=3650))  # datetime.datetime.now(datetime.UTC)
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.public_key(public_key)

        builder = builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True
        )
        builder = builder.add_extension(
            x509.SubjectKeyIdentifier.from_public_key(public_key),
            critical=False
        )
        builder = builder.add_extension(
            x509.KeyUsage(
                key_cert_sign=True,
                crl_sign=True,
                digital_signature=False,
                key_encipherment=False,
                key_agreement=False,
                data_encipherment=False,
                content_commitment=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True
        )
        return builder

    # Dùng public key từ DCA để tạo file ca.crt.pem chuẩn X.509, ECDSA-secp256k1-sha256
    def self_signed_certificate(self):
        # 1. Build X.509 TBS Certificate
        # Parse EC public key
        # 2. Build Certificate (Không ký)
        builder = self.create_tbs_self_signed_builder()

        # 3. Tạo TBS bằng ephemeral key
        # ============================
        _ephemeral_priv = _ec.generate_private_key(_ec.SECP256R1())
        _temp_cert = builder.sign(
            private_key=_ephemeral_priv,
            algorithm=_hashes.SHA256()
        )

        # # Lấy TBS (To-Be-Signed)
        tbs_bytes = _temp_cert.tbs_certificate_bytes
        # optionally delete ephemeral key reference
        del _ephemeral_priv
        # 2. MPC Signature (r,s) → ASN.1 ECDSA signature
        # 4. MPC signature cho TBS → r, s
        sig_der, r, s = self.mpc_sign_ecdsa_secp256k1_threshold(tbs_bytes)
        # signature = {"r": hex(r), "s": hex(s)}
        # ---------------------------------------------------
        # (a) Put TBS
        # 5. Build final ASN.1 Certificate
        return build_certificate_asn1(tbs_bytes, sig_der)

    def mpc_sign_ecdsa_secp256k1_threshold(self, tbs_bytes):
        # 2. Create TBS (To-Be-Signed) Structure
        z = int.from_bytes(hash_sha256(tbs_bytes), "big")

        # 3. MPC Signing Logic (Tính toán phân tán r, s)
        # k = kA + kB
        k_a = self.node_a.generate_k_share()
        k_b = self.node_b.generate_k_share()
        k_total = (k_a + k_b) % ORDER

        # R point
        R_point = k_total * G
        r = R_point.x() % ORDER

        # s = k^-1 * (z + r*sk_total)  # sk_total private share key
        sk_total = (self.node_a._sk_share + self.node_b._sk_share) % ORDER
        # print(f"DEBUG [SYSTEM] CA Initialized PRK: {hex(sk_total)[2:]}")
        inv_k = numbertheory.inverse_mod(k_total, ORDER)
        s = (inv_k * (z + r * sk_total)) % ORDER

        # signature = {"r": hex(r), "s": hex(s)}
        sig_der = encode_dss_signature(r, s)

        return sig_der, r, s

    def mpc_verify_ecdsa_secp256k1_threshold(self, tbs_bytes, signature_der):
        z = int.from_bytes(hash_sha256(tbs_bytes), "big")
        """
        r = int(signature['r'], 16)
        s = int(signature['s'], 16)
        """
        r,s = decode_dss_signature(signature_der)
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

    def encode_der_emn178(self, r, s):
        def der_int(x):
            b = x.to_bytes((x.bit_length() + 7) // 8, 'big')
            if b[0] & 0x80:
                b = b'\x00' + b
            return b'\x02' + bytes([len(b)]) + b

        r_der = der_int(r)
        s_der = der_int(s)
        return b'\x30' + bytes([len(r_der + s_der)]) + r_der + s_der

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
            script_path = os.path.join(zk_dir, "generate_proof_wrapper.js")
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

    def sign_issue(self, file_bytes, metadata):
        timing = {}  # lưu thời gian từng giai đoạn (ms)
        t0_total = now_ms()
        t0 = now_ms()
        """
        Quy trình: Hash File -> MPC Sign -> LevelDB Store -> ZK Proof -> Blockchain Commit
        """

        # 1. Prepare Hash file content
        # 2. Create TBS (To-Be-Signed) Structure
        build_tbs = build_tbs_from_csr(self.dca_cert_obj, file_bytes, self.issuer, metadata["metadata"])
        tbs_bytes = get_tbs_bytes(build_tbs)

        # 3. MPC Signing Logic (Tính toán phân tán r, s)
        sig_der, r, s = self.mpc_sign_ecdsa_secp256k1_threshold(tbs_bytes)
        # signature = {"r": hex(r), "s": hex(s)}
        signature_endcode = self.encode_der_emn178(r, s).hex()
        timing["mpc_sign_ms"] = round(now_ms() - t0, 2)

        # (a) Put TBS
        # 5. Build final ASN.1 Certificate
        cert_pem_bytes = build_certificate_asn1(tbs_bytes, sig_der).encode("utf-8")
        cert_pem_b64 = base64.b64encode(cert_pem_bytes).decode() # response client

        # 4. Update Merkle Tree (Sử dụng LevelDB)
        # Hash toàn bộ chứng chỉ (TBS + Signature) để tạo lá
        t0 = now_ms()
        certificate_hash = hash_sha256((cert_pem_bytes + metadata["metadata"].encode("utf-8"))).hex()
        # Thêm vào DB và lấy Root mới ngay lập tức
        self.root_merkle = self.merkle_tree.add_leaf(certificate_hash)
        timing["merkle_update_ms"] = round(now_ms() - t0, 2)

        # 5. Generate ZK Proof (Simplified) & Blockchain Commit
        # Secret ở đây ta lấy ví dụ là file_hash (dạng số)
        # Chứng minh: "Tôi biết file gốc có hash SHA256 này, tương ứng với hash Poseidon trên chain"
        t0 = now_ms()
        tx_hash = None
        #  gọi snarkjs
        file_hash = hash_sha256(cert_pem_bytes)
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
            zk_proof_json_data = zk_result['proof']  ## json.dumps(zk_result['proof'])
            zk_public_signals = zk_result['public_hash']  # string
            # Poseidon dùng cho ZK Verification riêng
        # Bắt buộc phải lưu Proof để đảm bảo tính Public Verifiability (Khả năng xác minh công khai)
        #     và Non-repudiation (Chống chối bỏ).
        #     Nếu không có Proof, hệ thống chỉ là "Trust me", không phải "Don't trust, Verify".
        # Proof Groth16 rất nhẹ (256 bytes).
        # Sử dụng Event/Logs và calldata thay vì Storage string giúp chi phí Gas cực thấp, hoàn toàn khả thi cho thực tế.
        zk_proof = {
            "root": self.root_merkle,
            "status": "VALID_ON_CHAIN" if self.chain_client else "INVALID_ON_CHAIN",
            "proof_data": zk_proof_json_data
        }
        timing["zk_proof_ms"] = round(now_ms() - t0, 2)

        if self.chain_client:
            t0 = now_ms()
            try:
                # Gửi Root mới lên Blockchain
                tx_hash = self.chain_client.submit_root_on_chain(self.root_merkle, zk_public_signals)
                print(
                    f"Transaction commitment on chain Tx: {tx_hash} has \nSignal public: {zk_public_signals}  -  Signal Ethernal: {f'0x{int(zk_public_signals):064x}'}")
            except Exception as e:
                print(f"Lỗi submit blockchain: {e}")
            timing["blockchain_commit_ms"] = round(now_ms() - t0, 2)

        timing["total_ms"] = round(now_ms() - t0_total, 2)

        return {
            "timing": timing,
            "tbs_data": tbs_bytes.hex(),
            "metadata": metadata,
            "signature": sig_der.hex(),
            "public_key_hex": self.get_public_key_uncompressed_hex(),
            "certificate_hash": certificate_hash,
            "blockchain_tx": tx_hash,  # Transaction hash để client tra cứu explorer
            "zk_proof": zk_proof,
            # Privacy-Preserving: Có thể verify chứng chỉ (thông qua Y) mà không cần lộ nội dung chứng chỉ (X) cho người xác thực (Verifier) cho đến khi cần thiết.
            "certificate_crt_pem": cert_pem_b64,
        }

    def verify_signature(self, user_cert_obj):
        if self.dca_cert_obj is None:
            raise Exception("Root CA is not initialized")
        ca_public_key = self.dca_cert_obj.public_key()
        tbs_bytes = user_cert_obj.tbs_certificate_bytes
        signature = user_cert_obj.signature
        sig_alg = user_cert_obj.signature_hash_algorithm

        try:
            ca_public_key.verify(
                signature,
                tbs_bytes,
                ec.ECDSA(sig_alg)
            )
            print("Signature OK")
            return True
        except Exception as e:
            print("Signature FAILED:", e)
            return False

    def verify_user_certificate(self, user_cert_obj):
        # region Method verify_user_certificate
        def check_validity(cert):
            now = datetime.now(timezone.utc)
            if now < cert.not_valid_before.replace(tzinfo=timezone.utc):
                return False, "Certificate not valid yet"
            if now > cert.not_valid_after.replace(tzinfo=timezone.utc):
                return False, "Certificate expired"
            return True, "OK"
        # Require BasicConstraints = CA:FALSE
        def check_basic_constraints(cert):
            bc = cert.extensions.get_extension_for_class(x509.BasicConstraints).value
            if bc.ca:
                return False, "End-user certificate must not be CA"
            return True, "OK"
        def check_key_usage(cert):
            try:
                ku = cert.extensions.get_extension_for_class(x509.KeyUsage).value
                if not ku.digital_signature:
                    return False, "KeyUsage requires digitalSignature"
                return True, "OK"
            except x509.ExtensionNotFound:
                return True, "No KeyUsage extension"
        def check_issuer(cert, dca_subject):
            if cert.issuer != dca_subject:
                return False, "Issuer mismatch"
            return True, "OK"
        # endregion Method verify_user_certificate
        # ==============================================

        print("Checking signature...")
        if not self.verify_signature(user_cert_obj):
            return False, "Invalid signature"

        print("Checking validity...")
        ok, msg = check_validity(user_cert_obj)
        if not ok:
            return False, msg

        print("Checking BasicConstraints...")
        ok, msg = check_basic_constraints(user_cert_obj)
        if not ok:
            return False, msg

        print("Checking KeyUsage...")
        ok, msg = check_key_usage(user_cert_obj)
        if not ok:
            return False, msg

        print("Checking issuer...")
        ok, msg = check_issuer(user_cert_obj, self.dca_cert_obj.subject)
        if not ok:
            return False, msg

        return True, "Certificate valid"

    def verify_issue(self, pem_crt_certificate_str, cert_json):
        timing = {}  # lưu thời gian từng giai đoạn (ms)
        t0_total = now_ms()
        t0 = now_ms()
        client_tbs_data = cert_json['tbs_data']
        metadata = cert_json['metadata']
        signature = cert_json['signature']
        tx_hash = cert_json['blockchain_tx']
        """
        Verify: CRT Verify ECDSA -> Verify Integrity (LevelDB + Blockchain)
        """

        # 1. Re-construct TBS Check from file and provided metadata
        # Client gửi file lên, server hash file đó để so khớp với hash trong tbs_data
        user_cert_obj = x509.load_pem_x509_certificate(
            pem_crt_certificate_str #.decode("utf-8") # <-- cert_pem_bytes
        )

        # Decode bytes same with tbs data when issue_ing
        tbs_bytes = user_cert_obj.tbs_certificate_bytes

        certificate_hash = hash_sha256((pem_crt_certificate_str + metadata["metadata"].encode("utf-8"))).hex()
        if (certificate_hash != cert_json["certificate_hash"]):
            return False, "Nội dung file không khớp với chứng chỉ."

        # 2. Verify ECDSA Signature
        self.verify_user_certificate(user_cert_obj)
        # No need self.merkle_tree.add_leaf(certificate_hash)

        # 3. Transparency Check (LevelDB & Blockchain)
        # Check 3.1: Có tồn tại trong DB Off-chain của CA không? Check Merkle Existence (Transparency)
        # Ở đây ta dùng hàm get_merkle_proof để kiểm tra sự tồn tại
        # Hash lại toàn bộ để xem có trong cây không
        merkle_path = self.merkle_tree.get_merkle_proof(certificate_hash)
        if merkle_path is None:  # signature valid, but hash of tbs_data and signal not in DB
            return False, "Chữ ký Hợp lệ nhưng KHÔNG tìm thấy trong Database (Cảnh báo: Có thể là chứng chỉ chui)."

        # Check 3.2: Root hiện tại trên Blockchain có khớp với Root tính từ DB không?
        # (Đây là bước đảm bảo CA không sửa DB sau khi công bố)
        current_db_root = self.merkle_tree.get_root()

        chain_msg = ""
        on_chain_signal = ""
        if self.chain_client and self.chain_client.contract:
            try:
                on_chain_root = self.chain_client.contract.functions.merkleRoot().call()
                # Chuyển bytes32 về hex string (bỏ 0x)
                on_chain_root_hex = on_chain_root.hex()

                # Hardhat thường trả về hex string, ta cần normalize để so sánh
                if on_chain_root_hex.startswith('0x'):
                    on_chain_root_hex = on_chain_root_hex[2:]

                if current_db_root == on_chain_root_hex:  # root_merkle db and on-chain
                    chain_msg = " (Đã xác thực khớp với Blockchain)"
                else:
                    chain_msg = f" (CẢNH BÁO: Root trên Blockchain khác với DB. Chain: {on_chain_root_hex[:10]}...)"

                # Bước 2: Verify Blockchain Existence
                # CHECK BLOCKCHAIN
                # Truy vấn Blockchain lấy Signal thực tế đã lưu
                on_chain_signal = self.chain_client.get_signal_from_tx(tx_hash)
                if on_chain_signal is None:
                    return False, "Không tìm thấy thông tin Signal trong Transaction Hash này (hoặc Tx lỗi)."
                #

                proof_json = cert_json['zk_proof']['proof_data']
                # 3. VERIFY ZK PROOF (Toán học)
                # Dùng Signal đã được Chain xác nhận để verify Proof
                is_math_valid = self.verify_zk_math(proof_json, on_chain_signal)
                if is_math_valid:
                    chain_msg += " & ZK Proof hợp lệ"
                else:
                    chain_msg += " & CẢNH BÁO: ZK Proof không hợp lệ"
            except Exception as e:
                chain_msg = " (Không thể kết nối Blockchain để check Root)"
                traceback.print_exc()
        total_ms = round(now_ms() - t0_total, 2)
        return True, f"Chứng chỉ Hợp lệ & Đã được lưu trữ minh bạch {chain_msg};  Với TIME là {total_ms} millisecond.", on_chain_signal


    def sign_file(self, file_bytes, metadata):
        timing = {}  # lưu thời gian từng giai đoạn (ms)
        t0_total = now_ms()
        t0 = now_ms()
        """
        Quy trình: Hash File -> MPC Sign -> LevelDB Store -> ZK Proof -> Blockchain Commit
        """

        # 1. Hash file content
        file_hash = hash_sha256(file_bytes)
        # 2. Create TBS (To-Be-Signed) Structure
        tbs_json, tbs_bytes = create_tbs_bytes(file_hash, metadata)  # signature_input is tbs_bytes
        # 3. MPC Signing Logic (Tính toán phân tán r, s)
        sig_der, r, s = self.mpc_sign_ecdsa_secp256k1_threshold(tbs_bytes)
        signature = {"r": hex(r), "s": hex(s)}
        signature_endcode = self.encode_der_emn178(r, s)
        timing["mpc_sign_ms"] = round(now_ms() - t0, 2)

        # 4. Update Merkle Tree (Sử dụng LevelDB)
        # Hash toàn bộ chứng chỉ (TBS + Signature) để tạo lá
        t0 = now_ms()
        cert_full_hash = hash_sha256((tbs_json + json.dumps(signature)).encode()).hex()
        # Thêm vào DB và lấy Root mới ngay lập tức
        self.root_merkle = self.merkle_tree.add_leaf(cert_full_hash)
        timing["merkle_update_ms"] = round(now_ms() - t0, 2)

        # 5. Generate ZK Proof (Simplified) & Blockchain Commit
        # Secret ở đây ta lấy ví dụ là file_hash (dạng số)
        # Chứng minh: "Tôi biết file gốc có hash SHA256 này, tương ứng với hash Poseidon trên chain"
        t0 = now_ms()
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
            zk_proof_json_data = zk_result['proof']  ## json.dumps(zk_result['proof'])
            zk_public_signals = zk_result['public_hash']  # string
            # Poseidon dùng cho ZK Verification riêng
        # Bắt buộc phải lưu Proof để đảm bảo tính Public Verifiability (Khả năng xác minh công khai)
        #     và Non-repudiation (Chống chối bỏ).
        #     Nếu không có Proof, hệ thống chỉ là "Trust me", không phải "Don't trust, Verify".
        # Proof Groth16 rất nhẹ (256 bytes).
        # Sử dụng Event/Logs và calldata thay vì Storage string giúp chi phí Gas cực thấp, hoàn toàn khả thi cho thực tế.
        zk_proof = {
            "root": self.root_merkle,
            "status": "VALID_ON_CHAIN" if self.chain_client else "INVALID_ON_CHAIN",
            "proof_data": zk_proof_json_data
        }
        timing["zk_proof_ms"] = round(now_ms() - t0, 2)

        if self.chain_client:
            t0 = now_ms()
            try:
                # Gửi Root mới lên Blockchain
                tx_hash = self.chain_client.submit_root_on_chain(self.root_merkle, zk_public_signals)
                print(
                    f"Transaction commitment on chain Tx: {tx_hash} has \nSignal public: {zk_public_signals}  -  Signal Ethernal: {f'0x{int(zk_public_signals):064x}'}")
            except Exception as e:
                print(f"Lỗi submit blockchain: {e}")
            timing["blockchain_commit_ms"] = round(now_ms() - t0, 2)

        timing["total_ms"] = round(now_ms() - t0_total, 2)

        return {
            "timing": timing,
            "tbs_data": json.loads(tbs_json),
            "signature_input": tbs_bytes.hex(),
            "signature": signature,
            "signature_value": signature_endcode.hex(),
            "public_key_hex": self.get_public_key_uncompressed_hex(),
            "certificate_hash": cert_full_hash,
            "blockchain_tx": tx_hash,  # Transaction hash để client tra cứu explorer
            "zk_proof": zk_proof,
            # Privacy-Preserving: Có thể verify chứng chỉ (thông qua Y) mà không cần lộ nội dung chứng chỉ (X) cho người xác thực (Verifier) cho đến khi cần thiết.
        }

    def verify_file(self, file_bytes, cert_json):
        timing = {}  # lưu thời gian từng giai đoạn (ms)
        t0_total = now_ms()
        t0 = now_ms()
        client_tbs_data = cert_json['tbs_data']
        signature = cert_json['signature']
        tx_hash = cert_json['blockchain_tx']
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
        if merkle_path is None:  # signature valid, but hash of tbs_data and signal not in DB
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

                if current_db_root == on_chain_root_hex:  # root_merkle db and on-chain
                    chain_msg = " (Đã xác thực khớp với Blockchain)"
                else:
                    chain_msg = f" (CẢNH BÁO: Root trên Blockchain khác với DB. Chain: {on_chain_root_hex[:10]}...)"

                # Bước 2: Verify Blockchain Existence
                # CHECK BLOCKCHAIN
                # Truy vấn Blockchain lấy Signal thực tế đã lưu
                on_chain_signal = self.chain_client.get_signal_from_tx(tx_hash)
                if on_chain_signal is None:
                    return False, "Không tìm thấy thông tin Signal trong Transaction Hash này (hoặc Tx lỗi)."
                #

                proof_json = cert_json['zk_proof']['proof_data']
                # 3. VERIFY ZK PROOF (Toán học)
                # Dùng Signal đã được Chain xác nhận để verify Proof
                is_math_valid = self.verify_zk_math(proof_json, on_chain_signal)
                if is_math_valid:
                    chain_msg += " & ZK Proof hợp lệ"
                else:
                    chain_msg += " & CẢNH BÁO: ZK Proof không hợp lệ"
            except Exception as e:
                chain_msg = " (Không thể kết nối Blockchain để check Root)"
                traceback.print_exc()
        total_ms = round(now_ms() - t0_total, 2)
        return True, f"Chứng chỉ Hợp lệ & Đã được lưu trữ minh bạch {chain_msg};  Với TIME là {total_ms} millisecond."

    def verify_zk_proof(self):
        # Client gửi: { "proof": ..., "public_signal": lấy từ chain... }
        """
        Input:
        - file: File gốc cần xác thực (để tính ra signal)
        - proof: JSON Proof mà Client đang giữ
        """
        if 'file' not in request.files or 'proof' not in request.form:
            return jsonify({"error": "Thiếu File hoặc Proof"}), 400

        file = request.files['file']
        data = request.json
        tx_hash = data.get('tx_hash')
        # proof_json_str = data.get('proof')
        # proof_json = json.loads(proof_json_str)
        proof_json = data.get('proof')
        # signal = data.get('public_signal')

        # is_valid, msg = ca_system.verify_transaction_integrity(file_bytes, tx_hash, proof_json)
        try:
            # Bước 1: Verify toán học (Server chạy snarkjs verify, circom tính hash từ file)
            # Tính toán Signal từ File gốc (Server tự tính, không tin Client)
            # Lưu ý: Python verify groth16 hơi phức tạp, thường gọi subprocess snarkjs verify
            # Logic tính hash này phải khớp y hệt logic lúc tạo (VD: Poseidon hoặc SHA256->BigInt)
            # Giả sử hàm hash của bạn chuyển bytes -> số int (Signal)
            # Trong thực tế ZK, thường là: Hash(File) -> Int string
            """
            Tính toán Public Signal (Input cho ZK) từ file bytes.
            Phải khớp logic với file 'input.json' lúc tạo proof.
            """
            # Ví dụ: Hash SHA256 rồi chuyển thành số nguyên
            file_hash = hash_sha256(file.read())  # file.read() as file_bytes
            # Generate ZK Proof (Simplified) against file_hash
            # Secret ở đây ta lấy ví dụ là file_hash (dạng số)
            # Chứng minh: "Tôi biết file gốc có hash SHA256 này, tương ứng với hash Poseidon trên chain"
            t0 = now_ms()
            #  gọi snarkjs
            zk_result = self.generate_real_zk_proof(file_hash)
            zk_public_signals = zk_result['public_hash']  # string
            print(f"[Verify] Calculated Signal from File Poseidon again: {zk_public_signals}")
            # Chuyển đổi thành số nguyên (BigInt) để làm Signal cho Circom
            calculated_signal_int = int.from_bytes(zk_public_signals, 'big')

            # Bước 2: Verify Blockchain Existence
            # CHECK BLOCKCHAIN
            # Truy vấn Blockchain lấy Signal thực tế đã lưu
            on_chain_signal = self.chain_client.get_signal_from_tx(tx_hash)
            if on_chain_signal is None:
                return jsonify({
                    "valid": False,
                    "error": "Không tìm thấy thông tin Signal trong Transaction Hash này (hoặc Tx lỗi)."
                }), 400
            #
            # "Signal số này có phải do CA cấp không?"
            # Gọi smart contract check xem signal này có được Admin commit không
            is_valid_on_chain = self.chain_client.contract.functions.checkSignal(
                int(calculated_signal_int)
            ).call()

            if not is_valid_on_chain:
                return jsonify({
                    "valid": False,
                    "error": "File này chưa từng được CA cấp chứng chỉ (Signal không tìm thấy trên Blockchain) (Fake CA?)."
                }), 400

            # 3. VERIFY ZK PROOF (Toán học)
            # Dùng Signal đã được Chain xác nhận để verify Proof
            is_math_valid = self.verify_zk_math(proof_json, calculated_signal_int)
            if is_math_valid:
                return jsonify({
                    "valid": True,
                    "message": "Xác thực thành công! (Proof khớp với File & File đã được lưu trên Blockchain)"
                })
            return jsonify({
                "valid": False,
                "error": "Proof sai! (File đúng là có trên chain, nhưng Proof này không phải của file đó)"
            }), 400
        #
        except Exception as e:
            print(f"Exception during ZK verify: {e}")
            traceback.print_exc()
            return jsonify({"valid": False, "error": str(e)}), 500

    def verify_zk_math(self, proof_json, public_signal):
        """
        Gọi snarkjs để verify proof với public_signal. Cần file verification_key.json từ circuit.
        """
        import subprocess, json, tempfile

        zk_dir = "../../hybridzkcircuit"
        vkey_path = os.path.join(zk_dir, "verification_key.json")

        if not os.path.exists(vkey_path):
            print("Lỗi: Không tìm thấy verification_key.json")
            return False

        # Tạo file public.json tạm thời chứa Signal
        # SnarkJS verify cần file public.json chứa mảng các signal
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as public_file:
            json.dump([str(public_signal)], public_file)
            public_file_path = public_file.name

        # Tạo file proof.json tạm thời
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as proof_file:
            json.dump(proof_json, proof_file)
            proof_file_path = proof_file.name

        try:
            # Gọi lệnh: snarkjs groth16 verify verification_key.json public.json proof.json
            cmd = [
                "/home/nguyentthai96/.nvm/versions/node/v22.21.0/bin/node",  # Path tới node
                os.path.join(zk_dir, "node_modules/.bin/snarkjs"),
                "groth16", "verify",
                vkey_path,
                public_file_path,
                proof_file_path
            ]

            # Chạy lệnh
            result = subprocess.run(cmd, capture_output=True, text=True)

            # Dọn dẹp file tạm
            os.unlink(public_file_path)
            os.unlink(proof_file_path)

            if result.returncode == 0 and "OK" in result.stdout:
                print("[ZK Check] Verify Success!")
                return True
            else:
                print(f"[ZK Check] Verify Failed: {result.stdout} {result.stderr}")
                return False

        except Exception as e:
            print(f"Exception during ZK verify: {e}")
            return False


def build_certificate_asn1(tbs_bytes, sig_der):
    cert_asn1 = CertificateASN1()

    # TBS
    cert_asn1['tbsCertificate'] = der_decode(tbs_bytes)[0]

    # AlgorithmIdentifier ecdsa-with-SHA256
    alg = AlgorithmIdentifier()
    alg['algorithm'] = univ.ObjectIdentifier("1.2.840.10045.4.3.2")
    alg['parameters'] = univ.Null() # remove Theo RFC 3279 / RFC 5758: # For ECDSA, parameters MUST be ABSENT

    cert_asn1['signatureAlgorithm'] = alg

    # Signature BIT STRING
    cert_asn1['signatureValue'] = univ.BitString.fromOctetString(sig_der)

    # Encode full cert
    final_der = der_encode(cert_asn1)
    pem = (
            b"-----BEGIN CERTIFICATE-----\n" +
            base64.encodebytes(final_der) +
            b"-----END CERTIFICATE-----\n"
    )
    return pem.decode()


# call build_tbs_from_csr get builder
def get_tbs_bytes(builder):
    ephemeral_priv = ec.generate_private_key(ec.SECP256R1())
    temp_cert = builder.sign(
        private_key=ephemeral_priv,
        algorithm=hashes.SHA256(),
    )
    tbs_bytes = temp_cert.tbs_certificate_bytes
    return tbs_bytes


def build_tbs_from_csr(ca_cert, csr_pem: bytes, issuer_subject, user_uuid: str):
    owner_subject, owner_public_key = parse_csr(csr_pem)

    builder = x509.CertificateBuilder()
    builder = builder.subject_name(owner_subject)
    builder = builder.issuer_name(issuer_subject)

    not_before = datetime.now(timezone.utc)  # datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    not_after = not_before + timedelta(days=365)

    builder = builder.not_valid_before(not_before)
    builder = builder.not_valid_after(not_after)

    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.public_key(owner_public_key)

    # Basic constraints
    builder = builder.add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True
    )

    # SubjectKeyIdentifier
    builder = builder.add_extension(
        x509.SubjectKeyIdentifier.from_public_key(owner_public_key),
        critical=False
    )
    # AuthorityKeyIdentifier
    builder = builder.add_extension(
        x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_cert.public_key()),
        critical=False
    )
    # ski = ca_cert.extensions.get_extension_for_class(
    #     x509.SubjectKeyIdentifier
    # ).value.digest
    # builder = builder.add_extension(
    #     x509.AuthorityKeyIdentifier(
    #         key_identifier=ski,
    #         authority_cert_issuer=None,
    #         authority_cert_serial_number=None
    #     ),
    #     critical=False
    # )

    builder = builder.add_extension(
        x509.KeyUsage(digital_signature=True,
                      content_commitment=False,
                      key_encipherment=False,
                      data_encipherment=False,
                      key_agreement=False,
                      key_cert_sign=False,
                      crl_sign=False,
                      encipher_only=False,
                      decipher_only=False,
                      ),
        critical=True
    # ).add_extension(
    #     x509.ExtendedKeyUsage([univ.ObjectIdentifier("1.2.840.113583.1.1.10")]),
    #     critical=True
    )

    # Add private extension for UUID
    uuid_oid = x509.oid.ObjectIdentifier("1.3.6.1.4.1.55555.1.1")
    uuid_extension = x509.UnrecognizedExtension(uuid_oid, user_uuid.encode("utf-8"))

    builder = builder.add_extension(uuid_extension, critical=False)

    return builder


def parse_csr(csr_pem: bytes):
    csr = x509.load_pem_x509_csr(csr_pem)

    owner_subject = csr.subject  # Subject DN của Owner
    owner_public_key = csr.public_key()  # EC/RSA public key

    return owner_subject, owner_public_key
