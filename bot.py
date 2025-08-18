import os
import re
import asyncio
from bale import Bot, Message
from yt_dlp import YoutubeDL

# توکن ربات Bale
bot = Bot(token="210722128:ZVA73ro5RguzGOUUKstc1cDChCnSLfKExxmKTpvB")

# الگوی تشخیص لینک یوتیوب
YOUTUBE_REGEX = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/[^\s]+"

# 📡 سرور جعلی روی پورت 10000
async def fake_server(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"📡 اتصال جعلی از {addr}")
    writer.write(b"✅ این یه پورت تستیه روی 10000!\n")
    await writer.drain()
    writer.close()

async def start_fake_port():
    server = await asyncio.start_server(fake_server, '0.0.0.0', 10000)
    addr = server.sockets[0].getsockname()
    print(f"✅ پورت جعلی روی {addr} باز شد.")
    async with server:
        await server.serve_forever()

# 📩 رویداد آماده بودن ربات
@bot.event
async def on_ready():
    print("🤖 ربات Bale آماده است.")
    # اجرای سرور جعلی در پس‌زمینه
    asyncio.create_task(start_fake_port())

# 📥 رویداد دریافت پیام
@bot.event
async def on_message(message: Message):
    if getattr(message.chat, "type", None) != "private":
        return

    text = message.content.strip()

    # پاسخ به سلام
    if text.lower() == "سلام":
        await bot.send_message(chat_id=message.chat.chat_id, text="سلام! لینک یوتیوب بفرست تا برات دانلود کنم.")
        return

    # بررسی لینک یوتیوب
    match = re.search(YOUTUBE_REGEX, text)
    if match:
        url = match.group(0)
        await bot.send_message(chat_id=message.chat.chat_id, text="⏳ در حال دانلود ویدیو...")

        # تنظیمات yt-dlp
        ydl_opts = {
            'outtmpl': 'video.%(ext)s',
            'format': 'mp4',
            'quiet': True
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # ارسال فایل
            if os.path.exists("video.mp4"):
                await bot.send_document(chat_id=message.chat.chat_id, document="video.mp4")
                os.remove("video.mp4")
            else:
                await bot.send_message(chat_id=message.chat.chat_id, text="❌ مشکلی در دانلود فایل پیش آمد.")
        except Exception as e:
            await bot.send_message(chat_id=message.chat.chat_id, text=f"❌ خطا: {str(e)}")
    else:
        await bot.send_message(chat_id=message.chat.chat_id, text="لطفاً لینک معتبر یوتیوب بفرست.")

# 🚀 اجرای ربات
bot.run()
