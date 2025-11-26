Biên dịch mạch:
circom hash_prover.circom --r1cs --wasm --sym


# 1. Start a new ceremony
npx snarkjs powersoftau new bn128 12 pot12_0000.ptau -v

# 2. Contribute entropy (gõ lung tung bàn phím khi được hỏi)
npx snarkjs powersoftau contribute pot12_0000.ptau pot12_0001.ptau --name="FirstContribution" -v

# 3. Prepare phase 2
npx snarkjs powersoftau prepare phase2 pot12_0001.ptau pot12_final.ptau -v

# 4. Generate zkey (Proving Key)
npx snarkjs groth16 setup hash_prover.r1cs pot12_final.ptau hash_prover_0000.zkey

# 5. Contribute to zkey
npx snarkjs zkey contribute hash_prover_0000.zkey hash_prover_final.zkey --name="SecondContribution" -v

# 6. Export Verification Key (JSON) -> Để xác thực
npx snarkjs zkey export verificationkey hash_prover_final.zkey verification_key.json




npm install circomlibjs