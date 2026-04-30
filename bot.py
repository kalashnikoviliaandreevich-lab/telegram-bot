import os
import numpy as np
import httpx

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from rag import embed, split
from db import save_chunk, get_all, clear

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

keyboard = ReplyKeyboardMarkup(
    [["📂 файл", "❓ вопрос"], ["🧹 очистить"]],
    resize_keyboard=True
)


async def ask_gemini(context, question):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    data = {
        "contents": [{
            "parts": [{
                "text": f"КОНТЕКСТ:\n{context}\n\nВОПРОС:\n{question}"
            }]
        }]
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=data)

    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("PRO бот готов", reply_markup=keyboard)


# --- FILE ---
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    path = "temp"

    await file.download_to_drive(path)

    text = open(path, "r", encoding="utf-8", errors="ignore").read()

    chunks = split(text)

    for c in chunks:
        vec = await embed(c)
        save_chunk(update.message.from_user.id, c, vec)

    await update.message.reply_text("Файл сохранён ✔️")


# --- TEXT ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    query = update.message.text

    rows = get_all(user_id)

    if not rows:
        await update.message.reply_text("Нет данных")
        return

    q_vec = await embed(query)

    scored = []

    for chunk, emb_blob in rows:
        emb = np.frombuffer(emb_blob, dtype="float32")
        score = np.dot(q_vec, emb)
        scored.append((score, chunk))

    scored.sort(reverse=True)

    context_text = "\n\n".join([c for _, c in scored[:3]])

    answer = await ask_gemini(context_text, query)

    await update.message.reply_text(answer)


# --- CLEAR ---
async def clear_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear(update.message.from_user.id)
    await update.message.reply_text("Очищено")


# --- MAIN ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()


if __name__ == "__main__":
    main()        "contents": [{"parts": [{"text": text[:MAX_INPUT]}]}],
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
