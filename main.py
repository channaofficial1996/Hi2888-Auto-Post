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
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ====== ENV CONFIG ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ENV = os.getenv("TARGET_GROUP_IDS") or os.getenv("TARGET_GROUP_ID", "")
ADMIN_IDS_ENV = os.getenv("ADMIN_IDS", "")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not TARGET_CHAT_ENV:
    raise RuntimeError("TARGET_GROUP_IDS not set")

# parse target chats (support id + @channel)
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

# parse admin ids
ADMIN_IDS = []
for part in ADMIN_IDS_ENV.split(","):
    part = part.strip()
    if part:
        try:
            ADMIN_IDS.append(int(part))
        except ValueError:
            pass

# ====== STATE KEYS ======
STATE_KEY = "state"
MEDIA_KEY = "media"          # for single media
ALBUM_KEY = "album_media"    # for media group
STATE_WAIT_MEDIA = "wait_media"
STATE_WAIT_CAPTION = "wait_caption"


def build_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🐓ជជែកគ្នាអំពីមាន់", url="https://t.me/livesb24h"),
                InlineKeyboardButton("🎬 វីដេអូថ្មីៗ", url="https://t.me/livesb24h"),
            ],
            [
                InlineKeyboardButton("☎️បើកអាខោន", url="https://t.me/Hi2888CS1"),
            ],
        ]
    )


def build_reply_keyboard() -> ReplyKeyboardMarkup:
    kb = [[KeyboardButton("▶️ ចាប់ផ្តើម")]]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=False)


# ========== /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data[STATE_KEY] = STATE_WAIT_MEDIA
    # clear old album
    context.user_data.pop(ALBUM_KEY, None)
    context.user_data.pop(MEDIA_KEY, None)

    await update.message.reply_text(
        "📥 សូមផ្ញើ វីដេអូ ឬ រូបភាព (អាចជា album ផងបាន) មក bot សិន\n"
        "បន្ទាប់មកបញ្ចូល caption📤",
        reply_markup=build_reply_keyboard(),
    )


# ========== pinned button ==========
async def start_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data[STATE_KEY] = STATE_WAIT_MEDIA
    context.user_data.pop(ALBUM_KEY, None)
    context.user_data.pop(MEDIA_KEY, None)
    await update.message.reply_text("🎬 សូមផ្ញើ វីដេអូ ឬ រូបភាព (album ក៏បាន) មក bot នេះសិន")


# ========== handle media (photo/video/document) ==========
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id

    if user_id not in ADMIN_IDS:
        await msg.reply_text("🚫 អ្នកមិនមានសិទ្ធិបោះទៅក្រុមទេ!")
        return

    # media from album?
    media_group_id = msg.media_group_id

    # build media dict
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

    # ===== case 1: media group (album) =====
    if media_group_id:
        album_list = context.user_data.get(ALBUM_KEY)
        if not album_list:
            # first item of album
            album_list = []
            context.user_data[ALBUM_KEY] = album_list
            # ask caption only once
            await msg.reply_text(
                "📝 សូមបញ្ចូល caption ឥឡូវនេះ\n➡ អាចដាក់អក្សរយូរបាន និងដាក់ Link បានគ្រប់យ៉ាង។"
            )
        # append this media
        album_list.append(media_info)
        # wait for caption
        context.user_data[STATE_KEY] = STATE_WAIT_CAPTION
        return

    # ===== case 2: single media =====
    context.user_data[MEDIA_KEY] = media_info
    context.user_data[STATE_KEY] = STATE_WAIT_CAPTION

    await msg.reply_text(
        "📝 សូមបញ្ចូល caption ឥឡូវនេះ\n➡ អាចដាក់អក្សរយូរបាន និងដាក់ Link បានគ្រប់យ៉ាង។"
    )


# ========== handle caption ==========
async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id

    if context.user_data.get(STATE_KEY) != STATE_WAIT_CAPTION:
        return

    if user_id not in ADMIN_IDS:
        await msg.reply_text("🚫 អ្នកមិនមានសិទ្ធិ!")
        return

    caption_text = msg.text or ""

    album_list = context.user_data.get(ALBUM_KEY)
    single_media = context.user_data.get(MEDIA_KEY)

    success = 0
    errors = []

    # ===== if we have album =====
    if album_list:
        # build telegram InputMedia list
        media_group = []
        for i, m in enumerate(album_list):
            if m["type"] == "photo":
                im = InputMediaPhoto(media=m["file_id"])
            else:
                im = InputMediaVideo(media=m["file_id"])
            if i == 0:
                im.caption = caption_text  # caption only on first
            media_group.append(im)

        for chat in TARGET_CHATS:
            try:
                await context.bot.send_media_group(chat_id=chat, media=media_group)
                # send extra message for buttons
                await context.bot.send_message(
                    chat_id=chat,
                    text=" ",
                    reply_markup=build_inline_keyboard(),
                )
                success += 1
            except Exception as e:
                errors.append(f"{chat}: {e}")

    # ===== else single media =====
    elif single_media:
        for chat in TARGET_CHATS:
            try:
                if single_media["type"] == "video":
                    await context.bot.send_video(
                        chat_id=chat,
                        video=single_media["file_id"],
                        caption=caption_text,
                        reply_markup=build_inline_keyboard(),
                    )
                else:
                    await context.bot.send_photo(
                        chat_id=chat,
                        photo=single_media["file_id"],
                        caption=caption_text,
                        reply_markup=build_inline_keyboard(),
                    )
                success += 1
            except Exception as e:
                errors.append(f"{chat}: {e}")
    else:
        await msg.reply_text("❗ មិនមានមេឌៀសម្រាប់បញ្ជូនទេ សូម /start ម្តងទៀត.")
        context.user_data[STATE_KEY] = STATE_WAIT_MEDIA
        return

    # ===== report back =====
    if success and not errors:
        await msg.reply_text(
            f"✅ បានបញ្ជូនទៅ Group/Channel ចំនួន {success} ជោគជ័យ!",
            reply_markup=build_reply_keyboard(),
        )
    elif success and errors:
        await msg.reply_text(
            "⚠️ បញ្ជូនបានខ្លះ ប៉ុន្តែខ្លះបរាជ័យ:\n" + "\n".join(errors),
            reply_markup=build_reply_keyboard(),
        )
    else:
        await msg.reply_text(
            "❌ បញ្ជូនមិនបានទៅកន្លែងណាទេ.\n" + ("\n".join(errors) if errors else ""),
            reply_markup=build_reply_keyboard(),
        )

    # reset
    context.user_data[STATE_KEY] = STATE_WAIT_MEDIA
    context.user_data.pop(ALBUM_KEY, None)
    context.user_data.pop(MEDIA_KEY, None)


# ========== auto repost from channel ==========
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
                await context.bot.send_video(
                    chat_id=chat,
                    video=file_id,
                    caption=caption,
                    reply_markup=build_inline_keyboard(),
                )
            else:
                await context.bot.send_photo(
                    chat_id=chat,
                    photo=file_id,
                    caption=caption,
                    reply_markup=build_inline_keyboard(),
                )
        except Exception as e:
            print(f"error send to {chat}: {e}")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # pinned button
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & filters.Regex("^▶️ ចាប់ផ្តើម$"),
            start_button,
        )
    )

    # channel auto
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post))

    # media (single or album)
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & (filters.PHOTO | filters.VIDEO | filters.Document.VIDEO),
            handle_media,
        )
    )

    # caption
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & (~filters.COMMAND),
            handle_caption,
        )
    )

    print("🤖 Bot running ...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
