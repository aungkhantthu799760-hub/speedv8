# =====================================================================
# license.py - Stable Local License System (No more asking every time)
# =====================================================================

import hmac
import hashlib
import base64
import time
import json
import os
import uuid
import platform

SECRET_KEY = b"kavin799_v8_ultra_secret_2024"
LICENSE_FILE = "license.dat"

def get_stable_id():
    """Termux မှာ ပိတ်လိုက်ဖွင့်လိုက်လုပ်တိုင်း မပြောင်းတဲ့ ID ကို ယူတယ်"""
    # ဖုန်းရဲ့ Model နဲ့ Termux ရဲ့ Installation Path ကို ပေါင်းပြီး သီးသန့် ID တစ်ခု ဆောက်တယ်
    # ဒါက Termux ကို ဖျက်လိုက်မှပဲ ပြောင်းသွားမှာပါ
    base_str = f"{platform.node()}-{platform.machine()}-{os.path.expanduser('~')}"
    return hashlib.sha256(base_str.encode()).hexdigest()[:16]

def _generate_signature(payload_bytes):
    signature = hmac.new(SECRET_KEY, payload_bytes, hashlib.sha256).digest()
    return signature

def generate_license_key(days=30):
    """Key ဖန်တီးတဲ့အခါ ဖုန်း ID မလိုတော့ပါဘူး"""
    expiry = int(time.time()) + int(days * 24 * 60 * 60)
    random_id = os.urandom(4).hex()
    
    payload = {"e": expiry, "r": random_id}
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    sig = _generate_signature(payload_bytes)
    
    def to_base36(num):
        if num == 0: return '0'
        chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        res = ''
        while num > 0:
            num, rem = divmod(num, 36)
            res = chars[rem] + res
        return res.zfill(6)
        
    exp_b36 = to_base36(expiry)[-6:]
    b64_sig = base64.urlsafe_b64encode(sig).decode('utf-8').rstrip('=')[:8]
    
    p1 = exp_b36[0:3] + random_id[0:1].upper()
    p2 = exp_b36[3:6] + random_id[1:2].upper()
    p3 = b64_sig[0:4].upper()
    
    return f"KAVIN-{p1}-{p2}-{p3}"

def activate(key):
    """Key ကို စစ်ဆေးပြီး သိမ်းမယ်"""
    try:
        if not key.startswith("KAVIN-"): return False, "Invalid Key Format"
        parts = key.split('-')
        if len(parts) != 4: return False, "Invalid Format"
            
        p1, p2 = parts[1], parts[2]
        exp_b36 = p1[0:3] + p2[0:3]
        
        def from_base36(s):
            chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            res = 0
            for char in s:
                if char not in chars: return 0
                res = res * 36 + chars.index(char)
            return res
            
        expiry = from_base36(exp_b36)
        if time.time() > expiry: return False, "Key Expired"
            
        # ⭐ တည်ငြိမ်တဲ့ ID ကို ယူပြီး Key နဲ့ တွဲသိမ်းမယ်
        current_id = get_stable_id()
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump({"key": key, "id": current_id}, f)
            
        return True, f"Activated! Expiry: {time.strftime('%Y-%m-%d', time.localtime(expiry))}"
    except Exception as e:
        return False, f"Error: {e}"

def check_approval():
    """Program စတင်ချိန်မှာ စစ်ဆေးမယ်"""
    if not os.path.exists(LICENSE_FILE):
        return False, "No License Found"
    
    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        key = data.get("key")
        saved_id = data.get("id")
        current_id = get_stable_id()
        
        # ⭐ ID မတူရင် (တခြားဖုန်းမှာ ခိုးသုံးရင်) အလုပ်မလုပ်ခိုင်းဘူး
        if saved_id != current_id:
            return False, "License is locked to another device!"
            
        # သက်တမ်းကို ပြန်စစ်မယ်
        parts = key.split('-')
        exp_b36 = parts[1][0:3] + parts[2][0:3]
        def from_base36(s):
            chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            res = 0
            for char in s:
                if char not in chars: return 0
                res = res * 36 + chars.index(char)
            return res
        expiry = from_base36(exp_b36)
        
        if time.time() > expiry:
            return False, "License Expired"
            
        return True, time.strftime('%Y-%m-%d %H:%M', time.localtime(expiry))
        
    except Exception:
        return False, "License Error"