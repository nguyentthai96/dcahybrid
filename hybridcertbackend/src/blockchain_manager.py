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
            # Load ABI và Bytecode
            with open('compiled_contract.json', 'r') as f:
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

        except FileNotFoundError as e:
            print("[Blockchain] Warning: 'compiled_contract.json' not found. Cannot deploy.")
            print("Exception message:", e)
            traceback.print_exc()
        except Exception as e:
            print("[Blockchain] Unexpected error during contract deployment.")
            print("Exception message:", e)
            traceback.print_exc()

    def submit_root_on_chain(self, root_hex, proof_bytes):
        if not self.contract: return None

        # Hàm updateRoot(bytes32 newRoot) trong Solidity
        tx = self.contract.functions.updateRoot(
            bytes.fromhex(root_hex)  # bytes32 cần kiểu bytes "0x" + root_hex
        ).build_transaction({
            'from': self.account, #.address,
            'nonce': self.w3.eth.get_transaction_count(self.account),
            'gas': 500000,
            'gasPrice': self.w3.to_wei('1', 'gwei')
        })
        signed_tx = self.w3.eth.account.sign_transaction(tx, DEPLOYER_PRIVATE_KEY)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_hash.hex()