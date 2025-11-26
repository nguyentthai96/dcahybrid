const snarkjs = require("snarkjs");
const fs = require("fs");
const path = require("path");
// Thư viện poseidon được cài sẵn trong circomlibjs (cần cài thêm nếu thiếu)
// npm install circomlibjs
const { buildPoseidon } = require("circomlibjs");

async function run() {
    const secretStr = process.argv[2]; // Lấy tham số từ Python truyền vào
    const secretBigInt = BigInt(secretStr);

    // 1. Tính Poseidon Hash của secret
    const poseidon = await buildPoseidon();
    const hashBytes = poseidon([secretBigInt]);
    const hashBigInt = poseidon.F.toObject(hashBytes); // Convert sang số trường hữu hạn
    const hashStr = hashBigInt.toString();

    console.log("Calculated Poseidon Hash:", hashStr);

    // 2. Tạo file input.json CHUẨN (với public_hash đúng)
    const input = {
        "secret": secretStr,
        "public_hash": hashStr
    };

    fs.writeFileSync(path.join(__dirname, "input.json"), JSON.stringify(input));

    // 3. Tính toán Witness & Sinh Proof
    // Yêu cầu: Đã có file .wasm và .zkey
    const { proof, publicSignals } = await snarkjs.groth16.fullProve(
        input,
        path.join(__dirname, "hash_prover_js/hash_prover.wasm"),
        path.join(__dirname, "hash_prover_final.zkey")
    );

    // 4. Xuất file kết quả để Python đọc
    fs.writeFileSync(path.join(__dirname, "proof.json"), JSON.stringify(proof, null, 2));
    fs.writeFileSync(path.join(__dirname, "public.json"), JSON.stringify(publicSignals, null, 2));

    console.log("Proof generated successfully.");
    process.exit(0);
}

run().catch(err => {
    console.error(err);
    process.exit(1);
});