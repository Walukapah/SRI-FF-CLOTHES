from flask import Flask, request, jsonify
from PIL import Image
import requests
from io import BytesIO
import json
import os
from datetime import datetime
import mimetypes

app = Flask(__name__)

# Load itemData.json
with open("itemData.json", "r", encoding="utf-8") as f:
    item_data = json.load(f)

item_lookup = {item["Id"]: item for item in item_data}

# Hex positions
hex_positions = [
    (150, 250), (158, 554), (267, 802),
    (848, 186), (911, 408), (802, 617), (889, 864)
]
icon_size = 90
keyword_to_index = {
    "top": 0, "bottom": 2, "hair": 3,
    "headadditive": 4, "accessory": 5, "shoe": 6,
}

# Catbox uploader class
class CatboxUploader:
    def __init__(self, filename):
        self.filename = filename
        self.file_host_url = "https://catbox.moe/user/api.php"

    def _mimetype(self):
        return mimetypes.guess_type(self.filename)[0] or 'application/octet-stream'

    def execute(self):
        with open(self.filename, 'rb') as file:
            files = {
                'fileToUpload': (file.name, file, self._mimetype())
            }
            data = {
                'reqtype': 'fileupload',
                'userhash': ''  # Optional Catbox userhash (leave blank for anonymous)
            }
            response = requests.post(self.file_host_url, data=data, files=files)
            return response.text

@app.route('/api/ff-clothes')
def ff_clothes():
    uid = request.args.get("uid")
    region = request.args.get("region")

    if not uid or not region:
        return jsonify({"error": "Missing uid or region"}), 400

    try:
        # Fetch player info
        url = f"https://free-fire-info-site-phi.vercel.app/player-info?region={region}&uid={uid}"
        data = requests.get(url).json()
        avatar_id = data["profileInfo"]["avatarId"]
        clothes = data["profileInfo"]["clothes"]

        bg_path = f"avatar/{avatar_id}.png"
        if not os.path.exists(bg_path):
            return jsonify({"error": f"Avatar image not found: {bg_path}"}), 404

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

        # Save image to /tmp folder
        now = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filename = f"{uid}-{now}.png"
        output_path = f"/tmp/{filename}"
        background.save(output_path)

        # Upload to Catbox
        uploader = CatboxUploader(output_path)
        image_url = uploader.execute()

        return jsonify({
            "uid": uid,
            "region": region,
            "image_url": image_url
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
