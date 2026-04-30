import asyncio
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from backend.database import users_col

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Willkommen! Sende /register <benutzername>")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Bitte gib deinen Benutzernamen an: /register Anna")
        return
    username = context.args[0]
    chat_id = update.effective_chat.id
    result = await users_col.update_one(
        {"username": username},
        {"$set": {"telegram_chat_id": chat_id}}
    )
    if result.modified_count:
        await update.message.reply_text(f"Chat-ID für {username} gespeichert.")
    else:
        await update.message.reply_text("Benutzer nicht gefunden.")

async def run_telegram_bot():
    if not TELEGRAM_TOKEN:
        print("Telegram-Token fehlt. Bot wird nicht gestartet.")
        return
    try:
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("register", register))
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        print(f"Telegram-Bot konnte nicht gestartet werden: {e}")