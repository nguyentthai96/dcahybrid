import json
import hashlib
from ecdsa import VerifyingKey, SECP256k1, util
from binascii import unhexlify, hexlify

# helpers
def hash_sha256(data_bytes):
    return hashlib.hash_sha256(data_bytes).digest()

def canonicalize_tbs(tbs: dict) -> bytes:
    # Deterministic JSON serialization: sort keys, ensure separators, utf-8
    return json.dumps(tbs, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

# build_cert_full_bytes + compute_cert_full_hash: domain prefixes (0x10, 0xFF) prevent collision.
def build_cert_full_bytes(tbs_bytes: bytes, signature_der: bytes) -> bytes:
    # domain separators: 0x10 for tbs, 0x30 for cert concat (example)
    return b'\x10' + tbs_bytes + b'\xFF' + signature_der

def compute_cert_full_hash(tbs_bytes: bytes, signature_der: bytes) -> str:
    return hash_sha256(build_cert_full_bytes(tbs_bytes, signature_der)).hex()

# rebuild root from leaf_hash and path; node prefix 0x01.
def verify_merkle_inclusion(leaf_hash_hex: str, merkle_path: list, leaf_index: int, expected_root_hex: str) -> bool:
    # merkle_path: list of sibling hashes hex, ordered bottom->top
    cur = bytes.fromhex(leaf_hash_hex)
    # leaf domain separator when leaf_hash already is hash_sha256(leaf_bytes) — expect leaf_hash is raw 32 bytes
    # but here we assume cert_full_hash is already leaf hash (no extra prefix)
    idx = leaf_index
    for sibling_hex in merkle_path:
        sibling = bytes.fromhex(sibling_hex)
        if idx % 2 == 0:
            cur = hash_sha256(b'\x01' + cur + sibling)  # node prefix 0x01
        else:
            cur = hash_sha256(b'\x01' + sibling + cur)
        idx //= 2
    return cur.hex() == expected_root_hex

def verify_ecdsa_signature_over_tbs(tbs_bytes: bytes, signature_der: bytes, joint_pubkey_hex: str) -> bool:
    # Compute message digest for signature (use domain prefix if desired)
    # Typically you hash the canonical tbs bytes, optionally prefix with domain
    z = hash_sha256(b'\x20' + tbs_bytes)  # use domain prefix for tbs-hash in signature
    vk = VerifyingKey.from_string(bytes.fromhex(joint_pubkey_hex), curve=SECP256k1)
    try:
        return vk.verify(signature_der, z, hashfunc=None, sigdecode=util.sigdecode_der)
    except Exception:
        return False

# Main verify function
def verify_file(file_bytes: bytes, cert_json: dict, merkle_api, chain_client, joint_pubkey_hex: str):
    """
    cert_json expected fields:
      - tbs_data (dict)
      - signature_der_hex (hex string of DER(r,s))
      - certificate_hash (hex)  # cert_full_hash
      - merkle_leaf_index (int)  # optional, speeds lookup
      - zk_proof (optional)
      - blockchain_tx (optional)
    merkle_api: object to fetch merkle_path and db_root
    chain_client: object to fetch on-chain root
    """

    # 1) Check file hash matches tbs_data.file_hash
    file_hash_hex = hash_sha256(file_bytes).hex()
    if file_hash_hex != cert_json['tbs_data']['file_hash'].lower():
        return False, "Nội dung file không khớp với file_hash trong tbs_data."

    # 2) Canonicalize tbs and compute cert_full_hash locally
    tbs_bytes = canonicalize_tbs(cert_json['tbs_data'])
    signature_der = bytes.fromhex(cert_json['signature_der_hex'])
    computed_cert_hash = compute_cert_full_hash(tbs_bytes, signature_der)
    if computed_cert_hash != cert_json['certificate_hash'].lower():
        return False, "certificate_hash không khớp (tbs hoặc signature bị sửa)."

    # 3) Verify signature (ECDSA) using joint public key
    if not verify_ecdsa_signature_over_tbs(tbs_bytes, signature_der, joint_pubkey_hex):
        return False, "Chữ ký ECDSA không hợp lệ."

    # 4) Verify inclusion in Merkle DB (off-chain)
    leaf_index = cert_json.get('merkle_leaf_index', None)
    merkle_path = merkle_api.get_merkle_proof(cert_json['certificate_hash'], leaf_index)
    if merkle_path is None:
        return False, "Không có inclusion proof trong Merkle DB (có thể là chứng chỉ chui)."

    db_root_hex = merkle_api.get_current_root()
    included = verify_merkle_inclusion(cert_json['certificate_hash'], merkle_path, leaf_index, db_root_hex)
    if not included:
        return False, "Inclusion proof không hợp lệ so với Merkle root trong DB."

    # 5) Optionally compare DB root with on-chain root (integrity anchoring)
    onchain_root_hex = None
    if chain_client is not None:
        try:
            onchain_root_bytes = chain_client.contract.functions.merkleRoot().call()
            onchain_root_hex = onchain_root_bytes.hex()
            if db_root_hex != onchain_root_hex:
                return True, f"Chứng chỉ hợp lệ nhưng CẢNH BÁO: root trên DB khác root trên chain. Chain root: {onchain_root_hex}"
        except Exception:
            return True, "Chứng chỉ hợp lệ; không thể kết nối blockchain để kiểm tra root."

    return True, "Chứng chỉ hợp lệ & đã được lưu trữ minh bạch (DB root khớp chain nếu có)."