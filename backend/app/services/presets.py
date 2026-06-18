from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import ROOT_DIR


PRESET_PROJECT_NAME = "BlockTest EVM Presets"
PRESET_PROJECT_DESCRIPTION = (
    "Auto-created Ethereum/EVM preset suite with ready-to-run blockchain checks, diagnostics, and load scenarios."
)
PRESET_IMAGE = "blocktest-evm-presets:latest"
PRESET_BUILD_CONTEXT = ROOT_DIR / "presets" / "evm"
LOCAL_DOCKER_IMAGE_BUILDERS: dict[str, Path] = {PRESET_IMAGE: PRESET_BUILD_CONTEXT}


@dataclass(frozen=True)
class PresetDefinition:
    name: str
    description: str
    scenario: str
    command: str
    docker_image: str = PRESET_IMAGE


PRESET_TESTS: tuple[PresetDefinition, ...] = (
    PresetDefinition(
        name="Wallet: Checksum address derivation",
        description="Derives an Ethereum account from a private key and validates the EIP-55 checksum.",
        scenario="Recover a deterministic wallet address from a fixed private key and verify its checksum casing.",
        command="python /opt/blocktest-presets/run_preset.py wallet_checksum",
    ),
    PresetDefinition(
        name="Wallet: HD mnemonic derivation",
        description="Derives the first Ethereum account from the standard Hardhat mnemonic.",
        scenario="Enable HD wallet support, derive m/44'/60'/0'/0/0 and verify the expected address.",
        command="python /opt/blocktest-presets/run_preset.py wallet_mnemonic",
    ),
    PresetDefinition(
        name="Signature: Personal message recovery",
        description="Signs an EIP-191 personal message and recovers the signer address.",
        scenario="Create a defunct Ethereum message, sign it, and prove that address recovery matches the source wallet.",
        command="python /opt/blocktest-presets/run_preset.py personal_sign",
    ),
    PresetDefinition(
        name="Signature: Typed data EIP-712",
        description="Signs structured typed data and validates signer recovery.",
        scenario="Use EIP-712 typed data for a permit-like message and verify the recovered wallet address.",
        command="python /opt/blocktest-presets/run_preset.py eip712_sign",
    ),
    PresetDefinition(
        name="Transaction: Legacy transfer signing",
        description="Builds and signs a legacy Ethereum transaction offline.",
        scenario="Construct a legacy transfer transaction, sign it, and recover the sender from the raw bytes.",
        command="python /opt/blocktest-presets/run_preset.py legacy_tx",
    ),
    PresetDefinition(
        name="Transaction: EIP-1559 transfer signing",
        description="Builds and signs a type-2 Ethereum transaction offline.",
        scenario="Construct an EIP-1559 transaction with max fees, sign it, and recover the sender from the raw bytes.",
        command="python /opt/blocktest-presets/run_preset.py eip1559_tx",
    ),
    PresetDefinition(
        name="Contract: ERC20 transfer ABI",
        description="Encodes and decodes an ERC20 transfer call payload.",
        scenario="Generate calldata for transfer(address,uint256), then decode the payload back into recipient and amount.",
        command="python /opt/blocktest-presets/run_preset.py erc20_abi",
    ),
    PresetDefinition(
        name="Contract: Transfer event decoding",
        description="Builds and decodes a canonical ERC20 Transfer event log.",
        scenario="Compute the Transfer event topic, assemble indexed topics and data, and decode them back into event fields.",
        command="python /opt/blocktest-presets/run_preset.py transfer_event",
    ),
    PresetDefinition(
        name="Protocol: Merkle proof verification",
        description="Builds a small Merkle tree with keccak hashing and verifies an inclusion proof.",
        scenario="Hash a few leaves, construct a Merkle root, and verify that a proof reconstructs the same root.",
        command="python /opt/blocktest-presets/run_preset.py merkle_proof",
    ),
    PresetDefinition(
        name="Load: Batch signature benchmark",
        description="Executes a synthetic blockchain-oriented load test by signing and recovering 250 messages.",
        scenario="Perform a burst of signature and recovery operations and report elapsed time and throughput.",
        command="python /opt/blocktest-presets/run_preset.py batch_signatures",
    ),
    PresetDefinition(
        name="Debug: Revert reason decoding",
        description="Encodes and decodes a standard Solidity revert payload for root-cause analysis.",
        scenario="Build an Error(string) revert payload and recover the revert reason text from the bytes.",
        command="python /opt/blocktest-presets/run_preset.py revert_reason",
    ),
    PresetDefinition(
        name="Security: Tampered signature rejection",
        description="Verifies that a modified signature does not recover to the trusted signer.",
        scenario="Sign a message, tamper with the signature, and assert that recovery no longer matches the original wallet.",
        command="python /opt/blocktest-presets/run_preset.py tampered_signature",
    ),
    PresetDefinition(
        name="Transaction: Access-list signing",
        description="Signs and recovers an EIP-2930 access-list transaction offline.",
        scenario="Construct a type-1 transaction with an access list and verify the recovered sender.",
        command="python /opt/blocktest-presets/run_preset.py access_list_tx",
    ),
    PresetDefinition(
        name="Monitoring: Structured telemetry stream",
        description="Emits JSON checkpoints that are useful for log parsing and monitoring demos.",
        scenario="Print multiple telemetry events for setup, execution, and verification phases.",
        command="python /opt/blocktest-presets/run_preset.py json_telemetry",
    ),
    PresetDefinition(
        name="Load: ABI encoding benchmark",
        description="Measures throughput for repeated ERC20 calldata generation.",
        scenario="Encode 500 transfer payloads and report elapsed time and throughput for regression tracking.",
        command="python /opt/blocktest-presets/run_preset.py batch_abi",
    ),
    PresetDefinition(
        name="Live: Hardhat node health",
        description="Подключается к запущенной Hardhat-ноде и проверяет идентификатор сети и номер блока.",
        scenario="Установить RPC-соединение с локальной Hardhat-нодой и убедиться, что она возвращает chainId 31337.",
        command="python /opt/blocktest-presets/run_preset.py node_health",
    ),
    PresetDefinition(
        name="Live: Hardhat account balance",
        description="Запрашивает ETH-баланс первого аккаунта Hardhat через JSON-RPC.",
        scenario="Подключиться к Hardhat, вызвать eth_getBalance для стандартного адреса с балансом и убедиться, что баланс ненулевой.",
        command="python /opt/blocktest-presets/run_preset.py balance_check",
    ),
    PresetDefinition(
        name="Live: Hardhat ETH transfer",
        description="Подписывает и отправляет реальную транзакцию перевода ETH на Hardhat-ноду.",
        scenario="Подписать транзакцию перевода 0.1 ETH офлайн, отправить её на Hardhat, дождаться квитанции и убедиться, что баланс получателя вырос.",
        command="python /opt/blocktest-presets/run_preset.py eth_transfer",
    ),
    PresetDefinition(
        name="Live: Counter contract compile and deploy",
        description="Компилирует Solidity-контракт Counter через solc 0.8.24, деплоит его на Hardhat, вызывает increment и проверяет состояние в сети.",
        scenario="Скомпилировать Counter.sol, задеплоить подписанной транзакцией, вызвать increment, затем прочитать count через eth_call и убедиться, что значение равно 1.",
        command="python /opt/blocktest-presets/run_preset.py deploy_counter",
    ),
)
