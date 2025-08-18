import asyncio
import re
from bale import Bot, Message
from pytube import YouTube
from aiohttp import web

# ربات Bale
bot = Bot(token="210722128:ZVA73ro5RguzGOUUKstc1cDChCnSLfKExxmKTpvB")

# تابع استخراج لینک یوتیوب از متن
def extract_youtube_url(text):
    pattern = r"(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[^\s]+)"
    match = re.search(pattern, text)
    return match.group(0) if match else None

# تابع پاک‌سازی لینک و استخراج Video ID
def clean_youtube_url(url):
    try:
        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
        elif "youtube.com/watch?v=" in url:
            video_id = url.split("v=")[1].split("&")[0]
        else:
            return None
        return f"https://www.youtube.com/watch?v={video_id}"
    except Exception:
        return None

@bot.event
async def on_ready():
    print("✅ ربات Bale آماده است.")

@bot.event
async def on_message(message: Message):
    if getattr(message.chat, "type", None) != "private":
        return

    text = message.content.strip()

    if text.lower() == "سلام":
        await bot.send_message(chat_id=message.author.user_id, text="سلام 👋")

    youtube_url = extract_youtube_url(text)
    if youtube_url:
        cleaned_url = clean_youtube_url(youtube_url)
        if cleaned_url:
            try:
                yt = YouTube(cleaned_url)
                title = yt.title
                duration = yt.length
                thumbnail = yt.thumbnail_url
                channel = yt.author

                response = (
                    f"🎬 عنوان: {title}\n"
                    f"📺 کانال: {channel}\n"
                    f"⏱ مدت زمان: {duration} ثانیه\n"
                    f"🖼 تصویر بندانگشتی:\n{thumbnail}"
                )
            except Exception as e:
                response = f"❌ خطا در دریافت اطلاعات ویدیو:\n{str(e)}"
        else:
            response = "❌ لینک یوتیوب معتبر نیست."

        await bot.send_message(chat_id=message.author.user_id, text=response)

# سرور پورت جعلی با aiohttp
async def fake_port_handler(request):
    return web.Response(text="✅ ربات Bale روی پورت جعلی 8080 فعال است.")

async def start_fake_port():
    app = web.Application()
    app.router.add_get('/', fake_port_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    print("🌀 پورت جعلی فعال شد: http://localhost:8080")

# اجرای همزمان ربات و پورت
async def main():
    await asyncio.gather(
        start_fake_port(),
        bot.run_async()
    )

if __name__ == '__main__':
    asyncio.run(main())
