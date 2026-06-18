from __future__ import annotations

import json
import os
import sys
import time
from typing import Callable

from eth_abi import decode, encode
from eth_account import Account
from eth_account.messages import encode_defunct, encode_typed_data
from eth_utils import keccak, to_checksum_address, to_hex
from web3 import Web3


HARDHAT_URL = os.environ.get("HARDHAT_URL", "http://hardhat:8545")


PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
EXPECTED_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
RECIPIENT = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
THIRD_ACCOUNT = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
HARDHAT_MNEMONIC = "test test test test test test test test test test test junk"


#Tut obrabatyvayu raw_transaction_bytes, vse po delu i bez lishnego.
def raw_transaction_bytes(signed_transaction) -> bytes:
    if hasattr(signed_transaction, "raw_transaction"):
        return signed_transaction.raw_transaction
    return signed_transaction.rawTransaction


#Zdes sobrana logika json_log, tak ee proshche podderzhivat.
def json_log(preset: str, **payload: object) -> None:
    print(json.dumps({"preset": preset, **payload}, sort_keys=True))


#Zdes sobrana logika assert_equal, tak ee proshche podderzhivat.
def assert_equal(actual: object, expected: object, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


#Tut obrabatyvayu assert_true, vse po delu i bez lishnego.
def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


#Tut ya vynes hash_pair, chtoby ne razduvat ostalnoy kod.
def hash_pair(left: bytes, right: bytes) -> bytes:
    first, second = sorted((left, right))
    return keccak(first + second)


#Tut obrabatyvayu run_wallet_checksum, vse po delu i bez lishnego.
def run_wallet_checksum() -> None:
    account = Account.from_key(PRIVATE_KEY)
    checksum = to_checksum_address(account.address.lower())

    assert_equal(account.address, EXPECTED_ADDRESS, "wallet address mismatch")
    assert_equal(checksum, EXPECTED_ADDRESS, "checksum address mismatch")

    json_log("wallet_checksum", address=account.address, checksum=checksum)


#Zdes sobrana logika run_wallet_mnemonic, tak ee proshche podderzhivat.
def run_wallet_mnemonic() -> None:
    Account.enable_unaudited_hdwallet_features()
    account = Account.from_mnemonic(HARDHAT_MNEMONIC, account_path="m/44'/60'/0'/0/0")

    assert_equal(account.address, EXPECTED_ADDRESS, "mnemonic derivation mismatch")

    json_log("wallet_mnemonic", address=account.address, derivation_path="m/44'/60'/0'/0/0")


#Funkciya run_personal_sign zakryvaet konkretnuyu zadachu v etom meste.
def run_personal_sign() -> None:
    account = Account.from_key(PRIVATE_KEY)
    message = encode_defunct(text="BlockTest personal sign preset")
    signed = Account.sign_message(message, PRIVATE_KEY)
    recovered = Account.recover_message(message, signature=signed.signature)

    assert_equal(recovered, account.address, "recovered signer mismatch")

    json_log(
        "personal_sign",
        address=account.address,
        signature=signed.signature.hex(),
        message_hash=signed.message_hash.hex(),
    )


#Tut obrabatyvayu run_eip712_sign, vse po delu i bez lishnego.
def run_eip712_sign() -> None:
    account = Account.from_key(PRIVATE_KEY)
    signable = encode_typed_data(
        domain_data={
            "name": "BlockTestPermit",
            "version": "1",
            "chainId": 1,
            "verifyingContract": RECIPIENT,
        },
        message_types={
            "Permit": [
                {"name": "owner", "type": "address"},
                {"name": "spender", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "nonce", "type": "uint256"},
                {"name": "deadline", "type": "uint256"},
            ]
        },
        message_data={
            "owner": account.address,
            "spender": THIRD_ACCOUNT,
            "value": 250000000000000000,
            "nonce": 3,
            "deadline": 1735689600,
        },
    )
    signed = Account.sign_message(signable, PRIVATE_KEY)
    recovered = Account.recover_message(signable, signature=signed.signature)

    assert_equal(recovered, account.address, "typed-data recovered signer mismatch")

    json_log(
        "eip712_sign",
        address=account.address,
        signature=signed.signature.hex(),
        message_hash=signed.message_hash.hex(),
    )


#Tut obrabatyvayu run_legacy_tx, vse po delu i bez lishnego.
def run_legacy_tx() -> None:
    account = Account.from_key(PRIVATE_KEY)
    transaction = {
        "chainId": 1,
        "nonce": 7,
        "gasPrice": 2000000000,
        "gas": 21000,
        "to": RECIPIENT,
        "value": 12345678900000000,
        "data": "0x",
    }
    signed = Account.sign_transaction(transaction, PRIVATE_KEY)
    raw = raw_transaction_bytes(signed)
    recovered = Account.recover_transaction(raw)

    assert_equal(recovered, account.address, "legacy transaction sender mismatch")

    json_log(
        "legacy_tx",
        sender=account.address,
        recipient=RECIPIENT,
        transaction_hash=signed.hash.hex(),
        raw_transaction=raw.hex(),
    )


#Funkciya run_eip1559_tx zakryvaet konkretnuyu zadachu v etom meste.
def run_eip1559_tx() -> None:
    account = Account.from_key(PRIVATE_KEY)
    transaction = {
        "chainId": 1,
        "nonce": 8,
        "type": 2,
        "maxPriorityFeePerGas": 1500000000,
        "maxFeePerGas": 30000000000,
        "gas": 21000,
        "to": THIRD_ACCOUNT,
        "value": 42000000000000000,
        "data": "0x",
    }
    signed = Account.sign_transaction(transaction, PRIVATE_KEY)
    raw = raw_transaction_bytes(signed)
    recovered = Account.recover_transaction(raw)

    assert_equal(recovered, account.address, "eip1559 transaction sender mismatch")

    json_log(
        "eip1559_tx",
        sender=account.address,
        recipient=THIRD_ACCOUNT,
        transaction_hash=signed.hash.hex(),
        raw_transaction=raw.hex(),
    )


#Tut ya vynes run_erc20_abi, chtoby ne razduvat ostalnoy kod.
def run_erc20_abi() -> None:
    selector = keccak(text="transfer(address,uint256)")[:4]
    amount = 500000000000000000
    encoded_args = encode(["address", "uint256"], [RECIPIENT, amount])
    calldata = selector + encoded_args
    decoded_recipient, decoded_amount = decode(["address", "uint256"], calldata[4:])

    assert_equal(to_checksum_address(decoded_recipient), RECIPIENT, "decoded recipient mismatch")
    assert_equal(decoded_amount, amount, "decoded amount mismatch")

    json_log(
        "erc20_abi",
        method_selector=to_hex(selector),
        calldata=to_hex(calldata),
        decoded_recipient=RECIPIENT,
        decoded_amount=amount,
    )


#Tut obrabatyvayu run_transfer_event, vse po delu i bez lishnego.
def run_transfer_event() -> None:
    topic0 = keccak(text="Transfer(address,address,uint256)")
    from_topic = bytes(12) + bytes.fromhex(EXPECTED_ADDRESS[2:])
    to_topic = bytes(12) + bytes.fromhex(RECIPIENT[2:])
    amount = 987654321000000000
    data = encode(["uint256"], [amount])

    decoded_from = to_checksum_address(from_topic[-20:])
    decoded_to = to_checksum_address(to_topic[-20:])
    decoded_amount = decode(["uint256"], data)[0]

    assert_equal(decoded_from, EXPECTED_ADDRESS, "event sender mismatch")
    assert_equal(decoded_to, RECIPIENT, "event recipient mismatch")
    assert_equal(decoded_amount, amount, "event amount mismatch")

    json_log(
        "transfer_event",
        topic0=to_hex(topic0),
        indexed_from=decoded_from,
        indexed_to=decoded_to,
        decoded_amount=decoded_amount,
    )


#Tut obrabatyvayu run_merkle_proof, vse po delu i bez lishnego.
def run_merkle_proof() -> None:
    leaves = [
        keccak(text="alice:100"),
        keccak(text="bob:55"),
        keccak(text="carol:72"),
        keccak(text="dave:33"),
    ]
    left = hash_pair(leaves[0], leaves[1])
    right = hash_pair(leaves[2], leaves[3])
    root = hash_pair(left, right)

    proof = [leaves[1], right]
    computed = leaves[0]
    for sibling in proof:
        computed = hash_pair(computed, sibling)

    assert_equal(computed, root, "merkle proof mismatch")

    json_log(
        "merkle_proof",
        leaf=to_hex(leaves[0]),
        proof=[to_hex(item) for item in proof],
        root=to_hex(root),
    )


#Tut ya vynes run_batch_signatures, chtoby ne razduvat ostalnoy kod.
def run_batch_signatures() -> None:
    start = time.perf_counter()
    last_signature = ""
    for index in range(250):
        message = encode_defunct(text=f"batch-signature-{index}")
        signed = Account.sign_message(message, PRIVATE_KEY)
        recovered = Account.recover_message(message, signature=signed.signature)
        assert_equal(recovered, EXPECTED_ADDRESS, "batch recovered signer mismatch")
        last_signature = signed.signature.hex()

    elapsed = time.perf_counter() - start
    throughput = round(250 / elapsed, 2) if elapsed else 0.0

    json_log(
        "batch_signatures",
        iterations=250,
        elapsed_seconds=round(elapsed, 4),
        throughput_per_second=throughput,
        last_signature=last_signature,
    )


#Tut ya vynes run_revert_reason, chtoby ne razduvat ostalnoy kod.
def run_revert_reason() -> None:
    selector = keccak(text="Error(string)")[:4]
    revert_reason = "ERC20: transfer amount exceeds balance"
    payload = selector + encode(["string"], [revert_reason])
    decoded_reason = decode(["string"], payload[4:])[0]

    assert_equal(decoded_reason, revert_reason, "decoded revert reason mismatch")

    json_log(
        "revert_reason",
        selector=to_hex(selector),
        payload=to_hex(payload),
        decoded_reason=decoded_reason,
    )


#Zdes sobrana logika run_tampered_signature, tak ee proshche podderzhivat.
def run_tampered_signature() -> None:
    message = encode_defunct(text="BlockTest signature tamper preset")
    signed = Account.sign_message(message, PRIVATE_KEY)
    tampered_signature = bytearray(signed.signature)
    tampered_signature[-1] ^= 0x01

    try:
        recovered = Account.recover_message(message, signature=bytes(tampered_signature))
    except ValueError:
        recovered = "invalid-signature"

    assert_true(recovered != EXPECTED_ADDRESS, "tampered signature unexpectedly recovered original signer")

    json_log(
        "tampered_signature",
        original_signature=signed.signature.hex(),
        tampered_signature=bytes(tampered_signature).hex(),
        recovered=recovered,
    )


#Funkciya run_access_list_tx zakryvaet konkretnuyu zadachu v etom meste.
def run_access_list_tx() -> None:
    account = Account.from_key(PRIVATE_KEY)
    transaction = {
        "chainId": 1,
        "nonce": 11,
        "type": 1,
        "gasPrice": 2500000000,
        "gas": 35000,
        "to": RECIPIENT,
        "value": 0,
        "data": "0x",
        "accessList": [{"address": RECIPIENT, "storageKeys": []}],
    }
    signed = Account.sign_transaction(transaction, PRIVATE_KEY)
    raw = raw_transaction_bytes(signed)
    recovered = Account.recover_transaction(raw)

    assert_equal(recovered, account.address, "access-list transaction sender mismatch")

    json_log(
        "access_list_tx",
        sender=account.address,
        recipient=RECIPIENT,
        transaction_hash=signed.hash.hex(),
        raw_transaction=raw.hex(),
    )


#Eto otdelnyy shag run_json_telemetry, chtoby ne kopipastit odno i to zhe.
def run_json_telemetry() -> None:
    phases = [
        ("setup", "Load deterministic wallet fixtures"),
        ("execution", "Sign transaction and recover sender"),
        ("verification", "Validate decoded fields and counters"),
    ]
    for index, (phase, detail) in enumerate(phases, start=1):
        json_log(
            "json_telemetry",
            checkpoint=index,
            phase=phase,
            detail=detail,
            elapsed_ms=index * 35,
            severity="info",
        )


#Eto otdelnyy shag run_batch_abi, chtoby ne kopipastit odno i to zhe.
def run_batch_abi() -> None:
    selector = keccak(text="transfer(address,uint256)")[:4]
    start = time.perf_counter()
    last_payload = b""
    for index in range(500):
        encoded_args = encode(["address", "uint256"], [RECIPIENT, index + 1])
        last_payload = selector + encoded_args

    elapsed = time.perf_counter() - start
    throughput = round(500 / elapsed, 2) if elapsed else 0.0

    json_log(
        "batch_abi",
        iterations=500,
        elapsed_seconds=round(elapsed, 4),
        throughput_per_second=throughput,
        last_calldata=to_hex(last_payload),
    )


COUNTER_ABI = [
    {
        "inputs": [],
        "name": "count",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "get",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "increment",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

COUNTER_BYTECODE = (
    "608060405234801561000f575f80fd5b506101778061001d5f395ff3fe"
    "608060405234801561000f575f80fd5b506004361061003f575f3560e01c"
    "806306661abd146100435780636d4ce63c14610061578063d09de08a1461007f575b5f80fd"
    "5b61004b610089565b60405161005891906100c8565b60405180910390f35b61006961008e565b"
    "60405161007691906100c8565b60405180910390f35b610087610096565b005b5f5481565b5f805490"
    "5090565b60015f808282546100a7919061010e565b92505081905550565b5f819050919050565b"
    "6100c2816100b0565b82525050565b5f6020820190506100db5f8301846100b9565b92915050565b"
    "7f4e487b71000000000000000000000000000000000000000000000000000000005f526011600452"
    "60245ffd5b5f610118826100b0565b9150610123836100b0565b925082820190508082111561013b"
    "5761013a6100e1565b5b9291505056fea2646970667358221220e8d2144b2b5714abf70ee7b89bc815"
    "b1ba0dfe934e8f5d55b8b62b704eb10e2664736f6c63430008180033"
)


#Zdes sobrana logika _get_web3, tak ee proshche podderzhivat.
def _get_web3() -> Web3:
    w3 = Web3(Web3.HTTPProvider(HARDHAT_URL))
    assert_true(w3.is_connected(), f"cannot connect to Hardhat node at {HARDHAT_URL}")
    return w3


#Tut ya vynes run_node_health, chtoby ne razduvat ostalnoy kod.
def run_node_health() -> None:
    w3 = _get_web3()
    chain_id = w3.eth.chain_id
    block = w3.eth.block_number
    json_log("node_health", url=HARDHAT_URL, chain_id=chain_id, block_number=block)


#Tut obrabatyvayu run_balance_check, vse po delu i bez lishnego.
def run_balance_check() -> None:
    w3 = _get_web3()
    balance_wei = w3.eth.get_balance(EXPECTED_ADDRESS)
    assert_true(balance_wei > 0, f"expected non-zero balance for {EXPECTED_ADDRESS}")
    json_log(
        "balance_check",
        address=EXPECTED_ADDRESS,
        balance_wei=str(balance_wei),
        balance_eth=str(w3.from_wei(balance_wei, "ether")),
    )


#Tut obrabatyvayu run_eth_transfer, vse po delu i bez lishnego.
def run_eth_transfer() -> None:
    w3 = _get_web3()
    amount = w3.to_wei(0.1, "ether")
    recipient_before = w3.eth.get_balance(RECIPIENT)
    tx = {
        "chainId": 31337,
        "nonce": w3.eth.get_transaction_count(EXPECTED_ADDRESS),
        "gasPrice": w3.eth.gas_price,
        "gas": 21000,
        "to": RECIPIENT,
        "value": amount,
        "data": "0x",
    }
    signed = Account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(raw_transaction_bytes(signed))
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    assert_equal(receipt["status"], 1, "transfer transaction reverted")
    recipient_after = w3.eth.get_balance(RECIPIENT)
    assert_true(recipient_after > recipient_before, "recipient balance did not increase")
    json_log(
        "eth_transfer",
        from_address=EXPECTED_ADDRESS,
        to_address=RECIPIENT,
        amount_eth="0.1",
        tx_hash=receipt["transactionHash"].hex(),
        block_number=receipt["blockNumber"],
        status=receipt["status"],
    )


#Funkciya run_deploy_counter zakryvaet konkretnuyu zadachu v etom meste.
def run_deploy_counter() -> None:
    w3 = _get_web3()
    Counter = w3.eth.contract(abi=COUNTER_ABI, bytecode=COUNTER_BYTECODE)
    gas_price = w3.eth.gas_price

    deploy_tx = Counter.constructor().build_transaction({
        "chainId": 31337,
        "from": EXPECTED_ADDRESS,
        "nonce": w3.eth.get_transaction_count(EXPECTED_ADDRESS),
        "gasPrice": gas_price,
    })
    signed = Account.sign_transaction(deploy_tx, PRIVATE_KEY)
    deploy_hash = w3.eth.send_raw_transaction(raw_transaction_bytes(signed))
    deploy_receipt = w3.eth.wait_for_transaction_receipt(deploy_hash)
    assert_equal(deploy_receipt["status"], 1, "deploy transaction reverted")

    contract_address = deploy_receipt["contractAddress"]
    counter = w3.eth.contract(address=contract_address, abi=COUNTER_ABI)

    inc_tx = counter.functions.increment().build_transaction({
        "chainId": 31337,
        "from": EXPECTED_ADDRESS,
        "nonce": w3.eth.get_transaction_count(EXPECTED_ADDRESS),
        "gasPrice": gas_price,
    })
    signed = Account.sign_transaction(inc_tx, PRIVATE_KEY)
    inc_hash = w3.eth.send_raw_transaction(raw_transaction_bytes(signed))
    inc_receipt = w3.eth.wait_for_transaction_receipt(inc_hash)
    assert_equal(inc_receipt["status"], 1, "increment transaction reverted")

    count = counter.functions.get().call()
    assert_equal(count, 1, "counter value mismatch after increment")

    json_log(
        "deploy_counter",
        contract_address=contract_address,
        deploy_tx_hash=deploy_receipt["transactionHash"].hex(),
        increment_tx_hash=inc_receipt["transactionHash"].hex(),
        counter_value=count,
    )


PRESETS: dict[str, Callable[[], None]] = {
    "wallet_checksum": run_wallet_checksum,
    "wallet_mnemonic": run_wallet_mnemonic,
    "personal_sign": run_personal_sign,
    "eip712_sign": run_eip712_sign,
    "legacy_tx": run_legacy_tx,
    "eip1559_tx": run_eip1559_tx,
    "erc20_abi": run_erc20_abi,
    "transfer_event": run_transfer_event,
    "merkle_proof": run_merkle_proof,
    "batch_signatures": run_batch_signatures,
    "revert_reason": run_revert_reason,
    "tampered_signature": run_tampered_signature,
    "access_list_tx": run_access_list_tx,
    "json_telemetry": run_json_telemetry,
    "batch_abi": run_batch_abi,
    "node_health": run_node_health,
    "balance_check": run_balance_check,
    "eth_transfer": run_eth_transfer,
    "deploy_counter": run_deploy_counter,
}


#Tut obrabatyvayu main, vse po delu i bez lishnego.
def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in PRESETS:
        available = ", ".join(sorted(PRESETS))
        print(f"Usage: python run_preset.py <preset>; available: {available}", file=sys.stderr)
        return 2

    PRESETS[sys.argv[1]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
