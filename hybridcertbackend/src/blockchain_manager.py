import os
import traceback

from web3 import Web3
import json


# Cấu hình Hardhat Local
HARDHAT_URL = "http://127.0.0.1:8545"
CHAIN_ID = 31337  # Hardhat default chain id
# Private key mặc định của Account #0 trong Hardhat (Test only!)
DEPLOYER_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
# Ganache
# DEPLOYER_PRIVATE_KEY = "0x57fd59f097e3d71b5206b37891521db8c5aa8e02411c3432567f770cfa67d1a9"

class HardhatClient:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(HARDHAT_URL))
        if not self.w3.is_connected():
            raise Exception("Cannot connect to Hardhat node at " + HARDHAT_URL)

        # Lấy account đầu tiên làm Admin (người deploy/update)
        self.account = self.w3.eth.accounts[0]
        # self.account = self.w3.eth.account.from_key(DEPLOYER_PRIVATE_KEY)
        self.contract_address = None
        self.contract = None
        self.abi = None
        print(f"[Blockchain] Connected. Admin: {self.account}")

    def deploy_contract(self):
        """Deploy Smart Contract CA_Ledger"""
        # ABI và Bytecode (compile file .sol)
        # code logic deploy
        # file compiled_contract.json từ bước compile Solidity
        try:
            # Load ABI và Bytecode, cp artifacts/contracts/DCALedger.sol/DCALedger.json ./compiled_contract.json
            smartcontract_path = os.path.join('../../hybridsmartcontract', "compiled_contract.json")
            with open(smartcontract_path, 'r') as f:
                data = json.load(f)
                self.abi = data['abi']
                bytecode = data['bytecode']
            print("[Blockchain] Loaded ABI and Bytecode successfully.")

            # Tạo contract object
            Contract = self.w3.eth.contract(abi=self.abi, bytecode=bytecode)

            # Build transaction
            tx = Contract.constructor().build_transaction({
                'from': self.account, #.address
                'nonce': self.w3.eth.get_transaction_count(self.account), # .address
                'gas': 20000000,
                'gasPrice': self.w3.to_wei('1', 'gwei')
            })
            print(f"[Blockchain] constructor address", self.account)
            # Sign & Send
            signed_tx = self.w3.eth.account.sign_transaction(tx, DEPLOYER_PRIVATE_KEY)
            print(dir(signed_tx))
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f"[Blockchain] Transaction sent. TX Hash: {tx_hash.hex()}")

            # Wait for receipt
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            self.contract_address = tx_receipt.contractAddress
            self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)
            print(f"[Blockchain] Contract deployed at: {self.contract_address}")
        #
        except FileNotFoundError as e:
            print("[Blockchain] Warning: 'compiled_contract.json' not found. Cannot deploy.")
            print("Exception message:", e)
            traceback.print_exc()
        except Exception as e:
            print("[Blockchain] Unexpected error during contract deployment.")
            print("Exception message:", e)
            traceback.print_exc()

    def submit_root_on_chain(self, root_hex, public_signals):
        """
        root_hex: Merkle Root (Hex String không có 0x)
        zk_public_signals: Số dạng chuỗi (đầu ra của Poseidon/Circom)
        zk_proof_json Chuỗi JSON của proof, kiểm tra ở client
        """
        if not self.contract: return None
        try:
            # OLD remove Hàm updateRoot(bytes32 newRoot) trong Solidity
            # Solidity: function submitCertificateProof(bytes32, uint256, string)
            tx = self.contract.functions.submitCertificate(
                bytes.fromhex(root_hex),  # bytes32 cần kiểu bytes "0x" + root_hex
                int(public_signals),      # uint256 (Convert string số sang int)
            ).build_transaction({
                'from': self.account, #.address,
                'nonce': self.w3.eth.get_transaction_count(self.account),
                'gas': 800000,
                'gasPrice': self.w3.to_wei('2', 'gwei')  # Tăng gas price chút sẽ nhanh
            })
            signed_tx = self.w3.eth.account.sign_transaction(tx, DEPLOYER_PRIVATE_KEY)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

            # Wait receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"[Blockchain] Transaction confirmed in block {receipt.blockNumber}")
            return tx_hash.hex()

        except Exception as e:
            print(f"[Blockchain Error] {str(e)}")
            traceback.print_exc()
            return None

    def get_signal_from_tx(self, tx_hash_hex):
        """
        Input: Transaction Hash (string hex)
        Output: Public Signal (int) tìm thấy trong sự kiện của giao dịch đó
        """
        if not self.contract: return None
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash_hex)
            if receipt['status'] != 1:
                print(f"[Blockchain] Transaction {tx_hash_hex} failed.")
                return None

            # 2. Lọc sự kiện 'CertificateCommitted' từ logs của receipt
            # contract.events.<EventName>().process_receipt(receipt) giúp parse log tự động
            logs = self.contract.events.CertificateCommitted().process_receipt(receipt)

            if not logs:
                print("[Blockchain] Không tìm thấy sự kiện CertificateCommitted trong Tx này.")
                return None

            # 3. Lấy dữ liệu từ sự kiện đầu tiên tìm thấy
            # Cấu trúc log: args -> {'root': ..., 'publicSignal': 12345, 'timestamp': ...}
            event_args = logs[0]['args']
            if not event_args: return None
            # old_root = event_args['oldRoot']
            # new_root = event_args['newRoot']
            on_chain_signal = event_args['publicSignal']
            timestamp = event_args['timestamp']
            print(f"[Blockchain] Timestamp: {timestamp}  {tx_hash_hex} with Signal: {on_chain_signal}")
            emitter_ethernal = on_chain_signal.to_bytes(32, 'big').hex()
            print(f"[Blockchain] Tìm thấy Signal trên Chain: {on_chain_signal}  -  Signal: {emitter_ethernal}")
            return on_chain_signal
        except Exception as e:
            print(f"[Blockchain Error] Lỗi khi đọc Tx: {e}")
            traceback.print_exc()
            return None