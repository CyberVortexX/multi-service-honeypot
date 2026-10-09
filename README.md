<div align="center">

![HoneyTrap Banner](banner.jpg)

# 🍯 HoneyTrap — Multi-Service Honeypot

**A production-grade cybersecurity honeypot that lures, captures, and visualizes real-world attack behavior in real time.**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/CyberVortexX/multi-service-honeypot)
[![MITRE ATT&CK](https://img.shields.io/badge/MITRE-ATT%26CK%20Tagged-red?style=for-the-badge)](https://attack.mitre.org/)
[![WebSocket](https://img.shields.io/badge/Real--time-WebSocket-orange?style=for-the-badge&logo=socket.io&logoColor=white)](https://socket.io)

[**Demo Video**](#-demo-video) · [**Quick Start**](#-quick-start) · [**Architecture**](#-architecture) · [**Dashboard**](#-dashboard-preview)

</div>

---

## 📽 Demo Video

https://github.com/CyberVortexX/multi-service-honeypot/releases/download/v1.0.0/honey-trap-demo.mp4

> Watch HoneyTrap intercept SSH brute-force, FTP credential stuffing, Telnet IoT botnet attacks, and HTTP exploit scans — all visualized live on the world map dashboard.

---

## ✨ What Is HoneyTrap?

HoneyTrap is a **multi-protocol honeypot** that simultaneously emulates **SSH, FTP, Telnet, and HTTP** servers on decoy ports. Every connection attempt is:

1. **Captured** — credentials, payloads, user-agents, and headers logged
2. **Geolocated** — attacker IP resolved to city, country, and ISP via ip-api.com
3. **Tagged** — classified with MITRE ATT&CK tactic, technique, and severity
4. **Streamed** — pushed instantly to a live web dashboard via WebSocket
5. **Persisted** — stored to a JSONL log file for offline analysis

---

## 🚀 Features

| Feature | Description |
|---|---|
| 🔐 **SSH Honeypot** | Full Paramiko SSH handshake — captures brute-force credentials on port **2222** |
| 📂 **FTP Honeypot** | RFC-compliant FTP banner — captures credential stuffing on port **2121** |
| 💻 **Telnet Honeypot** | Ubuntu 22.04 login banner — catches IoT Mirai botnet sweeps on port **2323** |
| 🌐 **HTTP Honeypot** | Apache/PHP fingerprint — logs web crawlers and exploit paths on port **8080** |
| 🗺 **Live Attack Map** | Leaflet.js world map with animated markers per attacker geolocation |
| ⚡ **Real-time Feed** | Instant WebSocket push via Flask-SocketIO — zero polling |
| 📊 **KPI Dashboard** | Live counters per service with sparkline trend charts |
| 📋 **Filterable Log Table** | Searchable event table — filter by SSH / FTP / Telnet / HTTP |
| 🎯 **MITRE ATT&CK Tags** | Every event tagged with tactic, technique (e.g. T1110.001), and severity |
| 🎭 **5-Campaign Simulator** | Realistic attack simulator (Mirai Botnet, APT, Script-Kiddie, and more) |
| ⬇ **JSON Export** | One-click download of all captured events |
| 🔄 **Persistent Logs** | Events survive server restarts — reloaded from JSONL on startup |
| 🌍 **IP Geolocation** | City, country, ISP, and GPS coordinates for map plotting |
| 🖥 **Windows One-Click Launch** | `start.bat` auto-installs deps, starts server, opens browser |

---

## 📸 Dashboard Preview

Layout of the live dashboard served at `http://localhost:5000`:

```text
+-----------------------------------------------------------------------+
|  HONEYTRAP            * LIVE MONITORING             [Clear] [Export]  |
+------------+------------+------------+------------+-------------------+
|    847     |    312     |    198     |    224     |        113        |
|   Total    |    SSH     |    FTP     |   Telnet   |       HTTP        |
|    ~~~~    |    ~~~~    |    ~~~~    |    ~~~~    |       ~~~~        |
+------------+------------+------------+------------+-------------------+
| Global Attack Map (Leaflet)                | Live Feed                |
+--------------------------------------------+--------------------------+
| [ world map with animated markers ]        | [SSH] 185.220.x.x DE     |
| red/orange dot per attacker IP             | [FTP] 218.92.x.x  CN     |
| popup: IP, city, ISP                       | [TEL] 91.108.x.x  UA     |
|                                            | [HTTP] 45.95.x.x   NL    |
+--------------------------------------------+--------------------------+
| Attack Log   [All] [SSH] [FTP] [Telnet] [HTTP]       Search: [____]   |
+-----------------------------------------------------------------------+
| #   Time      Service     IP              Location   User    Pass     |
+-----------------------------------------------------------------------+
| 1   12:34:01  SSH  HIGH   185.220.x.x     Germany    root    123456   |
| 2   12:34:03  FTP  HIGH   218.92.x.x      China      admin   admin    |
| 3   12:34:05  TEL  MED    91.108.x.x      Ukraine    root    xc3511   |
+-----------------------------------------------------------------------+
```

| Panel | What it shows |
|---|---|
| **Header** | Live-monitoring status, plus **Clear** (reset log) and **Export** (download JSON) buttons |
| **KPI cards** | Total events and per-service counters (SSH / FTP / Telnet / HTTP) with sparkline trends |
| **Global Attack Map** | Leaflet world map; one animated marker per attacker IP, popup shows IP, city, and ISP |
| **Live Feed** | Newest events pushed over WebSocket as they happen |
| **Attack Log** | Filterable, searchable table with time, service, severity, IP, location, username, and password |

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.12+** installed and on your PATH
- Internet connection (for IP geolocation lookups)

### Option A — Windows (One-Click)

Double-click `start.bat`, or run it from a terminal:

```bat
start.bat
```

It will: kill old instances → install dependencies → start the server → open the browser.

### Option B — Manual (All Platforms)

```bash
# 1. Install dependencies
pip install flask flask-socketio paramiko requests eventlet

# 2. Start the honeypot (all 4 services + dashboard)
python honeypot_server.py

# 3. Open the dashboard in your browser
#    http://localhost:5000

# 4. (Optional) Run the attack simulation in a second terminal
python simulate_attacks.py
```

---

## 🔌 Port Map

| Service | Honeypot Port | Emulates Real Port |
|---|:---:|:---:|
| 🔐 SSH | **2222** | 22 |
| 📂 FTP | **2121** | 21 |
| 💻 Telnet | **2323** | 23 |
| 🌐 HTTP | **8080** | 80 |
| 📊 Dashboard | **5000** | — |

> **Note:** Alternate ports are used for safe testing without root/admin privileges. To capture attacks on real ports (22, 21, 23, 80), run with elevated privileges and change the port constants in `honeypot_server.py`.

---

## 🏗 Architecture

### System Overview

```mermaid
flowchart TB
    ATT(["Attackers: bots, scanners, brute-forcers"])

    subgraph HP["Honeypot Services - honeypot_server.py"]
        direction LR
        SSH["SSH :2222<br/>Paramiko"]
        FTP["FTP :2121<br/>raw socket"]
        TEL["Telnet :2323<br/>raw socket"]
        HTTP["HTTP :8080<br/>socket"]
    end

    ATT --> SSH
    ATT --> FTP
    ATT --> TEL
    ATT --> HTTP

    SSH --> LOG
    FTP --> LOG
    TEL --> LOG
    HTTP --> LOG

    LOG{{"log_event()"}}

    subgraph PIPE["Event Pipeline"]
        direction TB
        G["1. Geo lookup<br/>ip-api.com"]
        M["2. MITRE ATT&CK tagging<br/>tactic, technique, severity"]
        P["3. Append to<br/>logs/attacks.json"]
        E["4. socketio.emit()<br/>to all clients"]
        G --> M --> P --> E
    end

    LOG --> G

    subgraph WEB["Flask Dashboard :5000"]
        direction TB
        R1["GET / : index.html"]
        R2["GET /api/events : JSON log"]
        R3["GET /api/stats : KPI data"]
        R4["POST /api/inject : simulator"]
        R5["POST /api/clear : reset"]
    end

    P --> DB[("JSONL log file")]
    DB -. reload on startup .-> WEB
    E ==>|WebSocket / Socket.IO| UI

    subgraph UI["Browser Dashboard"]
        direction LR
        MAP["Leaflet map"]
        FEED["Live feed"]
        KPI["KPI cards"]
        TBL["Log table"]
    end

    WEB --> UI
    SIM["simulate_attacks.py<br/>5 campaigns"] -. POST /api/inject .-> R4
```

### Event Lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant A as Attacker
    participant H as Honeypot (SSH / FTP / Telnet / HTTP)
    participant P as Event Pipeline
    participant G as ip-api.com
    participant F as logs/attacks.json
    participant D as Browser Dashboard

    A->>H: Connect and attempt login / request
    H->>P: log_event(service, ip, creds, payload)
    P->>G: Geolocate IP
    G-->>P: city, country, ISP, lat/lon
    P->>P: Tag MITRE tactic, technique, severity
    P->>F: Append JSON line
    P-->>D: socketio.emit (WebSocket push)
    D->>D: Update map, feed, KPIs, table
    H-->>A: Realistic failure / banner response
```

### Component Summary

| Layer | Component | Responsibility |
|---|---|---|
| **Capture** | SSH / FTP / Telnet / HTTP listeners | Emulate real services on decoy ports and record every interaction |
| **Enrich** | Event pipeline | Geolocate, classify with MITRE ATT&CK, assign severity |
| **Store** | `logs/attacks.json` | Append-only JSONL log, reloaded on startup |
| **Serve** | Flask + Flask-SocketIO (:5000) | REST API for history and stats, WebSocket for live push |
| **Visualize** | Browser SPA | Leaflet map, live feed, KPI cards, filterable log table |
| **Test** | `simulate_attacks.py` | Injects realistic attack campaigns via `POST /api/inject` |

---

## 🌐 Dashboard API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Dashboard single-page app (`templates/index.html`) |
| `GET` | `/api/events` | Full event log as JSON |
| `GET` | `/api/stats` | KPI counters per service |
| `POST` | `/api/inject` | Inject a simulated event (used by the simulator) |
| `POST` | `/api/clear` | Clear all stored events |

---

## 🎭 Attack Simulator (5 Campaigns)

Run `python simulate_attacks.py` to generate realistic attack traffic:

| Campaign | Services | Tactic | Severity |
|---|---|---|---|
| 🤖 **Mirai Botnet Sweep** | Telnet + SSH | Initial Access | HIGH |
| 📦 **Credential Stuffing** | FTP + SSH | Credential Access | HIGH |
| 🔍 **Web Vulnerability Scan** | HTTP | Discovery | MEDIUM |
| 🎩 **APT Reconnaissance** | All services | Reconnaissance | CRITICAL |
| 💥 **Script-Kiddie Blast** | All services | Execution | LOW |

Each campaign uses realistic IP pools from **12 countries** with proper protocol handshakes.

---

## 📝 Sample Log Entry

```json
{
  "id": 42,
  "timestamp": "2026-10-09T05:14:23.456Z",
  "service": "SSH",
  "ip": "185.220.101.45",
  "port": 54312,
  "username": "root",
  "password": "password123",
  "geo": {
    "city": "Frankfurt",
    "country": "Germany",
    "lat": 50.1109,
    "lon": 8.6821,
    "org": "AS13335 Cloudflare, Inc."
  },
  "tactic": "Credential Access",
  "technique": "T1110.001 - Password Guessing",
  "severity": "HIGH",
  "campaign": "Mirai Botnet Sweep"
}
```

---

## 🗂 Project Structure

```text
honeypot/
├── honeypot_server.py        # Core server: all honeypot services + dashboard API
├── simulate_attacks.py       # 5-campaign MITRE ATT&CK attack simulator
├── start.bat                 # Windows one-click launcher
├── banner.jpg                # Project banner
├── templates/
│   └── index.html            # Dashboard SPA (Leaflet map + Socket.IO + tables)
├── static/
│   ├── css/
│   │   ├── style.css         # Dark cyber theme (glassmorphism + neon effects)
│   │   └── leaflet.css       # Leaflet map styles
│   └── js/
│       ├── dashboard.js      # Real-time frontend logic (WebSocket + map + KPIs)
│       ├── leaflet.js        # Interactive world map library
│       └── socket.io.min.js  # WebSocket client
├── logs/
│   ├── attacks.json          # Persistent JSONL event log (gitignored)
│   └── host_rsa.key          # Auto-generated SSH host key (gitignored)
└── README.md
```

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Core Runtime** | Python 3.12+ |
| **SSH Emulation** | Paramiko (full SSH handshake) |
| **Web Framework** | Flask 3.x |
| **Real-time Push** | Flask-SocketIO + Socket.IO |
| **Map Rendering** | Leaflet.js (offline-capable) |
| **IP Geolocation** | ip-api.com (free, 45 req/min) |
| **Frontend Fonts** | Google Fonts — Outfit + JetBrains Mono |
| **Event Persistence** | JSONL flat-file database |

---

## 🧰 Troubleshooting

| Problem | Fix |
|---|---|
| `Address already in use` | Another instance is running. Stop it, or on Windows run `start.bat` (it kills old instances first). |
| Permission denied on ports 21/22/23/80 | Use the default high ports, or run with admin/root privileges. |
| Map shows no location for an IP | ip-api.com is rate-limited to 45 requests/min, and private IPs cannot be geolocated. |
| Dashboard is empty | Run `python simulate_attacks.py` to generate test events. |

---

## ⚠️ Ethical & Legal Notice

> **This project is for educational and research purposes only.**

- ✅ Deploy only on **networks and systems you own** or have explicit written permission to monitor
- ✅ Use in **isolated lab environments** or **CTF / academic research**
- ❌ Do **not** deploy on public networks to intercept traffic without authorization
- ❌ Do **not** use captured credentials for any unauthorized access
- ❌ Do **not** violate any computer crime laws (CFAA, Computer Misuse Act, etc.)

Captured data may contain real credentials from scanning bots — handle responsibly.

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ by [CyberVortexX](https://github.com/CyberVortexX)**

*If this project helped you learn about cybersecurity honeypots, please star the repo!*

[![GitHub stars](https://img.shields.io/github/stars/CyberVortexX/multi-service-honeypot?style=social)](https://github.com/CyberVortexX/multi-service-honeypot/stargazers)

</div>
