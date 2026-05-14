import os
import sys
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_defunct
from colorama import Fore, Style, init
import pyfiglet

load_dotenv()
init(autoreset=False)

GREEN = Fore.GREEN + Style.BRIGHT
YELLOW = Fore.YELLOW + Style.BRIGHT
RED = Fore.RED + Style.BRIGHT
CYAN = Fore.CYAN + Style.BRIGHT
MAGENTA = Fore.MAGENTA + Style.BRIGHT
BOLD = Style.BRIGHT
RESET = Style.RESET_ALL

BASE_URL = "https://task.simplechain.com/api/v1"
INVITE_CODE = "9v5kef2828e"

SKIP_TASK_CODES = {
    "INVITE_FRIEND",
    "SHARE_TWITTER",
    "COMMENT_TWITTER",
    "FOLLOW_TWITTER",
    "TELEGRAM_JOIN",
    "CLAIM_TEST_TOKEN",
}

HEADERS_BASE = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-JP,en;q=0.9,ja-JP;q=0.8,ja;q=0.7,id-ID;q=0.6,id;q=0.5,en-GB;q=0.4,en-US;q=0.3",
    "content-type": "application/json",
    "origin": "https://task.simplechain.com",
    "referer": f"https://task.simplechain.com/?inviteCode={INVITE_CODE}",
    "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
}


def LG(msg):
    print(f"{GREEN}{msg}{RESET}")


def LY(msg):
    print(f"{YELLOW}{msg}{RESET}")


def LR(msg):
    print(f"{RED}{msg}{RESET}")


def banner():
    os.system("cls" if os.name == "nt" else "clear")
    ascii_art = pyfiglet.figlet_format("Yuurisandesu", font="standard").rstrip("\n")
    print(Fore.CYAN + Style.BRIGHT + ascii_art + RESET)
    print(Fore.MAGENTA + Style.BRIGHT + "Welcome to Yuuri, Simplechain" + RESET)
    LG("Ready to hack the world?")
    print(f"{YELLOW}{BOLD}Current time: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}{RESET}\n")


def set_title():
    sys.stdout.write("\033]2;Simplechain by : 佐賀県産 (YUURI)\007")
    sys.stdout.flush()


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


def get_nonce(address):
    try:
        resp = requests.post(
            f"{BASE_URL}/get/nonce",
            headers=HEADERS_BASE,
            json={"address": address},
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            return None, None
        return data["data"]["nonce"], data["data"]["message"]
    except Exception:
        return None, None


def get_token(signature, message, address):
    try:
        resp = requests.post(
            f"{BASE_URL}/login",
            headers=HEADERS_BASE,
            json={
                "signature": signature,
                "message": message,
                "address": address,
                "inviteCode": INVITE_CODE,
            },
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            return None
        return data["data"]["token"]
    except Exception:
        return None


def get_checkin_status(token):
    try:
        headers = {**HEADERS_BASE, "authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{BASE_URL}/campaign/checkin/status",
            headers=headers,
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            return None
        return data["data"]
    except Exception:
        return None


def do_checkin(token):
    try:
        headers = {**HEADERS_BASE, "authorization": f"Bearer {token}"}
        resp = requests.post(
            f"{BASE_URL}/campaign/checkin",
            headers=headers,
            json={},
            timeout=30,
        )
        return resp.json()
    except Exception:
        return {}


def get_task_list(token):
    try:
        headers = {**HEADERS_BASE, "authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{BASE_URL}/task/list",
            headers=headers,
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            return []
        return data["data"]["tasks"]
    except Exception:
        return []


def complete_task(token, task_id):
    try:
        headers = {**HEADERS_BASE, "authorization": f"Bearer {token}"}
        resp = requests.post(
            f"{BASE_URL}/task/complete",
            headers=headers,
            json={"taskId": task_id},
            timeout=30,
        )
        return resp.json()
    except Exception:
        return {}


def process_account(pk, index):
    account = Account.from_key(pk)
    address = account.address
    short_addr = address[:6] + "..." + address[-4:]

    LY(f"Processing account {index} using wallet {short_addr}")

    nonce, message = get_nonce(address)
    if not nonce:
        LR(f"Account {index} failed to retrieve nonce from the server.")
        return

    msg_encoded = encode_defunct(text=message)
    signed = account.sign_message(msg_encoded)
    signature = signed.signature.hex()
    if not signature.startswith("0x"):
        signature = "0x" + signature

    token = get_token(signature, message, address)
    if not token:
        LR(f"Account {index} authentication failed. Unable to obtain access token.")
        return

    checkin_data = get_checkin_status(token)
    if checkin_data is None:
        LR(f"Account {index} failed to fetch check-in status.")
    elif checkin_data.get("todayChecked"):
        streak = checkin_data.get("currentStreak", 0)
        LY(f"Account {index} already checked in today with a streak of {streak} day(s).")
    else:
        result = do_checkin(token)
        if result.get("code") == 0:
            LG(f"Account {index} daily check-in completed successfully.")
        else:
            LR(f"Account {index} check-in failed. Server returned: {result.get('message', 'unknown error')}")

    tasks = get_task_list(token)
    if not tasks:
        LR(f"Account {index} failed to retrieve the task list.")
        return

    available = [
        t for t in tasks
        if t.get("completionStatus") == "AVAILABLE"
        and t.get("taskCode") not in SKIP_TASK_CODES
    ]

    if not available:
        LY(f"Account {index} has no available tasks to complete at this time.")
        return

    for task in available:
        task_name = task.get("taskName", "Unknown Task")
        task_points = task.get("rewardPoints", 0)
        task_id = task.get("taskId")

        result = complete_task(token, task_id)
        if result.get("code") == 0:
            earned = result.get("data", {}).get("rewardPoints", task_points)
            LG(f"Account {index} completed '{task_name}' and earned {earned} points.")
        else:
            LR(f"Account {index} could not complete '{task_name}'. Server returned: {result.get('message', 'unknown error')}")


def countdown(seconds):
    while seconds > 0:
        hrs = seconds // 3600
        mins = (seconds % 3600) // 60
        secs = seconds % 60
        print(f"\r{YELLOW}Next cycle starts in {hrs:02d}:{mins:02d}:{secs:02d}{RESET}", end="", flush=True)
        time.sleep(1)
        seconds -= 1
    print()


def main():
    set_title()
    banner()

    private_keys = load_private_keys()
    if not private_keys:
        LR("No private keys found. Please configure your .env file with PRIVATEKEY_1, PRIVATEKEY_2, etc.")
        sys.exit(1)

    while True:
        for i, pk in enumerate(private_keys, 1):
            process_account(pk, i)
            print()

        LY("All accounts have been processed.")
        countdown(3600)
        banner()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        LR("Script stopped by user.")
        sys.exit(0)
