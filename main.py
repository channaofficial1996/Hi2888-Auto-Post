from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, MessageHandler, CommandHandler,
    ContextTypes, filters
)

# ===== CONFIG =====
BOT_TOKEN = "8221221491:AAHEVZELAwPqRrazGpa3JW5jH-_YN6eXzbM"
TARGET_GROUP_ID = -1003479799816
ADMIN_IDS = [5529358783, 5658686099, 111111111, 222222222]
# ==================


def build_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("💬 ក្រុមចាត់", url="https://t.me/yourgroup"),
            InlineKeyboardButton("🎬 វីដេអូថ្មីៗ", url="https://t.me/yourchannel"),
        ],
        [
            InlineKeyboardButton("📱 បែបបទរាយការណ៍", url="https://yourwebsite.com/form"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 Bot ready!\n\n"
        "• ផ្ញើវីដេអូមក bot (admin only) → បោះទៅ group\n"
        "• បើ bot ជា admin នៅក្នុង channel → វានឹង auto repost វីដេអូទៅ group\n\n"
        "✅ Buttons 3 គ្រាប់នឹងភ្ជាប់ដោយស្វ័យប្រវត្តិ!"
    )
    await update.message.reply_text(text)


# auto-post from channel
async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    if not post:
        return

    file_id = None
    if post.video:
        file_id = post.video.file_id
    elif post.document and post.document.mime_type and post.document.mime_type.startswith("video/"):
        file_id = post.document.file_id
    if not file_id:
        return

    caption = post.caption or ""
    await context.bot.send_video(
        chat_id=TARGET_GROUP_ID,
        video=file_id,
        caption=caption,
        reply_markup=build_keyboard()
    )


# manual from admin
async def video_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    user_id = msg.from_user.id
    if user_id not in ADMIN_IDS:
        await msg.reply_text("🚫 អ្នកមិនមានសិទ្ធិបោះវីដេអូទៅ group ទេ!")
        return

    file_id = None
    if msg.video:
        file_id = msg.video.file_id
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video/"):
        file_id = msg.document.file_id
    if not file_id:
        return

    caption = msg.caption or ""
    await context.bot.send_video(
        chat_id=TARGET_GROUP_ID,
        video=file_id,
        caption=caption,
        reply_markup=build_keyboard()
    )
    await msg.reply_text("✅ បោះវីដេអូទៅ group រួចរាល់!")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & (filters.VIDEO | filters.Document.VIDEO), video_from_admin))
    print("🤖 Bot running 24h ...")
    app.run_polling()


if __name__ == "__main__":
    main()
