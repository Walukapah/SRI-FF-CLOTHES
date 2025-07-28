from flask import Flask, request, send_file
from PIL import Image
import requests
from io import BytesIO
import json
import os
from datetime import datetime

app = Flask(__name__)

# Create output folder
SAVE_FOLDER = "SRIAPI"
os.makedirs(SAVE_FOLDER, exist_ok=True)

# Load itemData.json once
with open("itemData.json", "r", encoding="utf-8") as f:
    item_data = json.load(f)
item_lookup = {item["Id"]: item for item in item_data}

# Hexagon positions
hex_positions = [
    (150, 250),  # 0 - top
    (158, 554),  # 1 - default
    (267, 802),  # 2 - bottom
    (848, 186),  # 3 - hair
    (911, 408),  # 4 - headadditive
    (802, 617),  # 5 - accessory
    (889, 864)   # 6 - shoe
]

# Keyword to hex index mapping
keyword_to_index = {
    "top": 0,
    "bottom": 2,
    "hair": 3,
    "headadditive": 4,
    "accessory": 5,
    "shoe": 6,
}

@app.route("/ff-clothes")
def ff_clothes():
    uid = request.args.get("uid")
    region = request.args.get("region")

    if not uid or not region:
        return {"error": "Missing uid or region"}, 400

    try:
        # Get player info
        api_url = f"https://free-fire-info-site-phi.vercel.app/player-info?region={region}&uid={uid}"
        response = requests.get(api_url)
        data = response.json()

        avatar_id = data["profileInfo"]["avatarId"]
        clothes = data["profileInfo"]["clothes"]

        # Load background from avatar folder
        background_path = f"avatar/{avatar_id}.png"
        if not os.path.exists(background_path):
            return {"error": f"Background not found for avatarId {avatar_id}"}, 404

        background = Image.open(background_path).convert("RGBA")
        icon_size = 90
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
                matched_index = 1  # Default to second hex

            if matched_index in used_indexes:
                continue  # Skip already filled position

            used_indexes.add(matched_index)

            icon_url = f"https://icons-freefire.vercel.app/ICONS/{item_id}.png"
            icon_response = requests.get(icon_url)
            icon = Image.open(BytesIO(icon_response.content)).convert("RGBA")
            icon = icon.resize((icon_size, icon_size))

            cx, cy = hex_positions[matched_index]
            x = cx - icon_size // 2
            y = cy - icon_size // 2

            background.paste(icon, (x, y), icon)

        # Save with filename: UID_YYYY-MM-DD_HH-MM-SS.png
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{uid}_{now}.png"
        filepath = os.path.join(SAVE_FOLDER, filename)
        background.save(filepath)

        return send_file(filepath, mimetype='image/png')

    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True, port=3000)
