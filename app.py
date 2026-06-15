from flask import Flask, render_template_string, request, redirect, url_for, send_file, session
import subprocess

app = Flask(__name__)
app.secret_key = "ansible-secret-key"

USERNAME = "admin"
PASSWORD = "admin123"
last_status = ""

html = """
<!DOCTYPE html>
<html>
<head>
<title>Ansible Portal</title>
<style>
body { font-family: Arial; background:#f4f6f8; text-align:center; padding:50px; }
.box { background:white; padding:30px; border-radius:12px; max-width:650px; margin:auto; box-shadow:0 4px 12px rgba(0,0,0,.15); }
a, button { display:block; margin:12px auto; padding:12px; width:320px; background:#2563eb; color:white; text-decoration:none; border:0; border-radius:8px; font-weight:bold; cursor:pointer; }
button.run { background:#16a34a; }
input { padding:10px; margin:8px; width:250px; }
.status { margin:15px; font-weight:bold; color:#16a34a; }
</style>
</head>
<body>
<div class="box">
<h1>Ansible Automation Portal</h1>

{% if not session.get('logged_in') %}
<form method="post" action="/login">
<input name="username" placeholder="Username"><br>
<input name="password" type="password" placeholder="Password"><br>
<button type="submit">Login</button>
</form>
{% else %}

<h2>Run Ansible Playbooks</h2>

<form method="post" action="/run/backup.yml">
<button class="run" type="submit">Run Backup Playbook</button>
</form>

<form method="post" action="/run/vlan.yml">
<button class="run" type="submit">Run VLAN Playbook</button>
</form>

<form method="post" action="/run/interface.yml">
<button class="run" type="submit">Run Interface Playbook</button>
</form>

<div class="status">{{ status }}</div>

<h2>Download Files</h2>
<a href="/download/switch_backup.txt">Download Switch Backup</a>
<a href="/download/vlan_config.txt">Download VLAN Config</a>
<a href="/download/interface_config.txt">Download Interface Config</a>
<a href="/download/backup.yml">Download Backup Playbook</a>
<a href="/download/vlan.yml">Download VLAN Playbook</a>
<a href="/download/interface.yml">Download Interface Playbook</a>

<a href="/logout">Logout</a>
{% endif %}
</div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(html, status=last_status)

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
    global last_status

    if not session.get("logged_in"):
        return redirect(url_for("home"))

    allowed = ["backup.yml", "vlan.yml", "interface.yml"]

    if playbook not in allowed:
        last_status = "Invalid playbook"
        return redirect(url_for("home"))

    result = subprocess.run(
        ["ansible-playbook", "-i", "hosts.ini", playbook],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        last_status = f"{playbook} executed successfully ✅"
    else:
        last_status = f"{playbook} failed ❌"

    return redirect(url_for("home"))

@app.route("/download/<filename>")
def download(filename):
    if not session.get("logged_in"):
        return redirect(url_for("home"))
    return send_file(filename, as_attachment=True)

app.run(host="0.0.0.0", port=5000)
