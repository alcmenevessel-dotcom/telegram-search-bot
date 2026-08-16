import os
from flask import Flask, request
import requests

app = Flask(__name__)

TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"


def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text
        },
        timeout=15
    )


def get_telegram_file(file_id):
    response = requests.get(
        f"{TELEGRAM_API}/getFile",
        params={"file_id": file_id},
        timeout=15
    )

    data = response.json()

    if not data.get("ok"):
        return None

    file_path = data["result"]["file_path"]

    return f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"


@app.route("/", methods=["GET"])
def home():
    return "Telegram bot is running!", 200


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
        photo = message["photo"][-1]
        file_id = photo["file_id"]

        photo_url = get_telegram_file(file_id)

        if photo_url:
            send_message(
                chat_id,
                "📷 Photo received ✅\n\n"
                "The bot can now receive photos.\n"
                "Next step: connect reverse image search."
            )
        else:
            send_message(chat_id, "❌ Could not download the photo.")

        return "OK", 200

    # TEXT
    text = message.get("text", "")

    if text == "/start":
        send_message(
            chat_id,
            "Bot is online! ✅\n\n"
            "Send me text, a link, or a photo."
        )

    elif text.startswith("/search"):
        query = text[len("/search"):].strip()

        if not query:
            send_message(
                chat_id,
                "🔎 Usage:\n/search your query"
            )
        else:
            send_message(
                chat_id,
                f"🔎 Search request received:\n{query}\n\n"
                "Internet search will be connected next."
            )

    elif text:
        send_message(
            chat_id,
            f"You sent: {text}"
        )

    else:
        send_message(
            chat_id,
            "Unsupported message type."
        )

    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
