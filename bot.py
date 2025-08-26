import asyncio
import os
import tempfile
from bale import Bot, Message
import aiohttp
import re
import json
from urllib.parse import quote

bot = Bot(token="210722128:ZVA73ro5RguzGOUUKstc1cDChCnSLfKExxmKTpvB")

# چندین API عمومی برای fallback خودکار
PUBLIC_APIS = [
    {
        'name': 'yt5s',
        'url': 'https://yt5s.io/api/ajaxSearch',
        'method': 'POST',
        'data': lambda url: {'q': url, 'vt': 'home'}
    },
    {
        'name': 'dlyoutube',
        'url': 'https://api.dlyoutube.com/api/converter',
        'method': 'POST', 
        'data': lambda url: {'url': url, 'format': 'mp4', 'quality': '360p'}
    },
    {
        'name': 'loader',
        'url': 'https://loader.to/api/extract',
        'method': 'GET',
        'params': lambda url: {'url': url, 'format': 'mp4'}
    }
]

processing_users = {}

@bot.event
async def on_ready():
    print("✅ ربات آماده است! (بدون نیاز به کوکی)")

def is_youtube_url(text):
    """بررسی لینک یوتیوب با regex دقیق تر"""
    patterns = [
        r'(https?://)?(www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(https?://)?(www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(https?://)?(www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})'
    ]
    return any(re.search(pattern, text) for pattern in patterns)

async def get_download_link(youtube_url):
    """دریافت لینک دانلود از بهترین API در دسترس"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    for api in PUBLIC_APIS:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as session:
                
                if api['method'] == 'POST':
                    data = api['data'](youtube_url)
                    async with session.post(api['url'], json=data, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            download_url = extract_download_url(result, api['name'])
                            if download_url:
                                title = extract_title(result, api['name'])
                                return download_url, title
                
                else:  # GET method
                    params = api['params'](youtube_url)
                    async with session.get(api['url'], params=params, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            download_url = extract_download_url(result, api['name'])
                            if download_url:
                                title = extract_title(result, api['name'])
                                return download_url, title
                                
        except Exception as e:
            print(f"خطا در API {api['name']}: {e}")
            continue
    
    return None, "❌ سرویس‌های دانلود موقتاً در دسترس نیستند. لطفاً بعداً تلاش کنید."

def extract_download_url(data, api_name):
    """استخراج لینک دانلود از پاسخ API"""
    if api_name == 'yt5s':
        return data.get('mp4', {}).get('links', {}).get('360p')
    elif api_name == 'dlyoutube':
        return data.get('url') or data.get('downloadUrl')
    elif api_name == 'loader':
        return data.get('url') or data.get('download_url')
    return None

def extract_title(data, api_name):
    """استخراج عنوان ویدیو"""
    if api_name == 'yt5s':
        return data.get('title', 'ویدیو یوتیوب')
    elif api_name in ['dlyoutube', 'loader']:
        return data.get('title') or data.get('meta', {}).get('title', 'ویدیو یوتیوب')
    return 'ویدیو یوتیوب'

async def download_video(download_url, file_path):
    """دانلود ویدیو با مدیریت خطا و timeout"""
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=90),
            connector=aiohttp.TCPConnector(limit=5)
        ) as session:
            async with session.get(download_url) as response:
                if response.status == 200:
                    total_size = 0
                    with open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            total_size += len(chunk)
                            if total_size > 50 * 1024 * 1024:  # 50MB limit
                                raise Exception("حجم فایل بیش از حد مجاز")
                    return True
        return False
    except Exception as e:
        print(f"خطا در دانلود: {e}")
        return False

@bot.event
async def on_message(message: Message):
    if getattr(message.chat, "type", None) != "private":
        return
    
    # تصحیح: استفاده از message.chat.id به جای message.chat.chat_id
    user_id = message.chat.id
    text = message.content.strip()
    
    if user_id in processing_users:
        await message.reply("⏳ درخواست قبلی شما در حال پردازش است...")
        return
    
    if text.lower() in ["/start", "سلام", "hello", "/help"]:
        help_text = (
            "🎥 **ربات دانلود یوتیوب**\n\n"
            "لینک یوتیوب را ارسال کنید تا آن را دانلود کنم.\n\n"
            "📋 **مثال‌ها:**\n"
            "• `https://www.youtube.com/watch?v=...`\n"
            "• `https://youtu.be/...`\n\n"
            "⚡ **ویژگی‌ها:**\n"
            "• دانلود بدون نیاز به کوکی\n"
            "• کیفیت مناسب (360p)\n"
            "• حداکثر حجم: 45MB\n\n"
            "🔄 در صورت خطا، چند دقیقه بعد تلاش کنید."
        )
        await message.reply(help_text)
        return
    
    if is_youtube_url(text):
        try:
            processing_users[user_id] = True
            processing_msg = await message.reply("⏳ در حال پردازش لینک...")
            
            # دریافت لینک دانلود
            await processing_msg.edit_text("🔍 در حال پیدا کردن بهترین سرویس...")
            download_url, video_title = await get_download_link(text)
            
            if not download_url:
                await processing_msg.edit_text(video_title)
                return
            
            # ایجاد فایل موقت
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                temp_path = tmp_file.name
            
            # دانلود ویدیو
            await processing_msg.edit_text("⬇️ در حال دانلود ویدیو...")
            success = await download_video(download_url, temp_path)
            
            if not success:
                await processing_msg.edit_text("❌ خطا در دانلود ویدیو")
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return
            
            # بررسی حجم
            file_size = os.path.getsize(temp_path)
            if file_size > 45 * 1024 * 1024:
                await processing_msg.edit_text("❌ حجم ویدیو بیش از حد مجاز است (45MB)")
                os.unlink(temp_path)
                return
            
            # ارسال ویدیو
            await processing_msg.edit_text("📤 در حال آپلود...")
            
            try:
                with open(temp_path, 'rb') as video_file:
                    # تصحیح: استفاده از chat_id=user_id به جای chat_id=message.chat.chat_id
                    await bot.send_video(
                        chat_id=user_id,
                        video=video_file,
                        caption=f"🎥 {video_title}",
                        supports_streaming=True
                    )
                
                await processing_msg.delete()
                
            except Exception as upload_error:
                await processing_msg.edit_text(f"❌ خطا در آپلود: {upload_error}")
            
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
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
            "• https://youtube.com/shorts/..."
        )

if __name__ == "__main__":
    print("🚀 در حال راه اندازی ربات روی Render...")
    try:
        bot.run()
    except KeyboardInterrupt:
        print("❌ ربات متوقف شد")
    except Exception as e:
        print(f"❌ خطا در اجرای ربات: {e}")
