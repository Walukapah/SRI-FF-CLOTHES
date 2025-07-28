from flask import Flask, request, jsonify
from PIL import Image
import requests
from io import BytesIO
import json
import os
from datetime import datetime

app = Flask(__name__)

# Load itemData.json once
with open("itemData.json", "r", encoding="utf-8") as f:
    item_data = json.load(f)

item_lookup = {item["Id"]: item for item in item_data}

# Hex positions
hex_positions = [
    (150, 250),  # 0 - top
    (158, 554),  # 1 - default
    (267, 802),  # 2 - bottom
    (848, 186),  # 3 - hair
    (911, 408),  # 4 - headadditive
    (802, 617),  # 5 - accessory
    (889, 864)   # 6 - shoe
]
icon_size = 90
keyword_to_index = {
    "top": 0,
    "bottom": 2,
    "hair": 3,
    "headadditive": 4,
    "accessory": 5,
    "shoe": 6,
}

@app.route('/api/ff-clothes')
def ff_clothes():
    uid = request.args.get("uid")
    region = request.args.get("region")

    if not uid or not region:
        return jsonify({"error": "Missing uid or region"}), 400

    try:
        # Fetch player info
        api_url = f"https://free-fire-info-site-phi.vercel.app/player-info?region={region}&uid={uid}"
        data = requests.get(api_url).json()

        avatar_id = data["profileInfo"]["avatarId"]
        clothes = data["profileInfo"]["clothes"]

        bg_path = f"avatar/{avatar_id}.png"
        if not os.path.exists(bg_path):
            return jsonify({"error": "Avatar image not found"}), 404

        background = Image.open(bg_path).convert("RGBA")
        used_indexes = set()

        for item_id in clothes:
            item = item_lookup.get(item_id)
            if not item:
                continue
            icon_name = item.get("Icon", "").lower()
            matched_index = None
            for keyword, idx in keyword_to_index.items():
                if keyword in icon_name:
                    matched_index = idx
                    break
            if matched_index is None:
                matched_index = 1  # default

            if matched_index in used_indexes:
                continue
            used_indexes.add(matched_index)

            icon_url = f"https://icons-freefire.vercel.app/ICONS/{item_id}.png"
            icon = Image.open(BytesIO(requests.get(icon_url).content)).convert("RGBA")
            icon = icon.resize((icon_size, icon_size))

            cx, cy = hex_positions[matched_index]
            x = cx - icon_size // 2
            y = cy - icon_size // 2
            background.paste(icon, (x, y), icon)

        # Save with UID-date-time name
        now = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        filename = f"{uid}-{now}.png"
        output_folder = "SRIAPI"
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, filename)
        background.save(output_path)

        return jsonify({"image": f"/{output_path}"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
