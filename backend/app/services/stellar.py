"""Execution layer — Stellar testnet path payment (or clearly-labeled simulation).

If `stellar-sdk` is installed AND STELLAR_SECRET_KEY is set, a real testnet
path payment is attempted. Any failure — or absence of the SDK/keys — falls
back to a deterministic simulated hash. `network` is ALWAYS explicit:
"TESTNET" | "SIMULATED". PII never touches the ledger; only the memo + hash.
"""
import hashlib
import os
import uuid

try:
    import stellar_sdk  # noqa: F401

    STELLAR_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover
    STELLAR_SDK_AVAILABLE = False

HORIZON_TESTNET = "https://horizon-testnet.stellar.org"


def _memo(tx_seed: str) -> str:
    return "BM-" + hashlib.sha256(tx_seed.encode()).hexdigest()[:8].upper()


def _simulated_hash(tx_seed: str) -> str:
    return hashlib.sha256(("borderless-money:" + tx_seed).encode()).hexdigest()


def execute_path_payment(route_name: str, amount_source: float, source_asset: str = "AED",
                         dest_asset: str = "BDT") -> dict:
    """Settle via Stellar testnet when configured; else return a simulated result."""
    tx_seed = uuid.uuid4().hex
    memo = _memo(tx_seed)

    secret = os.environ.get("STELLAR_SECRET_KEY")
    if STELLAR_SDK_AVAILABLE and secret:
        try:
            from stellar_sdk import Asset, Keypair, Network, Server, TransactionBuilder

            server = Server(HORIZON_TESTNET)
            source = Keypair.from_secret(secret)
            account = server.load_account(source.public_key)
            tx = (
                TransactionBuilder(account, Network.TESTNET_NETWORK_PASSPHRASE)
                .add_text_memo(memo)
                .append_path_payment_strict_receive_op(
                    destination=source.public_key,  # demo: self-hosted anchor loop
                    send_code=source_asset, send_issuer=source.public_key,
                    dest_code=dest_asset, dest_issuer=source.public_key,
                    send_max=str(amount_source), dest_amount=str(amount_source),
                )
                .build()
            )
            tx.sign(source)
            response = server.submit_transaction(tx)
            return {
                "status": "COMPLETED",
                "stellar_hash": response["hash"],
                "network": "TESTNET",
                "simulated": False,
                "memo": memo,
                "explorer_url": f"https://stellar.expert/explorer/testnet/tx/{response['hash']}",
            }
        except Exception as exc:  # noqa: BLE001 - fall back, but say why
            fallback_reason = str(exc)
    else:
        fallback_reason = "stellar-sdk or STELLAR_SECRET_KEY not configured"

    return {
        "status": "COMPLETED",
        "stellar_hash": _simulated_hash(tx_seed),
        "network": "SIMULATED",
        "simulated": True,
        "memo": memo,
        "fallback_reason": fallback_reason,
        "explorer_url": None,
    }
