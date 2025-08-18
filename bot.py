from bale import Bot, Message
from pytube import YouTube
import re

bot = Bot(token="210722128:ZVA73ro5RguzGOUUKstc1cDChCnSLfKExxmKTpvB")

# تابع تشخیص لینک یوتیوب
def extract_youtube_url(text):
    pattern = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/[^\s]+"
    match = re.search(pattern, text)
    return match.group(0) if match else None

@bot.event
async def on_ready():
    print("✅ ربات آماده است.")

@bot.event
async def on_message(message: Message):
    if getattr(message.chat, "type", None) != "private":
        return

    text = message.content.strip().lower()

    # اگر فقط "سلام" بود
    if text == "سلام":
        await bot.send_message(chat_id=message.author.user_id, text="سلام 👋")

    # بررسی لینک یوتیوب
    youtube_url = extract_youtube_url(text)
    if youtube_url:
        try:
            yt = YouTube(youtube_url)
            title = yt.title
            duration = yt.length  # به ثانیه
            thumbnail = yt.thumbnail_url

            response = f"🎬 عنوان: {title}\n⏱ مدت زمان: {duration} ثانیه\n🖼 تصویر بندانگشتی:\n{thumbnail}"
        except Exception as e:
            response = f"❌ خطا در دریافت اطلاعات ویدیو: {str(e)}"

        await bot.send_message(chat_id=message.author.user_id, text=response)

bot.run()
