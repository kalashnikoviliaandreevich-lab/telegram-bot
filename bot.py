import os
import logging
import httpx
from PIL import Image
import pytesseract

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- ENV ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-2.0-flash"

logging.basicConfig(level=logging.INFO)

SYSTEM_INSTRUCTION = """
Ты — спокойный учитель.
Объясняй просто, коротко и понятно.
Добавляй примеры.
В конце задавай 1-2 вопроса с ответами.
"""


MAX_INPUT = 3000


# --- Gemini ---
async def ask_gemini(text: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    data = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_INSTRUCTION}]
        },
        "contents": [{"parts": [{"text": text[:MAX_INPUT]}]}],
        "generationConfig": {"temperature": 0.7}
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=data)
        r.raise_for_status()

        return r.json()["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        logging.error(e)
        return "Ошибка AI-ответа."


# --- OCR ---
def ocr_image(path: str) -> str:
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="rus+eng")
        return text.strip()
    except Exception as e:
        logging.error(e)
        return ""


# --- handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли текст или фото — объясню.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Думаю...")
    answer = await ask_gemini(update.message.text)
    await update.message.reply_text(answer)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Читаю фото...")

    photo = await update.message.photo[-1].get_file()
    path = "temp.jpg"

    await photo.download_to_drive(path)

    text = ocr_image(path)

    os.remove(path)

    if not text:
        await update.message.reply_text("Не смог распознать текст 😔")
        return

    await update.message.reply_text("Думаю...")
    answer = await ask_gemini(text)
    await update.message.reply_text(answer)


def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("No TELEGRAM_TOKEN")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
