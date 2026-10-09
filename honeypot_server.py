"""
Multi-Service Honeypot Server
Simulates SSH, FTP, Telnet, and HTTP services to capture attacker behavior.
Logs all attempts and streams them to the dashboard via Flask-SocketIO.
"""

import socket
import threading
import logging
import json
import os
import datetime
import time
import paramiko
import requests
from flask import Flask, render_template, jsonify, send_from_directory, request
from flask_socketio import SocketIO, emit

# ─────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────
SSH_PORT     = 2222   # Fake SSH   (real SSH is 22)
FTP_PORT     = 2121   # Fake FTP   (real FTP is 21)
TELNET_PORT  = 2323   # Fake Telnet(real Telnet is 23)
HTTP_PORT    = 8080   # Fake HTTP  (real HTTP is 80)
DASHBOARD_PORT = 5000 # Flask dashboard

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ─────────────────────────────────────────────
#  Logging Setup
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("honeypot")

# Suppress noisy Paramiko internal errors (SSH banner errors from raw-socket scanners)
logging.getLogger("paramiko.transport").setLevel(logging.CRITICAL)

attack_log_file = os.path.join(LOG_DIR, "attacks.json")

# ─────────────────────────────────────────────
#  Load persisted events on startup
# ─────────────────────────────────────────────
def _load_persisted_events():
    """Reload attack_events and stats from the on-disk JSONL log."""
    if not os.path.exists(attack_log_file):
        return [], {"total": 0, "ssh": 0, "ftp": 0, "telnet": 0, "http": 0}
    events = []
    _stats = {"total": 0, "ssh": 0, "ftp": 0, "telnet": 0, "http": 0}
    try:
        with open(attack_log_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    events.append(ev)
                    _stats["total"] += 1
                    svc = ev.get("service", "").lower()
                    _stats[svc] = _stats.get(svc, 0) + 1
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        logging.warning("Could not load persisted events: %s", e)
    return events, _stats

attack_events, stats = _load_persisted_events()
logging.info("Loaded %d persisted events from disk", len(attack_events))


# Flask app for the dashboard
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = "honeypot-secret-2026"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ─────────────────────────────────────────────
#  Geolocation Helper
# ─────────────────────────────────────────────
geo_cache = {}

def get_geo(ip):
    """Fetch geolocation for an IP (with simple cache)."""
    if ip in geo_cache:
        return geo_cache[ip]
    if ip in ("127.0.0.1", "::1", "localhost"):
        info = {"city": "Localhost", "country": "Local", "lat": 0.0, "lon": 0.0, "org": "Local"}
        geo_cache[ip] = info
        return info
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,city,country,lat,lon,org",
                         timeout=3)
        data = r.json()
        if data.get("status") == "success":
            info = {
                "city":    data.get("city", "Unknown"),
                "country": data.get("country", "Unknown"),
                "lat":     data.get("lat", 0.0),
                "lon":     data.get("lon", 0.0),
                "org":     data.get("org", "Unknown"),
            }
        else:
            info = {"city": "Unknown", "country": "Unknown", "lat": 0.0, "lon": 0.0, "org": "Unknown"}
    except Exception:
        info = {"city": "Unknown", "country": "Unknown", "lat": 0.0, "lon": 0.0, "org": "Unknown"}
    geo_cache[ip] = info
    return info

# ─────────────────────────────────────────────
#  Event Logger
# ─────────────────────────────────────────────
def log_event(service, ip, port, username=None, password=None, payload=None, extra=None,
              tactic=None, technique=None, severity=None, campaign=None, geo_override=None):
    """Record an attack event, persist to file, and push to dashboard."""
    geo = geo_override if geo_override else get_geo(ip)
    event = {
        "id":        len(attack_events) + 1,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "service":   service,
        "ip":        ip,
        "port":      port,
        "username":  username or "",
        "password":  password or "",
        "payload":   payload or "",
        "extra":     extra or "",
        "geo":       geo,
        "tactic":    tactic    or "Credential Access",
        "technique": technique or "T1110.001 - Password Guessing",
        "severity":  severity  or "MEDIUM",
        "campaign":  campaign  or "",
    }
    attack_events.append(event)
    stats["total"] += 1
    stats[service.lower()] = stats.get(service.lower(), 0) + 1

    # Append to JSON log
    with open(attack_log_file, "a") as f:
        f.write(json.dumps(event) + "\n")

    logger.info("[%s] %s:%s  user=%s  pass=%s  tactic=%s  severity=%s",
                service, ip, port, username, password, tactic, severity)

    # Push to dashboard clients
    socketio.emit("new_event", event)
    socketio.emit("stats_update", stats)

# ─────────────────────────────────────────────
#  SSH Honeypot
# ─────────────────────────────────────────────
class FakeSSHServer(paramiko.ServerInterface):
    def __init__(self, client_ip, client_port):
        self.client_ip   = client_ip
        self.client_port = client_port

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED if kind == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        log_event("SSH", self.client_ip, self.client_port, username=username, password=password)
        return paramiko.AUTH_FAILED  # Always reject

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"


def _generate_rsa_key():
    key_path = os.path.join(LOG_DIR, "host_rsa.key")
    if not os.path.exists(key_path):
        k = paramiko.RSAKey.generate(2048)
        k.write_private_key_file(key_path)
    return paramiko.RSAKey(filename=key_path)


HOST_KEY = None  # Loaded lazily

def handle_ssh_client(conn, addr):
    global HOST_KEY
    if HOST_KEY is None:
        HOST_KEY = _generate_rsa_key()
    try:
        transport = paramiko.Transport(conn)
        transport.add_server_key(HOST_KEY)
        server = FakeSSHServer(addr[0], addr[1])
        transport.start_server(server=server)
        chan = transport.accept(20)
        if chan:
            chan.send(b"Permission denied.\r\n")
            chan.close()
        transport.close()
    except Exception as e:
        logger.debug("SSH handler error: %s", e)
    finally:
        conn.close()


def start_ssh_honeypot():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", SSH_PORT))
    sock.listen(50)
    logger.info("SSH honeypot listening on port %d", SSH_PORT)
    while True:
        try:
            conn, addr = sock.accept()
            t = threading.Thread(target=handle_ssh_client, args=(conn, addr), daemon=True)
            t.start()
        except Exception as e:
            logger.error("SSH accept error: %s", e)

# ─────────────────────────────────────────────
#  FTP Honeypot
# ─────────────────────────────────────────────
FTP_BANNER = b"220 FTP Server Ready\r\n"

def handle_ftp_client(conn, addr):
    ip, port = addr
    try:
        conn.sendall(FTP_BANNER)
        username = None
        buf = ""
        conn.settimeout(30)
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buf += data.decode(errors="ignore")
            while "\r\n" in buf:
                line, buf = buf.split("\r\n", 1)
                line = line.strip()
                if line.upper().startswith("USER"):
                    username = line[5:].strip()
                    conn.sendall(b"331 Password required\r\n")
                elif line.upper().startswith("PASS"):
                    password = line[5:].strip()
                    log_event("FTP", ip, port, username=username, password=password)
                    conn.sendall(b"530 Login incorrect\r\n")
                    conn.sendall(FTP_BANNER)
                    username = None
                elif line.upper() == "QUIT":
                    conn.sendall(b"221 Goodbye.\r\n")
                    return
                else:
                    conn.sendall(b"530 Please login with USER and PASS\r\n")
    except Exception as e:
        logger.debug("FTP handler error: %s", e)
    finally:
        conn.close()


def start_ftp_honeypot():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", FTP_PORT))
    sock.listen(50)
    logger.info("FTP honeypot listening on port %d", FTP_PORT)
    while True:
        try:
            conn, addr = sock.accept()
            t = threading.Thread(target=handle_ftp_client, args=(conn, addr), daemon=True)
            t.start()
        except Exception as e:
            logger.error("FTP accept error: %s", e)

# ─────────────────────────────────────────────
#  Telnet Honeypot
# ─────────────────────────────────────────────
TELNET_BANNER = b"\r\nUbuntu 22.04 LTS\r\nlogin: "

def handle_telnet_client(conn, addr):
    ip, port = addr
    try:
        conn.sendall(TELNET_BANNER)
        buf = b""
        username = None
        conn.settimeout(30)
        stage = "user"
        while True:
            data = conn.recv(256)
            if not data:
                break
            buf += data
            if b"\n" in buf or b"\r" in buf:
                line = buf.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                parts = line.split(b"\n")
                buf = parts[-1]
                for part in parts[:-1]:
                    text = part.decode(errors="ignore").strip()
                    if not text:
                        continue
                    if stage == "user":
                        username = text
                        conn.sendall(b"Password: ")
                        stage = "pass"
                    elif stage == "pass":
                        log_event("Telnet", ip, port, username=username, password=text)
                        conn.sendall(b"\r\nLogin incorrect\r\n\r\nlogin: ")
                        stage = "user"
                        username = None
    except Exception as e:
        logger.debug("Telnet handler error: %s", e)
    finally:
        conn.close()


def start_telnet_honeypot():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", TELNET_PORT))
    sock.listen(50)
    logger.info("Telnet honeypot listening on port %d", TELNET_PORT)
    while True:
        try:
            conn, addr = sock.accept()
            t = threading.Thread(target=handle_telnet_client, args=(conn, addr), daemon=True)
            t.start()
        except Exception as e:
            logger.error("Telnet accept error: %s", e)

# ─────────────────────────────────────────────
#  HTTP Honeypot  (raw socket – captures full request)
# ─────────────────────────────────────────────
HTTP_RESPONSE = (
    b"HTTP/1.1 200 OK\r\n"
    b"Content-Type: text/html\r\n"
    b"Server: Apache/2.4.41 (Ubuntu)\r\n"
    b"X-Powered-By: PHP/7.4.3\r\n\r\n"
    b"<html><body><h1>403 Forbidden</h1></body></html>"
)

def handle_http_client(conn, addr):
    ip, port = addr
    try:
        conn.settimeout(10)
        raw = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            raw += chunk
            if b"\r\n\r\n" in raw:
                break
        payload = raw.decode(errors="ignore")
        # Extract first request line and headers
        lines = payload.split("\r\n")
        request_line = lines[0] if lines else ""
        headers = {}
        for line in lines[1:]:
            if ": " in line:
                k, v = line.split(": ", 1)
                headers[k] = v
        extra = f"UA={headers.get('User-Agent', '')} | Ref={headers.get('Referer', '')}"
        log_event("HTTP", ip, port, payload=request_line, extra=extra)
        conn.sendall(HTTP_RESPONSE)
    except Exception as e:
        logger.debug("HTTP handler error: %s", e)
    finally:
        conn.close()


def start_http_honeypot():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", HTTP_PORT))
    sock.listen(100)
    logger.info("HTTP honeypot listening on port %d", HTTP_PORT)
    while True:
        try:
            conn, addr = sock.accept()
            t = threading.Thread(target=handle_http_client, args=(conn, addr), daemon=True)
            t.start()
        except Exception as e:
            logger.error("HTTP accept error: %s", e)

# ─────────────────────────────────────────────
#  Flask Dashboard Routes
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/events")
def api_events():
    return jsonify(list(reversed(attack_events[-500:])))

@app.route("/api/stats")
def api_stats():
    return jsonify(stats)

# ─────────────────────────────────────────────
#  Socket.IO client JS — fetched from CDN once and cached
# ─────────────────────────────────────────────
@app.route("/sio.js")
def serve_sio_js():
    """Serve socket.io client JS from the local static file."""
    from flask import Response
    local = os.path.join("static", "js", "socket.io.min.js")
    if os.path.exists(local):
        with open(local, "rb") as f:
            content = f.read()
        return Response(content, mimetype="application/javascript",
                        headers={"Cache-Control": "public, max-age=86400"})
    return Response("// socket.io.min.js not found", mimetype="application/javascript", status=404)



@app.route("/api/clear", methods=["POST"])
def api_clear():
    attack_events.clear()
    stats.update({"total": 0, "ssh": 0, "ftp": 0, "telnet": 0, "http": 0})
    socketio.emit("stats_update", stats)
    return jsonify({"ok": True})


@app.route("/api/inject", methods=["POST"])
def api_inject():
    """Accept a pre-crafted event from the simulator (with realistic fake IP & tactics)."""
    data     = request.get_json(force=True)
    service  = data.get("service", "SSH")
    ip       = data.get("ip", "127.0.0.1")
    port     = int(data.get("port", 0))
    country  = data.get("country", "Unknown")

    # Build a geo stub from the provided country (real lookup for public IPs)
    geo = get_geo(ip)
    if geo.get("country") in ("Unknown", "Local") and country not in ("", "Unknown"):
        geo["country"] = country

    log_event(
        service   = service,
        ip        = ip,
        port      = port,
        username  = data.get("username"),
        password  = data.get("password"),
        payload   = data.get("payload"),
        extra     = data.get("extra"),
        tactic    = data.get("tactic"),
        technique = data.get("technique"),
        severity  = data.get("severity"),
        campaign  = data.get("campaign"),
        geo_override = geo,
    )
    return jsonify({"ok": True})

# ─────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    services = [
        ("SSH",    start_ssh_honeypot),
        ("FTP",    start_ftp_honeypot),
        ("Telnet", start_telnet_honeypot),
        ("HTTP",   start_http_honeypot),
    ]

    for name, fn in services:
        t = threading.Thread(target=fn, name=f"{name}-honeypot", daemon=True)
        t.start()
        logger.info("Started %s honeypot thread", name)

    logger.info("Dashboard running at http://localhost:%d", DASHBOARD_PORT)
    socketio.run(app, host="0.0.0.0", port=DASHBOARD_PORT, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
