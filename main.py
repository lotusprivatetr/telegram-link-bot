import os
import json
from pathlib import Path
from typing import Optional, Tuple

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
FAST_RESERVATION_URL = "https://t.me/lotusprivate?direct"

HOME_TEXT = (
    "✨ *Lotus Private Link Merkezi*\n"
    "_Kanallarımız ve sitelerimiz tek yerde._\n\n"
    "Aşağıdan bir menü seç 👇"
)

DEFAULT_CHANNELS = [
    ["🔥 Lotus Private", "https://t.me/lotusprivate"],
    ["🎥 Lotus Private Live", "https://t.me/lotusprivatelive"],
    ["🤖 Lotus Private Bot", "https://t.me/LotusPrivateBot"],
]

DEFAULT_SITES = [
    ["🌐 bio.site/lotusprivate.com", "https://bio.site/lotusprivate.com"],
    ["🌐 bio.site/lotussiteler.com", "https://bio.site/lotussiteler.com"],
]


# =========================
# DATA (DOSYA)
# =========================
def save_data(data: dict) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_data_file() -> None:
    if not DATA_FILE.exists():
        data = {
            "quick": [],      # ana menüde görünen hızlı linkler
            "channels": DEFAULT_CHANNELS,
            "sites": DEFAULT_SITES,
        }
        save_data(data)


def load_data() -> dict:
    ensure_data_file()
    with DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("quick", [])
    data.setdefault("channels", [])
    data.setdefault("sites", [])
    return data


# =========================
# ADMIN
# =========================
def get_admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_IDS", "").strip()
    if not raw:
        return set()
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def is_admin(user_id: int) -> bool:
    return user_id in get_admin_ids()


# =========================
# UI / MENÜLER
# =========================
def build_2col_rows(items):
    rows = []
    row = []
    for title, url in items:
        row.append(InlineKeyboardButton(title, url=url))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


def home_back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Geri", callback_data="back_home")]])


def panel_back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Panele Dön", callback_data="back_panel")]])


def main_menu() -> InlineKeyboardMarkup:
    data = load_data()
    quick = data.get("quick", [])

    keyboard = []
    keyboard.append([InlineKeyboardButton("🚀 HIZLI REZERVASYON", url=FAST_RESERVATION_URL)])

    # Ana menüde görünen quick linkler (2'li)
    keyboard += build_2col_rows(quick)

    # Sekmeler
    keyboard.append([InlineKeyboardButton("📣 Telegram Kanalları", callback_data="menu_channels")])
    keyboard.append([InlineKeyboardButton("🌐 İnternet Siteleri", callback_data="menu_sites")])

    return InlineKeyboardMarkup(keyboard)


def list_to_keyboard(items) -> InlineKeyboardMarkup:
    keyboard = build_2col_rows(items)
    keyboard.append([InlineKeyboardButton("⬅️ Geri", callback_data="back_home")])
    return InlineKeyboardMarkup(keyboard)


def admin_panel_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📋 Listeyi Göster", callback_data="admin_list")],
        [InlineKeyboardButton("➕ Ekleme (Wizard)", callback_data="admin_add_help")],
        [InlineKeyboardButton("➖ Silme", callback_data="admin_del_help")],
    ]
    return InlineKeyboardMarkup(keyboard)


# Fotoğrafta caption, yazıda text editleyen akıllı fonksiyon
async def smart_edit(query, text: str, reply_markup=None, parse_mode="Markdown"):
    if query.message and query.message.photo:
        await query.edit_message_caption(
            caption=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    else:
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )


# =========================
# YARDIMCI: ADD PARSE / VALIDATION
# =========================
def parse_add_args(text: str) -> Tuple[Optional[str], Optional[str]]:
    # /addquick İsim | https://...
    parts = text.split(" ", 1)
    if len(parts) < 2:
        return None, None
    payload = parts[1]
    if "|" not in payload:
        return None, None
    name, url = [x.strip() for x in payload.split("|", 1)]
    if not name or not url:
        return None, None
    return name, url


def url_ok(url: str) -> bool:
    url = url.strip()
    return (
        url.startswith("https://")
        or url.startswith("http://")
        or url.startswith("tg://")
        or url.startswith("https://t.me/")
    )


# =========================
# KOMUTLAR
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # banner.jpg varsa fotoğraf + caption, yoksa metin
    if Path(BANNER_FILE).exists():
        with open(BANNER_FILE, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=HOME_TEXT,
                reply_markup=main_menu(),
                parse_mode="Markdown",
            )
    else:
        await update.message.reply_text(
            HOME_TEXT,
            reply_markup=main_menu(),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Senin Telegram ID: {update.effective_user.id}")


async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "🛠 *Admin Panel*\nAşağıdan seç 👇",
        reply_markup=admin_panel_menu(),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return

    data = load_data()
    quick = data.get("quick", [])
    channels = data.get("channels", [])
    sites = data.get("sites", [])

    text = "📌 *Kayıtlı Linkler*\n\n"

    text += "⚡️ *Ana Menü (Quick):*\n"
    if quick:
        for i, (t, u) in enumerate(quick, start=1):
            text += f"{i}) {t} — {u}\n"
    else:
        text += "_Boş_\n"

    text += "\n📣 *Kanallar:*\n"
    if channels:
        for i, (t, u) in enumerate(channels, start=1):
            text += f"{i}) {t} — {u}\n"
    else:
        text += "_Boş_\n"

    text += "\n🌐 *Siteler:*\n"
    if sites:
        for i, (t, u) in enumerate(sites, start=1):
            text += f"{i}) {t} — {u}\n"
    else:
        text += "_Boş_\n"

    text += "\nSilmek için örnek:\n`/delquick 1`  `/delchannel 2`  `/delsite 1`"

    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)


# =========================
# ADD WIZARD (| olmadan ekleme)
# =========================
# context.user_data["add_flow"] = {"cat": "...", "step": "name|url", "name": "..."}
async def start_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, cat: str) -> None:
    if not is_admin(update.effective_user.id):
        return
    context.user_data["add_flow"] = {"cat": cat, "step": "name", "name": ""}
    await update.message.reply_text(
        "✅ *Ekleme başlatıldı*\n\n1) Link adı yaz (butonda gözükecek isim):",
        parse_mode="Markdown",
    )


async def handle_add_flow_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    flow = context.user_data.get("add_flow")
    if not flow:
        return

    # Admin değilse hiç işleme
    if not is_admin(update.effective_user.id):
        context.user_data.pop("add_flow", None)
        return

    msg = (update.message.text or "").strip()
    if not msg:
        return

    if flow.get("step") == "name":
        flow["name"] = msg
        flow["step"] = "url"
        await update.message.reply_text(
            "2) Şimdi linki yapıştır (https://...):",
            parse_mode="Markdown",
        )
        return

    if flow.get("step") == "url":
        url = msg
        if not url_ok(url):
            await update.message.reply_text(
                "❌ Link formatı yanlış.\nhttps:// ile başlayan link gönder.",
                parse_mode="Markdown",
            )
            return

        cat = flow.get("cat")
        name = flow.get("name", "").strip()
        if not name:
            context.user_data.pop("add_flow", None)
            await update.message.reply_text("❌ İsim boş. /addquick veya /addsite ile tekrar dene.")
            return

        data = load_data()
        data.setdefault(cat, []).append([name, url])
        save_data(data)

        context.user_data.pop("add_flow", None)

        await update.message.reply_text(
            f"✅ Eklendi!\n\nKategori: *{cat}*\nİsim: *{name}*\nLink: {url}\n\n/start ile kontrol edebilirsin.",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        return


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("add_flow"):
        context.user_data.pop("add_flow", None)
        await update.message.reply_text("❌ İptal edildi.")
    else:
        await update.message.reply_text("İptal edilecek bir işlem yok.")


# =========================
# ADD (komutlar) — hem tek satır hem wizard
# =========================
async def cmd_addquick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return

    name, url = parse_add_args(update.message.text)
    if name and url:
        if not url_ok(url):
            await update.message.reply_text("❌ Link formatı yanlış (https:// ile başlamalı).")
            return
        data = load_data()
        data.setdefault("quick", []).append([name, url])
        save_data(data)
        await update.message.reply_text("✅ Ana menüye eklendi. /start ile görebilirsin.")
        return

    # args yoksa wizard
    await start_add_flow(update, context, "quick")


async def cmd_addsite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return

    name, url = parse_add_args(update.message.text)
    if name and url:
        if not url_ok(url):
            await update.message.reply_text("❌ Link formatı yanlış (https:// ile başlamalı).")
            return
        data = load_data()
        data.setdefault("sites", []).append([name, url])
        save_data(data)
        await update.message.reply_text("✅ Site eklendi. /list ile kontrol et.")
        return

    await start_add_flow(update, context, "sites")


async def cmd_addchannel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return

    name, url = parse_add_args(update.message.text)
    if name and url:
        if not url_ok(url):
            await update.message.reply_text("❌ Link formatı yanlış (https:// ile başlamalı).")
            return
        data = load_data()
        data.setdefault("channels", []).append([name, url])
        save_data(data)
        await update.message.reply_text("✅ Kanal eklendi. /list ile kontrol et.")
        return

    await start_add_flow(update, context, "channels")


# =========================
# DELETE
# =========================
async def del_generic(update: Update, context: ContextTypes.DEFAULT_TYPE, cat: str, usage: str) -> None:
    if not is_admin(update.effective_user.id):
        return

    parts = (update.message.text or "").strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await update.message.reply_text(f"Kullanım: {usage}")
        return

    idx = int(parts[1]) - 1
    data = load_data()
    items = data.get(cat, [])

    if idx < 0 or idx >= len(items):
        await update.message.reply_text("❌ Geçersiz sıra numarası. /list ile bak.")
        return

    removed = items.pop(idx)
    data[cat] = items
    save_data(data)

    await update.message.reply_text(f"🗑️ Silindi: {removed[0]}")


async def cmd_delquick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await del_generic(update, context, "quick", "/delquick 1")


async def cmd_delsite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await del_generic(update, context, "sites", "/delsite 1")


async def cmd_delchannel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await del_generic(update, context, "channels", "/delchannel 1")


# =========================
# CALLBACK (MENÜ & PANEL)
# =========================
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = load_data()
    channels = data.get("channels", [])
    sites = data.get("sites", [])
    quick = data.get("quick", [])

    if query.data == "menu_channels":
        await smart_edit(
            query,
            "📣 *Telegram Kanallarımız*\nAşağıdan kanala tıkla 👇",
            reply_markup=list_to_keyboard(channels),
        )
        return

    if query.data == "menu_sites":
        await smart_edit(
            query,
            "🌐 *İnternet Sitelerimiz*\nAşağıdan siteye tıkla 👇",
            reply_markup=list_to_keyboard(sites),
        )
        return

    if query.data == "back_home":
        await smart_edit(query, HOME_TEXT, reply_markup=main_menu())
        return

    # -------- PANEL CALLBACKS --------
    if query.data == "back_panel":
        if not is_admin(query.from_user.id):
            return
        await smart_edit(
            query,
            "🛠 *Admin Panel*\nAşağıdan seç 👇",
            reply_markup=admin_panel_menu(),
        )
        return

    if query.data == "admin_list":
        if not is_admin(query.from_user.id):
            return

        text = "📌 *Kayıtlı Linkler*\n\n"

        text += "⚡️ *Ana Menü (Quick):*\n"
        if quick:
            for i, (t, u) in enumerate(quick, start=1):
                text += f"{i}) {t} — {u}\n"
        else:
            text += "_Boş_\n"

        text += "\n📣 *Kanallar:*\n"
        if channels:
            for i, (t, u) in enumerate(channels, start=1):
                text += f"{i}) {t} — {u}\n"
        else:
            text += "_Boş_\n"

        text += "\n🌐 *Siteler:*\n"
        if sites:
            for i, (t, u) in enumerate(sites, start=1):
                text += f"{i}) {t} — {u}\n"
        else:
            text += "_Boş_\n"

        text += "\nSilmek için:\n`/delquick 1`  `/delchannel 1`  `/delsite 1`"

        await smart_edit(query, text, reply_markup=panel_back_menu())
        return

    if query.data == "admin_add_help":
        if not is_admin(query.from_user.id):
            return
        text = (
            "➕ *Ekleme (Wizard)*\n\n"
            "Quick (ana menü):\n"
            "`/addquick`  (sonra isim, sonra link)\n"
            "veya tek satır:\n"
            "`/addquick İsim | https://link`\n\n"
            "Site:\n"
            "`/addsite`  veya  `/addsite İsim | https://link`\n\n"
            "Kanal:\n"
            "`/addchannel`  veya  `/addchannel İsim | https://t.me/kanal`\n\n"
            "İptal:\n"
            "`/cancel`"
        )
        await smart_edit(query, text, reply_markup=panel_back_menu())
        return

    if query.data == "admin_del_help":
        if not is_admin(query.from_user.id):
            return
        text = (
            "➖ *Silme*\n\n"
            "Önce listele:\n`/list`\n\n"
            "Quick sil:\n`/delquick 1`\n"
            "Site sil:\n`/delsite 1`\n"
            "Kanal sil:\n`/delchannel 1`"
        )
        await smart_edit(query, text, reply_markup=panel_back_menu())
        return


# =========================
# MAIN
# =========================
def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN bulunamadı. export BOT_TOKEN=... yapmalısın.")

    ensure_data_file()

    app = Application.builder().token(token).build()

    # UI
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_callback))

    # Utility
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    # Admin panel + list
    app.add_handler(CommandHandler("panel", cmd_panel))
    app.add_handler(CommandHandler("list", cmd_list))

    # Add (wizard + tek satır)
    app.add_handler(CommandHandler("addquick", cmd_addquick))
    app.add_handler(CommandHandler("addsite", cmd_addsite))
    app.add_handler(CommandHandler("addchannel", cmd_addchannel))

    # Delete
    app.add_handler(CommandHandler("delquick", cmd_delquick))
    app.add_handler(CommandHandler("delsite", cmd_delsite))
    app.add_handler(CommandHandler("delchannel", cmd_delchannel))

    # Wizard mesaj yakalama (komut olmayan düz yazılar)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_flow_message))

    print("Bot çalışıyor... Telegram’da /start deneyebilirsin.")
    app.run_polling()


if __name__ == "__main__":
    main()

