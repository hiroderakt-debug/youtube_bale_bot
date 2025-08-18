import asyncio
import threading
from fastapi import FastAPI
import uvicorn
from bale import Bot, Message
import yt_dlp
import os

bot = Bot(token="210722128:ZVA73ro5RguzGOUUKstc1cDChCnSLfKExxmKTpvB")
app = FastAPI()

@app.get("/")
async def health_check():
    return {"status": "✅ Bale bot is running."}

@bot.event
async def on_ready():
    print("✅ ربات آماده است.")

def extract_youtube_link(text: str) -> str | None:
    if "youtube.com/watch" in text or "youtu.be/" in text:
        return text.strip()
    return None

async def download_video(url: str, filename: str = "video.mp4") -> str | None:
    ydl_opts = {
        "format": "best[height<=360][ext=mp4]/best[ext=mp4]/best",
        "outtmpl": filename,
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return filename if os.path.exists(filename) else None
    except Exception as e:
        print(f"❌ Error downloading video: {e}")
        return None

@bot.event
async def on_message(message: Message):
    if getattr(message.chat, "type", None) != "private":
        return

    text = message.content.strip()

    if text.lower() == "سلام":
        await bot.send_message(chat_id=message.author.user_id, text="سلام")
        return

    yt_link = extract_youtube_link(text)
    if yt_link:
        await bot.send_message(chat_id=message.author.user_id, text="⏳ در حال دانلود ویدیو...")
        filename = await download_video(yt_link)
        if filename:
            await bot.send_message(chat_id=message.author.user_id, text="📤 ارسال ویدیو...")
            await bot.send_file(chat_id=message.author.user_id, file=filename)
            os.remove(filename)
        else:
            await bot.send_message(chat_id=message.author.user_id, text="❌ خطا در دانلود ویدیو.")

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
