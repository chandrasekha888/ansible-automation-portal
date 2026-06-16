from flask import Flask, render_template_string, request, redirect, url_for, send_file, session
from datetime import datetime
import subprocess
import os
import csv

app = Flask(__name__)
app.secret_key = "ansible-secret-key"

USERNAME = "admin"
PASSWORD = "admin123"

INVENTORY_FILE = "inventory.csv"
LOG_FILE = "activity_logs.csv"

last_status = "Ready"
last_run_time = "Not executed yet"
last_playbook = "None"


def load_devices():
    devices = []
    if os.path.exists(INVENTORY_FILE):
        with open(INVENTORY_FILE, newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                devices.append(row)
    return devices


def save_devices(devices):
    fieldnames = ["name", "ip", "vendor", "role", "location", "status", "last_config"]
    with open(INVENTORY_FILE, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(devices)


def add_log(action, playbook, status, devices):
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as file:
        writer = csv.writer(file)
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


def load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)[-10:][::-1]


html = """
<!DOCTYPE html>
<html>
<head>
<title>Ansible Automation Portal</title>
<style>
body{margin:0;font-family:Arial,sans-serif;background:#eef2f7;}
.sidebar{width:230px;height:100vh;background:#111827;color:white;position:fixed;padding:25px 15px;}
.sidebar h2{font-size:20px;margin-bottom:35px;}
.sidebar a{display:block;color:#d1d5db;text-decoration:none;padding:12px;margin:8px 0;border-radius:8px;}
.sidebar a:hover{background:#1f2937;}
.main{margin-left:260px;padding:30px;}
.header,.panel,.card{background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08);}
.header{padding:20px;margin-bottom:20px;}
.cards{display:grid;grid-template-columns:repeat(5,1fr);gap:15px;margin-bottom:20px;}
.card{padding:20px;}
.card h3{margin:0;color:#6b7280;font-size:14px;}
.card p{font-size:24px;font-weight:bold;margin:10px 0 0;}
.panel{padding:20px;margin-bottom:20px;}
table{width:100%;border-collapse:collapse;}
th{background:#f3f4f6;text-align:left;padding:12px;font-size:14px;}
td{padding:12px;border-bottom:1px solid #e5e7eb;}
.badge{padding:6px 10px;border-radius:20px;font-size:12px;font-weight:bold;}
.success{background:#dcfce7;color:#166534;}
.pending{background:#fef9c3;color:#854d0e;}
.failed{background:#fee2e2;color:#991b1b;}
.btn{padding:8px 12px;border:none;border-radius:6px;color:white;font-weight:bold;cursor:pointer;margin-right:4px;text-decoration:none;display:inline-block;font-size:13px;}
.green{background:#16a34a;}
.blue{background:#2563eb;}
.orange{background:#f97316;}
.gray{background:#6b7280;color:white;}
.login-box{max-width:400px;background:white;margin:120px auto;padding:35px;border-radius:12px;box-shadow:0 3px 12px rgba(0,0,0,.12);text-align:center;}
input,select{padding:10px;margin:6px;border:1px solid #d1d5db;border-radius:8px;}
.search{width:350px;}
.status-box{background:#f9fafb;padding:15px;border-left:5px solid #2563eb;margin-top:10px;}
.ip-link{color:#2563eb;font-weight:bold;text-decoration:none;}
.actions{white-space:nowrap;min-width:300px;}
.bulk-actions{margin:15px 0;}
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
    <a href="#devices">Switch Inventory</a>
    <a href="#logs">Activity Logs</a>
    <a href="/logout">Logout</a>
</div>

<div class="main">

    <div class="header">
        <h1>Enterprise Network Automation Portal</h1>
        <p>Centralized Ansible platform for switch inventory, backup, VLAN deployment, and interface automation.</p>
    </div>

    <div class="cards">
        <div class="card"><h3>Total Devices</h3><p>{{ total_switches }}</p></div>
        <div class="card"><h3>Success</h3><p>{{ success_count }}</p></div>
        <div class="card"><h3>Failed</h3><p>{{ failed_count }}</p></div>
        <div class="card"><h3>Pending</h3><p>{{ pending_count }}</p></div>
        <div class="card"><h3>Last Updated</h3><p style="font-size:16px;">{{ last_run_time }}</p></div>
    </div>

    <div class="panel">
        <h2>Automation Status</h2>
        <div class="status-box">
            <b>Status:</b> {{ last_status }}<br>
            <b>Last Playbook:</b> {{ last_playbook }}<br>
            <b>Updated Time:</b> {{ last_run_time }}
        </div>
    </div>

    <div class="panel" id="devices">
        <h2>Switch Inventory</h2>

        <input class="search" type="text" id="searchInput" onkeyup="searchTable()" placeholder="Search switch name, IP, vendor, role, location...">

        <select id="vendorFilter" onchange="searchTable()">
            <option value="">All Vendors</option>
            <option value="Cisco">Cisco</option>
            <option value="Arista">Arista</option>
            <option value="Juniper">Juniper</option>
        </select>

        <select id="statusFilter" onchange="searchTable()">
            <option value="">All Status</option>
            <option value="Success">Success</option>
            <option value="Failed">Failed</option>
            <option value="Pending">Pending</option>
        </select>

        <form method="post" action="/bulk-run" id="bulkForm"></form>

        <div class="bulk-actions">
            <button form="bulkForm" class="btn green" name="playbook" value="backup.yml">Backup Selected</button>
            <button form="bulkForm" class="btn blue" name="playbook" value="vlan.yml">VLAN Selected</button>
            <button form="bulkForm" class="btn orange" name="playbook" value="interface.yml">Interface Selected</button>
        </div>

        <table id="deviceTable">
            <tr>
                <th>Select</th>
                <th>Switch Name</th>
                <th>IP Address</th>
                <th>Vendor</th>
                <th>Role</th>
                <th>Location</th>
                <th>Status</th>
                <th>Last Configured</th>
                <th>Actions</th>
            </tr>

            {% for device in devices %}
            <tr>
                <td><input form="bulkForm" type="checkbox" name="selected_devices" value="{{ device.name }}"></td>
                <td><b>{{ device.name }}</b></td>
                <td><a class="ip-link" href="http://{{ device.ip }}" target="_blank">{{ device.ip }}</a></td>
                <td>{{ device.vendor }}</td>
                <td>{{ device.role }}</td>
                <td>{{ device.location }}</td>
                <td>
                    {% if device.status == "Success" %}
                    <span class="badge success">Success</span>
                    {% elif device.status == "Failed" %}
                    <span class="badge failed">Failed</span>
                    {% else %}
                    <span class="badge pending">Pending</span>
                    {% endif %}
                </td>
                <td>{{ device.last_config }}</td>
                <td class="actions">
                    <form style="display:inline;" method="post" action="/run/backup.yml">
                        <button class="btn green" type="submit">Backup</button>
                    </form>
                    <form style="display:inline;" method="post" action="/run/vlan.yml">
                        <button class="btn blue" type="submit">VLAN</button>
                    </form>
                    <form style="display:inline;" method="post" action="/run/interface.yml">
                        <button class="btn orange" type="submit">Interface</button>
                    </form>
                    <a class="btn gray" href="/download/switch_backup.txt">Download</a>
                </td>
            </tr>
            {% endfor %}
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
function searchTable() {
    let input = document.getElementById("searchInput").value.toLowerCase();
    let vendor = document.getElementById("vendorFilter").value.toLowerCase();
    let status = document.getElementById("statusFilter").value.toLowerCase();
    let table = document.getElementById("deviceTable");
    let rows = table.getElementsByTagName("tr");

    for (let i = 1; i < rows.length; i++) {
        let rowText = rows[i].innerText.toLowerCase();
        let showSearch = rowText.includes(input);
        let showVendor = vendor === "" || rowText.includes(vendor);
        let showStatus = status === "" || rowText.includes(status);
        rows[i].style.display = (showSearch && showVendor && showStatus) ? "" : "none";
    }
}
</script>

{% endif %}
</body>
</html>
"""


@app.route("/")
def home():
    devices = load_devices()
    success_count = len([d for d in devices if d["status"] == "Success"])
    failed_count = len([d for d in devices if d["status"] == "Failed"])
    pending_count = len([d for d in devices if d["status"] == "Pending"])
    logs = load_logs()

    return render_template_string(
        html,
        devices=devices,
        logs=logs,
        total_switches=len(devices),
        success_count=success_count,
        failed_count=failed_count,
        pending_count=pending_count,
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


def execute_playbook(playbook, selected_devices=None):
    result = subprocess.run(
        ["ansible-playbook", "-i", "hosts.ini", playbook],
        capture_output=True,
        text=True
    )

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    devices = load_devices()
    selected_devices = selected_devices or [d["name"] for d in devices]

    if result.returncode == 0:
        status = "Success"
        for device in devices:
            if device["name"] in selected_devices:
                device["status"] = "Success"
                device["last_config"] = current_time
    else:
        status = "Failed"
        for device in devices:
            if device["name"] in selected_devices:
                device["status"] = "Failed"
                device["last_config"] = current_time

    save_devices(devices)
    add_log("Run Playbook", playbook, status, selected_devices)
    return status, current_time


@app.route("/run/<playbook>", methods=["POST"])
def run_playbook(playbook):
    global last_status, last_run_time, last_playbook

    if not session.get("logged_in"):
        return redirect(url_for("home"))

    allowed = ["backup.yml", "vlan.yml", "interface.yml"]

    if playbook not in allowed:
        last_status = "Invalid playbook"
        return redirect(url_for("home"))

    status, current_time = execute_playbook(playbook)

    last_status = f"{playbook} executed with status: {status}"
    last_playbook = playbook
    last_run_time = current_time

    return redirect(url_for("home"))


@app.route("/bulk-run", methods=["POST"])
def bulk_run():
    global last_status, last_run_time, last_playbook

    if not session.get("logged_in"):
        return redirect(url_for("home"))

    playbook = request.form.get("playbook")
    selected_devices = request.form.getlist("selected_devices")

    if not selected_devices:
        last_status = "No devices selected"
        return redirect(url_for("home"))

    status, current_time = execute_playbook(playbook, selected_devices)

    last_status = f"{playbook} executed on selected devices with status: {status}"
    last_playbook = playbook
    last_run_time = current_time

    return redirect(url_for("home"))


@app.route("/download/<filename>")
def download(filename):
    if not session.get("logged_in"):
        return redirect(url_for("home"))
    return send_file(filename, as_attachment=True)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
