pragma circom 2.0.0;

// Import thư viện băm Poseidon
include "node_modules/circomlib/circuits/poseidon.circom";

template HashProver() {
    // Input bí mật (Nội dung chứng chỉ/Preimage) -> Client giữ, không lộ
    signal input secret;

    // Input công khai (Hash đã ghi trên Blockchain) -> Ai cũng biết
    signal input public_hash;

    // Khai báo component băm Poseidon (1 đầu vào)
    component hasher = Poseidon(1);
    hasher.inputs[0] <== secret;

    // Ràng buộc (Constraint):
    // Hash tính được từ secret PHẢI BẰNG public_hash
    public_hash === hasher.out;
}

// Hàm main
component main {public [public_hash]} = HashProver();


// circom hash_prover.circom --r1cs --wasm --sym