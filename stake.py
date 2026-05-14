import os
import sys
import json
import time
import logging
from web3 import Web3
from dotenv import load_dotenv
from colorama import Fore, Style, init
from utils.banner import show_banner

init(autoreset=True)
load_dotenv()

logging.getLogger("web3").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("requests").setLevel(logging.CRITICAL)

MY_PROJECT = "Simplechain Stake"

G = Fore.GREEN + Style.BRIGHT
Y = Fore.YELLOW + Style.BRIGHT
R = Fore.RED + Style.BRIGHT
X = Style.RESET_ALL

RPC_URL = "https://rpc-c.simplechain.com"
CHAIN_ID = 1913
STAKE_CONTRACT = "0x0000000000000000000000000000000000002002"
STAKE_AMOUNT_WEI = Web3.to_wei(1, "ether")

DELEGATE_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "operatorAddress", "type": "address"},
            {"internalType": "bool", "name": "delegateVotePower", "type": "bool"}
        ],
        "name": "delegate",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]


def log_g(msg):
    print(f"{G}{msg}{X}")


def log_y(msg):
    print(f"{Y}{msg}{X}")


def log_r(msg):
    print(f"{R}{msg}{X}")


def load_private_keys():
    keys = []
    i = 1
    while True:
        key = os.getenv(f"PRIVATEKEY_{i}")
        if not key:
            break
        keys.append(key.strip())
        i += 1
    return keys


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)


def countdown(seconds):
    while seconds > 0:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        print(f"\r{Y}Next cycle starts in {h:02d}:{m:02d}:{s:02d}{X}", end="", flush=True)
        time.sleep(1)
        seconds -= 1
    print()


def delegate_to_operator(w3, contract, account, operator_name, operator_address, nonce):
    log_g(f"Initiating delegation to {operator_name} at {operator_address}")
    try:
        tx = contract.functions.delegate(
            Web3.to_checksum_address(operator_address),
            False
        ).build_transaction({
            "from": account.address,
            "value": STAKE_AMOUNT_WEI,
            "chainId": CHAIN_ID,
            "nonce": nonce,
            "gas": 300000,
            "gasPrice": w3.eth.gas_price,
        })
        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        log_y(f"Transaction submitted for {operator_name}, hash {tx_hash.hex()}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status == 1:
            log_g(f"Delegation to {operator_name} confirmed in block {receipt.blockNumber}")
            return True, nonce + 1
        else:
            log_r(f"Delegation to {operator_name} reverted on chain in block {receipt.blockNumber}")
            return False, nonce + 1
    except Exception as e:
        log_r(f"Delegation to {operator_name} failed with error: {e}")
        return False, nonce + 1


def process_account(w3, contract, private_key, config, index):
    try:
        account = w3.eth.account.from_key(private_key)
        log_g(f"Processing account {index} with address {account.address}")

        balance = w3.eth.get_balance(account.address)
        balance_eth = Web3.from_wei(balance, "ether")
        log_g(f"Current balance is {balance_eth:.4f} SRW")

        if balance < STAKE_AMOUNT_WEI:
            log_r(f"Account {index} has insufficient balance to delegate, skipping this account")
            return

        operators = config.get("operators", {})
        enabled_operators = {k: v for k, v in operators.items() if v.get("enabled", False)}

        if not enabled_operators:
            log_y(f"No operators are enabled for account {index}, skipping this account")
            return

        log_y(f"Found {len(enabled_operators)} enabled operator(s) to delegate for account {index}")

        nonce = w3.eth.get_transaction_count(account.address, "pending")
        success_count = 0

        for name, info in enabled_operators.items():
            success, nonce = delegate_to_operator(
                w3, contract, account, name, info["address"], nonce
            )
            if success:
                success_count += 1
            time.sleep(2)

        log_g(f"Account {index} completed delegation to {success_count} of {len(enabled_operators)} operator(s)")

    except Exception as e:
        log_r(f"Account {index} encountered a critical error: {e}")


def main():
    show_banner(MY_PROJECT)

    keys = load_private_keys()
    if not keys:
        log_r("No private keys found in the environment file, exiting")
        sys.exit(1)

    log_g(f"Loaded {len(keys)} account(s) from environment")

    try:
        config = load_config()
    except Exception as e:
        log_r(f"Failed to load configuration file: {e}")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        log_r("Failed to connect to SimpleChain RPC endpoint, exiting")
        sys.exit(1)

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(STAKE_CONTRACT),
        abi=DELEGATE_ABI
    )

    cycle = 1
    while True:
        log_g(f"Starting delegation cycle {cycle}")

        for i, key in enumerate(keys, 1):
            process_account(w3, contract, key, config, i)
            if i < len(keys):
                print()

        print()
        log_y(f"Cycle {cycle} completed for all accounts")
        sleep_seconds = config.get("sleep_seconds", 3600)
        countdown(sleep_seconds)
        cycle += 1


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        log_r("Script stopped by user")
