import asyncio
import threading
import os
from fastapi import FastAPI
import uvicorn
from bale import Bot, Message
import httpx
import json

bot = Bot(token="210722128:ZVA73ro5RguzGOUUKstc1cDChCnSLfKExxmKTpvB")
app = FastAPI()

@app.get("/")
async def health_check():
    return {"status": "✅ Bale bot with yt1s is running."}

@bot.event
async def on_ready():
    print("✅ ربات آماده است.")

def extract_youtube_link(text: str) -> str | None:
    if ("youtube.com/watch?v=" in text or "youtu.be/" in text) and "VIDEO_ID" not in text:
        return text.strip()
    return None

async def get_download_link_yt1s(url: str) -> str | None:
    try:
        async with httpx.AsyncClient() as client:
            # مرحله اول: ارسال لینک برای پردازش
            data = {
                "q": url,
                "vt": "mp4"
            }
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            res1 = await client.post("https://yt1s.ltd/api/ajaxSearch/index", data=data, headers=headers)
            info = res1.json()
            vid = info.get("vid")
            k = info.get("links", {}).get("mp4", {}).get("18", {}).get("k")

            if not vid or not k:
                return None

            # مرحله دوم: دریافت لینک نهایی
            data2 = {
                "vid": vid,
                "k": k
            }
            res2 = await client.post("https://yt1s.ltd/api/ajaxConvert/convert", data=data2, headers=headers)
            final = res2.json()
            return final.get("dlink")
    except Exception as e:
        print(f"❌ yt1s error: {e}")
        return None

async def download_file(url: str, output_path: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            with open(output_path, "wb") as f:
                f.write(response.content)
        return True
    except Exception as e:
        print(f"❌ دانلود فایل: {e}")
        return False

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
        await bot.send_message(chat_id=message.author.user_id, text="⏳ در حال دریافت لینک از yt1s...")
        direct_url = await get_download_link_yt1s(yt_link)
        if direct_url:
            filename = "video.mp4"
            success = await download_file(direct_url, filename)
            if success:
                try:
                    await bot.send_document(chat_id=message.author.user_id, file=filename)
                    await bot.send_message(chat_id=message.author.user_id, text="✅ ویدیو ارسال شد.")
                except Exception as e:
                    await bot.send_message(chat_id=message.author.user_id, text="❌ ارسال فایل ناموفق بود.")
                    print(f"❌ ارسال فایل: {e}")
                finally:
                    os.remove(filename)
            else:
                await bot.send_message(chat_id=message.author.user_id, text="❌ دانلود فایل ناموفق بود.")
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
