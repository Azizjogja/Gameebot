import os
import requests
from collections import defaultdict, deque

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_BOT_TOKEN = os.environ.get("8513790057:AAFU3x_Xd4Nxslae6sDX1SKrJY9alDeKzGM")
DEEPSEEK_API_KEY = os.environ.get("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")

# DeepSeek OpenAI-compatible endpoint
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN env var")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("Missing DEEPSEEK_API_KEY env var")

# Simpan konteks chat per user (biar nyambung). Batasi biar gak bengkak.
history = defaultdict(lambda: deque(maxlen=12))  # 12 pesan terakhir

def deepseek_chat(messages):
    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 800,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hai! Kirim pesan apa saja—aku jawab pakai DeepSeek.\n"
        "Perintah: /reset untuk hapus konteks."
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    history[uid].clear()
    await update.message.reply_text("Konteks chat sudah di-reset ✅")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_text = update.message.text.strip()

    # Optional: system prompt
    system = {"role": "system", "content": "Kamu asisten yang helpful, jawab ringkas dan jelas dalam Bahasa Indonesia."}

    # Ambil riwayat + pesan user terbaru
    msgs = [system]
    msgs.extend(list(history[uid]))
    msgs.append({"role": "user", "content": user_text})

    try:
        await update.message.chat.send_action("typing")
        answer = deepseek_chat(msgs)
    except requests.HTTPError as e:
        await update.message.reply_text(f"Error dari DeepSeek API: {e}")
        return
    except Exception as e:
        await update.message.reply_text(f"Terjadi error: {e}")
        return

    # Simpan ke history
    history[uid].append({"role": "user", "content": user_text})
    history[uid].append({"role": "assistant", "content": answer})

    await update.message.reply_text(answer)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()