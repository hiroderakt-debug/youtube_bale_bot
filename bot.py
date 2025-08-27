import asyncio
import os
import tempfile
import re
import json
from bale import Bot, Message
from yt_dlp import YoutubeDL
import aiohttp
from urllib.parse import quote

bot = Bot(token="210722128:ZVA73ro5RguzGOUUKstc1cDChCnSLfKExxmKTpvB")

# تنظیمات پایه
DOWNLOAD_FOLDER = "Downloads"
processing_users = {}

def ensure_dirs():
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

def is_youtube_url(text):
    """بررسی لینک یوتیوب"""
    patterns = [
        r'(https?://)?(www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(https?://)?(www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(https?://)?(www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})'
    ]
    return any(re.search(pattern, text) for pattern in patterns)

def sanitize(s):
    """پاکسازی نام فایل"""
    return re.sub(r'[\/\\\:\*\?"<>\|]', '_', s)

def natural_size(num):
    """تبدیل حجم به فرمت خوانا"""
    for unit in ['B','KB','MB','GB','TB']:
        if abs(num) < 1024.0:
            return "%3.1f %s" % (num, unit)
        num /= 1024.0
    return "%.1f PB" % num

async def download_media(url, format_type="video", user_id=None):
    """دانلود رسانه از یوتیوب"""
    try:
        ensure_dirs()
        
        # تنظیمات yt-dlp
        opts = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'http_chunk_size': 524288,
        }
        
        if format_type == "audio":
            opts.update({
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioformat': 'mp3',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3'
                }],
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s')
            })
        else:
            opts.update({
                'format': 'best[height<=720][filesize<45M]',
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s')
            })
        
        # دانلود
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # پیدا کردن مسیر فایل دانلود شده
            if 'requested_downloads' in info:
                file_path = info['requested_downloads'][0]['filepath']
            else:
                filename = sanitize(info.get('title', 'video')) + ('.mp3' if format_type == "audio" else '.mp4')
                file_path = os.path.join(DOWNLOAD_FOLDER, filename)
            
            return file_path, info.get('title', 'YouTube Media')
            
    except Exception as e:
        return None, f"❌ خطا در دانلود: {str(e)}"

@bot.event
async def on_ready():
    print("✅ ربات دانلود یوتیوب آماده است!")

@bot.event
async def on_message(message: Message):
    if getattr(message.chat, "type", None) != "private":
        return
    
    user_id = message.chat.id
    text = message.content.strip()
    
    # مدیریت کاربران در حال پردازش
    if user_id in processing_users:
        await message.reply("⏳ درخواست قبلی شما در حال پردازش است...")
        return
    
    if text.lower() in ["/start", "سلام", "hello", "/help"]:
        help_text = (
            "🎥 **ربات دانلود یوتیوب**\n\n"
            "لینک یوتیوب را ارسال کنید تا آن را دانلود کنم.\n\n"
            "🎵 **برای دانلود صدا:**\n"
            "ارسال لینک + کلمه 'صدا' یا 'audio'\n\n"
            "🎬 **برای دانلود ویدیو:**\n"
            "فقط لینک را ارسال کنید\n\n"
            "📋 **مثال‌ها:**\n"
            "• https://youtu.be/... (برای ویدیو)\n"
            "• https://youtu.be/... صدا (برای صوت)\n\n"
            "⚡ **ویژگی‌ها:**\n"
            "• کیفیت مناسب\n"
            "• حداکثر حجم: 45MB\n"
            "• دانلود سریع"
        )
        await message.reply(help_text)
        return
    
    # بررسی لینک یوتیوب
    if is_youtube_url(text):
        try:
            processing_users[user_id] = True
            
            # تشخیص نوع درخواست (صدا یا ویدیو)
            format_type = "audio" if any(word in text.lower() for word in ['صدا', 'audio', 'mp3']) else "video"
            
            # استخراج لینک خالص
            url = text
            for word in ['صدا', 'audio', 'mp3']:
                url = url.replace(word, '').strip()
            
            processing_msg = await message.reply(
                f"⏳ در حال دانلود {'صدا' if format_type == 'audio' else 'ویدیو'}..."
            )
            
            # دانلود رسانه
            file_path, title = await asyncio.to_thread(
                download_media, url, format_type, user_id
            )
            
            if not file_path:
                await processing_msg.edit(f"❌ {title}")
                return
            
            # بررسی وجود فایل و حجم آن
            if not os.path.exists(file_path):
                await processing_msg.edit("❌ فایل دانلود شده یافت نشد")
                return
            
            file_size = os.path.getsize(file_path)
            if file_size > 50 * 1024 * 1024:
                await processing_msg.edit("❌ حجم فایل بیش از حد مجاز است (50MB)")
                os.remove(file_path)
                return
            
            # ارسال فایل
            await processing_msg.edit("📤 در حال آپلود...")
            
            try:
                if format_type == "audio":
                    with open(file_path, 'rb') as audio_file:
                        await bot.send_audio(
                            chat_id=user_id,
                            audio=audio_file,
                            caption=f"🎵 {title}",
                            title=title[:64]  # محدودیت طول عنوان
                        )
                else:
                    with open(file_path, 'rb') as video_file:
                        await bot.send_video(
                            chat_id=user_id,
                            video=video_file,
                            caption=f"🎥 {title}",
                            supports_streaming=True
                        )
                
                await processing_msg.delete()
                
            except Exception as upload_error:
                await processing_msg.edit(f"❌ خطا در آپلود: {upload_error}")
            
            finally:
                # حذف فایل موقت
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
        except Exception as e:
            await message.reply(f"❌ خطای سیستمی: {str(e)}")
        
        finally:
            if user_id in processing_users:
                del processing_users[user_id]
    
    else:
        await message.reply(
            "❌ لینک معتبر یوتیوب نیست\n\n"
            "📋 فرمت‌های قابل قبول:\n"
            "• https://www.youtube.com/watch?v=...\n"
            "• https://youtu.be/...\n"
            "• https://youtube.com/shorts/...\n\n"
            "برای راهنمایی /help را ارسال کنید"
        )

if __name__ == "__main__":
    print("🚀 در حال راه اندازی ربات دانلود یوتیوب...")
    try:
        bot.run()
    except KeyboardInterrupt:
        print("❌ ربات متوقف شد")
    except Exception as e:
        print(f"❌ خطا در اجرای ربات: {e}")
