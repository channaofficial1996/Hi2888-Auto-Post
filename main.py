import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ===== CONFIG (from Railway env) =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_GROUP_ID = os.getenv("TARGET_GROUP_ID")
ADMIN_IDS_ENV = os.getenv("ADMIN_IDS", "")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not TARGET_GROUP_ID:
    raise RuntimeError("TARGET_GROUP_ID not set")

TARGET_GROUP_ID = int(TARGET_GROUP_ID)

# parse admin ids: "111,222,333"
ADMIN_IDS = []
for part in ADMIN_IDS_ENV.split(","):
    part = part.strip()
    if part:
        try:
            ADMIN_IDS.append(int(part))
        except ValueError:
            pass

# state keys inside user_data
STATE_KEY = "state"
MEDIA_KEY = "media"
CAPTION_KEY = "caption"

STATE_WAIT_MEDIA = "wait_media"
STATE_WAIT_CAPTION = "wait_caption"


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
    # when user /start → ask for media
    context.user_data[STATE_KEY] = STATE_WAIT_MEDIA
    await update.message.reply_text(
        "📥 សូមផ្ញើ វីដេអូ ឬ រូបភាព មក bot នេះก่อน\n"
        " (មានសិទ្ធិเฉพาะ admin ដែលដាក់ក្នុង ADMIN_IDS ប៉ុណ្ណោះ)"
    )


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """รับ video/photo จาก admin แล้วถาม caption"""
    msg = update.message
    user_id = msg.from_user.id

    # check admin
    if user_id not in ADMIN_IDS:
        await msg.reply_text("🚫 អ្នកមិនមានសិទ្ធិប្រើប៊ូតុងបោះទៅ group ទេ!")
        return

    # only allow if user is in state wait_media (optional but good)
    context.user_data[STATE_KEY] = STATE_WAIT_CAPTION

    media_info = {}

    # video
    if msg.video:
        media_info["type"] = "video"
        media_info["file_id"] = msg.video.file_id
    # photo
    elif msg.photo:
        # last photo = highest quality
        media_info["type"] = "photo"
        media_info["file_id"] = msg.photo[-1].file_id
    # document video
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video/"):
        media_info["type"] = "video"
        media_info["file_id"] = msg.document.file_id
    else:
        await msg.reply_text("⚠️ សូមផ្ញើតែ វីដេអូ ឬ រូបភាព ប៉ុណ្ណោះ.")
        return

    # save media in user_data
    context.user_data[MEDIA_KEY] = media_info

    await msg.reply_text(
        "📝 សូមបញ្ចូល caption ឥឡូវនេះ\n"
        "➡ អាចដាក់អក្សរយូរៗបាន និងដាក់ Link បានគ្រប់យ៉ាង។\n"
        "បន្ទាប់មកខ្ញុំនឹងបញ្ជូនទៅ Group ឲ្យអ្នក ដោយស្វ័យប្រវត្តិ ✅"
    )


async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """รับ caption แล้วส่งไป group"""
    msg = update.message
    user_id = msg.from_user.id

    # check state
    state = context.user_data.get(STATE_KEY)
    if state != STATE_WAIT_CAPTION:
        # user sent text but not in caption state
        await msg.reply_text("⚠️ សូម /start ម្តងទៀត ហើយផ្ញើ វីដេអូ/រូបភាព សិន។")
        return

    # check admin again
    if user_id not in ADMIN_IDS:
        await msg.reply_text("🚫 អ្នកមិនមានសិទ្ធិ!")
        return

    caption_text = msg.text or ""
    media_info = context.user_data.get(MEDIA_KEY)

    if not media_info:
        await msg.reply_text("❗ មិនរកឃើញវីដេអូ/រូបភាពដែលបានផ្ញើមុនទេ។ សូម /start សារជាថ្មី.")
        context.user_data[STATE_KEY] = STATE_WAIT_MEDIA
        return

    # try to send to group
    try:
        if media_info["type"] == "video":
            await context.bot.send_video(
                chat_id=TARGET_GROUP_ID,
                video=media_info["file_id"],
                caption=caption_text,
                reply_markup=build_keyboard()
            )
        elif media_info["type"] == "photo":
            await context.bot.send_photo(
                chat_id=TARGET_GROUP_ID,
                photo=media_info["file_id"],
                caption=caption_text,
                reply_markup=build_keyboard()
            )

        await msg.reply_text("✅ បានបញ្ជូនទៅ Group ជោគជ័យ!")
    except Exception as e:
        # show error so you know what's wrong (not admin in group, group id wrong, ...)
        await msg.reply_text(f"❌ បញ្ជូនមិនបានទេ: {e}")

    # reset state
    context.user_data[STATE_KEY] = STATE_WAIT_MEDIA
    context.user_data.pop(MEDIA_KEY, None)


async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    auto repost from channel -> group (ច旧 logic)
    """
    post = update.channel_post
    if not post:
        return

    file_id = None
    media_type = None

    if post.video:
        file_id = post.video.file_id
        media_type = "video"
    elif post.photo:
        file_id = post.photo[-1].file_id
        media_type = "photo"
    elif post.document and post.document.mime_type and post.document.mime_type.startswith("video/"):
        file_id = post.document.file_id
        media_type = "video"

    if not file_id:
        return

    caption = post.caption or ""

    try:
        if media_type == "video":
            await context.bot.send_video(
                chat_id=TARGET_GROUP_ID,
                video=file_id,
                caption=caption,
                reply_markup=build_keyboard(),
            )
        else:
            await context.bot.send_photo(
                chat_id=TARGET_GROUP_ID,
                photo=file_id,
                caption=caption,
                reply_markup=build_keyboard(),
            )
    except Exception as e:
        # optional: send to your own id
        print("Error reposting from channel:", e)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # /start
    app.add_handler(CommandHandler("start", start))

    # from channel (auto)
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post))

    # media from admin (in private) → ask caption
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (filters.VIDEO | filters.PHOTO | filters.Document.VIDEO),
        handle_media
    ))

    # caption from admin
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT & (~filters.COMMAND),
        handle_caption
    ))

    print("🤖 Bot running ...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
