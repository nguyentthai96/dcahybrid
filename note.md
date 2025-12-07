
Next.js (App Router) 
npx create-next-app@latest

React Router (v7) 
npx create-react-router@latest

Create with template
npm create vite@latest my-app -- --template react-ts

Adding TypeScript to an existing React project 
npm install —save-dev @types/react @types/react-dom



yarn global add react-devtools

Install React Compiler as a devDependency:
npm install -D babel-plugin-react-compiler@latest
or
yarn add -D babel-plugin-react-compiler@latest
or
pnpm install -D babel-plugin-react-compiler@latest



Instructions to setup and run:

Ubuntu add user into "input" group
sudo usermod -aG input $USER
newgrp input

sudo apt install python3 python3-pip python3-venv python3-full -y
python3 -m venv .venv
source .venv/bin/activate
python3 mouse_python.py
install library
pip install -U pip setuptools wheel pyinstaller
pip freeze > requirements.txt

pyinstaller --onefile --hidden-import=evdev --hidden-import=sklearn --hidden-import=joblib





npx hardhat node
https://app.tryethernal.com/blocks

# Khởi tạo blockchain local và lưu DB
ganache --db /home/nguyentthai96/Desktop/dcahybrid/hybridsmartcontract/mychain --chain.chainId 31337 --accounts 10




```sequenceDiagram
    participant C as Client (Browser)
    participant A as App (/api/sign)
    participant DCA as DecentralizedCA
    participant MPCA as MPCNode A
    participant MPCB as MPCNode B
    participant MT as LevelDBMerkleTree
    participant ZKS as ZK Snark Engine (JS Script)
    participant BC as HardhatClient (Blockchain)

    C->>A: POST /api/sign (File, Metadata)
    activate A

    A->>DCA: sign_file(file_bytes, metadata)
    activate DCA

    DCA->>DCA: 1. Hash File & Tạo TBS (To-Be-Signed)
    
    note over DCA, MPCB: 2. THRESHOLD SIGNATURE (MPC)
    DCA->>MPCA: generate_k_share()
    MPCA-->>DCA: kA
    DCA->>MPCB: generate_k_share()
    MPCB-->>DCA: kB
    DCA->>DCA: Tính toán R, r, s (k_total=kA+kB, sk_total=skA+skB)
    
    note right of DCA: Kết quả: Signature (r, s)

    DCA->>DCA: 3. Tính cert_full_hash (TBS + Sig)
    
    note over DCA, MT: 4. CẬP NHẬT MINH BẠCH (Transparency Log)
    DCA->>MT: add_leaf(cert_full_hash)
    MT->>MT: Lưu Leaf & Tính Root mới
    MT-->>DCA: Merkle Root mới
    
    DCA->>DCA: 5. Chuẩn bị dữ liệu ZK (file_hash)
    
    note over DCA, ZKS: 6. SINH BẰNG CHỨNG ZK
    DCA->>ZKS: generate_real_zk_proof(file_hash)
    ZKS-->>DCA: zk_result (Proof, public_hash/Poseidon Hash)
    
    note over DCA, BC: 7. CAM KẾT ON-CHAIN
    Dalt[Tồn tại HardhatClient?]
        DCA->>BC: submit_root_on_chain(Root, Poseidon Hash)
        BC-->>DCA: tx_hash
    else
        DCA->>DCA: Bỏ qua commit On-chain
    end

    DCA-->>A: Kết quả Chứng chỉ (tbs_data, signature, root, tx_hash, zk_proof)
    deactivate DCA

    A-->>C: JSON Result
    deactivate A
```



```shell
#
# Tạo CSR với OpenSSL rsa
openssl req -new -newkey rsa:2048 -nodes -out HybridDCA.csr -keyout HybridDCA.key -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=NTT/OU=IT/CN=NTTHAI"

OpenSSL fingerprint
openssl x509 -noout -fingerprint -sha1 -inform pem -in HybridDCA.csr
########


# Xem nội dung chứng chỉ của bạn
openssl x509 -in cert.crt.pem -text -noout
# Xem nội dung chứng chỉ CA gốc
openssl x509 -in ca.crt.pem -text -noout
# CSR
openssl req -text -noout -verify -in cert.csr.pem
#



2. Xác minh chữ ký của chứng chỉ con
xác nhận rằng cert.crt.pem thực sự được ký bởi ca.crt.pem, certificate được CA ký
openssl verify -CAfile ca.crt.pem cert.crt.pem
==> cert.crt.pem: OK

3. Kiểm tra sự khớp nhau giữa Khóa bí mật và Chứng chỉ --> RSA
3.1 Kiểm tra file khóa bí mật (key.key.pem) khớp với khóa công khai có trong file chứng chỉ (cert.crt.pem) cert.crt.pem
openssl x509 -in cert.crt.pem -pubkey -noout | openssl rsa -pubin -modulus -noout | openssl md5
3.2 Mã hash của khóa công khai từ file khóa bí mật key.key.pem
openssl rsa -in key.key.pem -pubout | openssl rsa -pubin -modulus -noout | openssl md5
==> Hai mã MD5 (ví dụ: (stdin)= e7a6f23e...) phải giống hệt nhau. 
#########################################################
########Create  ECDSA ecdsa-secp256k1-sha256
#
Tạo các tệp PEM bằng OpenSSL với ECDSA ecdsa-secp256k1-sha256
#Tạo khóa bí mật ECDSA cho CA (ca.key.pem)
openssl ecparam -name secp256k1 -genkey -noout -out ca.key.pem
#Tạo chứng chỉ tự ký cho CA root (ca.crt.pem)
openssl req -new -x509 -key ca.key.pem -sha256 -days 3650 -out ca.crt.pem -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=ConsortiumOrg/OU=IT/CN=HybridCA"
#Tạo khóa bí mật ECDSA cho chứng chỉ con (key.key.pem) owner_sign_key.key.pem
openssl ecparam -name secp256k1 -genkey -noout -out owner_sign_key.key.pem
#Tạo yêu cầu ký chứng chỉ (CSR) cho chứng chỉ con (cert.csr.pem) (-newkey create both private user owner)
openssl req -new -sha256 -key owner_sign_key.key.pem -out cert.csr.pem -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=ClientOrg/OU=IT/CN=ThaiNT"
#Tạo CRT: Ký CSR bằng CA để tạo chứng chỉ cuối cùng (cert.crt.pem)
openssl x509 -req -in cert.csr.pem -CA ca.crt.pem -CAkey ca.key.pem -CAcreateserial -out cert.crt.pem -days 365 -sha256
########Create  ECDSA ecdsa-prime256v1
#Tạo khóa bí mật ECDSA cho CA (ca.key.pem)
# openssl ecparam -name prime256v1 -genkey -noout -out ca.key.pem
#Tạo khóa bí mật ECDSA cho chứng chỉ con (key.key.pem) owner_sign_key.key.pem
# openssl ecparam -name prime256v1 -genkey -noout -out owner_sign_key.key.pem
#RSA Tạo yêu cầu ký chứng chỉ (CSR) cho chứng chỉ con (cert.csr.pem) (-newkey create both private user owner)
#openssl req -new -newkey rsa:2048 -nodes -out HybridDCA.csr -keyout HybridDCA.key -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=NTT/OU=IT/CN=NTTHAI"
#########################################################
######## RSA 3. Kiểm tra sự khớp nhau giữa Khóa bí mật và Chứng chỉ --> RSA
3.1 Kiểm tra file khóa bí mật (key.key.pem) khớp với khóa công khai có trong file chứng chỉ (cert.crt.pem) cert.crt.pem
openssl x509 -in cert.crt.pem -pubkey -noout | openssl rsa -pubin -modulus -noout | openssl md5
3.2 Mã hash của khóa công khai từ file khóa bí mật key.key.pem
openssl rsa -in key.key.pem -pubout | openssl rsa -pubin -modulus -noout | openssl md5
==> Hai mã MD5 (ví dụ: (stdin)= e7a6f23e...) phải giống hệt nhau. 
#########################################################
```