import os
import uuid
import requests
from flask import Flask, request, send_from_directory

app = Flask(__name__)

TOKEN = os.environ["BOT_TOKEN"]
SERPAPI_KEY = os.environ["SERPAPI_KEY"]

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# Render public URL
BASE_URL = "https://telegram-search-bot-8wpa.onrender.com"

UPLOAD_FOLDER = "/tmp/images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True
        },
        timeout=20
    )


def download_telegram_photo(file_id):
    response = requests.get(
        f"{TELEGRAM_API}/getFile",
        params={"file_id": file_id},
        timeout=20
    )

    data = response.json()

    if not data.get("ok"):
        return None

    file_path = data["result"]["file_path"]

    photo_response = requests.get(
        f"https://api.telegram.org/file/bot{TOKEN}/{file_path}",
        timeout=30
    )

    if photo_response.status_code != 200:
        return None

    filename = f"{uuid.uuid4().hex}.jpg"
    local_path = os.path.join(UPLOAD_FOLDER, filename)

    with open(local_path, "wb") as f:
        f.write(photo_response.content)

    return filename


def google_lens_search(image_url):
    params = {
        "engine": "google_lens",
        "url": image_url,
        "api_key": SERPAPI_KEY,
        "type": "visual_matches",
        "safe": "active"
    }

    response = requests.get(
        "https://serpapi.com/search.json",
        params=params,
        timeout=60
    )

    return response.json()


@app.route("/", methods=["GET"])
def home():
    return "Telegram image search bot is running!", 200


@app.route("/images/<filename>", methods=["GET"])
def serve_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(silent=True)

    if not update:
        return "OK", 200

    message = update.get("message")

    if not message:
        return "OK", 200

    chat_id = message["chat"]["id"]

    # PHOTO SEARCH
    if "photo" in message:

        send_message(
            chat_id,
            "🔎 Photo received. Searching for visual matches..."
        )

        photo = message["photo"][-1]
        file_id = photo["file_id"]

        filename = download_telegram_photo(file_id)

        if not filename:
            send_message(chat_id, "❌ Could not download the photo.")
            return "OK", 200

        image_url = f"{BASE_URL}/images/{filename}"

        try:
            results = google_lens_search(image_url)

            if "error" in results:
                send_message(
                    chat_id,
                    f"❌ Search error:\n{results['error']}"
                )
                return "OK", 200

            matches = results.get("visual_matches", [])

            if not matches:
                send_message(
                    chat_id,
                    "No visual matches found."
                )
                return "OK", 200

            message_text = "🔎 Visual matches found:\n\n"

            for i, item in enumerate(matches[:8], start=1):

                title = item.get("title", "Untitled")
                source = item.get("source", "")
                link = item.get("link", "")

                message_text += (
                    f"{i}. {title}\n"
                    f"{source}\n"
                    f"{link}\n\n"
                )

            send_message(chat_id, message_text)

        except Exception as e:
            send_message(
                chat_id,
                f"❌ Search failed: {str(e)}"
            )

        return "OK", 200

    # TEXT
    text = message.get("text", "")

    if text == "/start":
        send_message(
            chat_id,
            "Bot is online ✅\n\n"
            "Send me a photo and I will search for visually similar images and webpages."
        )

    elif text.startswith("/search"):
        query = text[len("/search"):].strip()

        if not query:
            send_message(
                chat_id,
                "Usage:\n/search your query"
            )
        else:
            send_message(
                chat_id,
                f"Search request received:\n{query}"
            )

    elif text:
        send_message(chat_id, f"You sent: {text}")

    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
