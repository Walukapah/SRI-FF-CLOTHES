from flask import Flask, request, send_file
from PIL import Image
import requests
from io import BytesIO
import json
import os
from datetime import datetime

app = Flask(__name__)

with open("itemData.json", "r", encoding="utf-8") as f:
    item_data = json.load(f)

item_lookup = {item["Id"]: item for item in item_data}

hex_positions = [
    (150, 250), (158, 554), (267, 802),
    (848, 186), (911, 408), (802, 617), (889, 864)
]
icon_size = 90
keyword_to_index = {
    "top": 0, "bottom": 2, "hair": 3,
    "headadditive": 4, "accessory": 5, "shoe": 6,
}

@app.route('/api/ff-clothes')
def ff_clothes():
    uid = request.args.get("uid")
    region = request.args.get("region")

    if not uid or not region:
        return {"error": "Missing uid or region"}, 400

    try:
        # Get API data
        url = f"https://free-fire-info-site-phi.vercel.app/player-info?region={region}&uid={uid}"
        data = requests.get(url).json()
        avatar_id = data["profileInfo"]["avatarId"]
        clothes = data["profileInfo"]["clothes"]

        bg_path = f"avatar/{avatar_id}.jpg"
        if not os.path.exists(bg_path):
            return {"error": "Avatar image not found"}, 404

        background = Image.open(bg_path).convert("RGBA")
        used_indexes = set()

        for item_id in clothes:
            item = item_lookup.get(item_id)
            if not item:
                continue

            icon_name = item.get("Icon", "").lower()
            matched_index = 1  # default

            for keyword, index in keyword_to_index.items():
                if keyword in icon_name:
                    matched_index = index
                    break

            if matched_index in used_indexes:
                continue
            used_indexes.add(matched_index)

            icon_url = f"https://icons-freefire.vercel.app/ICONS/{item_id}.png"
            icon = Image.open(BytesIO(requests.get(icon_url).content)).convert("RGBA")
            icon = icon.resize((icon_size, icon_size))
            cx, cy = hex_positions[matched_index]
            background.paste(icon, (cx - icon_size // 2, cy - icon_size // 2), icon)

        # Save image to /tmp
        now = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filename = f"{uid}-{now}.png"
        output_path = f"/tmp/{filename}"
        background.save(output_path)

        return send_file(output_path, mimetype='image/png')

    except Exception as e:
        return {"error": str(e)}, 500
