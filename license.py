# =====================================================================
# license.py - License Management with Device Lock (Minute-Based)
# KAVIN FAST SPEED V8
# =====================================================================

import os
import json
import time
import hashlib
import hmac
import base64
import uuid
import platform
from datetime import datetime, timedelta

LICENSE_FILE = "license.dat"
SECRET_KEY = b"KavinFastSpeed2024SecretKey!@#$%^&*()"

MAX_MINUTES = 3650 * 24 * 60   # ၁၀ နှစ်


# =====================================================================
#  STABLE DEVICE ID
# =====================================================================
def get_stable_device_id():
    """တည်ငြိမ်တဲ့ device ID (run တိုင်း တူတူ)"""
    try:
        parts = [
            str(uuid.getnode()),        # MAC address
            platform.system(),          # Android / Linux / Windows
            platform.machine(),         # arm64 / x86_64
        ]
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]
    except Exception:
        return "UNKNOWN_DEVICE_ID_00000"


# =====================================================================
#  ENCODE / DECODE
# =====================================================================
def _encode_license(data: dict) -> str:
    try:
        json_str = json.dumps(data, separators=(',', ':'))
        raw = json_str.encode('utf-8')
        sig = hmac.new(SECRET_KEY, raw, hashlib.sha256).hexdigest()[:16]
        return f"{sig}.{base64.b64encode(raw).decode()}"
    except Exception:
        return ""


def _decode_license(encoded: str) -> dict:
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


# =====================================================================
#  CHECK APPROVAL
# =====================================================================
def check_approval():
    """License စစ် → (is_valid, expiry_msg)"""
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

        # Device ID စစ်
        current_device = get_stable_device_id()
        licensed_device = data.get("device_id", "")
        if licensed_device != current_device:
            return False, "License is locked to another device"

        # Expiry စစ်
        expiry_str = data.get("expiry", "")
        try:
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return False, "Invalid expiry format"

        now = datetime.now()
        if now > expiry:
            return False, f"Expired on {expiry_str}"

        delta = expiry - now
        days_left = delta.days
        hours_left = delta.seconds // 3600
        mins_left = (delta.seconds % 3600) // 60

        if days_left > 0:
            return True, f"{expiry_str} ({days_left}d {hours_left}h left)"
        elif hours_left > 0:
            return True, f"{expiry_str} ({hours_left}h {mins_left}m left)"
        else:
            return True, f"{expiry_str} ({mins_left}m left)"

    except Exception as e:
        return False, f"Error: {e}"


# =====================================================================
#  ACTIVATE
# =====================================================================
def activate(key: str):
    """Key activate → (ok, msg)"""
    try:
        key = key.strip()
        if not key:
            return False, "Empty key"

        # Format: KAVIN-<minutes>-<device_id>-<sig>
        parts = key.split("-")
        if len(parts) != 4 or parts[0] != "KAVIN":
            return False, "Invalid key format"

        try:
            minutes = int(parts[1])
        except ValueError:
            return False, "Invalid minutes in key"

        key_device = parts[2].lower()
        sig = parts[3]

        if minutes < 1 or minutes > MAX_MINUTES:
            return False, f"Minutes out of range (1-{MAX_MINUTES})"

        # Signature စစ်
        payload = f"KAVIN-{minutes}-{key_device}"
        expected_sig = hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).hexdigest()[:6].upper()

        if not hmac.compare_digest(sig, expected_sig):
            return False, "Invalid signature"

        # Device ID စစ်
        current_device = get_stable_device_id()
        if key_device != current_device:
            return False, f"Key is for another device (your ID: {current_device[:8]}...)"

        # License ထုတ်
        now = datetime.now()
        expiry = now + timedelta(minutes=minutes)
        data = {
            "key_hash": hashlib.sha256(key.encode()).hexdigest()[:32],
            "issued": now.strftime("%Y-%m-%d %H:%M:%S"),
            "expiry": expiry.strftime("%Y-%m-%d %H:%M:%S"),
            "minutes": minutes,
            "device_id": current_device,
        }

        encoded = _encode_license(data)
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


# =====================================================================
#  DEACTIVATE / INFO
# =====================================================================
def deactivate():
    try:
        if os.path.exists(LICENSE_FILE):
            os.remove(LICENSE_FILE)
        return True, "Deactivated"
    except Exception as e:
        return False, f"Error: {e}"


def info():
    is_valid, msg = check_approval()
    return {
        "valid": is_valid,
        "message": msg,
        "device_id": get_stable_device_id(),
        "file": LICENSE_FILE,
        "exists": os.path.exists(LICENSE_FILE),
    }


# =====================================================================
#  CLI TEST
# =====================================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python license.py check")
        print("  python license.py activate <KEY>")
        print("  python license.py deactivate")
        print("  python license.py info")
        print("  python license.py deviceid")
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
    elif cmd == "deviceid":
        print(f"Your Device ID: {get_stable_device_id()}")
    else:
        print(f"Unknown command: {cmd}")