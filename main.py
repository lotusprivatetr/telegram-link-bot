import os
import json
import html
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

HOME_TEXT_HTML = (
    "✨ <b>Lotus Private Link Merkezi</b>\n"
    "<i>Kanallarımız ve sitelerimiz tek yerde.</i>\n\n"
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
            "quick": [],
            "channels": DEFAULT_CHANNELS,
            "sites": DEFAULT_SITES,
            "started_users": []  # /start yapan user_id'ler
        }
        save_data(data)

def load_data() -> dict:
    ensure_data_file()
    with DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    data.setdefault("quick", [])
    data.setdefault("channels", [])
    data.setdefault("sites", [])
    data.setdefault("started_users", [])

    return data

def register_started_user(user_id: int) -> None:
    """Kullanıcı /start yaptıysa ID'sini kaydet."""
    data = load_data()
    lst = data.get("started_users", [])

    s = set()
    for x in lst:
        try:
            s.add(int(x))
        except:
            pass

    s.add(int(user_id))
    data["started_users"] = sorted(s)
    save_data(data)


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
# BROADCAST (Hedef: /start yapan herkes)
# =========================
def get_broadcast_user_ids() -> list[int]:
    data = load_data()
    out = []
    for x in data.get("started_users", []):
        try:
            out.append(int(x))
        except:
            pass
    return out

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return

    context.user_data["broadcast_flow"] = {"step": "photo", "file_id": None}

    await update.message.reply_text(
        "📣 <b>Broadcast başlatıldı</b>\n\n"
        "1) Şimdi duyuru <b>fotoğrafını</b> gönder.\n"
        "İptal etmek için: /cancel",
        parse_mode="HTML",
    )

async def handle_broadcast_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    flow = context.user_data.get("broadcast_flow")
    if not flow:
        return

    if not is_admin(update.effective_user.id):
        context.user_data.pop("broadcast_flow", None)
        return

    if flow.get("step") != "photo":
        return

    if not update.message.photo:
        await update.message.reply_text("❌ Fotoğraf gelmedi. Lütfen fotoğraf gönder.")
        return

    file_id = update.message.photo[-1].file_id
    flow["file_id"] = file_id
    flow["step"] = "caption"

    await update.message.reply_text(
        "2) Şimdi bu fotoğrafın <b>açıklamasını</b> yaz (caption).\n"
        "İptal: /cancel",
        parse_mode="HTML",
    )


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

def main_menu() -> InlineKeyboardMarkup:
    data = load_data()
    quick = data.get("quick", [])

    keyboard = []
    keyboard.append([InlineKeyboardButton("🚀 HIZLI REZERVASYON", url=FAST_RESERVATION_URL)])

    keyboard += build_2col_rows(quick)

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
        [InlineKeyboardButton("➕ Ekleme (Yardım)", callback_data="admin_add_help")],
        [InlineKeyboardButton("➖ Silme (Yardım)", callback_data="admin_del_help")],
    ]
    return InlineKeyboardMarkup(keyboard)

def panel_back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Panele Dön", callback_data="back_panel")]])

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
# ADD PARSE / VALIDATION
# =========================
def parse_add_args(text: str) -> Tuple[Optional[str], Optional[str]]:
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

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Senin Telegram ID: {update.effective_user.id}")

async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "🛠 <b>Admin Panel</b>\nAşağıdan seç 👇",
        reply_markup=admin_panel_menu(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return

    data = load_data()
    quick = data.get("quick", [])
    channels = data.get("channels", [])
    sites = data.get("sites", [])
    started_count = len(data.get("started_users", []))

    def fmt(items):
        if not items:
            return "<i>Boş</i>\n"
        out = ""
        for i, (t, u) in enumerate(items, start=1):
            out += f"{i}) {html.escape(t)} — {html.escape(u)}\n"
        return out

    text = "📌 <b>Kayıtlı Linkler</b>\n\n"
    text += f"👥 <b>/start yapan kişi:</b> {started_count}\n\n"
    text += "⚡️ <b>Ana Menü (Quick):</b>\n" + fmt(quick) + "\n"
    text += "📣 <b>Kanallar:</b>\n" + fmt(channels) + "\n"
    text += "🌐 <b>Siteler:</b>\n" + fmt(sites) + "\n"
    text += "Silmek için:\n<code>/delquick 1</code>  <code>/delchannel 1</code>  <code>/delsite 1</code>"

    await update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cancelled = False

    if context.user_data.get("add_flow"):
        context.user_data.pop("add_flow", None)
        cancelled = True

    if context.user_data.get("broadcast_flow"):
        context.user_data.pop("broadcast_flow", None)
        cancelled = True

    if cancelled:
        await update.message.reply_text("❌ İptal edildi.")
    else:
        await update.message.reply_text("İptal edilecek bir işlem yok.")


# =========================
# ADD WIZARD (quick/site/channel)
# =========================
async def start_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, cat: str) -> None:
    if not is_admin(update.effective_user.id):
        return
    context.user_data["add_flow"] = {"cat": cat, "step": "name", "name": ""}
    await update.message.reply_text(
        "✅ <b>Ekleme başlatıldı</b>\n\n1) Link adı yaz (butonda gözükecek isim):",
        parse_mode="HTML",
    )

async def handle_text_flows(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if not text:
        return

    # ---- BROADCAST caption ----
    bflow = context.user_data.get("broadcast_flow")
    if bflow and bflow.get("step") == "caption":
        if not is_admin(update.effective_user.id):
            context.user_data.pop("broadcast_flow", None)
            return

        caption = text
        file_id = bflow.get("file_id")
        if not file_id:
            context.user_data.pop("broadcast_flow", None)
            await update.message.reply_text("❌ Fotoğraf bulunamadı. /broadcast ile yeniden başlat.")
            return

        user_ids = get_broadcast_user_ids()
        if not user_ids:
            context.user_data.pop("broadcast_flow", None)
            await update.message.reply_text("⚠️ Henüz hedef kitle yok. (Kimse /start yapmamış)")
            return

        ok, fail = 0, 0
        for uid in user_ids:
            try:
                await context.bot.send_photo(chat_id=uid, photo=file_id, caption=caption)
                ok += 1
            except Exception:
                fail += 1

        context.user_data.pop("broadcast_flow", None)
        await update.message.reply_text(f"✅ Broadcast bitti.\nGönderildi: {ok}\nHata: {fail}")
        return

    # ---- ADD wizard ----
    flow = context.user_data.get("add_flow")
    if not flow:
        return

    if not is_admin(update.effective_user.id):
        context.user_data.pop("add_flow", None)
        return

    if flow.get("step") == "name":
        flow["name"] = text
        flow["step"] = "url"
        await update.message.reply_text("2) Şimdi linki yapıştır (https://...):")
        return

    if flow.get("step") == "url":
        url = text
        if not url_ok(url):
            await update.message.reply_text("❌ Link formatı yanlış. https:// ile başlayan link gönder.")
            return

        cat = flow.get("cat")
        name = (flow.get("name") or "").strip()
        if not name:
            context.user_data.pop("add_flow", None)
            await update.message.reply_text("❌ İsim boş. Tekrar dene.")
            return

        data = load_data()
        data.setdefault(cat, []).append([name, url])
        save_data(data)
        context.user_data.pop("add_flow", None)

        await update.message.reply_text(
            f"✅ Eklendi!\nKategori: {cat}\nİsim: {name}\nLink: {url}\n\n/start ile kontrol edebilirsin.",
            disable_web_page_preview=True,
        )
        return


# =========================
# ADD / DELETE KOMUTLARI
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

    if query.data == "menu_channels":
        await smart_edit(
            query,
            "📣 <b>Telegram Kanallarımız</b>\nAşağıdan kanala tıkla 👇",
            reply_markup=list_to_keyboard(channels),
        )
        return

    if query.data == "menu_sites":
        await smart_edit(
            query,
            "🌐 <b>İnternet Sitelerimiz</b>\nAşağıdan siteye tıkla 👇",
            reply_markup=list_to_keyboard(sites),
        )
        return

    if query.data == "back_home":
        await smart_edit(query, HOME_TEXT_HTML, reply_markup=main_menu())
        return

    if query.data == "back_panel":
        if not is_admin(query.from_user.id):
            return
        await smart_edit(
            query,
            "🛠 <b>Admin Panel</b>\nAşağıdan seç 👇",
            reply_markup=admin_panel_menu(),
        )
        return

    if query.data == "admin_list":
        if not is_admin(query.from_user.id):
            return

        quick = data.get("quick", [])
        channels2 = data.get("channels", [])
        sites2 = data.get("sites", [])
        started_count = len(data.get("started_users", []))

        def fmt(items):
            if not items:
                return "<i>Boş</i>\n"
            out = ""
            for i, (t, u) in enumerate(items, start=1):
                out += f"{i}) {html.escape(t)} — {html.escape(u)}\n"
            return out

        text = "📌 <b>Kayıtlı Linkler</b>\n\n"
        text += f"👥 <b>/start yapan kişi:</b> {started_count}\n\n"
        text += "⚡️ <b>Ana Menü (Quick):</b>\n" + fmt(quick) + "\n"
        text += "📣 <b>Kanallar:</b>\n" + fmt(channels2) + "\n"
        text += "🌐 <b>Siteler:</b>\n" + fmt(sites2) + "\n"
        text += "Silmek için:\n<code>/delquick 1</code>  <code>/delchannel 1</code>  <code>/delsite 1</code>"

        await smart_edit(query, text, reply_markup=panel_back_menu())
        return

    if query.data == "admin_add_help":
        if not is_admin(query.from_user.id):
            return
        text = (
            "➕ <b>Ekleme</b>\n\n"
            "Quick:\n<code>/addquick</code> veya <code>/addquick İsim | https://link</code>\n\n"
            "Site:\n<code>/addsite</code> veya <code>/addsite İsim | https://link</code>\n\n"
            "Kanal:\n<code>/addchannel</code> veya <code>/addchannel İsim | https://t.me/kanal</code>\n\n"
            "İptal:\n<code>/cancel</code>"
        )
        await smart_edit(query, text, reply_markup=panel_back_menu())
        return

    if query.data == "admin_del_help":
        if not is_admin(query.from_user.id):
            return
        text = (
            "➖ <b>Silme</b>\n\n"
            "Önce:\n<code>/list</code>\n\n"
            "Quick:\n<code>/delquick 1</code>\n"
            "Site:\n<code>/delsite 1</code>\n"
            "Kanal:\n<code>/delchannel 1</code>"
        )
        await smart_edit(query, text, reply_markup=panel_back_menu())
        return


# =========================
# MAIN
# =========================
def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN bulunamadı. Render ENV'e BOT_TOKEN girmelisin.")

    ensure_data_file()

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_callback))

    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    app.add_handler(CommandHandler("panel", cmd_panel))
    app.add_handler(CommandHandler("list", cmd_list))

    app.add_handler(CommandHandler("addquick", cmd_addquick))
    app.add_handler(CommandHandler("addsite", cmd_addsite))
    app.add_handler(CommandHandler("addchannel", cmd_addchannel))

    app.add_handler(CommandHandler("delquick", cmd_delquick))
    app.add_handler(CommandHandler("delsite", cmd_delsite))
    app.add_handler(CommandHandler("delchannel", cmd_delchannel))

    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(MessageHandler(filters.PHOTO, handle_broadcast_photo))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_flows))

    print("Bot çalışıyor... Telegram’da /start deneyebilirsin.")
    app.run_polling()

if __name__ == "__main__":
    main()

