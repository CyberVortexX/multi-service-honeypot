"""
simulate_attacks.py
===================
Realistic honeypot attack simulator with proper protocol handling and
MITRE ATT&CK-tagged tactics.

Attack Campaigns:
  1. Mirai Botnet Sweep      - IoT credential spray (Telnet / SSH)
  2. Credential Stuffing     - FTP / SSH with leaked password dumps
  3. Web Vulnerability Scan  - HTTP exploit-path enumeration
  4. APT Reconnaissance      - Low-and-slow multi-service probing
  5. Script-Kiddie Blast     - Noisy brute-force across all services

Each campaign injects realistic source IPs (from multiple countries) and
annotates events with tactic / technique / severity / campaign metadata via
the /api/inject endpoint.  SSH connections use Paramiko so the honeypot
SSH handshake completes without banner errors.
"""

import socket
import time
import random
import threading
import requests
import paramiko

HOST       = "127.0.0.1"
INJECT_URL = f"http://{HOST}:5000/api/inject"

# Realistic IP pools from known attack-heavy regions
IP_POOL = {
    "China":        ["218.92.0.198","221.194.44.201","101.71.0.14","117.136.0.1"],
    "Russia":       ["185.220.101.45","194.165.16.11","45.142.212.100","77.73.133.10"],
    "USA":          ["104.244.72.115","198.54.117.200","107.175.0.1","72.14.192.1"],
    "Brazil":       ["177.67.0.15","186.215.0.100","200.137.0.50","189.1.0.33"],
    "Germany":      ["185.130.5.220","46.4.0.100","78.46.0.50","88.198.0.20"],
    "Netherlands":  ["185.220.100.240","195.123.219.100","109.206.240.5"],
    "Ukraine":      ["91.108.4.20","185.129.62.10","5.188.206.14"],
    "India":        ["103.21.244.0","117.221.0.10","45.116.0.5"],
    "Romania":      ["89.40.0.10","5.2.72.100","188.27.0.50"],
    "South Korea":  ["175.193.0.10","222.112.0.5","211.234.0.3"],
    "Iran":         ["5.160.0.10","37.255.0.5","185.55.225.10"],
    "Vietnam":      ["113.161.0.50","27.72.0.20","118.70.0.10"],
}

def random_ip(country=None):
    if country and country in IP_POOL:
        pool = IP_POOL[country]
    else:
        pool = [ip for ips in IP_POOL.values() for ip in ips]
    return random.choice(pool)

def random_country():
    return random.choice(list(IP_POOL.keys()))

USERNAMES = [
    "admin","root","user","test","guest","ubuntu","pi","oracle","postgres",
    "mysql","deploy","ansible","vagrant","administrator","support","operator",
    "nagios","backup","jenkins","tomcat","ftp","web","www","mail","git",
]
PASSWORDS = [
    "password","123456","admin","root","toor","pass","letmein","qwerty",
    "1234","changeme","password1","abc123","welcome","12345678","dragon",
    "monkey","sunshine","master","alpine","raspberry","default","service",
    "manager","iloveyou","000000","654321","111111","P@ssw0rd","Admin123","root123",
]

# Mirai IoT default credentials
MIRAI_CREDS = [
    ("root","xc3511"),("root","vizxv"),("root","admin"),("admin","admin"),
    ("root","888888"),("root","xmhdipc"),("root","default"),("root","juantech"),
    ("root","123456"),("root","54321"),("support","support"),("root",""),
    ("root","root"),("root","12345"),("admin","password"),("guest","guest"),
    ("root","pass"),("admin","1234"),("root","klv123"),("Administrator","admin"),
    ("service","service"),("supervisor","supervisor"),("guest","12345"),
    ("admin","00000000"),("root","1111"),
]

HTTP_PATHS = [
    ("/admin",                   "Admin Panel Probe"),
    ("/wp-login.php",            "WordPress Brute-Force"),
    ("/.env",                    "Environment File Exfil"),
    ("/phpmyadmin",              "phpMyAdmin Discovery"),
    ("/manager/html",            "Tomcat Manager Probe"),
    ("/login",                   "Login Page Enum"),
    ("/config.php",              "Config Exfil Attempt"),
    ("/backup.zip",              "Backup File Download"),
    ("/.git/config",             "Git Config Leak"),
    ("/shell.php",               "Webshell Access"),
    ("/xmlrpc.php",              "WordPress XMLRPC Attack"),
    ("/actuator/env",            "Spring Boot Actuator Leak"),
    ("//etc/passwd",             "Path Traversal"),
    ("/index.php?cmd=id",        "RCE via GET Param"),
    ("/cgi-bin/bash",            "Shellshock"),
    ("/.htpasswd",               "HTPasswd Exfil"),
    ("/server-status",           "Apache Status Info"),
    ("/solr/admin/info/system",  "Solr Exploit"),
    ("/jenkins",                 "Jenkins Discovery"),
    ("/api/v1/pods",             "K8s API Probe"),
    ("/console",                 "JBoss Console"),
    ("/vendor/phpunit/phpunit/src/Util/PHP/eval-stdin.php", "PHPUnit RCE"),
    ("/boaform/admin/formLogin", "Router Exploit"),
    ("/GponForm/diag_Form?images/", "GPON Router RCE"),
]

USER_AGENTS = [
    ("masscan/1.3.2",          "Port Scanner"),
    ("Shodan.io",              "Shodan Crawler"),
    ("zgrab/0.x",              "ZGrab Banner Grabber"),
    ("python-requests/2.28.0", "Script Automation"),
    ("curl/7.81.0",            "Curl Exploitation"),
    ("Go-http-client/1.1",     "Go Exploit Tool"),
    ("Nuclei - Open-source vulnerability scanner", "Nuclei Scanner"),
    ("sqlmap/1.7.2#stable",    "SQLMap"),
    ("nikto/2.1.6",            "Nikto Web Scanner"),
    ("WPScan v3.8.22",         "WordPress Scanner"),
    ("libwww-perl/6.52",       "Perl LWP Scanner"),
]

TACTICS = {
    "brute_force":       ("Credential Access",  "T1110.001 - Password Guessing"),
    "cred_stuffing":     ("Credential Access",  "T1110.004 - Credential Stuffing"),
    "default_creds":     ("Initial Access",     "T1078.001 - Default Accounts"),
    "web_exploit":       ("Initial Access",     "T1190 - Exploit Public-Facing App"),
    "web_scan":          ("Reconnaissance",     "T1595.002 - Vulnerability Scanning"),
    "path_traversal":    ("Credential Access",  "T1555 - Path Traversal Exploit"),
    "service_discovery": ("Reconnaissance",     "T1046 - Network Service Scanning"),
    "rce_attempt":       ("Execution",          "T1203 - Exploitation for Client Exec"),
}

SEVERITY = {
    "brute_force":       "MEDIUM",
    "cred_stuffing":     "HIGH",
    "default_creds":     "CRITICAL",
    "web_exploit":       "CRITICAL",
    "web_scan":          "LOW",
    "path_traversal":    "HIGH",
    "service_discovery": "LOW",
    "rce_attempt":       "CRITICAL",
}


def inject_event(service, ip, port, username=None, password=None,
                 payload=None, extra=None, tactic_key="brute_force",
                 campaign="Unknown", country="Unknown"):
    tactic, technique = TACTICS.get(tactic_key, ("Unknown", "Unknown"))
    severity          = SEVERITY.get(tactic_key, "LOW")
    try:
        requests.post(INJECT_URL, json={
            "service":   service,
            "ip":        ip,
            "port":      port,
            "username":  username or "",
            "password":  password or "",
            "payload":   payload  or "",
            "extra":     extra    or "",
            "tactic":    tactic,
            "technique": technique,
            "severity":  severity,
            "campaign":  campaign,
            "country":   country,
        }, timeout=3)
    except Exception as e:
        print(f"  [INJECT ERR] {e}")


# -- CAMPAIGN 1: Mirai Botnet Sweep --------------------------
def campaign_mirai(n=20):
    print("\n[CAMPAIGN 1] Mirai Botnet Sweep - IoT default credential spray")
    countries = ["China", "Vietnam", "Brazil", "Romania", "Iran"]
    for i in range(n):
        user, pw = random.choice(MIRAI_CREDS)
        country  = random.choice(countries)
        ip       = random_ip(country)
        service  = random.choice(["Telnet", "SSH"])

        inject_event(
            service=service, ip=ip,
            port=(2323 if service == "Telnet" else 2222),
            username=user, password=pw, tactic_key="default_creds",
            campaign="Mirai Botnet", country=country,
            extra=f"IoT sweep attempt #{i+1}",
        )

        if service == "Telnet":
            try:
                s = socket.socket()
                s.settimeout(4)
                s.connect((HOST, 2323))
                s.recv(256)
                s.sendall(f"{user}\r\n".encode())
                s.recv(256)
                s.sendall(f"{pw}\r\n".encode())
                s.recv(256)
                s.close()
            except Exception:
                pass

        time.sleep(random.uniform(0.15, 0.5))
    print(f"  Done: {n} Mirai attempts sent")


# -- CAMPAIGN 2: Credential Stuffing -------------------------
def campaign_cred_stuffing(n=15):
    print("\n[CAMPAIGN 2] Credential Stuffing - leaked password dump replay")
    countries = ["Russia", "Ukraine", "Netherlands", "Germany"]
    for i in range(n):
        user    = random.choice(USERNAMES)
        pw      = random.choice(PASSWORDS)
        country = random.choice(countries)
        ip      = random_ip(country)
        service = random.choice(["FTP", "SSH"])

        inject_event(
            service=service, ip=ip,
            port=(2121 if service == "FTP" else 2222),
            username=user, password=pw, tactic_key="cred_stuffing",
            campaign="Credential Stuffing", country=country,
            extra=f"Leaked-db combo #{i+1}",
        )

        if service == "FTP":
            try:
                s = socket.socket()
                s.settimeout(5)
                s.connect((HOST, 2121))
                s.recv(256)
                s.sendall(f"USER {user}\r\n".encode())
                s.recv(256)
                s.sendall(f"PASS {pw}\r\n".encode())
                s.recv(256)
                s.sendall(b"QUIT\r\n")
                s.close()
            except Exception:
                pass
        else:
            # Proper SSH auth via Paramiko (no banner errors)
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(
                    HOST, port=2222, username=user, password=pw,
                    timeout=5, banner_timeout=10,
                    look_for_keys=False, allow_agent=False,
                )
            except paramiko.AuthenticationException:
                pass  # Expected - honeypot always rejects
            except Exception:
                pass
            finally:
                try:
                    client.close()
                except Exception:
                    pass

        time.sleep(random.uniform(0.3, 0.7))
    print(f"  Done: {n} credential stuffing attempts sent")


# -- CAMPAIGN 3: Web Vulnerability Scan ----------------------
def campaign_web_scan(n=25):
    print("\n[CAMPAIGN 3] Web Vulnerability Scan - automated exploit-path enumeration")
    countries = ["USA", "Germany", "Netherlands", "South Korea"]
    for i in range(n):
        path, path_desc = random.choice(HTTP_PATHS)
        ua, tool_name   = random.choice(USER_AGENTS)
        country         = random.choice(countries)
        ip              = random_ip(country)

        if "cmd=" in path or "shell" in path or "eval" in path or "gpon" in path.lower():
            tactic_key = "rce_attempt"
        elif "passwd" in path or "etc" in path or "htpasswd" in path:
            tactic_key = "path_traversal"
        elif "wp-login" in path or "xmlrpc" in path or "admin" in path:
            tactic_key = "web_exploit"
        else:
            tactic_key = "web_scan"

        inject_event(
            service="HTTP", ip=ip, port=8080,
            payload=f"GET {path} HTTP/1.1",
            extra=f"UA={ua} | Tool={tool_name} | Target={path_desc}",
            tactic_key=tactic_key,
            campaign="Web Vulnerability Scan",
            country=country,
        )

        try:
            req = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {HOST}\r\n"
                f"User-Agent: {ua}\r\n"
                f"Accept: */*\r\n\r\n"
            )
            s = socket.socket()
            s.settimeout(4)
            s.connect((HOST, 8080))
            s.sendall(req.encode())
            s.recv(1024)
            s.close()
        except Exception:
            pass

        time.sleep(random.uniform(0.1, 0.35))
    print(f"  Done: {n} web probes sent")


# -- CAMPAIGN 4: APT Reconnaissance --------------------------
def campaign_apt_recon(n=10):
    print("\n[CAMPAIGN 4] APT Reconnaissance - low-and-slow targeted probing")
    countries = ["Netherlands", "Germany", "USA"]
    apt_users = ["admin", "sysadmin", "root", "backup", "deploy", "devops"]
    apt_pass  = ["Summer2024!", "P@ssw0rd!", "C0mpany2024", "Welcome1!", "Qwerty123!"]
    services  = ["SSH", "FTP", "Telnet", "SSH", "SSH"]
    for i in range(n):
        country = random.choice(countries)
        ip      = random_ip(country)
        service = random.choice(services)
        user    = random.choice(apt_users)
        pw      = random.choice(apt_pass)

        inject_event(
            service=service, ip=ip,
            port={"SSH": 2222, "FTP": 2121, "Telnet": 2323}[service],
            username=user, password=pw,
            tactic_key="service_discovery" if i < 3 else "brute_force",
            campaign="APT Reconnaissance",
            country=country,
            extra=f"Targeted recon phase {i+1}/{n}",
        )
        time.sleep(random.uniform(0.8, 2.0))  # Slow - mimics APT behaviour
    print(f"  Done: {n} APT recon probes sent")


# -- CAMPAIGN 5: Script-Kiddie Blast -------------------------
def campaign_script_kiddie(n=15):
    print("\n[CAMPAIGN 5] Script-Kiddie Blast - noisy multi-service brute-force")
    countries = ["Russia", "China", "Brazil", "Ukraine", "India"]
    for i in range(n):
        country = random.choice(countries)
        ip      = random_ip(country)
        service = random.choice(["SSH", "FTP", "Telnet"])
        user    = random.choice(USERNAMES)
        pw      = random.choice(PASSWORDS)

        inject_event(
            service=service, ip=ip,
            port={"SSH": 2222, "FTP": 2121, "Telnet": 2323}[service],
            username=user, password=pw,
            tactic_key="brute_force",
            campaign="Script-Kiddie Blast",
            country=country,
        )
        time.sleep(random.uniform(0.05, 0.2))
    print(f"  Done: {n} script-kiddie blasts sent")


if __name__ == "__main__":
    print("=" * 60)
    print("  HoneyTrap Attack Simulator  - Realistic Tactics Edition")
    print("  Make sure honeypot_server.py is running first!")
    print("=" * 60)
    print("\nRunning 5 attack campaigns in parallel...")
    print("Each campaign uses realistic IPs and MITRE ATT&CK tactics.\n")

    campaigns = [
        threading.Thread(target=campaign_mirai,         kwargs={"n": 20}, name="Mirai",     daemon=True),
        threading.Thread(target=campaign_cred_stuffing, kwargs={"n": 15}, name="CredStuff", daemon=True),
        threading.Thread(target=campaign_web_scan,      kwargs={"n": 25}, name="WebScan",   daemon=True),
        threading.Thread(target=campaign_apt_recon,     kwargs={"n": 10}, name="APT",       daemon=True),
        threading.Thread(target=campaign_script_kiddie, kwargs={"n": 15}, name="ScriptKid", daemon=True),
    ]

    for t in campaigns:
        t.start()
        time.sleep(0.5)

    for t in campaigns:
        t.join()

    print("\n" + "=" * 60)
    print("  SIMULATION COMPLETE!")
    print("  Dashboard: http://localhost:5000")
    print("=" * 60)
