import os
import logging
import httpx
import pytesseract

from PIL import Image
from pdfminer.high_level import extract_text
from docx import Document

from telegram import (
    Update,
    ReplyKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ================= SETTINGS =================

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

MODEL = "gemini-2.0-flash"

MAX_TEXT = 15000

# user_id -> document text
user_docs = {}

keyboard = ReplyKeyboardMarkup(
    [
        ["🧹 Очистить память"],
    ],
    resize_keyboard=True
)

# ================= GEMINI =================

async def ask_gemini(prompt: str) -> str:

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent?key={GEMINI_API_KEY}"
    )

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt[:MAX_TEXT]
                    }
                ]
            }
        ]
    }

    try:

        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(url, json=data)

        response.raise_for_status()

        result = response.json()

        return result["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:

        logging.error(e)

        return "Ошибка Gemini API."

# ================= FILE READERS =================

def read_txt(path):

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def read_pdf(path):

    return extract_text(path)

def read_docx(path):

    doc = Document(path)

    return "\n".join(
        [p.text for p in doc.paragraphs]
    )

def read_image(path):

    image = Image.open(path)

    text = pytesseract.image_to_string(
        image,
        lang="eng"
    )

    return text

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📚 AI Study Bot\n\n"
        "Отправь:\n"
        "- txt\n"
        "- pdf\n"
        "- docx\n"
        "- фото с текстом\n\n"
        "Потом задавай вопросы.",
        reply_markup=keyboard
    )

# ================= CLEAR =================

async def clear_memory(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.message.from_user.id

    user_docs.pop(user_id, None)

    await update.message.reply_text(
        "Память очищена 🧹"
    )

# ================= FILES =================

async def handle_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.message.from_user.id

    document = update.message.document

    if not document:
        return

    await update.message.reply_text(
        "📂 Обрабатываю файл..."
    )

    file = await document.get_file()

    path = f"temp_{user_id}"

    await file.download_to_drive(path)

    text = ""

    try:

        filename = document.file_name.lower()

        if filename.endswith(".txt"):

            text = read_txt(path)

        elif filename.endswith(".pdf"):

            text = read_pdf(path)

        elif filename.endswith(".docx"):

            text = read_docx(path)

        else:

            await update.message.reply_text(
                "❌ Только txt/pdf/docx"
            )

            return

        text = text[:MAX_TEXT]

        user_docs[user_id] = text

        await update.message.reply_text(
            "✅ Файл загружен.\n"
            "Теперь задавай вопросы."
        )

    except Exception as e:

        logging.error(e)

        await update.message.reply_text(
            "Ошибка обработки файла."
        )

    finally:

        if os.path.exists(path):
            os.remove(path)

# ================= PHOTOS OCR =================

async def handle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.message.from_user.id

    await update.message.reply_text(
        "📸 Считываю текст..."
    )

    photo = await update.message.photo[-1].get_file()

    path = f"photo_{user_id}.jpg"

    await photo.download_to_drive(path)

    try:

        text = read_image(path)

        if not text.strip():

            await update.message.reply_text(
                "Не смог прочитать текст 😔"
            )

            return

        text = text[:MAX_TEXT]

        user_docs[user_id] = text

        await update.message.reply_text(
            "✅ Текст с фото сохранён.\n"
            "Теперь можешь задавать вопросы."
        )

    except Exception as e:

        logging.error(e)

        await update.message.reply_text(
            "Ошибка OCR."
        )

    finally:

        if os.path.exists(path):
            os.remove(path)

# ================= QUESTIONS =================

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text

    if text == "🧹 Очистить память":

        await clear_memory(update, context)

        return

    user_id = update.message.from_user.id

    if user_id not in user_docs:

        await update.message.reply_text(
            "📂 Сначала отправь файл или фото."
        )

        return

    doc_text = user_docs[user_id]

    prompt = f"""
Ты умный помощник по учебным материалам.

Вот текст:

{doc_text}

Вопрос пользователя:

{text}

Отвечай:
- понятно
- кратко
- с примерами если нужно
"""

    await update.message.reply_text(
        "🧠 Думаю..."
    )

    answer = await ask_gemini(prompt)

    await update.message.reply_text(answer)

# ================= MAIN =================

def main():

    app = Application.builder().token(
        TELEGRAM_TOKEN
    ).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        MessageHandler(
            filters.Document.ALL,
            handle_document
        )
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text
        )
    )

    print("BOT STARTED")

    app.run_polling()

if __name__ == "__main__":
    main()# --- START ---
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
   main() 
    

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
