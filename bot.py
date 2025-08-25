import asyncio
import os
import tempfile
from bale import Bot, Message
from yt_dlp import YoutubeDL
import aiohttp
import uuid

bot = Bot(token="210722128:ZVA73ro5RguzGOUUKstc1cDChCnSLfKExxmKTpvB")

# تنظیمات yt-dlp برای بهترین کیفیت و سازگاری با ایران
YDL_OPTIONS = {
    'format': 'best[height<=720]',  # حداکثر کیفیت 720p برای حجم کمتر
    'quiet': True,
    'no_warnings': True,
    'socket_timeout': 30,
    'http_chunk_size': 1048576,  # کاهش اندازه chunk برای اینترنت کند
}


@bot.event
async def on_ready():
    print("✅ ربات آماده است و می‌تواند ویدیوهای یوتیوب را دانلود کند.")


@bot.event
async def on_message(message: Message):
    if getattr(message.chat, "type", None) != "private":
        return

    text = message.content.strip()

    if text.lower() in ["/start", "سلام", "hello"]:
        await message.reply("سلام! 👋\nلینک یوتیوب را برای من بفرستید تا آن را دانلود کنم.")
        return

    # بررسی آیا متن یک لینک یوتیوب است
    if "youtube.com" in text or "youtu.be" in text:
        try:
            # ارسال پیام "در حال پردازش"
            processing_msg = await message.reply("⏳ در حال دانلود ویدیو... لطفاً منتظر بمانید.")

            # ایجاد فایل موقت برای ذخیره ویدیو
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                temp_path = tmp_file.name

            # تنظیمات yt-dlp با مسیر فایل خروجی
            ydl_opts = YDL_OPTIONS.copy()
            ydl_opts['outtmpl'] = temp_path

            # دانلود ویدیو
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(text, download=True)

                    # بررسی اندازه فایل (حداکثر 50MB برای تلگرام)
                    file_size = os.path.getsize(temp_path)
                    if file_size > 50 * 1024 * 1024:
                        await processing_msg.edit_text("❌ حجم ویدیو بیش از حد مجاز (50MB) است.")
                        os.unlink(temp_path)
                        return

                    # ارسال ویدیو
                    with open(temp_path, 'rb') as video_file:
                        await bot.send_video(
                            chat_id=message.chat.chat_id,
                            video=video_file,
                            caption=f"🎥 {info.get('title', 'ویدیو یوتیوب')}",
                            supports_streaming=True
                        )

                    await processing_msg.delete()

            except Exception as e:
                await processing_msg.edit_text(f"❌ خطا در دانلود: {str(e)}")

            finally:
                # حذف فایل موقت
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            await message.reply(f"❌ خطای سیستمی: {str(e)}")

    else:
        await message.reply("لطفاً یک لینک معتبر یوتیوب ارسال کنید.")


# اجرای ربات
if __name__ == "__main__":
    try:
        print("🚀 در حال راه اندازی ربات...")
        bot.run()
    except Exception as e:
        print(f"❌ خطا در اجرای ربات: {e}")
