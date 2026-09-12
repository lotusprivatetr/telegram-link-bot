import os
import json
import html
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================
# AYARLAR
# =========================
DATA_FILE = Path("links.json")
BANNER_FILE = "banner.jpg"
TZ = ZoneInfo("Europe/Istanbul")

FAST_RESERVATION_URL = "https://t.me/lotusprivate?direct"
CURRENT_ENTRY_URL = "https://lotusprivate.live/giris"

HOME_TEXT_HTML = (
    "<b>Lotus Private Date'in ayrıcalıklı dünyasına hızlı bir adım atın!</b>\n\n"
    "Hemen aşağıdan neyi aradığını seç!"
)

# Telegram adresleri
TELEGRAM_LINKS = [
    ["Ana Kanal", "https://t.me/lotusprivate"],
    ["Etkinlik ve Duyuru", "https://t.me/lotusprivatelive"],
    ["Freespin Kod", "https://t.me/lotusprivatekod"],
    ["Lotus Private VIP", "https://t.me/+ESFVuQOKhfc2ZWY0"],
]

# Reklam / işbirliği
AD_CONTACT_TELEGRAM = "https://t.me/lotusprivatepr"
AD_CONTACT_TEAMS = "https://lotusprivate.live/teams"


# =========================
# VERİ
# =========================
def save_data(data: dict) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_data_file() -> None:
    if not DATA_FILE.exists():
        save_data({
            "sponsors": [],
            "started_users": [],
            "analytics": {
                "hourly": {}
            },
        })


def load_data() -> dict:
    ensure_data_file()

    with DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    data.setdefault("sponsors", [])
    data.setdefault("started_users", [])
    data.setdefault("analytics", {})
    data["analytics"].setdefault("hourly", {})

    return data


def register_started_user(user_id: int) -> None:
    data = load_data()

    users = set()

    for x in data.get("started_users", []):
        try:
            users.add(int(x))
        except Exception:
            pass

    users.add(int(user_id))

    data["started_users"] = sorted(users)
    save_data(data)


def track_click() -> None:
    data = load_data()

    now = datetime.now(TZ)
    day = now.strftime("%Y-%m-%d")
    hour = now.strftime("%H")

    hourly = data["analytics"].get("hourly", {})

    hourly.setdefault(day, {})
    hourly[day][hour] = int(hourly[day].get(hour, 0)) + 1

    data["analytics"]["hourly"] = hourly

    save_data(data)


# =========================
# ADMIN
# =========================
def get_admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_IDS", "").strip()

    if not raw:
        return set()

    ids = set()

    for part in raw.split(","):
        part = part.strip()

        if part.isdigit():
            ids.add(int(part))

    return ids


def is_admin(user_id: int) -> bool:
    return user_id in get_admin_ids()


# =========================
# ANA MENÜ
# =========================
def main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                "⚡ Hızlı Rezervasyon",
                url=FAST_RESERVATION_URL
            )
        ],
        [
            InlineKeyboardButton(
                "🔐 Güncel Giriş",
                url=CURRENT_ENTRY_URL
            )
        ],
        [
            InlineKeyboardButton(
                "📣 Telegram Adresleri",
                callback_data="telegram_addresses"
            )
        ],
        [
            InlineKeyboardButton(
                "🌍 GLOBAL SPONSORLAR",
                callback_data="global_sponsors"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# TELEGRAM ADRESLERİ MENÜSÜ
# =========================
def telegram_addresses_menu() -> InlineKeyboardMarkup:
    keyboard = []

    for title, url in TELEGRAM_LINKS:
        keyboard.append([
            InlineKeyboardButton(title, url=url)
        ])

    keyboard.append([
        InlineKeyboardButton(
            "⬅️ Geri",
            callback_data="back_home"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


# =========================
# GLOBAL SPONSORLAR MENÜSÜ
# =========================
def sponsors_menu() -> InlineKeyboardMarkup:
    data = load_data()
    sponsors = data.get("sponsors", [])

    keyboard = []

    row = []

    for title, url in sponsors:
        row.append(
            InlineKeyboardButton(
                title,
                url=url
            )
        )

        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    # SABİT REKLAM / İŞBİRLİĞİ BUTONU
    keyboard.append([
        InlineKeyboardButton(
            "🤝 Reklam ve İşbirliği",
            callback_data="advertising_contact"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            "⬅️ Geri",
            callback_data="back_home"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


# =========================
# REKLAM VE İŞBİRLİĞİ MENÜSÜ
# =========================
def advertising_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                "✈️ Telegram",
                url=AD_CONTACT_TELEGRAM
            )
        ],
        [
            InlineKeyboardButton(
                "💬 Teams",
                url=AD_CONTACT_TEAMS
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ GLOBAL SPONSORLAR",
                callback_data="global_sponsors"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# AKILLI MESAJ DÜZENLEME
# =========================
async def smart_edit(query, text_html: str, reply_markup=None):
    if query.message and query.message.photo:
        await query.edit_message_caption(
            caption=text_html,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    else:
        await query.edit_message_text(
            text=text_html,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


# =========================
# /START
# =========================
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:

    register_started_user(update.effective_user.id)

    if Path(BANNER_FILE).exists():

        with open(BANNER_FILE, "rb") as photo:

            await update.message.reply_photo(
                photo=photo,
                caption=HOME_TEXT_HTML,
                reply_markup=main_menu(),
                parse_mode="HTML",
            )

    else:

        await update.message.reply_text(
            HOME_TEXT_HTML,
            reply_markup=main_menu(),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


# =========================
# CALLBACK BUTONLAR
# =========================
async def on_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:

    query = update.callback_query
    await query.answer()

    # Saatlik analiz
    track_click()

    if query.data == "telegram_addresses":

        text = (
            "📣 <b>Telegram Adreslerimiz</b>\n\n"
            "Aşağıdan ulaşmak istediğin kanalı seç 👇"
        )

        await smart_edit(
            query,
            text,
            reply_markup=telegram_addresses_menu(),
        )

        return

    if query.data == "global_sponsors":

        text = (
            "🌍 <b>GLOBAL SPONSORLAR</b>\n\n"
            "Aşağıdan sponsorlarımızı inceleyebilirsin 👇"
        )

        await smart_edit(
            query,
            text,
            reply_markup=sponsors_menu(),
        )

        return

    if query.data == "advertising_contact":

        text = (
            "🤝 <b>Reklam ve İşbirliği</b>\n\n"
            "Bizimle iletişime geçmek için aşağıdaki "
            "adreslerden birini kullanabilirsin 👇"
        )

        await smart_edit(
            query,
            text,
            reply_markup=advertising_menu(),
        )

        return

    if query.data == "back_home":

        await smart_edit(
            query,
            HOME_TEXT_HTML,
            reply_markup=main_menu(),
        )

        return


# =========================
# SPONSOR YÖNETİMİ
# =========================
def parse_add_args(text: str):
    parts = text.split(" ", 1)

    if len(parts) < 2:
        return None, None

    payload = parts[1]

    if "|" not in payload:
        return None, None

    name, url = [
        x.strip()
        for x in payload.split("|", 1)
    ]

    if not name or not url:
        return None, None

    return name, url


def url_ok(url: str) -> bool:
    return (
        url.startswith("https://")
        or url.startswith("http://")
        or url.startswith("tg://")
    )


async def cmd_addsponsor(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:

    if not is_admin(update.effective_user.id):
        return

    name, url = parse_add_args(update.message.text)

    if not name or not url:

        await update.message.reply_text(
            "Kullanım:\n"
            "/addsponsor İsim | https://link"
        )

        return

    if not url_ok(url):

        await update.message.reply_text(
            "❌ Link formatı yanlış."
        )

        return

    data = load_data()

    data.setdefault("sponsors", []).append(
        [name, url]
    )

    save_data(data)

    await update.message.reply_text(
        "✅ Sponsor eklendi.\n"
        "/listsponsor ile kontrol edebilirsin."
    )


async def cmd_delsponsor(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:

    if not is_admin(update.effective_user.id):
        return

    parts = (
        update.message.text
        or ""
    ).strip().split()

    if (
        len(parts) != 2
        or not parts[1].isdigit()
    ):

        await update.message.reply_text(
            "Kullanım: /delsponsor 1"
        )

        return

    idx = int(parts[1]) - 1

    data = load_data()

    sponsors = data.get("sponsors", [])

    if idx < 0 or idx >= len(sponsors):

        await update.message.reply_text(
            "❌ Geçersiz sıra numarası.\n"
            "/listsponsor ile kontrol et."
        )

        return

    removed = sponsors.pop(idx)

    data["sponsors"] = sponsors

    save_data(data)

    await update.message.reply_text(
        f"🗑️ Silindi: {removed[0]}"
    )


async def cmd_listsponsor(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:

    if not is_admin(update.effective_user.id):
        return

    data = load_data()

    sponsors = data.get("sponsors", [])

    text = (
        "🌍 <b>GLOBAL SPONSORLAR</b>\n\n"
    )

    if not sponsors:

        text += (
            "<i>Henüz sponsor eklenmemiş.</i>"
        )

    else:

        for i, (title, url) in enumerate(
            sponsors,
            start=1
        ):

            text += (
                f"{i}) "
                f"{html.escape(title)} — "
                f"{html.escape(url)}\n"
            )

    text += (
        "\n\n➕ Sponsor ekle:\n"
        "<code>/addsponsor İsim | https://link</code>"
        "\n\n🗑️ Sponsor sil:\n"
        "<code>/delsponsor 1</code>"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# =========================
# ANALİZ
# =========================
async def cmd_analiz(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:

    if not is_admin(update.effective_user.id):
        return

    data = load_data()

    started_count = len(
        data.get("started_users", [])
    )

    hourly = (
        data
        .get("analytics", {})
        .get("hourly", {})
    )

    today = datetime.now(TZ).strftime(
        "%Y-%m-%d"
    )

    today_hours = hourly.get(
        today,
        {}
    )

    text = (
        "📊 <b>ANALİZ</b>\n\n"
        f"👥 <b>Toplam /start yapan kişi:</b> "
        f"{started_count}\n\n"
        "🕒 <b>Bugünkü saatlik tıklama dağılımı</b>\n"
        f"<i>{today} / Türkiye saati</i>\n\n"
    )

    for hour in range(24):

        key = f"{hour:02d}"

        count = int(
            today_hours.get(
                key,
                0
            )
        )

        text += (
            f"{key}:00 - {key}:59 → "
            f"<b>{count}</b>\n"
        )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
    )


# =========================
# /LIST
# =========================
async def cmd_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:

    if not is_admin(update.effective_user.id):
        return

    data = load_data()

    started_count = len(
        data.get("started_users", [])
    )

    sponsors_count = len(
        data.get("sponsors", [])
    )

    text = (
        "📌 <b>Bot Durumu</b>\n\n"
        f"👥 /start yapan kişi: "
        f"<b>{started_count}</b>\n"
        f"🌍 Global sponsor sayısı: "
        f"<b>{sponsors_count}</b>\n\n"
        "Sponsor listesi: /listsponsor"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
    )


# =========================
# /ID
# =========================
async def cmd_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:

    await update.message.reply_text(
        f"Senin Telegram ID: "
        f"{update.effective_user.id}"
    )


# =========================
# BROADCAST
# =========================
def get_broadcast_user_ids() -> list[int]:

    data = load_data()

    out = []

    for x in data.get(
        "started_users",
        []
    ):

        try:
            out.append(int(x))
        except Exception:
            pass

    return out


async def cmd_broadcast(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:

    if not is_admin(update.effective_user.id):
        return

    context.user_data[
        "broadcast_flow"
    ] = {
        "step": "photo",
        "file_id": None
    }

    await update.message.reply_text(
        "📣 Broadcast başlatıldı.\n\n"
        "1) Şimdi duyuru fotoğrafını gönder.\n"
        "İptal: /cancel"
    )


async def handle_broadcast_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:

    flow = context.user_data.get(
        "broadcast_flow"
    )

    if not flow:
        return

    if not is_admin(
        update.effective_user.id
    ):

        context.user_data.pop(
            "broadcast_flow",
            None
        )

        return

    if flow.get("step") != "photo":
        return

    if not update.message.photo:

        await update.message.reply_text(
            "❌ Lütfen fotoğraf gönder."
        )

        return

    file_id = (
        update
        .message
        .photo[-1]
        .file_id
    )

    flow["file_id"] = file_id
    flow["step"] = "caption"

    await update.message.reply_text(
        "2) Şimdi fotoğraf açıklamasını yaz.\n"
        "İptal: /cancel"
    )


async def handle_text_flows(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:

    text = (
        update.message.text
        or ""
    ).strip()

    flow = context.user_data.get(
        "broadcast_flow"
    )

    if (
        flow
        and flow.get("step") == "caption"
    ):

        if not is_admin(
            update.effective_user.id
        ):

            context.user_data.pop(
                "broadcast_flow",
                None
            )

            return

        file_id = flow.get(
            "file_id"
        )

        user_ids = (
            get_broadcast_user_ids()
        )

        if not user_ids:

            context.user_data.pop(
                "broadcast_flow",
                None
            )

            await update.message.reply_text(
                "⚠️ Henüz hedef kitle yok."
            )

            return

        ok = 0
        fail = 0

        for uid in user_ids:

            try:

                await context.bot.send_photo(
                    chat_id=uid,
                    photo=file_id,
                    caption=text,
                )

                ok += 1

            except Exception:

                fail += 1

        context.user_data.pop(
            "broadcast_flow",
            None
        )

        await update.message.reply_text(
            f"✅ Broadcast tamamlandı.\n"
            f"Gönderildi: {ok}\n"
            f"Hata: {fail}"
        )


async def cmd_cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:

    if context.user_data.get(
        "broadcast_flow"
    ):

        context.user_data.pop(
            "broadcast_flow",
            None
        )

        await update.message.reply_text(
            "❌ Broadcast iptal edildi."
        )

    else:

        await update.message.reply_text(
            "İptal edilecek işlem yok."
        )


# =========================
# MAIN
# =========================
def main():

    token = os.getenv(
        "BOT_TOKEN"
    )

    if not token:

        raise RuntimeError(
            "BOT_TOKEN bulunamadı."
        )

    ensure_data_file()

    app = (
        Application
        .builder()
        .token(token)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            on_callback
        )
    )

    app.add_handler(
        CommandHandler(
            "id",
            cmd_id
        )
    )

    app.add_handler(
        CommandHandler(
            "list",
            cmd_list
        )
    )

    app.add_handler(
        CommandHandler(
            "analiz",
            cmd_analiz
        )
    )

    app.add_handler(
        CommandHandler(
            "addsponsor",
            cmd_addsponsor
        )
    )

    app.add_handler(
        CommandHandler(
            "delsponsor",
            cmd_delsponsor
        )
    )

    app.add_handler(
        CommandHandler(
            "listsponsor",
            cmd_listsponsor
        )
    )

    app.add_handler(
        CommandHandler(
            "broadcast",
            cmd_broadcast
        )
    )

    app.add_handler(
        CommandHandler(
            "cancel",
            cmd_cancel
        )
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_broadcast_photo
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_text_flows
        )
    )

    print(
        "Bot çalışıyor... "
        "Telegram’da /start deneyebilirsin."
    )

    app.run_polling()


if __name__ == "__main__":
    main()
