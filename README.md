# Telegram Auto Video Poster Bot

This bot does two things:

1. If the bot is **admin in your channel**, every time you post a video there, it will **auto repost** it to your target group **with 3 buttons**.
2. If an **admin user sends a video in private chat** to the bot, the bot will **forward it to the target group** with the same 3 buttons.

Perfect for posting fight videos / content to multiple groups.

## Files

- `main.py` — bot source
- `requirements.txt` — Python deps
- `Procfile` — tell Railway to run the bot as a worker

## Deploy to Railway

1. Create a new project on Railway.
2. Upload these files (or connect to a GitHub repo with them).
3. In Railway → Variables, add:

   - `BOT_TOKEN` = `123456789:ABC...`
   - `TARGET_GROUP_ID` = `-100xxxxxxxxxx`
   - `ADMIN_IDS` = `111111111,222222222,333333333`

4. Deploy → Railway will run `python main.py` forever.

## Notes
- `ADMIN_IDS` is a comma separated list — all those users can send video to the bot and it will post to group.
- Buttons are inside `build_keyboard()` — you can change text and links easily.
