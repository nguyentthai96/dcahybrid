import hashlib
from fastecdsa import keys, curve, ecdsa
from fastecdsa.curve import secp256k1 as CURVE
import secrets

# Các tham số đường cong
G = CURVE.G
ORDER = CURVE.q

class YaoNode:
    """Đại diện cho một thực thể trong giao thức Yao"""
    def __init__(self, name, sk_share):
        self.name = name
        self.sk_share = sk_share
        self.k_share = None

    def generate_k_share(self):
        self.k_share = secrets.randbelow(ORDER)
        return self.k_share

class YaoGarbler(YaoNode):
    """Node A: Người tạo mạch (Garbler)"""
    def prepare_garbled_circuit(self, z, r):
        # Trong thực tế, bước này tạo ra các bảng sự thật đã mã hóa (Garbled Tables)
        # Hàm mục tiêu: s = k^-1 * (z + r * (sk_a + sk_b)) mod q
        print(f"[{self.name}] Đang tạo Garbled Circuit cho hàm ECDSA...")
        return "GC_STRUCTURE_DATA"

    def send_garbled_inputs(self):
        # Gửi nhãn (labels) cho input của chính mình (sk_a, k_a)
        return {"label_sk_a": "encoded_bits", "label_k_a": "encoded_bits"}

class YaoEvaluator(YaoNode):
    """Node B: Người thực thi (Evaluator)"""
    def oblivious_transfer_request(self):
        # B yêu cầu nhãn cho input của mình (sk_b, k_b) qua OT
        # để Garbler không biết B đang chọn bit 0 hay 1
        print(f"[{self.name}] Đang thực hiện Oblivious Transfer với Garbler...")
        return "OT_PAYLOAD"

    def evaluate(self, circuit, labels_a, labels_b):
        # Thực thi mạch logic để tính s
        print(f"[{self.name}] Đang thực thi mạch với nhãn của A và B...")
        # Giả định kết quả trả về từ mạch logic
        return "RESULT_S_SHARE"

class DecentralizedCA_Yao:
    def __init__(self, node_a, node_b):
        self.node_a = node_a  # Garbler
        self.node_b = node_b  # Evaluator
        self.joint_pk = (node_a.sk_share + node_b.sk_share) * G

    def mpc_sign(self, message_bytes):
        z = int.from_bytes(hashlib.sha256(message_bytes).digest(), "big")

        # 1. Sinh nonce phân tán (kA, kB)
        ka = self.node_a.generate_k_share()
        kb = self.node_b.generate_k_share()

        # 2. Tính R công khai (phần này có thể tính qua Diffie-Hellman)
        # R = (ka + kb) * G. Trong thực tế dùng 2-party multiplication
        k_total_inv = pow(ka + kb, -1, ORDER)
        R_point = (ka + kb) * G
        r = R_point.x % ORDER

        # 3. Chạy Yao Garbled Circuit cho phần tính 's'
        # Mục tiêu: Tính s = k_total_inv * (z + r * (sk_a + sk_b)) mod ORDER

        # Bước A: Garbler lập mạch
        circuit = self.node_a.prepare_garbled_circuit(z, r)
        labels_a = self.node_a.send_garbled_inputs()

        # Bước B: Evaluator lấy nhãn qua OT
        ot_data = self.node_b.oblivious_transfer_request()
        # Giả lập labels_b nhận được từ A qua OT
        labels_b = "labels_obtained_via_OT"

        # Bước C: Evaluator thực thi và cho ra kết quả s
        s = self.node_b.evaluate(circuit, labels_a, labels_b)


        s_real = (k_total_inv * (z + r * (self.node_a.sk_share + self.node_b.sk_share))) % ORDER

        return r, s_real

# --- TEST ---
sk_a = secrets.randbelow(ORDER)
sk_b = secrets.randbelow(ORDER)

node_a = YaoGarbler("NodeA", sk_a)
node_b = YaoEvaluator("NodeB", sk_b)

dca = DecentralizedCA_Yao(node_a, node_b)
r, s = dca.mpc_sign(b"Hello Yao ECDSA")

print(f"\n[RESULT] Signature (r, s):")
print(f"r: {hex(r)}")
print(f"s: {hex(s)}")