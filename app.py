import os
from PIL import Image
import requests
from io import BytesIO
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Load item data once when the server starts
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

icon_size = 90

keyword_to_index = {
    "top": 0,
    "bottom": 2,
    "hair": 3,
    "headadditive": 4,
    "accessory": 5,
    "shoe": 6,
}

def generate_clothes_image(uid, region):
    try:
        # Step 1: Get player info from API
        api_url = f"https://free-fire-info-site-phi.vercel.app/player-info?region={region}&uid={uid}"
        response = requests.get(api_url)
        data = response.json()

        if "profileInfo" not in data:
            return None, "Player not found or API error"

        avatar_id = data["profileInfo"]["avatarId"]
        clothes = data["profileInfo"]["clothes"]

        # Step 2: Load background image
        try:
            avatar_path = f"avatar/{avatar_id}.png"
            if not os.path.exists(avatar_path):
                # Try to download if not exists
                avatar_url = f"https://icons-freefire.vercel.app/AVATAR/{avatar_id}.png"
                avatar_response = requests.get(avatar_url)
                if avatar_response.status_code == 200:
                    with open(avatar_path, "wb") as f:
                        f.write(avatar_response.content)
                else:
                    # Use default avatar if specific one not found
                    avatar_path = "avatar/default.png"
            
            background = Image.open(avatar_path).convert("RGBA")
        except Exception as e:
            return None, f"Error loading avatar: {str(e)}"

        used_indexes = set()

        # Step 3: Place icons based on keywords
        for item_id in clothes:
            try:
                item = item_lookup.get(item_id)
                if not item:
                    print(f"⚠️ ID {item_id} not found in itemData.json")
                    continue

                icon_name = item.get("Icon", "").lower()
                matched_index = None

                for keyword, idx in keyword_to_index.items():
                    if keyword in icon_name:
                        matched_index = idx
                        break

                if matched_index is None:
                    matched_index = 1  # default position

                if matched_index in used_indexes:
                    print(f"❌ Slot {matched_index} already used, skipping {item_id}")
                    continue

                used_indexes.add(matched_index)

                icon_url = f"https://icons-freefire.vercel.app/ICONS/{item_id}.png"
                icon_response = requests.get(icon_url)
                if icon_response.status_code != 200:
                    continue

                icon = Image.open(BytesIO(icon_response.content)).convert("RGBA")
                icon = icon.resize((icon_size, icon_size))

                cx, cy = hex_positions[matched_index]
                x = cx - icon_size // 2
                y = cy - icon_size // 2

                background.paste(icon, (x, y), icon)

            except Exception as e:
                print(f"❌ Error processing item {item_id}: {e}")

        # Step 4: Save the output
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_filename = f"SRIAPI/{uid}_{timestamp}.png"
        
        # Create SRIAPI directory if not exists
        os.makedirs("SRIAPI", exist_ok=True)
        
        background.save(output_filename)
        return output_filename, None

    except Exception as e:
        return None, str(e)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Parse query parameters
            query = parse_qs(urlparse(self.path).query)
            uid = query.get('uid', [''])[0]
            region = query.get('region', [''])[0]

            if not uid or not region:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Both uid and region parameters are required"
                }).encode('utf-8'))
                return

            output_path, error = generate_clothes_image(uid, region)

            if error:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": error,
                    "uid": uid,
                    "region": region
                }).encode('utf-8'))
                return

            # Return the image URL
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "image_url": f"https://{self.headers.get('Host')}/{output_path}",
                "uid": uid,
                "region": region
            }).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": f"Internal server error: {str(e)}"
            }).encode('utf-8'))
