import asyncio
import threading
import os
from fastapi import FastAPI
import uvicorn
from bale import Bot, Message
import httpx
from bs4 import BeautifulSoup

bot = Bot(token="210722128:ZVA73ro5RguzGOUUKstc1cDChCnSLfKExxmKTpvB")
app = FastAPI()

@app.get("/")
async def health_check():
    return {"status": "✅ Bale bot is running."}

@bot.event
async def on_ready():
    print("✅ ربات آماده است.")

def extract_youtube_link(text: str) -> str | None:
    if ("youtube.com/watch?v=" in text or "youtu.be/" in text) and "VIDEO_ID" not in text:
        return text.strip()
    return None

async def get_download_link_y2mate(url: str) -> str | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://www.y2mate.is/en68", params={"url": url})
            soup = BeautifulSoup(response.text, "html.parser")
            link_tag = soup.find("a", {"id": "downloadmp4"})
            if link_tag and link_tag.get("href"):
                return link_tag["href"]
        return None
    except Exception as e:
        print(f"❌ Error scraping y2mate: {e}")
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
        await bot.send_message(chat_id=message.author.user_id, text="⏳ در حال دریافت لینک دانلود از y2mate...")
        direct_url = await get_download_link_y2mate(yt_link)
        if direct_url:
            await bot.send_message(chat_id=message.author.user_id, text=f"🎬 لینک دانلود:\n{direct_url}")
        else:
            await bot.send_message(chat_id=message.author.user_id, text="❌ نتونستم لینک دانلود رو پیدا کنم.")
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
