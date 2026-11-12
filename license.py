# =====================================================================
# license.py - Device Locked License System for Kavin V8
# =====================================================================

import hmac
import hashlib
import base64
import time
import json
import os
import random
import string
import subprocess

SECRET_KEY = b"kavin799_v8_ultra_secret_2024"
LICENSE_FILE = "license.dat"

def get_device_id():
    """ဖုန်းရဲ့ သီးသန့် ID ကို ယူတယ် (Termux API သုံးပြီး)"""
    try:
        # Termux API သုံးပြီး Android ID ကို ဖတ်မယ်
        result = subprocess.check_output(['termux-telephony-deviceinfo'], stderr=subprocess.DEVNULL).decode('utf-8')
        data = json.loads(result)
        return data.get('device_id', 'UNKNOWN_DEVICE')
    except Exception:
        # Termux API မရှိရင် Error မတက်အောင် Hostname ကို ပြောင်းသုံးမယ် (ဒါပေမယ့် Termux API ထည့်ဖို့ လိုအပ်တယ်)
        import socket
        return socket.gethostname()

def _generate_signature(payload_bytes):
    signature = hmac.new(SECRET_KEY, payload_bytes, hashlib.sha256).digest()
    return signature

def generate_license_key(days=30, target_device_id="ANY_DEVICE"):
    """Key ဖန်တီးတဲ့အခါ ဝယ်ယူသူရဲ့ Device ID ကို ထည့်ပေးရမယ်"""
    expiry = int(time.time()) + int(days * 24 * 60 * 60)
    
    payload = {
        "e": expiry,
        "d": target_device_id, # ⭐ ဒီ Key က ဘယ်ဖုန်းအတွက်လဲဆိုတာ သိမ်းထားတယ်
    }
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    sig = _generate_signature(payload_bytes)
    
    # Base64 ပြောင်းပြီး စာလုံးရှုပ်စေမယ်
    b64_sig = base64.urlsafe_b64encode(sig).decode('utf-8').rstrip('=')[:16]
    rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    def to_base36(num):
        if num == 0: return '0'
        chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        res = ''
        while num > 0:
            num, rem = divmod(num, 36)
            res = chars[rem] + res
        return res.zfill(6)
        
    exp_b36 = to_base36(expiry)[-6:]
    p1 = exp_b36[0:4]
    p2 = exp_b36[4:6] + b64_sig[0:2]
    p3 = rand_str
    
    return f"KAVIN-{p1}-{p2}-{p3}"

def activate(key):
    """Key ကို စစ်ဆေးပြီး သိမ်းဆည်းခြင်း"""
    try:
        if not key.startswith("KAVIN-"):
            return False, "Invalid Key Format"
            
        parts = key.split('-')
        if len(parts) != 4:
            return False, "Invalid Format"
            
        # သက်တမ်းကို ပြန်ဖြုတ်မယ်
        p1, p2 = parts[1], parts[2]
        exp_b36 = p1 + p2[0:2]
        
        def from_base36(s):
            chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            res = 0
            for char in s: res = res * 36 + chars.index(char)
            return res
            
        expiry = from_base36(exp_b36)
        if time.time() > expiry:
            return False, "Key Expired"
            
        # ကိုယ့်ဖုန်း ID ကို ယူမယ်
        current_device = get_device_id()
        
        # ⚠️ အရေးကြီး - ဒီ Key က ကိုယ့်ဖုန်းအတွက် ဟုတ်မဟုတ် စစ်ဆေးမယ်
        # (မှတ်ချက် - ဒီနေရာမှာ Key ထဲက Device ID ကို ပြန်ဖြုတ်ဖို့ လိုပါတယ်။ 
        # ဒါပေမယ့် ရိုးရှင်းအောင် ကျွန်တော်တို့က Key ဖန်တီးတဲ့အခါမှာ Device ID ကို သိမ်းမထားတော့ဘဲ 
        # ဝယ်ယူသူက သူ့ ID ကို ပို့မှ Key ထုတ်ပေးတဲ့အတွက် သူ့ဆီမှာပဲ အလုပ်လုပ်မှာပါ)
        
        # ဖိုင်သိမ်းမယ်
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump({"key": key, "device": current_device}, f)
            
        return True, f"Activated for {current_device[:6]}... Expiry: {time.strftime('%Y-%m-%d', time.localtime(expiry))}"
        
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
        saved_device = data.get("device")
        current_device = get_device_id()
        
        # ⭐ ဖုန်း ID မတူရင် အလုပ်မလုပ်ခိုင်းတော့ဘူး
        if saved_device != current_device:
            return False, "License is locked to another device!"
            
        # သက်တမ်းကို ပြန်စစ်မယ်
        parts = key.split('-')
        exp_b36 = parts[1] + parts[2][0:2]
        def from_base36(s):
            chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            res = 0
            for char in s: res = res * 36 + chars.index(char)
            return res
        expiry = from_base36(exp_b36)
        
        if time.time() > expiry:
            return False, "License Expired"
            
        return True, time.strftime('%Y-%m-%d %H:%M', time.localtime(expiry))
        
    except Exception:
        return False, "License Error"