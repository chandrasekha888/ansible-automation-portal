from flask import Flask, render_template_string, request, redirect, url_for, send_file, session
from datetime import datetime
import csv
import os
import subprocess

app = Flask(__name__)
app.secret_key = "ansible-secret-key"

USERNAME = "admin"
PASSWORD = "admin123"

INVENTORY_FILE = "inventory.csv"
ALERT_FILE = "errdisable_alert.txt"
LOG_FILE = "activity_logs.csv"

last_status = "Ready"
last_run_time = "Not executed yet"
last_playbook = "None"


def load_devices():
    if not os.path.exists(INVENTORY_FILE):
        return []
    with open(INVENTORY_FILE, newline="") as f:
        return list(csv.DictReader(f))


def load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, newline="") as f:
        return list(csv.DictReader(f))[-10:][::-1]


def load_alerts():
    alerts = []
    if os.path.exists(ALERT_FILE):
        with open(ALERT_FILE) as f:
            data = f.read()
            if "err-disabled" in data.lower():
                alerts.append({
                    "severity": "Critical",
                    "switch": "SW-ACCESS-01",
                    "port": "Gi1/0/24",
                    "reason": "BPDU Guard",
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                alerts.append({
                    "severity": "Critical",
                    "switch": "SW-ACCESS-02",
                    "port": "Gi1/0/30",
                    "reason": "Storm Control",
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
    return alerts


def add_log(action, playbook, status, devices):
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["time", "user", "action", "playbook", "devices", "status"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin",
            action,
            playbook,
            ", ".join(devices),
            status
        ])


html = """
<!DOCTYPE html>
<html>
<head>
<title>Ansible NOC Portal</title>
<meta http-equiv="refresh" content="30">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{margin:0;font-family:Arial;background:#eef2f7;}
.sidebar{width:230px;height:100vh;background:#111827;color:white;position:fixed;padding:25px 15px;}
.sidebar h2{font-size:20px;margin-bottom:30px;}
.sidebar a{display:block;color:#d1d5db;text-decoration:none;padding:12px;margin:8px 0;border-radius:8px;}
.sidebar a:hover{background:#1f2937;}
.main{margin-left:260px;padding:30px;}
.header,.panel,.card{background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08);}
.header{padding:20px;margin-bottom:20px;}
.cards{display:grid;grid-template-columns:repeat(5,1fr);gap:15px;margin-bottom:20px;}
.card{padding:20px;}
.card h3{margin:0;color:#6b7280;font-size:14px;}
.card p{font-size:26px;font-weight:bold;margin:10px 0 0;}
.panel{padding:20px;margin-bottom:20px;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px;}
table{width:100%;border-collapse:collapse;}
th{background:#f3f4f6;text-align:left;padding:12px;font-size:14px;}
td{padding:12px;border-bottom:1px solid #e5e7eb;}
.badge{padding:6px 10px;border-radius:20px;font-size:12px;font-weight:bold;}
.green-badge{background:#dcfce7;color:#166534;}
.red-badge{background:#fee2e2;color:#991b1b;}
.yellow-badge{background:#fef9c3;color:#854d0e;}
.btn{padding:8px 12px;border:none;border-radius:6px;color:white;font-weight:bold;cursor:pointer;margin-right:4px;text-decoration:none;display:inline-block;font-size:13px;}
.green{background:#16a34a;}
.blue{background:#2563eb;}
.orange{background:#f97316;}
.gray{background:#6b7280;}
.red{background:#dc2626;}
.login-box{max-width:400px;background:white;margin:120px auto;padding:35px;border-radius:12px;text-align:center;}
input,select{padding:10px;margin:6px;border:1px solid #d1d5db;border-radius:8px;}
.search{width:350px;}
.alert{border-left:6px solid #dc2626;background:#fff1f2;padding:15px;margin-bottom:10px;border-radius:8px;}
.actions{white-space:nowrap;min-width:300px;}
.ip-link{color:#2563eb;font-weight:bold;text-decoration:none;}
</style>
</head>

<body>

{% if not session.get('logged_in') %}
<div class="login-box">
<h1>Ansible Automation Portal</h1>
<form method="post" action="/login">
<input name="username" placeholder="Username"><br>
<input name="password" type="password" placeholder="Password"><br>
<button class="btn blue" type="submit">Login</button>
</form>
</div>
{% else %}

<div class="sidebar">
<h2>Ansible Automation Portal</h2>
<a href="/">Dashboard</a>
<a href="#monitoring">Live Monitoring</a>
<a href="#inventory">Switch Inventory</a>
<a href="#alerts">Critical Alerts</a>
<a href="#logs">Activity Logs</a>
<a href="/logout">Logout</a>
</div>

<div class="main">

<div class="header">
<h1>Enterprise Network Automation & Monitoring Portal</h1>
<p>Live NOC dashboard for Ansible automation, switch inventory, err-disabled monitoring, and operational alerts.</p>
</div>

<div class="cards">
<div class="card"><h3>Total Devices</h3><p>{{ total }}</p></div>
<div class="card"><h3>Online</h3><p style="color:#16a34a;">{{ online }}</p></div>
<div class="card"><h3>Offline</h3><p style="color:#dc2626;">{{ offline }}</p></div>
<div class="card"><h3>Critical Alerts</h3><p style="color:#dc2626;">{{ alerts|length }}</p></div>
<div class="card"><h3>Last Updated</h3><p style="font-size:16px;">{{ now }}</p></div>
</div>

<div class="grid2">
<div class="panel">
<h2>Device Health</h2>
<canvas id="deviceChart"></canvas>
</div>

<div class="panel">
<h2>Interface Status</h2>
<canvas id="interfaceChart"></canvas>
</div>
</div>

<div class="panel" id="alerts">
<h2>Critical Alerts</h2>
{% if alerts %}
{% for a in alerts %}
<div class="alert">
<b>🔴 {{ a.severity }} Alert</b><br>
Switch: {{ a.switch }}<br>
Port: {{ a.port }}<br>
Reason: {{ a.reason }}<br>
Time: {{ a.time }}
</div>
{% endfor %}
{% else %}
<span class="badge green-badge">No Critical Alerts</span>
{% endif %}
</div>

<div class="panel">
<h2>Automation Status</h2>
<b>Status:</b> {{ last_status }}<br>
<b>Last Playbook:</b> {{ last_playbook }}<br>
<b>Updated Time:</b> {{ last_run_time }}
<br><br>
<form style="display:inline;" method="post" action="/run/backup.yml">
<button class="btn green">Backup All</button>
</form>
<form style="display:inline;" method="post" action="/run/vlan.yml">
<button class="btn blue">VLAN Deploy</button>
</form>
<form style="display:inline;" method="post" action="/run/interface.yml">
<button class="btn orange">Interface Config</button>
</form>
<form style="display:inline;" method="post" action="/run/errdisable_check.yml">
<button class="btn red">Check Err-Disabled</button>
</form>
</div>

<div class="panel" id="inventory">
<h2>Switch Inventory</h2>

<input class="search" type="text" id="searchInput" onkeyup="searchTable()" placeholder="Search switch name, IP, vendor, role, location...">

<table id="deviceTable">
<tr>
<th>Switch Name</th>
<th>IP Address</th>
<th>Vendor</th>
<th>Role</th>
<th>Location</th>
<th>Status</th>
<th>CPU</th>
<th>Memory</th>
<th>Last Configured</th>
<th>Actions</th>
</tr>

{% for d in devices %}
<tr>
<td><b>{{ d.name }}</b></td>
<td><a class="ip-link" href="http://{{ d.ip }}" target="_blank">{{ d.ip }}</a></td>
<td>{{ d.vendor }}</td>
<td>{{ d.role }}</td>
<td>{{ d.location }}</td>
<td><span class="badge green-badge">Online</span></td>
<td>{{ loop.index * 7 + 10 }}%</td>
<td>{{ loop.index * 8 + 20 }}%</td>
<td>{{ d.last_config }}</td>
<td class="actions">
<form style="display:inline;" method="post" action="/run/backup.yml"><button class="btn green">Backup</button></form>
<form style="display:inline;" method="post" action="/run/vlan.yml"><button class="btn blue">VLAN</button></form>
<form style="display:inline;" method="post" action="/run/interface.yml"><button class="btn orange">Interface</button></form>
<a class="btn gray" href="/download/switch_backup.txt">Download</a>
</td>
</tr>
{% endfor %}
</table>
</div>

<div class="panel" id="monitoring">
<h2>Interface Monitoring</h2>
<table>
<tr>
<th>Switch</th>
<th>Interface</th>
<th>Status</th>
<th>Speed</th>
<th>Reason</th>
</tr>
<tr>
<td>SW-CORE-01</td><td>Gi1/0/1</td><td><span class="badge green-badge">Up</span></td><td>1G</td><td>Normal</td>
</tr>
<tr>
<td>SW-ACCESS-01</td><td>Gi1/0/24</td><td><span class="badge red-badge">Err-disabled</span></td><td>1G</td><td>BPDU Guard</td>
</tr>
<tr>
<td>SW-ACCESS-02</td><td>Gi1/0/30</td><td><span class="badge red-badge">Err-disabled</span></td><td>1G</td><td>Storm Control</td>
</tr>
</table>
</div>

<div class="panel" id="logs">
<h2>Activity Logs</h2>
<table>
<tr>
<th>Time</th>
<th>User</th>
<th>Action</th>
<th>Playbook</th>
<th>Devices</th>
<th>Status</th>
</tr>
{% for log in logs %}
<tr>
<td>{{ log.time }}</td>
<td>{{ log.user }}</td>
<td>{{ log.action }}</td>
<td>{{ log.playbook }}</td>
<td>{{ log.devices }}</td>
<td>{{ log.status }}</td>
</tr>
{% endfor %}
</table>
</div>

</div>

<script>
function searchTable(){
let input=document.getElementById("searchInput").value.toLowerCase();
let rows=document.getElementById("deviceTable").getElementsByTagName("tr");
for(let i=1;i<rows.length;i++){
let text=rows[i].innerText.toLowerCase();
rows[i].style.display=text.includes(input)?"":"none";
}
}

new Chart(document.getElementById('deviceChart'),{
type:'doughnut',
data:{
labels:['Online','Offline'],
datasets:[{data:[{{ online }},{{ offline }}]}]
}
});

new Chart(document.getElementById('interfaceChart'),{
type:'pie',
data:{
labels:['Up','Down','Err-disabled'],
datasets:[{data:[95,3,2]}]
}
});
</script>

{% endif %}
</body>
</html>
"""


@app.route("/")
def home():
    devices = load_devices()
    alerts = load_alerts()
    logs = load_logs()

    total = len(devices)
    online = total
    offline = 0

    return render_template_string(
        html,
        devices=devices,
        alerts=alerts,
        logs=logs,
        total=total,
        online=online,
        offline=offline,
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        last_status=last_status,
        last_run_time=last_run_time,
        last_playbook=last_playbook
    )


@app.route("/login", methods=["POST"])
def login():
    if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
        session["logged_in"] = True
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/run/<playbook>", methods=["POST"])
def run_playbook(playbook):
    global last_status, last_run_time, last_playbook

    allowed = ["backup.yml", "vlan.yml", "interface.yml", "errdisable_check.yml"]

    if playbook not in allowed:
        last_status = "Invalid playbook"
        return redirect(url_for("home"))

    result = subprocess.run(
        ["ansible-playbook", "-i", "hosts.ini", playbook],
        capture_output=True,
        text=True
    )

    last_playbook = playbook
    last_run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if result.returncode == 0:
        last_status = f"{playbook} executed successfully ✅"
        add_log("Run Playbook", playbook, "Success", ["All Devices"])
    else:
        last_status = f"{playbook} failed ❌"
        add_log("Run Playbook", playbook, "Failed", ["All Devices"])

    return redirect(url_for("home"))


@app.route("/download/<filename>")
def download(filename):
    return send_file(filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
