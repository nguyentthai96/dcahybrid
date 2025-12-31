import os
import random

from ecdsa import SECP256k1, NIST256p


class MPCNode:
    # prime256v1 = secp256r1 NIST256p | secp256k1 SECP256k1
    def __init__(self, name, key_dir="./keystore", curve=NIST256p):
        self.name = name
        _G = curve.generator
        # ORDER = CURVE.generator.order()
        self.ORDER = _G.order()
        self.key_file = os.path.join(key_dir, f"{name}.pem")

        # Tạo thư mục lưu key nếu chưa có
        if not os.path.exists(key_dir):
            os.makedirs(key_dir)

        # LOGIC QUAN TRỌNG: Load key nếu tồn tại, nếu không thì sinh mới
        if os.path.exists(self.key_file):
            print(f"[{name}] Loading existing key from {self.key_file}")
            with open(self.key_file, "r") as f:
                hex_key = f.read().strip()
                self._sk_share = int(hex_key, 16)
        else:
            print(f"[{name}] Generating NEW key pair...")
            self._sk_share = random.randrange(1, self.ORDER)
            # Lưu key lại để lần sau dùng
            with open(self.key_file, "w") as f:
                # Lưu dưới dạng Hex string
                f.write(hex(self._sk_share)[2:]) # bỏ tiền tố 0x

        # Tính Public Key từ Secret Share đã load/gen
        self.pk_share = self._sk_share * _G

    def generate_k_share(self):
        # k (ephemeral key) luôn phải random mỗi lần ký, KHÔNG ĐƯỢC LƯU
        return random.randrange(1, self.ORDER)
