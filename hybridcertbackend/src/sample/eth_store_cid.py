from web3 import Web3
import os

WEB3_PROVIDER = os.environ["WEB3_PROVIDER"]  # e.g. Infura endpoint
PRIVATE_KEY = os.environ["PRIVATE_KEY"]
CONTRACT_ADDRESS = os.environ["CONTRACT_ADDRESS"]
ABI = [...]  # ABI from compiled contract

w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))
acct = w3.eth.account.from_key(PRIVATE_KEY)
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

def eth_store_cid(cid):
    nonce = w3.eth.get_transaction_count(acct.address)
    tx = contract.functions.storeCID(cid).build_transaction({
        "chainId": w3.eth.chain_id,
        "gas": 200000,
        "gasPrice": w3.to_wei("10", "gwei"),
        "nonce": nonce
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return {"tx_hash": tx_hash.hex(), "receipt": dict(tx_receipt)}
