import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ENV = os.getenv("TARGET_GROUP_IDS") or os.getenv("TARGET_GROUP_ID", "")
ADMIN_IDS_ENV = os.getenv("ADMIN_IDS", "")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not TARGET_CHAT_ENV:
    raise RuntimeError("TARGET_GROUP_IDS not set")

# support id + @channel
TARGET_CHATS = []
for part in TARGET_CHAT_ENV.split(","):
    part = part.strip()
    if not part:
        continue
    if part.startswith("@"):
        TARGET_CHATS.append(part)
    else:
        try:
            TARGET_CHATS.append(int(part))
        except ValueError:
            pass

ADMIN_IDS = []
for part in ADMIN_IDS_ENV.split(","):
    part = part.strip()
    if part:
        try:
            ADMIN_IDS.append(int(part))
        except ValueError:
            pass

STATE_KEY = "state"
ALBUM_KEY = "album"
SINGLE_MEDIA_KEY = "media"
STATE_WAIT_MEDIA = "wait_media"
STATE_WAIT_CAPTION = "wait_caption"


def build_inline_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🐓ជជែកគ្នាអំពីមាន់", url="https://t.me/livesb24h"),
                InlineKeyboardButton("🎬 វីដេអូថ្មីៗ", url="https://t.me/livesb24h"),
            ],
            [InlineKeyboardButton("☎️បើកអាខោន", url="https://t.me/Hi2888CS1")],
        ]
    )


def build_reply_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("▶️ ចាប់ផ្តើម")]], resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data[STATE_KEY] = STATE_WAIT_MEDIA
    context.user_data.pop(ALBUM_KEY, None)
    context.user_data.pop(SINGLE_MEDIA_KEY, None)
    await update.message.reply_text(
        "📥 សូមផ្ញើ វីដេអូ ឬ រូបភាព (album ក៏បាន) មក bot សិន\nបន្ទាប់មកបញ្ចូល caption📤",
        reply_markup=build_reply_keyboard(),
    )


async def start_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data[STATE_KEY] = STATE_WAIT_MEDIA
    context.user_data.pop(ALBUM_KEY, None)
    context.user_data.pop(SINGLE_MEDIA_KEY, None)
    await update.message.reply_text("🎬 សូមផ្ញើ វីដេអូ ឬ រូបភាព (album ក៏បាន) មក bot នេះសិន")


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = msg.from_user.id
    if uid not in ADMIN_IDS:
        await msg.reply_text("🚫 អ្នកមិនមានសិទ្ធិបោះទៅក្រុមទេ!")
        return

    # detect media
    media_info = None
    if msg.video:
        media_info = {"type": "video", "file_id": msg.video.file_id}
    elif msg.photo:
        media_info = {"type": "photo", "file_id": msg.photo[-1].file_id}
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video/"):
        media_info = {"type": "video", "file_id": msg.document.file_id}
    else:
        await msg.reply_text("⚠️ សូមផ្ញើតែ វីដេអូ ឬ រូបភាព ប៉ុណ្ណោះ.")
        return

    # album?
    if msg.media_group_id:
        album = context.user_data.get(ALBUM_KEY)
        if not album:
            album = []
            context.user_data[ALBUM_KEY] = album
            await msg.reply_text(
                "📝 សូមបញ្ចូល caption ឥឡូវនេះ\n➡ អាចដាក់អក្សរយូរ និង Link បានគ្រប់យ៉ាង។"
            )
        album.append(media_info)
        context.user_data[STATE_KEY] = STATE_WAIT_CAPTION
        return

    # single
    context.user_data[SINGLE_MEDIA_KEY] = media_info
    context.user_data[STATE_KEY] = STATE_WAIT_CAPTION
    await msg.reply_text(
        "📝 សូមបញ្ចូល caption ឥឡូវនេះ\n➡ អាចដាក់អក្សរយូរ និង Link បានគ្រប់យ៉ាង។"
    )


async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if context.user_data.get(STATE_KEY) != STATE_WAIT_CAPTION:
        return

    uid = msg.from_user.id
    if uid not in ADMIN_IDS:
        await msg.reply_text("🚫 អ្នកមិនមានសិទ្ធិ!")
        return

    caption = msg.text or ""
    album = context.user_data.get(ALBUM_KEY)
    single_media = context.user_data.get(SINGLE_MEDIA_KEY)

    success = 0
    errors = []

    if album:
        # send album to each chat
        for chat in TARGET_CHATS:
            try:
                # rebuild fresh media list for this chat
                media_group = []
                for idx, m in enumerate(album):
                    if m["type"] == "photo":
                        im = InputMediaPhoto(media=m["file_id"])
                    else:
                        im = InputMediaVideo(media=m["file_id"])
                    if idx == 0:
                        im.caption = caption
                    media_group.append(im)

                await context.bot.send_media_group(chat_id=chat, media=media_group)
                # second message for buttons
                await context.bot.send_message(chat_id=chat, text=" ", reply_markup=build_inline_keyboard())
                success += 1
            except Exception as e:
                errors.append(f"{chat}: {e}")

    elif single_media:
        for chat in TARGET_CHATS:
            try:
                if single_media["type"] == "photo":
                    await context.bot.send_photo(
                        chat_id=chat,
                        photo=single_media["file_id"],
                        caption=caption,
                        reply_markup=build_inline_keyboard(),
                    )
                else:
                    await context.bot.send_video(
                        chat_id=chat,
                        video=single_media["file_id"],
                        caption=caption,
                        reply_markup=build_inline_keyboard(),
                    )
                success += 1
            except Exception as e:
                errors.append(f"{chat}: {e}")

    # report
    if success and not errors:
        await msg.reply_text(f"✅ បានបញ្ជូនជា album ទៅកន្លែង {success}!", reply_markup=build_reply_keyboard())
    elif success and errors:
        await msg.reply_text(
            "⚠️ បានបញ្ជូនខ្លះ ប៉ុន្តែមានបញ្ហាខ្លះ:\n" + "\n".join(errors),
            reply_markup=build_reply_keyboard(),
        )
    else:
        await msg.reply_text("❌ បញ្ជូនមិនបានទេ:\n" + "\n".join(errors), reply_markup=build_reply_keyboard())

    # reset
    context.user_data[STATE_KEY] = STATE_WAIT_MEDIA
    context.user_data.pop(ALBUM_KEY, None)
    context.user_data.pop(SINGLE_MEDIA_KEY, None)


# auto repost from channel (single only)
async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    for chat in TARGET_CHATS:
        try:
            if media_type == "video":
                await context.bot.send_video(chat_id=chat, video=file_id, caption=caption, reply_markup=build_inline_keyboard())
            else:
                await context.bot.send_photo(chat_id=chat, photo=file_id, caption=caption, reply_markup=build_inline_keyboard())
        except Exception as e:
            print(f"error send to {chat}: {e}")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & filters.Regex("^▶️ ចាប់ផ្តើម$"), start_button))
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & (filters.PHOTO | filters.VIDEO | filters.Document.VIDEO), handle_media))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & (~filters.COMMAND), handle_caption))

    print("🤖 Bot running ...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
