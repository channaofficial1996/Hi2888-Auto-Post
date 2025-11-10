import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, MessageHandler, CommandHandler,
    ContextTypes, filters
)

# ===== CONFIG =====
BOT_TOKEN = os.getenv("8221221491:AAHEVZELAwPqRrazGpa3JW5jH-_YN6eXzbM")
TARGET_GROUP_ID = os.getenv("-1003479799816")
ADMIN_IDS_ENV = os.getenv("5529358783", "")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not TARGET_GROUP_ID:
    raise RuntimeError("TARGET_GROUP_ID not set")

TARGET_GROUP_ID = int(TARGET_GROUP_ID)

# parse admin ids from comma separated string
ADMIN_IDS = []
for part in ADMIN_IDS_ENV.split(","):
    part = part.strip()
    if part:
        try:
            ADMIN_IDS.append(int(part))
        except ValueError:
            pass  # ignore bad ones


def build_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("💬 ក្រុមចាត់", url="https://t.me/yourgroup"),
            InlineKeyboardButton("🎬 រូបភាព និងវីដេអូ", url="https://t.me/Hi2888CS1"),
        ],
        [
            InlineKeyboardButton("បើកអាខោន", url="https://t.me/Hi2888CS1"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot ready!
"
        "• Send me a video here (if you're admin) → I will post to group
"
        "• Or post video in channel where I'm admin → I will repost to group
"
        "✅ Buttons will be attached automatically."
    )


async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    if not post:
        return

    is_video = False
    video_file_id = None

    if post.video:
        is_video = True
        video_file_id = post.video.file_id
    elif post.document and post.document.mime_type and post.document.mime_type.startswith("video/"):
        is_video = True
        video_file_id = post.document.file_id

    if not is_video:
        return

    caption = post.caption or ""

    await context.bot.send_video(
        chat_id=TARGET_GROUP_ID,
        video=video_file_id,
        caption=caption,
        reply_markup=build_keyboard()
    )


async def video_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    user_id = msg.from_user.id
    if user_id not in ADMIN_IDS:
        await msg.reply_text("🚫 You are not allowed to post to group.")
        return

    video_file_id = None

    if msg.video:
        video_file_id = msg.video.file_id
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video/"):
        video_file_id = msg.document.file_id

    if not video_file_id:
        return

    caption = msg.caption or ""

    await context.bot.send_video(
        chat_id=TARGET_GROUP_ID,
        video=video_file_id,
        caption=caption,
        reply_markup=build_keyboard()
    )

    await msg.reply_text("✅ Posted to group!")


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post))
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (filters.VIDEO | filters.Document.VIDEO),
        video_from_admin
    ))

    print("Bot is running ...")
    application.run_polling()


if __name__ == "__main__":
    main()
