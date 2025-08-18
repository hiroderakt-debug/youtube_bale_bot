import asyncio
import os
from datetime import datetime, timedelta
from collections import deque
from bale import Bot, Message, InputFile
import bale.error
import aiohttp
from fastapi import FastAPI
import uvicorn
import threading

# تنظیمات اولیه
delay_minutes = 20
paused = False
edit_mode = {}  # user_id -> message_id در حال ویرایش

bot = Bot(token="347447058:s19i9J3UPZLUrprUqrH12UYD1lDGcPPi1ulV9iFL")
send_queue = asyncio.Queue()
scheduled_queue = deque()  # هر آیتم: (message, scheduled_time, caption)

# وب‌سرور FastAPI
app = FastAPI()

@app.get("/")
def ping():
    return {"status": "ok"}

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

async def safe_send(chat_id: int, text: str):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except bale.error.Forbidden:
        print(f"❌ ارسال پیام به کاربر {chat_id} ممکن نیست.")

@bot.event
async def on_ready():
    print("✅ ربات آماده است.")
    asyncio.create_task(process_queue())
    asyncio.create_task(log_remaining_times())
    asyncio.create_task(keep_alive())

@bot.event
async def on_message(message: Message):
    global scheduled_queue, delay_minutes, paused, edit_mode

    if getattr(message.chat, "type", None) != "private":
        return
    if message.author.username != "heroderact":
        return

    user_id = message.author.user_id
    content = message.content.strip()

    # حالت ویرایش متن
    if user_id in edit_mode:
        target_id = edit_mode[user_id]
        for i, (msg, time, caption) in enumerate(scheduled_queue):
            if msg.message_id == target_id:
                scheduled_queue[i] = (msg, time, content)
                await safe_send(user_id, "✏️ متن پیام با موفقیت ویرایش شد.")
                del edit_mode[user_id]
                return
        await safe_send(user_id, "⚠️ پیام موردنظر برای ویرایش پیدا نشد.")
        del edit_mode[user_id]
        return

    # توقف ارسال‌ها
    if content.lower() == "توقف":
        paused = True
        await safe_send(user_id, "⛔ ارسال پیام‌ها متوقف شد.")
        return

    # ادامه ارسال‌ها
    if content.lower() == "ادامه":
        paused = False
        await safe_send(user_id, "▶️ ارسال پیام‌ها ادامه پیدا می‌کند.")
        return

    # لغو پیام
    if message.reply_to_message and content.lower() == "لغو":
        reply_id = message.reply_to_message.message_id
        scheduled_queue = deque([
            (msg, time, caption) for msg, time, caption in scheduled_queue if msg.message_id != reply_id
        ])
        await safe_send(user_id, "❌ پیام با موفقیت لغو شد.")
        return

    # نمایش زمان باقی‌مانده
    if message.reply_to_message and content.lower() == "زمان":
        reply_id = message.reply_to_message.message_id
        for msg, scheduled_time, _ in scheduled_queue:
            if msg.message_id == reply_id:
                remaining = scheduled_time - datetime.now()
                if remaining.total_seconds() > 0:
                    await safe_send(user_id, format_remaining_time(remaining))
                else:
                    await safe_send(user_id, "✅ این رسانه در حال ارسال یا ارسال شده است.")
                return
        await safe_send(user_id, "❌ این پیام در صف ارسال نیست یا قبلاً ارسال شده.")
        return

    # حذف کل صف
    if content.lower() == "حذف":
        scheduled_queue.clear()
        await safe_send(user_id, "🗑️ کل صف حذف شد.")
        return

    # تغییر زمان تأخیر
    if content.lower().startswith("تغییر زمان"):
        try:
            parts = content.split()
            if len(parts) == 3:
                delay_minutes = int(parts[2])
                await safe_send(user_id, f"⏱️ زمان تأخیر به {delay_minutes} دقیقه تغییر یافت.")
            else:
                await safe_send(user_id, "⚠️ فرمت صحیح: تغییر زمان [عدد]")
        except ValueError:
            await safe_send(user_id, "⚠️ لطفاً عدد معتبر وارد کنید.")
        return

    # ویرایش متن پیام
    if message.reply_to_message and content.lower() == "ویرایش":
        reply_id = message.reply_to_message.message_id
        for msg, _, _ in scheduled_queue:
            if msg.message_id == reply_id:
                edit_mode[user_id] = reply_id
                await safe_send(user_id, "📝 لطفاً متن جدید را ارسال کنید.")
                return
        await safe_send(user_id, "⚠️ این پیام در صف نیست یا قبلاً ارسال شده.")
        return

    # زمان‌بندی پیام جدید
    if scheduled_queue:
        last_scheduled_time = scheduled_queue[-1][1]
        scheduled_time = last_scheduled_time + timedelta(minutes=delay_minutes)
    else:
        scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)

    scheduled_queue.append((message, scheduled_time, content))
    await send_queue.put(message)

async def process_queue():
    global scheduled_queue, paused

    while True:
        message = await send_queue.get()

        while paused:
            await asyncio.sleep(5)

        user_id = message.author.user_id

        # پیدا کردن caption مربوط به پیام
        caption = ""
        scheduled_time = None
        for msg, time, cap in scheduled_queue:
            if msg.message_id == message.message_id:
                scheduled_time = time
                caption = cap
                break

        if scheduled_time:
            now = datetime.now()
            wait_seconds = (scheduled_time - now).total_seconds()
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

        try:
            if isinstance(message.video, dict) and "file_id" in message.video:
                await bot.send_video(
                    chat_id="@hiromce",
                    video=InputFile(message.video["file_id"]),
                    caption=caption
                )
                print(f"✅ ویدیو از کاربر {user_id} ارسال شد: {datetime.now()}")
                await safe_send(user_id, "🎥 ویدیو با موفقیت ارسال شد.")

            elif isinstance(message.photos, list) and len(message.photos) > 0:
                for photo in message.photos:
                    await bot.send_photo(
                        chat_id="@hiromce",
                        photo=InputFile(photo.file_id),
                        caption=caption
                    )
                    print(f"✅ عکس از کاربر {user_id} ارسال شد: {datetime.now()}")
                    await safe_send(user_id, "🖼️ عکس با موفقیت ارسال شد.")

            else:
                await safe_send(user_id, "⚠️ لطفاً فقط عکس یا ویدیو همراه با متن ارسال کنید.")

        except Exception as e:
            print(f"❌ خطا در ارسال رسانه: {e}")
            await safe_send(user_id, "⚠️ خطا در ارسال رسانه.")

        scheduled_queue = deque([
            (msg, time, cap) for msg, time, cap in scheduled_queue if msg.message_id != message.message_id
        ])

def format_remaining_time(remaining: timedelta) -> str:
    total_seconds = int(remaining.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days} روز")
    if hours > 0:
        parts.append(f"{hours} ساعت")
    if minutes > 0:
        parts.append(f"{minutes} دقیقه")
    if seconds > 0 and days == 0:
        parts.append(f"{seconds} ثانیه")

    return "⏳ حدود " + " و ".join(parts) + " تا ارسال باقی مانده."

async def log_remaining_times():
    while True:
        print("📋 وضعیت صف ارسال:")
        now = datetime.now()
        for msg, scheduled_time, _ in scheduled_queue:
            remaining = scheduled_time - now
            if remaining.total_seconds() <= 0:
                print(f"✅ پیام {msg.message_id} آماده ارسال است.")
            else:
                print(f"🕒 پیام {msg.message_id} از کاربر {msg.author.user_id} در {format_remaining_time(remaining)} دیگر ارسال می‌شود.")
        await asyncio.sleep(180)

async def keep_alive():
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:" + os.environ.get("PORT", "10000")) as resp:
                    print(f"🔄 پینگ داخلی: {resp.status}")
        except Exception as e:
            print(f"⚠️ خطا در پینگ داخلی: {e}")
        
        await asyncio.sleep(20*60)  # ← این خط باید دقیقاً در این سطح باشد

if __name__ == "__main__":
    print("🤖 ربات در حال اجرا...")
    threading.Thread(target=run_web_server).start()
    bot.run()
