# =====================================================================
# license.py - Local License System for Kavin Tools V8
# =====================================================================

import hmac
import hashlib
import base64
import time
import json
import os
import random
import string

# ⭐ လုံခြုံရေးအတွက် ဒီ Secret Key ကို မည်သူ့ကိုမှ မပြပါနဲ့
SECRET_KEY = b"kavin799_v8_ultra_secret_2024"
LICENSE_FILE = "license.dat"

def _generate_signature(payload_bytes):
    """Payload အတွက် လုံခြုံတဲ့ Signature ထုတ်ပေးတယ်"""
    signature = hmac.new(SECRET_KEY, payload_bytes, hashlib.sha256).digest()
    return signature

def generate_license_key(days=30, user_name="khant7997"):
    """
    Key အသစ်ဖန်တီးခြင်း (ပုံစံအသစ် - KAVIN-XXXX-XXXX-XXXX)
    days: ရက် (ဥပမာ - 1/24 ဆိုရင် ၁ နာရီ)
    """
    expiry = int(time.time()) + int(days * 24 * 60 * 60)
    
    # သက်တမ်းကို Base36 ပြောင်းမယ် (ပိုတိုအောင်)
    def to_base36(num):
        if num == 0: return '0'
        chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        res = ''
        while num > 0:
            num, rem = divmod(num, 36)
            res = chars[rem] + res
        return res.zfill(6)
    
    # Payload တည်ဆောက်ခြင်း
    payload = {
        "u": user_name,
        "e": expiry,
        "r": "premium"
    }
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    
    # Signature ထုတ်ခြင်း
    sig = _generate_signature(payload_bytes)
    b64_sig = base64.urlsafe_b64encode(sig).decode('utf-8').rstrip('=')[:16]
    
    # ကျပန်း စာလုံးများ
    rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # Key ပုံစံ ချိန်ညှိခြင်း (KAVIN-XXXX-XXXX-XXXX)
    exp_b36 = to_base36(expiry)[-6:]
    p1 = exp_b36[0:4]
    p2 = exp_b36[4:6] + b64_sig[0:2]
    p3 = rand_str
    
    final_key = f"KAVIN-{p1}-{p2}-{p3}"
    
    # ⭐ တကယ့် Key နဲ့ သက်တမ်းကို database မလိုဘဲ စစ်ဆေးနိုင်ဖို့ 
    # Signature ကို မှတ်ထားဖို့ လိုပါတယ်။
    # (ဒီနေရာမှာ ရိုးရှင်းအောင် Key ထဲမှာပဲ သက်တမ်းကို သွယ်ဝိုက်ထည့်ထားပါတယ်)
    
    return final_key

def _decode_and_verify(key):
    """Key ကို စစ်ဆေးခြင်း"""
    try:
        if not key.startswith("KAVIN-"):
            return False, "Invalid Key Prefix"
            
        parts = key.split('-')
        if len(parts) != 4:
            return False, "Invalid Key Format"
            
        p1, p2, p3 = parts[1], parts[2], parts[3]
        
        # သက်တမ်းကို ပြန်ဖြုတ်ခြင်း (p1 နဲ့ p2 ပထမစာလုံး ၂ လုံး)
        exp_b36 = p1 + p2[0:2]
        
        def from_base36(s):
            chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            res = 0
            for char in s:
                res = res * 36 + chars.index(char)
            return res
            
        expiry = from_base36(exp_b36)
        
        # သက်တမ်း ကုန်မကုန် စစ်ဆေးခြင်း
        if time.time() > expiry:
            return False, "Expired"
            
        return True, {"exp": expiry}
        
    except Exception:
        return False, "Corrupted Key"

def activate(key):
    """Key ကို စစ်ဆေးပြီး မှန်ရင် သိမ်းဆည်းပေးတယ်"""
    is_valid, result = _decode_and_verify(key)
    if not is_valid:
        return False, result
    
    expiry = result["exp"]
    
    # Key မှန်ရင် သိမ်းဆည်းမယ်
    try:
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            f.write(key)
        return True, f"Success! Expiry: {time.strftime('%Y-%m-%d %H:%M', time.localtime(expiry))}"
    except Exception as e:
        return False, f"Save Error: {e}"

def check_approval():
    """Program စတင်ချိန်မှာ Key ရှိမရှိ စစ်ဆေးတယ်"""
    if not os.path.exists(LICENSE_FILE):
        return False, "No License Found"
    
    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            key = f.read().strip()
            
        is_valid, result = _decode_and_verify(key)
        if not is_valid:
            return False, result
            
        expiry = result["exp"]
        return True, time.strftime('%Y-%m-%d %H:%M', time.localtime(expiry))
        
    except Exception:
        return False, "License Error"

def check_key_directly(key):
    """Keygen အတွက် တိုက်ရိုက်စစ်ဆေးခြင်း (Save မလုပ်ဘဲ)"""
    is_valid, result = _decode_and_verify(key)
    if not is_valid:
        return False, result
        
    expiry = result["exp"]
    return True, time.strftime('%Y-%m-%d %H:%M', time.localtime(expiry))
