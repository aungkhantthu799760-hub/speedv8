# =====================================================================
# license.py - License Management Module
# KAVIN FAST SPEED V6
# =====================================================================

import os
import json
import time
import hashlib
import hmac
import base64
from datetime import datetime, timedelta

LICENSE_FILE = "license.dat"
SECRET_KEY = b"KavinFastSpeed2024SecretKey!@#$%^&*()"


def _encode_license(data: dict) -> str:
    """License ကို encode လုပ် (base64 + HMAC signature)"""
    try:
        json_str = json.dumps(data, separators=(',', ':'))
        raw = json_str.encode('utf-8')
        sig = hmac.new(SECRET_KEY, raw, hashlib.sha256).hexdigest()[:16]
        combined = f"{sig}.{base64.b64encode(raw).decode()}"
        return combined
    except Exception:
        return ""


def _decode_license(encoded: str) -> dict:
    """License ကို decode လုပ် (signature စစ်)"""
    try:
        if '.' not in encoded:
            return None
        sig, payload_b64 = encoded.split('.', 1)
        raw = base64.b64decode(payload_b64)
        expected_sig = hmac.new(SECRET_KEY, raw, hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected_sig):
            return None
        return json.loads(raw.decode('utf-8'))
    except Exception:
        return None


def _generate_license(key: str, days: int = 365) -> str:
    """Key ကနေ license ထုတ်"""
    try:
        now = datetime.now()
        expiry = now + timedelta(days=days)
        data = {
            "key_hash": hashlib.sha256(key.encode()).hexdigest()[:32],
            "issued": now.strftime("%Y-%m-%d"),
            "expiry": expiry.strftime("%Y-%m-%d"),
            "days": days,
        }
        return _encode_license(data)
    except Exception:
        return ""


def check_approval():
    """
    License စစ်ဆေး
    return: (is_valid: bool, expiry_msg: str)
    """
    try:
        if not os.path.exists(LICENSE_FILE):
            return False, "No license"

        with open(LICENSE_FILE, "r") as f:
            encoded = f.read().strip()

        if not encoded:
            return False, "Empty license"

        data = _decode_license(encoded)
        if not data:
            return False, "Invalid license (signature)"

        expiry_str = data.get("expiry", "")
        try:
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d")
        except Exception:
            return False, "Invalid expiry format"

        now = datetime.now()
        if now > expiry:
            return False, f"Expired on {expiry_str}"

        days_left = (expiry - now).days
        return True, f"{expiry_str} ({days_left}d left)"

    except Exception as e:
        return False, f"Error: {e}"


def activate(key: str):
    """
    License key အသက်သွင်း
    return: (ok: bool, msg: str)
    """
    try:
        key = key.strip()
        if not key:
            return False, "Empty key"

        if len(key) < 16:
            return False, "Key too short (min 16 chars)"

        # Key format: KAVIN-<days>-<random>-<sig>
        days = 365
        if key.startswith("KAVIN-"):
            parts = key.split("-")
            if len(parts) >= 2:
                try:
                    days = int(parts[1])
                except ValueError:
                    days = 365

        encoded = _generate_license(key, days)
        if not encoded:
            return False, "Failed to generate license"

        with open(LICENSE_FILE, "w") as f:
            f.write(encoded)

        is_valid, msg = check_approval()
        if is_valid:
            return True, f"✓ Activated! {msg}"
        return False, "Activation failed"

    except Exception as e:
        return False, f"Error: {e}"


def deactivate():
    """License ဖျက်"""
    try:
        if os.path.exists(LICENSE_FILE):
            os.remove(LICENSE_FILE)
        return True, "Deactivated"
    except Exception as e:
        return False, f"Error: {e}"


def info():
    """License အချက်အလက် ပြ"""
    is_valid, msg = check_approval()
    return {
        "valid": is_valid,
        "message": msg,
        "file": LICENSE_FILE,
        "exists": os.path.exists(LICENSE_FILE),
    }


# ============ CLI Test ============
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python license.py check")
        print("  python license.py activate <KEY>")
        print("  python license.py deactivate")
        print("  python license.py info")
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "check":
        v, m = check_approval()
        print(f"Valid: {v}")
        print(f"Message: {m}")

    elif cmd == "activate":
        if len(sys.argv) < 3:
            print("Please provide a key")
            sys.exit(1)
        ok, m = activate(sys.argv[2])
        print(f"OK: {ok}")
        print(f"Message: {m}")

    elif cmd == "deactivate":
        ok, m = deactivate()
        print(f"OK: {ok}")
        print(f"Message: {m}")

    elif cmd == "info":
        print(json.dumps(info(), indent=2))

    else:
        print(f"Unknown command: {cmd}")