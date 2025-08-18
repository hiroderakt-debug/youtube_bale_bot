import os
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from aiogram.filters import CommandStart
from yt_dlp import YoutubeDL

BALE_TOKEN = "210722128:ZVA73ro5RguzGOUUKstc1cDChCnSLfKExxmKTpvB"
ONE_API_TOKEN = "295736:68a316750afc5"

bot = Bot(token=BALE_TOKEN)
dp = Dispatcher()

os.makedirs("assets", exist_ok=True)
os.makedirs("merge", exist_ok=True)

async def get_video_info(url):
    video_id = url.split("/")[-1].split("?")[0]
    api_url = f"https://youtube.one-api.ir/?token={ONE_API_TOKEN}&action=info&id={video_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            return await resp.json()

def download_stream(url, filename):
    ydl_opts = {
        "outtmpl": filename,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def merge_audio_video(video_path, audio_path, output_path):
    os.system(f'ffmpeg -y -i "{video_path}" -i "{audio_path}" -c:v copy -c:a aac "{output_path}"')

async def upload_to_transfer(file_path):
    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            async with session.post("https://transfer.sh/", data={"file": f}) as resp:
                return await resp.text()

@dp.message(CommandStart())
async def start(msg: types.Message):
    await msg.answer("سلام! لینک یوتیوب رو بفرست تا دانلود کنم 🎬")

@dp.message()
async def handle_url(msg: types.Message):
    url = msg.text.strip()
    await msg.answer("⏳ در حال دریافت اطلاعات ویدیو...")

    info = await get_video_info(url)
    if "streams" not in info:
        await msg.answer("❌ خطا در دریافت اطلاعات. لطفاً لینک معتبر بفرست.")
        return

    video_url = info["streams"]["video"][0]["url"]
    audio_url = info["streams"]["audio"][0]["url"]

    video_path = f"assets/video.mp4"
    audio_path = f"assets/audio.mp4"
    output_path = f"merge/final.mp4"

    await msg.answer("📥 در حال دانلود ویدیو و صدا...")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, download_stream, video_url, video_path)
    await loop.run_in_executor(None, download_stream, audio_url, audio_path)

    await msg.answer("🔀 در حال ادغام صدا و تصویر...")
    merge_audio_video(video_path, audio_path, output_path)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    if size_mb < 50:
        await msg.answer("📤 ارسال فایل نهایی...")
        await msg.answer_document(FSInputFile(output_path))
    else:
        await msg.answer("📤 حجم زیاد است، در حال آپلود روی transfer.sh...")
        link = await upload_to_transfer(output_path)
        await msg.answer(f"✅ فایل آماده است:\n{link}")

if __name__ == "__main__":
    dp.run_polling(bot)
