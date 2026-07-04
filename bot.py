import os
import io
import logging
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import telebot
from telebot import types

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
bot = telebot.TeleBot(BOT_TOKEN)

# Banner dimensions
BANNER_W = 1500
BANNER_H = 500

THEMES = {
    "Professional": {
        "gradient": [(15, 23, 42), (30, 58, 138)],
        "text_color": (255, 255, 255),
        "accent": (99, 179, 237),
        "sub_color": (148, 163, 184),
    },
    "Creator": {
        "gradient": [(109, 40, 217), (236, 72, 153)],
        "text_color": (255, 255, 255),
        "accent": (251, 191, 36),
        "sub_color": (233, 213, 255),
    },
    "Minimal": {
        "gradient": [(250, 250, 250), (226, 232, 240)],
        "text_color": (15, 23, 42),
        "accent": (59, 130, 246),
        "sub_color": (100, 116, 139),
    },
    "Neon": {
        "gradient": [(0, 0, 0), (10, 10, 20)],
        "text_color": (255, 255, 255),
        "accent": (0, 255, 170),
        "sub_color": (150, 150, 180),
    },
    "Sunset": {
        "gradient": [(194, 65, 12), (234, 179, 8)],
        "text_color": (255, 255, 255),
        "accent": (253, 224, 71),
        "sub_color": (254, 215, 170),
    },
    "Ocean": {
        "gradient": [(8, 145, 178), (6, 182, 212), (16, 185, 129)],
        "text_color": (255, 255, 255),
        "accent": (167, 243, 208),
        "sub_color": (207, 250, 254),
    },
}

user_sessions = {}


def make_gradient(size, colors):
    w, h = size
    base = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(base)
    if len(colors) == 2:
        r1, g1, b1 = colors[0]
        r2, g2, b2 = colors[1]
        for x in range(w):
            t = x / w
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            draw.line([(x, 0), (x, h)], fill=(r, g, b))
    elif len(colors) >= 3:
        r1, g1, b1 = colors[0]
        r2, g2, b2 = colors[1]
        r3, g3, b3 = colors[2]
        half = w // 2
        for x in range(half):
            t = x / half
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            draw.line([(x, 0), (x, h)], fill=(r, g, b))
        for x in range(half, w):
            t = (x - half) / (w - half)
            r = int(r2 + (r3 - r2) * t)
            g = int(g2 + (g3 - g2) * t)
            b = int(b2 + (b3 - b2) * t)
            draw.line([(x, 0), (x, h)], fill=(r, g, b))
    return base


def circle_crop(img, size):
    img = img.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([(0, 0), (size - 1, size - 1)], fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(img.convert("RGBA"), (0, 0), mask)
    return result


def draw_text_shadow(draw, pos, text, font, shadow_color, text_color, offset=2):
    x, y = pos
    draw.text((x + offset, y + offset), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=text_color)


def load_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", size)
        except:
            return ImageFont.load_default()


def load_font_regular(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", size)
        except:
            return ImageFont.load_default()


def make_banner(data: dict) -> bytes:
    theme = THEMES[data["theme"]]
    canvas = make_gradient((BANNER_W, BANNER_H), theme["gradient"]).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # Decorative shapes
    accent = theme["accent"]
    # Top-left glow circle
    glow = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([(0, 0), (399, 399)], fill=accent + (25,))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    canvas.alpha_composite(glow, dest=(-100, -100))

    # Bottom-right glow
    glow2 = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
    ImageDraw.Draw(glow2).ellipse([(0, 0), (499, 499)], fill=accent + (20,))
    glow2 = glow2.filter(ImageFilter.GaussianBlur(50))
    canvas.alpha_composite(glow2, dest=(BANNER_W - 300, BANNER_H - 300))

    # Accent bar on left
    bar = Image.new("RGBA", (6, 220), (0, 0, 0, 0))
    ImageDraw.Draw(bar).rounded_rectangle([(0, 0), (5, 219)], radius=3, fill=accent + (230,))
    canvas.alpha_composite(bar, dest=(60, 140))

    # Profile picture
    has_photo = data.get("photo_bytes") is not None
    avatar_size = 180
    avatar_x = 80
    avatar_y = BANNER_H // 2 - avatar_size // 2

    if has_photo:
        avatar = circle_crop(Image.open(io.BytesIO(data["photo_bytes"])), avatar_size)
        # Ring around avatar
        ring = Image.new("RGBA", (avatar_size + 8, avatar_size + 8), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([(0, 0), (avatar_size + 7, avatar_size + 7)], outline=accent, width=4)
        canvas.alpha_composite(ring, dest=(avatar_x - 4, avatar_y - 4))
        canvas.alpha_composite(avatar, dest=(avatar_x, avatar_y))
    else:
        # Placeholder circle
        placeholder = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
        ImageDraw.Draw(placeholder).ellipse(
            [(0, 0), (avatar_size - 1, avatar_size - 1)],
            fill=accent + (60,),
            outline=accent,
            width=3,
        )
        initials_font = load_font(64)
        name = data.get("name", "?")
        initial = name[0].upper() if name else "?"
        bbox = ImageDraw.Draw(placeholder).textbbox((0, 0), initial, font=initials_font)
        iw, ih = bbox[2] - bbox[0], bbox[3] - bbox[1]
        ImageDraw.Draw(placeholder).text(
            (avatar_size // 2 - iw // 2, avatar_size // 2 - ih // 2),
            initial,
            font=initials_font,
            fill=theme["text_color"],
        )
        canvas.alpha_composite(placeholder, dest=(avatar_x, avatar_y))

    # Text area
    text_x = avatar_x + avatar_size + 40
    draw = ImageDraw.Draw(canvas)

    # Name
    name_font = load_font(72)
    name = data.get("name", "Your Name")
    shadow_col = (0, 0, 0, 100) if theme["text_color"] == (255, 255, 255) else (200, 200, 200, 80)
    draw_text_shadow(draw, (text_x, 130), name, name_font, shadow_col, theme["text_color"])

    # Title / tagline
    title_font = load_font_regular(38)
    title = data.get("title", "")
    if title:
        draw.text((text_x, 220), title, font=title_font, fill=accent)

    # Bio line
    bio_font = load_font_regular(30)
    bio = data.get("bio", "")
    if bio:
        draw.text((text_x, 278), bio, font=bio_font, fill=theme["sub_color"])

    # Tags / skills
    tags = data.get("tags", [])
    if tags:
        tag_font = load_font(22)
        tx = text_x
        ty = 340
        for tag in tags[:6]:
            bbox = draw.textbbox((0, 0), f" {tag} ", font=tag_font)
            tw = bbox[2] - bbox[0] + 16
            th = bbox[3] - bbox[1] + 10
            # pill background
            pill = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            ImageDraw.Draw(pill).rounded_rectangle(
                [(0, 0), (tw - 1, th - 1)], radius=th // 2, fill=accent + (50,), outline=accent + (180,), width=1
            )
            canvas.alpha_composite(pill, dest=(tx, ty))
            draw = ImageDraw.Draw(canvas)
            draw.text((tx + 8, ty + 5), tag, font=tag_font, fill=theme["text_color"])
            tx += tw + 10
            if tx > BANNER_W - 200:
                break

    # Website / handle
    handle = data.get("handle", "")
    if handle:
        handle_font = load_font_regular(28)
        draw.text((text_x, 410), handle, font=handle_font, fill=theme["sub_color"])

    out = io.BytesIO()
    canvas.convert("RGB").save(out, format="PNG", optimize=True)
    out.seek(0)
    return out.read()


# ---- Conversation steps ----
STEPS = ["theme", "name", "title", "bio", "tags", "handle", "photo"]


def send_theme_picker(cid):
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("💼 Professional", callback_data="theme:Professional"),
        types.InlineKeyboardButton("🎨 Creator", callback_data="theme:Creator"),
        types.InlineKeyboardButton("⬜ Minimal", callback_data="theme:Minimal"),
        types.InlineKeyboardButton("⚡ Neon", callback_data="theme:Neon"),
        types.InlineKeyboardButton("🌅 Sunset", callback_data="theme:Sunset"),
        types.InlineKeyboardButton("🌊 Ocean", callback_data="theme:Ocean"),
    )
    bot.send_message(cid, "🎨 *Step 1/7 — Choose a theme:*", parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    cid = message.chat.id
    user_sessions[cid] = {}
    bot.send_message(
        cid,
        "👋 *Profile Banner Maker*\n\nI'll create a stunning profile banner for you in seconds!\n\nLet's build it step by step. Send /make to start.",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["make"])
def cmd_make(message):
    cid = message.chat.id
    user_sessions[cid] = {}
    send_theme_picker(cid)


@bot.callback_query_handler(func=lambda call: call.data.startswith("theme:"))
def handle_theme(call):
    cid = call.message.chat.id
    theme = call.data.split(":")[1]
    user_sessions.setdefault(cid, {})["theme"] = theme
    bot.answer_callback_query(call.id, f"{theme} selected!")
    bot.edit_message_text(f"✅ Theme: *{theme}*", cid, call.message.message_id, parse_mode="Markdown")
    bot.send_message(cid, "✏️ *Step 2/7 — Enter your name:*", parse_mode="Markdown")
    user_sessions[cid]["step"] = "name"


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "name")
def handle_name(message):
    cid = message.chat.id
    user_sessions[cid]["name"] = message.text.strip()
    bot.send_message(cid, "💼 *Step 3/7 — Your title or role:*\n_(e.g. Full Stack Developer, UX Designer)_\nSend /skip to leave blank.", parse_mode="Markdown")
    user_sessions[cid]["step"] = "title"


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "title")
def handle_title(message):
    cid = message.chat.id
    user_sessions[cid]["title"] = "" if message.text == "/skip" else message.text.strip()
    bot.send_message(cid, "📝 *Step 4/7 — Short bio or tagline:*\n_(one line, e.g. Building things people love)_\nSend /skip to leave blank.", parse_mode="Markdown")
    user_sessions[cid]["step"] = "bio"


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "bio")
def handle_bio(message):
    cid = message.chat.id
    user_sessions[cid]["bio"] = "" if message.text == "/skip" else message.text.strip()
    bot.send_message(cid, "🏷 *Step 5/7 — Skills or tags:*\n_(comma-separated, e.g. Python, React, Design)_\nSend /skip to leave blank.", parse_mode="Markdown")
    user_sessions[cid]["step"] = "tags"


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "tags")
def handle_tags(message):
    cid = message.chat.id
    if message.text == "/skip":
        user_sessions[cid]["tags"] = []
    else:
        user_sessions[cid]["tags"] = [t.strip() for t in message.text.split(",") if t.strip()][:6]
    bot.send_message(cid, "🔗 *Step 6/7 — Website or handle:*\n_(e.g. @yourhandle or yoursite.com)_\nSend /skip to leave blank.", parse_mode="Markdown")
    user_sessions[cid]["step"] = "handle"


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "handle")
def handle_handle(message):
    cid = message.chat.id
    user_sessions[cid]["handle"] = "" if message.text == "/skip" else message.text.strip()
    bot.send_message(cid, "📸 *Step 7/7 — Send your profile photo:*\n_(send as a photo or file)_\nSend /skip to use initials instead.", parse_mode="Markdown")
    user_sessions[cid]["step"] = "photo"


@bot.message_handler(commands=["skip"])
def handle_skip(message):
    cid = message.chat.id
    step = user_sessions.get(cid, {}).get("step")
    if step == "photo":
        user_sessions[cid]["photo_bytes"] = None
        generate_banner(cid)


@bot.message_handler(content_types=["photo", "document"],
                     func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "photo")
def handle_photo(message):
    cid = message.chat.id
    try:
        if message.content_type == "photo":
            file_id = message.photo[-1].file_id
        else:
            if not message.document.mime_type.startswith("image/"):
                bot.send_message(cid, "⚠️ Please send an image.")
                return
            file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        user_sessions[cid]["photo_bytes"] = bot.download_file(file_info.file_path)
        generate_banner(cid)
    except Exception as e:
        logger.exception("Photo error")
        bot.send_message(cid, f"❌ Error: {e}")


def generate_banner(cid):
    data = user_sessions.get(cid, {})
    msg = bot.send_message(cid, "⏳ Generating your banner…")
    try:
        result = make_banner(data)
        bot.send_photo(
            cid,
            result,
            caption="✅ *Here's your profile banner!*\n\nSave it and use it on Twitter/X, LinkedIn, GitHub, or anywhere else.\n\nSend /make to create another one!",
            parse_mode="Markdown",
        )
        bot.delete_message(cid, msg.message_id)
    except Exception as e:
        logger.exception("Banner generation error")
        bot.send_message(cid, f"❌ Failed to generate: {e}")


if __name__ == "__main__":
    logger.info("Banner bot starting…")
    bot.infinity_polling()
