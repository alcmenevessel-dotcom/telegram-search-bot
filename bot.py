import os
import uuid
import requests
from flask import Flask, request, send_from_directory

app = Flask(__name__)

TOKEN = os.environ["BOT_TOKEN"]
SERPAPI_KEY = os.environ["SERPAPI_KEY"]

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"
BASE_URL = "https://telegram-search-bot-8wpa.onrender.com"

UPLOAD_FOLDER = "/tmp/images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text[:4000],
            "disable_web_page_preview": True
        },
        timeout=20
    )


def web_search(query):
    response = requests.get(
        "https://serpapi.com/search.json",
        params={
            "engine": "google",
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": 10
        },
        timeout=60
    )

    return response.json()


def format_web_results(results):
    if "error" in results:
        return f"❌ Search error:\n{results['error']}"

    items = results.get("organic_results", [])

    if not items:
        return "No public web results found."

    output = "🔎 Public web results:\n\n"

    for i, item in enumerate(items[:8], start=1):
        title = item.get("title", "Untitled")
        link = item.get("link", "")
        snippet = item.get("snippet", "")

        output += f"{i}. {title}\n"

        if snippet:
            output += f"{snippet}\n"

        if link:
            output += f"{link}\n"

        output += "\n"

    return output


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

    with open(os.path.join(UPLOAD_FOLDER, filename), "wb") as file:
        file.write(photo_response.content)

    return filename


def google_lens_search(image_url):
    response = requests.get(
        "https://serpapi.com/search.json",
        params={
            "engine": "google_lens",
            "url": image_url,
            "type": "visual_matches",
            "safe": "active",
            "api_key": SERPAPI_KEY
        },
        timeout=60
    )

    return response.json()


def format_lens_results(results):
    if "error" in results:
        return f"❌ Image search error:\n{results['error']}"

    matches = results.get("visual_matches", [])

    if not matches:
        return "No visual matches found."

    output = "📷 Visual matches:\n\n"

    for i, item in enumerate(matches[:8], start=1):
        title = item.get("title", "Untitled")
        source = item.get("source", "")
        link = item.get("link", "")

        output += f"{i}. {title}\n"

        if source:
            output += f"{source}\n"

        if link:
            output += f"{link}\n"

        output += "\n"

    return output


@app.route("/", methods=["GET"])
def home():
    return "Telegram search bot is running!", 200


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

    # PHOTO
    if "photo" in message:
        send_message(
            chat_id,
            "🔎 Photo received. Searching for visual matches..."
        )

        photo = message["photo"][-1]
        filename = download_telegram_photo(photo["file_id"])

        if not filename:
            send_message(chat_id, "❌ Could not download the photo.")
            return "OK", 200

        image_url = f"{BASE_URL}/images/{filename}"

        try:
            results = google_lens_search(image_url)
            send_message(chat_id, format_lens_results(results))

        except Exception as error:
            send_message(chat_id, f"❌ Image search failed:\n{error}")

        return "OK", 200

    text = message.get("text", "").strip()

    # START
    if text == "/start":
        send_message(
            chat_id,
            "✅ Search bot is online.\n\n"
            "Commands:\n"
            "/name First Last\n"
            "/email example@email.com\n"
            "/phone +1234567890\n"
            "/search anything\n\n"
            "You can also send a photo."
        )

    # NAME
    elif text.startswith("/name"):
        query = text[len("/name"):].strip()

        if not query:
            send_message(chat_id, "Usage:\n/name First Last")
        else:
            send_message(chat_id, "🔎 Searching public web results...")

            try:
                results = web_search(query)
                send_message(chat_id, format_web_results(results))
            except Exception as error:
                send_message(chat_id, f"❌ Search failed:\n{error}")

    # EMAIL
    elif text.startswith("/email"):
        email = text[len("/email"):].strip()

        if not email:
            send_message(chat_id, "Usage:\n/email example@email.com")
        else:
            send_message(chat_id, "🔎 Searching public mentions of this email...")

            try:
                results = web_search(f'"{email}"')
                send_message(chat_id, format_web_results(results))
            except Exception as error:
                send_message(chat_id, f"❌ Search failed:\n{error}")

    # PHONE
    elif text.startswith("/phone"):
        phone = text[len("/phone"):].strip()

        if not phone:
            send_message(chat_id, "Usage:\n/phone +1234567890")
        else:
            send_message(chat_id, "🔎 Searching public mentions of this number...")

            try:
                results = web_search(f'"{phone}"')
                send_message(chat_id, format_web_results(results))
            except Exception as error:
                send_message(chat_id, f"❌ Search failed:\n{error}")

    # GENERAL SEARCH
    elif text.startswith("/search"):
        query = text[len("/search"):].strip()

        if not query:
            send_message(chat_id, "Usage:\n/search your query")
        else:
            send_message(chat_id, "🔎 Searching...")

            try:
                results = web_search(query)
                send_message(chat_id, format_web_results(results))
            except Exception as error:
                send_message(chat_id, f"❌ Search failed:\n{error}")

    elif text:
        send_message(
            chat_id,
            "Use one of these commands:\n\n"
            "/name First Last\n"
            "/email example@email.com\n"
            "/phone +1234567890\n"
            "/search anything\n\n"
            "Or send me a photo."
        )

    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
