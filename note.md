
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
# 1. Lấy modulus (public key hash) từ Private Key
openssl pkey -in user.key -pubout -outform PEM | openssl sha256
# 2. Lấy modulus từ Certificate
openssl x509 -in user.crt -pubkey -noout | openssl sha256
#########################################################
#########################################################
######## RSA 3. Kiểm tra sự khớp nhau giữa Khóa bí mật và Chứng chỉ --> RSA
3.1 Kiểm tra file khóa bí mật (key.key.pem) khớp với khóa công khai có trong file chứng chỉ (cert.crt.pem) cert.crt.pem
openssl x509 -in cert.crt.pem -pubkey -noout | openssl rsa -pubin -modulus -noout | openssl md5
3.2 Mã hash của khóa công khai từ file khóa bí mật key.key.pem
openssl rsa -in key.key.pem -pubout | openssl rsa -pubin -modulus -noout | openssl md5
==> Hai mã MD5 (ví dụ: (stdin)= e7a6f23e...) phải giống hệt nhau. 
#########################################################
```



```shell
PDF create certificate try

# 1. Tạo Root CA Key (EC secp256k1)
openssl ecparam -name secp256k1 -genkey -noout -out rootCA.key

# 2. Tạo Root CA Cert (Self-signed)
openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 3650 -out rootCA.pem -config ca.cnf

# 3. Tạo User Key (EC secp256k1)
openssl ecparam -name secp256k1 -genkey -noout -out user.key

# 4. Tạo User CSR
openssl req -new -key user.key -out user.csr -config user.cnf

# 5. Ký User CSR bằng Root CA
openssl x509 -req -in user.csr -CA rootCA.pem -CAkey rootCA.key -CAcreateserial -out user.crt -days 365 -sha256 -extfile user.cnf -extensions v3_req

#########################################################
```



Thư mục Trust Store của Ubuntu
/usr/local/share/ca-certificates/      # nơi bạn thêm custom CA (.crt)
/etc/ssl/certs/                        # nơi hệ thống tạo symlink sau khi update

Copy file CA (định dạng .crt, PEM) (File phải có đuôi .crt)
sudo cp my_ca.crt /usr/local/share/ca-certificates/

Update system CA
sudo update-ca-certificates

Kiểm tra CA đã được trust chưa
ls -l /etc/ssl/certs | grep my_ca


Xóa file CA khỏi thư mục nguồn
sudo rm /usr/local/share/ca-certificates/my_ca.crt
sudo update-ca-certificates --fresh


sudo update-ca-certificates --list







[//]: # (////////////////////////////////////////////////)
Sinh key & certificate prime256v1 (CA self-signed)
2.1 Sinh private key (prime256v1)
openssl ecparam -name prime256v1 -genkey -noout -out user.key.pem

Kiểm tra:
openssl ec -in user.key.pem -text -noout
-->
ASN1 OID: prime256v1

2.2 Sinh CSR
openssl req -new -key user.key.pem -out user_csr.csr.pem -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=ClientOrg/OU=IT/CN=ThaiNT"

2.3 Ký certificate (Self-signed – để test)
openssl x509 -req -in user_csr.csr.pem -signkey user.key.pem -days 365 -out user.crt.pem -sha256
SHA-256 bắt buộc

2.4 Thêm extensions chuẩn ký số
Tạo file ext.cnf:
basicConstraints = CA:FALSE
keyUsage = digitalSignature, nonRepudiation
extendedKeyUsage = emailProtection
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid

Ký lại:
openssl x509 -req -in CSRNTThai_user_crt_user_csr.csr_c92d25f6.crt.pem -signkey user_key.key.pem -days 365 -out NTThai_user_crt_user_csr.csr_c92d25f6.crt.pem -sha256 -extfile ext.cnf
3. Kiểm tra certificate trước khi dùng
   openssl x509 -in user.crt.pem -text -noout
































1034  git push origin develop --force-with-lease
1035  sudo apt install git
1036  git pull origin develop -f
1037  cd Desktop/
1038  ls
1039  cd CSR/
1040  openssl req -new -newkey rsa:2048 -nodes -out NTT.csr -keyout NTT.key -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=NTT/OU=IT/CN=NTT"
1041  cat NTT.csr
1042  cd Desktop/CSR/
1043  openssl req -new -newkey rsa:2048 -nodes -out THAI.csr -keyout THAI.key -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=NTT/OU=IT/CN=THAI"
1044  openssl req -new -newkey rsa:2048 -nodes -out HybridDCA.csr -keyout HybridDCA.key -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=NTT/OU=IT/CN=NTTHAI"
1045  cd hybridsmartcontract/
1046  npx hardhat node
1047  cd Desktop/
1048  mkdir BIDC_CAM
1049  cd BIDC_CAM/
1050  git clone https://git.vnpay.vn/dvnh/bidc-cam/app-backend-mb/bidc-cambodia-new.git
1051  ls
1052  pwd
1053  ssh bidccam
1054  ssh jum118
1055  ssh cpb_uat
1056  ssh jum118
1057  ls
1058  cd .git/
1059  ls
1060  cd config
1061  cat config
1062  ssh cpb_uat
1063  yarn
1064  npx hardhat node
1065  openssl ecparam -list_curves
1066  ssh jum118
1067  sha1sum '/home/nguyentthai96/Desktop/LuanVan/144fd20078d86763c317523762f7692a65eb824f (3).pem'
1068  openssl x509 -noout -fingerprint -sha1 -inform pem -in '/home/nguyentthai96/Desktop/LuanVan/144fd20078d86763c317523762f7692a65eb824f (3).pem'
1069  cat /home/nguyentthai96/.ssh/
1070  nautilus /home/nguyentthai96/.ssh/
1071  cd /opt/
1072  ls
1073  ls -la
1074  ls /opt/jsch-0.1.55/ant-jsch-1.10.11.jar
1075  ls /opt/jsch-0.1.55/jsch-0.1.55.jar
1076  ssh bidcvn
1077  mkdir /var/logs/bidc-cam/auth-service/
1078  mkdir -p /var/logs/bidc-cam/auth-service/
1079  sudo mkdir -p /var/logs/bidc-cam/auth-service/
1080  ls la /var/logs/bidc-cam/auth-service/
1081  ls -la /var/logs/bidc-cam/auth-service/
1082  sudo chown nguyentthai96:nguyentthai96 -R  /var/logs/bidc-cam
1083  ls -la /var/logs/bidc-cam/auth-service/
1084  pwd
1085  sshpass -p Pf~VGhUJVd ssh -L 22145:10.22.18.145:22 dvnh@10.22.133.118
1086  sudo apt install sshpass
1087  sshpass -p Pf~VGhUJVd ssh -L 22145:10.22.18.145:22 dvnh@10.22.133.118
1088  npx hardhat compile
1089  cd Desktop/
1090  cd CSR/
1091  mdkir democa
1092  mkdir democa
1093  cd democa/
1094  openssl ecparam -name secp256k1 -genkey -noout -out ca.key.pem
1095  ls
1096  openssl x509 -in cert.crt.pem -text -noout
1097  openssl x509 -in ca.crt.pem -text -noout
1098  openssl ecparam -name secp256k1 -genkey -noout -out ca.key.pem
1099  openssl ecparam -name secp256k1 -genkey -noout -out ca.key.pem
1100  openssl req -new -x509 -key ca.key.pem -sha256 -days 3650 -out ca.crt.pem -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=ConsortiumOrg/OU=IT/CN=HybridCA"
1101  openssl ecparam -name secp256k1 -genkey -noout -out key.key.pem
1102  openssl req -new -key -sha256 key.key.pem -out cert.csr.pem -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=ClientOrg/OU=IT/CN=ThaiNT"
1103  openssl req -new -newkey rsa:2048 -nodes -out HybridDCA.csr -keyout HybridDCA.key -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=NTT/OU=IT/CN=NTTHAI"
1104  openssl req -new -key -sha256 sign_key.key.pem -out cert.csr.pem -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=ClientOrg/OU=IT/CN=ThaiNT"
1105  openssl req -new -sha256 -key sign_key.key.pem -out cert.csr.pem -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=ClientOrg/OU=IT/CN=ThaiNT"
1106  openssl ecparam -name secp256k1 -genkey -noout -out owner_sign_key.key.pem
1107  openssl req -new -sha256 -key owner_sign_key.key.pem -out cert.csr.pem -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=ClientOrg/OU=IT/CN=ThaiNT"
1108  openssl x509 -req -in cert.csr.pem -CA ca.crt.pem -CAkey ca.key.pem -CAcreateserial -out cert.crt.pem -days 365 -sha256
1109  clear
1110  openssl x509 -in cert.crt.pem -text -noout
1111  openssl x509 -in cert.csr.pem -text -noout
1112  cat cert.csr.pem
1113  openssl req -text -noout -verify -in cert.csr.pem
1114  cd ..
1115  cd openssl_file/
1116  openssl x509 -in ca.crt.pem -text -noout
1117  openssl verify -CAfile ca.crt.pem cert.crt.pem
1118  openssl x509 -in cert.crt.pem -pubkey -noout | openssl rsa -pubin -modulus -noout | openssl md5
1119  pip install pyasn1 pyasn1-modules cryptography
1120  cd hybridsmartcontract/
1121  npx hardhat compile
1122  la
1123  rm -rf artifacts cache
1124  npx hardhat compile
1125  cp artifacts/contracts/DCALedger.sol/DCALedger.json ./compiled_contract.json
1126  ls
1127  npx hardhat node
1128  npm install uuid
1129  npm install @peculiar/x509
1130  npm audit fix
1131  npm install
1132  cat '/tmp/tmp2wyv4six'
1133  cat '/tmp/tmpt7vp3cfd'
1134  openssl ecparam -name secp256k1 -genkey -noout -out user_key.key.pem
1135  openssl req -new -sha256 -key user_key.key.pem -out user_cert.csr.pem -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=ClientOrg/OU=IT/CN=ThaiNT"
1136  sudo apt install pipx
1137  pipx ensurepath
1138  pipx install pyhanko
1139  pyhanko --version
1140  pip3 install --user pyHanko[crypto,pkcs11]
1141  ls ~/.local/bin | grep pyhanko~
1142  pyhanko-cli
1143  sudo apt install python3 python3-pip python3-venv -y
1144  cd Desktop/
1145  python3 -m venv venv
1146  source venv/bin/activate
1147  pip install pyHanko[pkcs11,crypto]
1148  pyhanko --version
1149  pip3 show pyHanko
1150  code ~/.bashrc
1151  /home/nguyentthai96/Desktop/venv/lib/python3.12/site-packages/pyhanko/
1152  pip3 install --user pyhanko-cli
1153  pip3 install  pyhanko-cli
1154  pyhanko
1155  clear
1156  pyhanko verify --pretty-print '/home/nguyentthai96/Downloads/signed_21C11026_NguyenThanhThai_PT3.pdf'
1157  pyhanko --version
1158  pyhanko --help
1159  pyhanko sign verify --pretty-print '/home/nguyentthai96/Downloads/signed_21C11026_NguyenThanhThai_PT3.pdf'
1160  npm install snarkjs
1161  cd ..
1162  npm install pdf-lib pkijs asn1js pvutils @mui/material @mui/icons-material @emotion/react @emotion/styled
1163  npm install elliptic
1164  npm install --save-dev @types/elliptic
1165  npm install elliptic
1166  npm install --save-dev @types/elliptic
1167  npm install pdf-lib pkijs asn1js pvutils elliptic @mui/material @mui/icons-material @emotion/react @emotion/styled
1168  npm install --save-dev @types/elliptic @types/node
1169  npx hardhat node
1170  pip install pyHanko[pkcs11,crypto]
1171  pip freeze > requirements.txt
1172  pyhanko --version
1173  pip install pyHanko
1174  pip freeze > requirements.txt
1175  pyhanko --version
1176  pip3 install --user pyHanko[crypto,pkcs11]
1177  pip3 install  pyHanko[crypto,pkcs11]
1178  venv/bin/pyhanko
1179  pip3 install --user pyhanko-cli[crypto,pkcs11]
1180  pip3 install pyhanko-cli[crypto,pkcs11]
1181  pip3 install --user pyhanko-cli
1182  pip3 install  pyhanko-cli
1183  npm install pkijs asn1js elliptic @types/elliptic
1184  npx hardhat node
1185  pyhanko
1186  cd Desktop/
1187  source venv/bin/activate
1188  cd /home/nguyentthai96/Downloads
1189  openssl pkcs12 -export -out user.p12 -inkey user_key.key.pem -in 41cdee82_user_crt_user_cert.csr_f40aa64d.crt.pem
1190  pyhanko sign add --field Sig1     --signer user.p12     --reason "Approved"     --location "Hanoi"     --output signed.pdf 21C11026_NguyenThanhThai_PT3.pdf
1191  pyhanko sign --help
1192  pyhanko sign addsig --field Sig1     --signer user.p12     --reason "Approved"     --location "Hanoi"     --output signed.pdf     21C11026_NguyenThanhThai_PT3.pdf
1193  pyhanko sign addsig --help
1194  clear
1195  pyhanko sign addsig     --field Sig1     --signer pemder:user_key.key.pem:41cdee82_user_crt_user_cert.csr_f40aa64d.crt.pem     --output signed.pdf     21C11026_NguyenThanhThai_PT3.pdf
1196  pyhanko sign addsig --help
1197  pyhanko sign addsig     --field Sig1     pemder:user_key.key.pem:41cdee82_user_crt_user_cert.csr_f40aa64d.crt.pem     --output signed.pdf     21C11026_NguyenThanhThai_PT3.pdf
1198  clear
1199  pyhanko sign addsig     --field Sig1     pemder:user_key.key.pem:41cdee82_user_crt_user_cert.csr_f40aa64d.crt.pem     --output signed.pdf     21C11026_NguyenThanhThai_PT3.pdf
1200  pyhanko sign pemder user_key.key.pem 41cdee82_user_crt_user_cert.csr_f40aa64d.crt.pem --out signer.json
1201  pyhanko --version
1202  pyhanko sign --help
1203  pyhanko sign addsign --help
1204  pyhanko sign --addsign --help
1205  pyhanko sign addsign --help
1206  clear
1207  pyhanko sign addsig     --field Sig1     --p12-file /đường/dẫn/tới/file_chữ_ký.p12     --output signed.pdf     21C11026_NguyenThanhThai_PT3.pdf
1208  openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=Nguyen Thanh Thai"
1209  openssl pkcs12 -export -out test_cert.p12 -inkey key.pem -in cert.pem -passout pass:123456
1210  pyhanko sign addsig     --field Sig1     --p12-file test_cert.p12     --p12-password "123456"     --output signed.pdf     21C11026_NguyenThanhThai_PT3.pdf
1211  pyhanko sign addsig --help
1212  pyhanko sign addsig pkcs12 --help
1213  pyhanko sign addsig pemder --help
1214  pyhanko sign addsig --field Sig1 pemder     --cert 41cdee82_user_crt_user_cert.csr_f40aa64d.crt.pem     --key user_key.key.pem     21C11026_NguyenThanhThai_PT3.pdf     signed.pdf
1215  pyhanko sign addsig --field Sig1 pemder     --cert 41cdee82_user_crt_user_cert.csr_f40aa64d.crt.pem     --key user_key.key.pem --no-pass    21C11026_NguyenThanhThai_PT3.pdf     signed.pdf
1216  mkdir newca
1217  cd newca/
1218  openssl ecparam -name secp256k1 -genkey -noout -out rootCA.key
1219  nano user.cnf
1220  nano ca.cnf
1221  openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 3650 -out rootCA.pem -config ca.cnf
1222  openssl ecparam -name secp256k1 -genkey -noout -out user.key
1223  openssl req -new -key user.key -out user.csr -config user.cnf
1224  openssl x509 -req -in user.csr -CA rootCA.pem -CAkey rootCA.key -CAcreateserial -out user.crt -days 365 -sha256 -extfile
1225  openssl x509 -req -in user.csr -CA rootCA.pem -CAkey rootCA.key -CAcreateserial -out user.crt -days 365 -sha256 -extfile user.cnf -extensions v3_req
1226  pyhanko sign sendsigned   --key user.key   --cert user.crt   --chain rootCA.pem   --field "Signature1"   --sig-position 1/50,150,250,200   input.pdf output_signed_visible.pdf
1227  pyhanko sign sendsigned --key user.key --cert user.crt --chain rootCA.pem input.pdf output_signed.pdf
1228  pip3 install endesive cryptography
1229  nano sign_tool.py
1230  python3 sign_tool.py input.pdf user.key user.crt doc_signed.pdf
1231  code sign_tool.py
1232  python3 sign_tool.py input.pdf user.key user.crt doc_signed.pdf
1233  sudo apt install okular
1234  sudo apt install qpdf openssl
1235  cd Downloads/
1236  qpdf --qdf '/home/nguyentthai96/Downloads/signed (1).pdf'  dsddssddssd.pdf
1237  pyhanko verify --pretty-print
1238  npx hardhat node
1239  npm install pdf-lib pkijs asn1js pvutils elliptic @mui/material @mui/icons-material @emotion/react @emotion/styled
1240  npm install --save-dev @types/elliptic
1241  npm install pdf-lib pkijs asn1js pvutils elliptic @mui/material @mui/icons-material @emotion/react @emotion/styled
1242  npm install --save-dev @types/elliptic @types/node
1243  npx hardhat node
1244  cd Downloads/
1245  grep -R "/Type /Sig" -n '/home/nguyentthai96/Downloads/dsddssddssd.pdf'
1246  qpdf --raw-stream-data=object-number out.bin "signed (1).pdf"
1247  nautilus /usr/local/share/ca-certificates/
1248  sudo update-ca-certificates
1249  ls -l /etc/ssl/certs | grep my_ca
1250  mkdir -p vn/vnpay/server/quick-jetty
1251  sudo apt install ntfs-3g
1252  sudo mount -t ntfs-3g /dev/nvme0n1p5 /mnt
1253  sudo ntfsfix /dev/nvme0n1p5
1254  ssh cpb_uat
1255  npx hardhat node
1256  ssh dvnh@10.22.133.118
1257  ssh dvnh@10.22.133.118 -p
1258  ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no dvnh@10.22.133.118
1259  ssh jump118
1260  ssh jum118
1261  ssh bidccam
1262  npx hardhat node
1263  ifconfig
1264  sudo ufw status
1265  cd ..
1266  npm install buffer
1267  openssl ecparam -name prime256v1 -genkey -noout -out ec_p256.key
1268  openssl genpkey -algorithm EC   -pkeyopt ec_paramgen_curve:prime256v1   -out ec_p256.key
1269  openssl req -new -x509   -key ec_p256.key   -sha256   -days 365   -out ec_p256.crt
1270  openssl req -new -key ec_p256.key -out user.csr
1271  openssl x509 -req   -in user.csr   -CA ca.crt   -CAkey ca.key   -CAcreateserial   -sha256   -days 365   -out user.crt
1272  openssl version
1273  cd ..
1274  sudo apt install poppler-utils
1275  pdfsig '/home/nguyentthai96/Documents/222222222aaaaaaaaaaaaaaaaaaaaa.pdf'
1276  sudo apt install qpdf
1277  qpdf --show-object=SIGNATURE_OBJ 222222222aaaaaaaaaaaaaaaaaaaaa.pdf
1278  pdfsig aaaaaaaaaaaaaaa222222222222222.pdf
1279  qpdf --show-object=SIGNATURE_OBJ aaaaaaaaaaaaaaa222222222222222.pdf
1280  cd cert_prime256v1/
1281  openssl ecparam -name prime256v1 -genkey -noout -out user.key.pem
1282  openssl ec -in user.key.pem -text -noout
1283  openssl req -new -key user.key.pem -out user.csr.pem   -subj "/C=VN/ST=HCM/L=Ho Chi Minh/O=ClientOrg/OU=IT/CN=ThaiNT"
1284  openssl x509 -req   -in user.csr.pem   -signkey user.key.pem   -days 365   -out user.crt.pem   -sha256
1285  code ext.cnf
1286  openssl x509 -req   -in user.csr.pem   -signkey user.key.pem   -days 365   -out user.crt.pem   -sha256   -extfile ext.cnf
1287  openssl x509 -in user.crt.pem -text -noout
1288  pdfsig aaaaaaaaaaa22222222222.pdf
1289  pdfsig 111111111111111111111.pdf 