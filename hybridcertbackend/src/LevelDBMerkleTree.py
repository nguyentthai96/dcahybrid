import hashlib
import os

import plyvel
import math

def hash_sha256(data):
    if isinstance(data, str): data = data.encode()
    return hashlib.sha256(data).digest()

class LevelDBMerkleTree:
    def __init__(self, db_path="./merkle_db"):
        os.makedirs(db_path, exist_ok=True)
        # Tạo DB nếu chưa tồn tại
        self.db = plyvel.DB(db_path, create_if_missing=True)

        # Load số lượng lá hiện tại từ DB (key metadata)
        count_bytes = self.db.get(b'leaf_count')
        self.leaf_count = int.from_bytes(count_bytes, 'big') if count_bytes else 0

    def add_leaf(self, leaf_hash_hex):
        """Thêm một hash chứng chỉ vào DB và trả về Root mới"""
        # Lưu: Key = Index, Value = Hash
        index = self.leaf_count
        self.db.put(index.to_bytes(4, 'big'), bytes.fromhex(leaf_hash_hex))

        # Update count
        self.leaf_count += 1
        self.db.put(b'leaf_count', self.leaf_count.to_bytes(4, 'big'))

        return self.get_root()

    def get_leaf(self, index):
        return self.db.get(index.to_bytes(4, 'big'))

    def get_all_leaves(self):
        leaves = []
        for i in range(self.leaf_count):
            leaves.append(self.get_leaf(i))
        return leaves

    def get_root(self):
        leaves = self.get_all_leaves()
        if not leaves:
            return hashlib.sha256(b'').hexdigest() # Empty root

        # Thuật toán Merkle Tree cơ bản (cân bằng cây bằng cách duplicate lá cuối nếu lẻ)
        current_level = leaves
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                node1 = current_level[i]
                if i + 1 < len(current_level):
                    node2 = current_level[i+1]
                else:
                    node2 = node1 # Duplicate nếu lẻ

                combined_hash = hash_sha256(node1 + node2)
                next_level.append(combined_hash)
            current_level = next_level

        return current_level[0].hex()

    def get_merkle_proof(self, leaf_hash_hex):
        """
        Tạo Path (Witness) cho ZK Circuit: leaf -> root
        Trả về: danh sách các hash anh em (siblings) cần thiết để tính lên root
        """
        target = bytes.fromhex(leaf_hash_hex)
        leaves = self.get_all_leaves()

        try:
            idx = leaves.index(target)
        except ValueError:
            return None # Không tìm thấy leaf

        proof = []
        current_level = leaves
        curr_idx = idx

        while len(current_level) > 1:
            next_level = []
            is_right_node = (curr_idx % 2 == 1)
            sibling_idx = curr_idx - 1 if is_right_node else curr_idx + 1

            # Tìm sibling
            if sibling_idx < len(current_level):
                sibling = current_level[sibling_idx]
            else:
                sibling = current_level[curr_idx] # Duplicate case

            proof.append({
                "sibling": sibling.hex(),
                "is_right": 1 if is_right_node else 0
            })

            # Build next level
            for i in range(0, len(current_level), 2):
                n1 = current_level[i]
                n2 = current_level[i+1] if i+1 < len(current_level) else n1
                next_level.append(hash_sha256(n1 + n2))

            current_level = next_level
            curr_idx = curr_idx // 2

        return proof

    def close(self):
        try:
            self.db.close()
        except Exception:
            pass
