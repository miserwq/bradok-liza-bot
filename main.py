
import os
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
ALLOWED_CHAT_ID = os.getenv("ALLOWED_CHAT_ID", "")
MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")

client = OpenAI(api_key=OPENAI_API_KEY)
history = {}

SYSTEM_PROMPT = """
Ты — Брадок, дружелюбный Telegram-бот.
Ты общаешься с Лизой, которую ласково называют Бабачай.
Говори на русском языке, тепло, естественно и с юмором.
Можешь шутить и использовать разговорный стиль.
Не утверждай, что ты настоящий Максим или что пишешь от его имени.
Если не знаешь чего-то о Максиме, не выдумывай.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет, Бабачай! ❤️ Я Брадок. Теперь можем поболтать!"
    )

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type != "private":
        return

    chat_id = str(update.effective_chat.id)

    if not ALLOWED_CHAT_ID or chat_id != ALLOWED_CHAT_ID:
        logger.info("Неавторизованный chat_id: %s", chat_id)
        await update.message.reply_text(
            "Пока доступ не настроен ❤️"
        )
        return

    if not update.message or not update.message.text:
        return

    messages = history.setdefault(chat_id, [])
    messages.append({
        "role": "user",
        "content": update.message.text
    })
    messages[:] = messages[-12:]

    try:
        response = await asyncio.to_thread(
            client.responses.create,
            model=MODEL,
            instructions=SYSTEM_PROMPT,
            input=messages,
        )
        answer = response.output_text or "Я немного задумался 😅"
        messages.append({
            "role": "assistant",
            "content": answer
        })
        messages[:] = messages[-12:]
        await update.message.reply_text(answer)
    except Exception:
        logger.exception("Ошибка OpenAI")
        await update.message.reply_text(
            "Что-то у меня случилось с мозгами 😅 Попробуй ещё раз."
        )

telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, chat)
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    yield
    await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def home():
    return {"status": "Bradok is alive"}
