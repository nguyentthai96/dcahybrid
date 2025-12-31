import hashlib
import secrets
import time
import traceback
import gmpy2
from gmpy2 import mpz
from datetime import datetime, timezone, timedelta

# Cryptography
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from phe import paillier # Thư viện mã hóa đồng cấu Paillier

# Thông số secp256k1
ORDER = gmpy2.mpz(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141)
CURVE = ec.SECP256K1()

def now_ms():
    return time.time() * 1000

class MPCNode:
    def __init__(self, name):
        self.name = name
        # Mỗi node giữ một share của Private Key
        self._sk_share = mpz(secrets.randbelow(int(ORDER)))
        # Node B sẽ tạo cặp khóa Paillier (trong Lindell 2PC)
        self.cached_enc_sk = None  # Cache cho bản mã Paillier
        if name == "NodeB":
            print(f"[{name}] Đang sinh cặp khóa Paillier (Chỉ thực hiện 1 lần)...")
            self.paillier_pub, self.paillier_priv = paillier.generate_paillier_keypair()
            # TỐI ƯU: Mã hóa sẵn Private Share ngay khi khởi tạo
            #self.cached_enc_sk = self.paillier_pub.encrypt(self._sk_share)
            # Mã hóa sẵn Private Key Share (Pre-encryption)
            t_start = now_ms()
            self.enc_sk_share = self.paillier_pub.encrypt(self._sk_share)
            print(f"[{name}] Pre-encryption hoàn tất: {round(now_ms()-t_start, 2)} ms")

    @property
    def public_key_share(self):
        priv_key = ec.derive_private_key(self._sk_share, CURVE, default_backend())
        return priv_key.public_key()

class Lindell2PECDSA:
    def __init__(self, node_a, node_b):
        self.node_a = node_a
        self.node_b = node_b
        self.precomputed_pool = []

    def precompute(self, amount=10):
        """Bước OFFLINE: Chuẩn bị sẵn các bộ nguyên liệu ký"""
        print(f"[Offline] Đang chuẩn bị {amount} bộ ký dự phòng...")
        for _ in range(amount):
            k1 = secrets.randbelow(ORDER)
            k2 = secrets.randbelow(ORDER)
            k_inv = pow(k1 * k2, -1, ORDER)

            # Tính r trước
            temp_priv = ec.derive_private_key(pow(k_inv, -1, ORDER), CURVE, default_backend())
            r = temp_priv.public_key().public_numbers().x % ORDER

            # Mã hóa sẵn các phần liên quan đến x2
            enc_x2 = self.node_b.paillier_pub.encrypt(self.node_b._sk_share)

            self.precomputed_pool.append({
                'k1_inv': pow(k1, -1, ORDER),
                'k2_inv': pow(k2, -1, ORDER),
                'r': r,
                'enc_x2': enc_x2
            })

    def sign(self, message_hash_int):
        print(f"--- Bắt đầu giao thức Lindell 2PC ---")

        # 1. Hiệp thương k (k = k1 * k2 mod q)
        k1 = secrets.randbelow(ORDER)
        k2 = secrets.randbelow(ORDER)

        # Tính R = (k1 * k2)^-1 * G. Trong Lindell, bước này cần Zero Knowledge Proof.
        # Ở đây ta tính r công khai sau khi hiệp thương k
        k_inv = pow(k1 * k2, -1, ORDER)
        R_point_priv = ec.derive_private_key(pow(k_inv, -1, ORDER), CURVE, default_backend())
        r = R_point_priv.public_key().public_numbers().x % ORDER

        # 2. Bob (Node B) mã hóa share x2 của mình bằng Paillier
        # Encryption(x2)
        t0 = now_ms()
        enc_x2 = self.node_b.cached_enc_sk # get from cache self.node_b.paillier_pub.encrypt(self.node_b._sk_share)
        # 3. Alice (Node A) thực hiện tính toán đồng cấu trên Ciphertext
        # Alice muốn tính Enc(s') nơi s' = k1^-1 * (m + r*x1 + r*x2)
        # s = k1^-1 * m + k1^-1 * r * x1 + k1^-1 * r * x2
        print("Signal s", round(now_ms() - t0,2))

        m = message_hash_int
        x1 = self.node_a._sk_share
        k1_inv = pow(k1, -1, ORDER)

        # (k1^-1 * m) + (k1^-1 * r * x1)
        part1 = (k1_inv * m) + (k1_inv * r * x1)

        # Đồng cấu: (k1^-1 * r) * Enc(x2)
        coeff = (k1_inv * r) % ORDER
        enc_part2 = enc_x2 * coeff

        # Tổng đồng cấu: Enc(part1 + part2)
        enc_s_prime = enc_part2 + part1

        # 4. Bob giải mã enc_s_prime và nhân với k2^-1 mod q
        s_prime = self.node_b.paillier_priv.decrypt(enc_s_prime)
        k2_inv = pow(k2, -1, ORDER)
        s = (s_prime * k2_inv) % ORDER

        # 5. Yao's GC (Lý thuyết):
        # Trong Lindell, Yao GC được dùng ở bước này để đảm bảo Bob không gian lận
        # khi giải mã hoặc để thực hiện phép Modulo ORDER một cách bí mật.

        print(f"[Lindell] Chữ ký tạo thành công r, s")
        return r, s

    def fast_sign(self, m_int):
        """Bước ONLINE: Chỉ thực hiện phép tính nhẹ"""
        if not self.precomputed_pool:
            self.precompute(1)

        data = self.precomputed_pool.pop(0)

        t_online = time.time() * 1000

        # 1. Alice tính đồng cấu (vẫn nhanh vì chỉ là nhân/cộng trên bản mã)
        part1 = (data['k1_inv'] * m_int) + (data['k1_inv'] * data['r'] * self.node_a._sk_share)
        coeff = (data['k1_inv'] * data['r']) % ORDER
        enc_s_prime = (data['enc_x2'] * coeff) + part1

        # 2. Bob giải mã (Phần này nặng nhất nhưng đã giảm bớt các bước khác)
        s_prime = self.node_b.paillier_priv.decrypt(enc_s_prime)
        s = (s_prime * data['k2_inv']) % ORDER

        print(f"-> Online Sign Time: {round(time.time()*1000 - t_online, 2)} ms")
        return data['r'], s
    def sign_mpz(self, m_int):
        t_sign = now_ms()
        m = mpz(m_int)

        # 1. Hiệp thương k (Sử dụng mpz)
        k1 = mpz(secrets.randbelow(int(ORDER)))
        k2 = mpz(secrets.randbelow(int(ORDER)))

        # TỐI ƯU 2: Tính toán r nhanh với gmpy2 powmod
        k_inv = gmpy2.invert(k1 * k2, ORDER)

        # Tính R point (Vẫn dùng cryptography cho đường cong)
        k_total = (k1 * k2) % ORDER
        temp_priv = ec.derive_private_key(int(k_total), CURVE, default_backend())
        r = mpz(temp_priv.public_key().public_numbers().x % int(ORDER))

        # 2. Alice tính toán (Sử dụng Homomorphic properties)
        # Alice cần tính: Enc(k1^-1 * (m + r*x1 + r*x2))
        k1_inv = gmpy2.invert(k1, ORDER)
        x1 = self.node_a._sk_share

        # part1 = k1^-1 * (m + r*x1)
        part1 = (k1_inv * (m + r * x1)) % ORDER

        # TỐI ƯU 3: Phép nhân vô hướng đồng cấu (Rất nhanh với gmpy2)
        coeff = (k1_inv * r) % ORDER
        enc_part2 = self.node_b.enc_sk_share * coeff

        # Cộng đồng cấu
        enc_s_prime = enc_part2 + part1

        # 3. Bob giải mã (Phần nặng nhất)
        t_decrypt = now_ms()
        s_prime = self.node_b.paillier_priv.decrypt(enc_s_prime)
        d_time = now_ms() - t_decrypt

        # s = s_prime * k2^-1 mod ORDER
        k2_inv = gmpy2.invert(k2, ORDER)
        s = (mpz(s_prime) * k2_inv) % ORDER

        duration = now_ms() - t_sign
        print(f"[Lindell-gmpy2] Tổng thời gian ký: {round(duration, 2)} ms (Giải mã: {round(d_time, 2)}ms)")
        return int(r), int(s)

class DecentralizedCA:
    def __init__(self):
        self.node_a = MPCNode("NodeA")
        self.node_b = MPCNode("NodeB")

        # Tính Joint Public Key: Q = (x1 + x2) * G
        # Lưu ý: Lindell chuẩn thường dùng x = x1 * x2, nhưng ở đây dùng Additive cho giống CA của bạn
        x_total = (self.node_a._sk_share + self.node_b._sk_share) % ORDER
        self.joint_priv_key = ec.derive_private_key(x_total, CURVE, default_backend())
        self.joint_pub_key = self.joint_priv_key.public_key()

        self.protocol = Lindell2PECDSA(self.node_a, self.node_b)

    def get_tbs_bytes(self, builder):
        """Lấy TBS bytes chuẩn bằng cách ký tạm"""
        temp_key = ec.generate_private_key(CURVE, default_backend())
        return builder.sign(temp_key, hashes.SHA256(), default_backend()).tbs_certificate_bytes

    def create_certificate(self):
        # Tạo cấu trúc chứng chỉ
        builder = x509.CertificateBuilder()
        builder = builder.subject_name(x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "Lindell-CA")]))
        builder = builder.issuer_name(x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "Lindell-CA")]))
        builder = builder.not_valid_before(datetime.now(timezone.utc))
        builder = builder.not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.public_key(self.joint_pub_key)

        t0 = now_ms()

        # 1. Lấy dữ liệu cần ký
        tbs_bytes = self.get_tbs_bytes(builder)
        m_int = int.from_bytes(hashlib.sha256(tbs_bytes).digest(), "big")

        # 2. Ký bằng Lindell 2PC

        r, s = self.protocol.sign_mpz(m_int)
        print("Chữ ký Lindell 2PC signed!  "+str(round(now_ms() - t0, 2))+" ms")

        # 3. Đóng gói ASN.1
        sig_der = encode_dss_signature(r, s)
        print("sig_der",sig_der.hex())

        # Tạo đối tượng Certificate cuối cùng
        # Vì cryptography không hỗ trợ 'nhồi' signature, ta dùng logic DER thủ công
        # (Sử dụng code CertificateASN1 đã cung cấp ở các câu trả lời trước)
        print("--- Hoàn tất đóng gói chứng chỉ ---")
        return sig_der, tbs_bytes

if __name__ == "__main__":
    ca = DecentralizedCA()
    t0 = now_ms()
    sig, tbs = ca.create_certificate()
    sig, tbs = ca.create_certificate()
    sig, tbs = ca.create_certificate()
    sig, tbs = ca.create_certificate()
    sig, tbs = ca.create_certificate()
    sig, tbs = ca.create_certificate()
    sig, tbs = ca.create_certificate()
    sig, tbs = ca.create_certificate()
    sig, tbs = ca.create_certificate()
    sig, tbs = ca.create_certificate()
    sig, tbs = ca.create_certificate()
    sig, tbs = ca.create_certificate()
    print("Chữ ký Lindell 2PC signed!  "+str(round(now_ms() - t0, 2))+" ms")

    # Kiểm tra
    try:
        ca.joint_pub_key.verify(sig, tbs, ec.ECDSA(hashes.SHA256()))
        print("Chữ ký Lindell 2PC hợp lệ!  "+str(round(now_ms() - t0, 2))+" ms")
    except Exception as e:
        traceback.print_exc()
        print(f"Lỗi xác thực: {e}")