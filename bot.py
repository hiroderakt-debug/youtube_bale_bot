import asyncio
import threading
import os
from fastapi import FastAPI
import uvicorn
from bale import Bot, Message
import yt_dlp

bot = Bot(token="210722128:ZVA73ro5RguzGOUUKstc1cDChCnSLfKExxmKTpvB")
app = FastAPI()

@app.get("/")
async def health_check():
    return {"status": "✅ Bale bot with yt-dlp is running."}

@bot.event
async def on_ready():
    print("✅ ربات آماده است.")

def extract_youtube_link(text: str) -> str | None:
    if ("youtube.com/watch?v=" in text or "youtu.be/" in text) and "VIDEO_ID" not in text:
        return text.strip()
    return None

def get_direct_link(url: str) -> str | None:
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'format': 'best',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('url')
    except Exception as e:
        print(f"❌ yt-dlp error: {e}")
        return None

@bot.event
async def on_message(message: Message):
    if getattr(message.chat, "type", None) != "private":
        return

    text = message.content.strip()

    if text.lower() == "سلام":
        await bot.send_message(chat_id=message.author.user_id, text="سلام 👋")
        return

    yt_link = extract_youtube_link(text)
    if yt_link:
        await bot.send_message(chat_id=message.author.user_id, text="⏳ در حال استخراج لینک دانلود با yt-dlp...")
        direct_url = get_direct_link(yt_link)
        if direct_url:
            await bot.send_message(chat_id=message.author.user_id, text=f"🎬 لینک دانلود:\n{direct_url}")
        else:
            await bot.send_message(chat_id=message.author.user_id, text="❌ نتونستم لینک رو استخراج کنم.")
        return

def run_bot_thread():
    bot.run()

async def run_api():
    config = uvicorn.Config(app, host="0.0.0.0", port=10000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    threading.Thread(target=run_bot_thread, daemon=True).start()
    await run_api()

if __name__ == "__main__":
    asyncio.run(main())
