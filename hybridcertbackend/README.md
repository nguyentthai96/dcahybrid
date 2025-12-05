Quick start for backend:

1. Create and activate virtualenv:
   python3 -m venv .venv
   source .venv/bin/activate

2. Install requirements:
   pip install -r requirements.txt

3. Run:
   python app.py

Backend listens on http://localhost:5000


npm install (trong folder blockchain)
npx hardhat --init
npx hardhat compile
node scripts/export_abi.js -> Copy file JSON sang Python.
Mở Terminal 1 (Blockchain): npx hardhat node



[//]: # (Cài thư viện Python:)
pip install flask flask-cors ecdsa pycryptodome web3 plyvel


[//]: # (Cài Hardhat & SnarkJS Javascript)
mkdir hybridsmartcontract && cd hybridsmartcontract
npm init -y
npm install --save-dev hardhat
npm install snarkjs circomlib
npm install -g circom # Nếu chưa có circom binary


[//]: # (Thiết lập ZK Circuit)
mkdir hybridzkcircuit && cd hybridzkcircuit
- Tạo file circuit.circom
- Biên dịch & Setup (Trusted Setup)
```shell
# 1. Compile Circuit
circom circuit.circom --r1cs --wasm --sym

# 2. Tải file Powers of Tau (PTAU) - File có sẵn của cộng đồng
wget https://hermez.s3-eu-west-1.amazonaws.com/powersOfTau28_hez_final_12.ptau

# 3. Setup Groth16 (Phase 2)
snarkjs groth16 setup circuit.r1cs powersOfTau28_hez_final_12.ptau circuit_0000.zkey

# 4. Đóng góp ngẫu nhiên (Ceremony) - Nhập text bừa cũng được
snarkjs zkey contribute circuit_0000.zkey circuit_final.zkey --name="My Name" -v -e="some random text"

# 5. Xuất Verification Key (Dùng cho Python verify)
snarkjs zkey export verificationkey circuit_final.zkey verification_key.json
```
- Tạo script wrapper (NodeJS) để Python gọi: file generate_proof_wrapper.js trong thư mục hybridzkcircuit


[//]: # (Thiết lập Smart Contract (Hardhat))
```shell

npx hardhat init
# Chọn: Create a basic sample project -> Yes -> Yes

npx hardhat compile
-- remove cache
rm -rf artifacts cache
-- or forces
npx hardhat compile --force
--> file artifacts/contracts/DCALedger.sol/DCALedger.json sẽ được tạo ra. Python cần file này.

Copy file JSON đã compile ra root để Python đọc (dễ):
cp artifacts/contracts/DCALedger.sol/DCALedger.json ./compiled_contract.json

Blockchain Local:
npx hardhat node
```