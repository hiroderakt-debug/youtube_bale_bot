import os
import re
import asyncio
import requests
from bale import Bot, Message
from yt_dlp import YoutubeDL

# 🎯 توکن ربات Bale
bot = Bot(token="210722128:ZVA73ro5RguzGOUUKstc1cDChCnSLfKExxmKTpvB")

# 🔑 کلید API از Upload.io
UPLOADIO_API_KEY = "your-uploadio-api-key"  # 🔁 جایگزین کن با کلید واقعی

# 📁 مسیر امن کوکی‌ها در Render
COOKIES_PATH = "/etc/secrets/cookies.txt"

# 🔍 الگوی تشخیص لینک یوتیوب
YOUTUBE_REGEX = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/[^\s]+"

# 📡 سرور جعلی روی پورت 10000
async def fake_server(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"📡 اتصال جعلی از {addr}")
    writer.write("✅ این یه پورت تستیه روی 10000!\n".encode("utf-8"))
    await writer.drain()
    writer.close()

async def start_fake_port():
    server = await asyncio.start_server(fake_server, '0.0.0.0', 10000)
    addr = server.sockets[0].getsockname()
    print(f"✅ پورت جعلی روی {addr} باز شد.")
    async with server:
        await server.serve_forever()

# 📤 آپلود فایل روی Upload.io
def upload_to_uploadio(filepath):
    try:
        headers = {
            "Authorization": f"Bearer {UPLOADIO_API_KEY}"
        }
        with open(filepath, 'rb') as f:
            files = {
                "file": (os.path.basename(filepath), f)
            }
            response = requests.post("https://api.upload.io/v2/files", headers=headers, files=files)
            print("📤 پاسخ Upload.io:", response.status_code, response.text)
            if response.ok:
                return response.json().get("fileUrl")
    except Exception as e:
        print(f"❌ خطا در آپلود: {e}")
    return None

# 🎬 دانلود ویدیو با yt_dlp
def download_youtube_video(url, output_file="video.mp4"):
    if not os.path.exists(COOKIES_PATH):
        raise FileNotFoundError("فایل کوکی پیدا نشد!")

    ydl_opts = {
        'outtmpl': output_file,
        'format': 'mp4',
        'quiet': True,
        'cookies': COOKIES_PATH,
        'noplaylist': True,
        'retries': 3,
        'no_warnings': True,
        'ignoreerrors': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# 📩 رویداد آماده بودن ربات
@bot.event
async def on_ready():
    print("🤖 ربات Bale آماده است.")
    asyncio.create_task(start_fake_port())

# 📥 رویداد دریافت پیام
@bot.event
async def on_message(message: Message):
    if getattr(message.chat, "type", None) != "private":
        return

    text = message.content.strip()

    if text.lower() == "سلام":
        await bot.send_message(chat_id=message.chat.id, text="سلام! لینک یوتیوب بفرست تا برات دانلود کنم.")
        return

    match = re.search(YOUTUBE_REGEX, text)
    if not match:
        await bot.send_message(chat_id=message.chat.id, text="لطفاً لینک معتبر یوتیوب بفرست.")
        return

    url = match.group(0)
    await bot.send_message(chat_id=message.chat.id, text="⏳ در حال دانلود ویدیو...")

    try:
        download_youtube_video(url)

        if os.path.exists("video.mp4"):
            link = upload_to_uploadio("video.mp4")
            os.remove("video.mp4")

            if link:
                await bot.send_message(chat_id=message.chat.id, text=f"✅ ویدیو آماده‌ست:\n{link}")
            else:
                await bot.send_message(chat_id=message.chat.id, text="❌ خطا در آپلود فایل.")
        else:
            await bot.send_message(chat_id=message.chat.id, text="❌ مشکلی در دانلود فایل پیش آمد.")
    except Exception as e:
        await bot.send_message(chat_id=message.chat.id, text=f"❌ خطا در پردازش: {str(e)}")

# 🚀 اجرای ربات
bot.run()
