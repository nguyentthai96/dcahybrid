import os
import plyvel
from pymerkle import InmemoryTree

class LevelDBMerkleTreePymerkle:
    def __init__(self, db_path="./merkle_db"):
        os.makedirs(db_path, exist_ok=True)
        self.db = plyvel.DB(db_path, create_if_missing=True)

        # FIX 1: Khởi tạo InmemoryTree với thuật toán 'sha256'
        # Pymerkle v6 lưu trữ state trong RAM, chúng ta sẽ restore từ LevelDB
        self.tree = InmemoryTree(algorithm='sha256')

        # Load leaf count
        count_bytes = self.db.get(b'leaf_count')
        self.leaf_count = int.from_bytes(count_bytes, 'big') if count_bytes else 0

        # Nếu DB đã có leaf, load lại vào tree
        print(f"Restoring {self.leaf_count} leaves from LevelDB...")
        for i in range(self.leaf_count):
            leaf = self.db.get(i.to_bytes(4, 'big'))
            if leaf:
                # FIX 2: Dùng append_entry thay vì insert
                self.tree.append_entry(leaf)

    def add_leaf(self, leaf_data_hex: str):
        """Thêm một leaf vào DB và MerkleTree, trả về root mới"""
        # Pymerkle v6 tự handle encoding, nhưng tốt nhất truyền bytes
        leaf_bytes = bytes.fromhex(leaf_data_hex)
        index = self.leaf_count

        # Lưu leaf vào LevelDB
        self.db.put(index.to_bytes(4, 'big'), leaf_bytes)

        # FIX 2: Thêm vào MerkleTree dùng append_entry
        self.tree.append_entry(leaf_bytes)

        # Update leaf_count
        self.leaf_count += 1
        self.db.put(b'leaf_count', self.leaf_count.to_bytes(4, 'big'))

        return self.get_root()

    def get_leaf(self, index: int):
        return self.db.get(index.to_bytes(4, 'big'))

    def get_all_leaves(self):
        leaves = []
        for i in range(self.leaf_count):
            leaf = self.get_leaf(i)
            if leaf:
                leaves.append(leaf)
        return leaves

    def get_root(self):
        """Lấy Merkle Root"""
        if self.leaf_count == 0:
            return None

        # Lấy root hash thông qua thuộc tính .root
        # Lưu ý: .root trả về bytes, cần convert sang hex nếu muốn string
        if self.tree.root:
            # Truy cập vào .value để lấy bytes hash, sau đó mới .hex()
            return self.tree.root.digest.hex()
        return None

    def get_merkle_proof(self, leaf_data_hex: str):
        """Trả về proof cho leaf cụ thể"""
        leaf_bytes = bytes.fromhex(leaf_data_hex)

        try:
            # FIX 4: Dùng prove_inclusion thay vì auditProof
            proof = self.tree.prove_inclusion(leaf_bytes)

            # Serialize proof thành dictionary
            return proof.serialize()
        except Exception as e:
            print(f"Error generating proof: {e}")
            return None

        # FIX 5: Serialize proof theo format của v6
        # Proof object trong v6 có method serialize() trả về dict
        serialized_proof = proof.serialize()

        # Format custom (sibling + direction) như code cũ:
        # FIX v6 structure trả về serialized_proof gốc
        return serialized_proof

    def close(self):
        try:
            self.db.close()
        except Exception:
            pass