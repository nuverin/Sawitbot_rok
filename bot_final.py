"""
RoK Kingdom Seeds Bot - Telegram Bot
Data source: heroscroll.com/rok/seeds
"""

import os
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ─── Konfigurasi ────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8991221360:AAE-7K2ZKHIZG49FqvViFqeCeK0pDvf3VWY")
API_BASE  = "https://heroscroll.com/api"   # endpoint internal (reverse engineered)
HEADERS   = {
    "User-Agent": "Mozilla/5.0 (compatible; RoKBot/1.0)",
    "Accept": "application/json",
    "Referer": "https://heroscroll.com/rok/seeds",
}

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ─── State untuk ConversationHandler ────────────────────────────────────────
WAITING_KID   = 1   # menunggu user ketik Kingdom ID
WAITING_RANGE = 2   # menunggu input range filter


# ════════════════════════════════════════════════════════════════════════════
#  HELPER: ambil data dari heroscroll
# ════════════════════════════════════════════════════════════════════════════

async def fetch_kingdoms(
    page: int = 1,
    limit: int = 10,
    kingdom_id: int | None = None,
    kid_min: int | None = None,
    kid_max: int | None = None,
    power_min: int | None = None,
    power_max: int | None = None,
    kill_min: int | None = None,
    kill_max: int | None = None,
    dead_min: int | None = None,
    dead_max: int | None = None,
    kvk_status: str | None = None,
    kvk_season: str | None = None,
    kvk_story: str | None = None,
    sort_by: str = "rank",
    sort_dir: str = "asc",
) -> dict:
    """
    Ambil data kingdom dari heroscroll API.
    Catatan: heroscroll adalah SPA (JavaScript-rendered). Bot ini
    menggunakan endpoint JSON internal yang ditemukan via DevTools.
    Jika endpoint berubah, lihat bagian CATATAN PENGEMBANG di README.
    """
    params: dict = {
        "page": page,
        "limit": limit,
        "sortBy": sort_by,
        "sortDir": sort_dir,
    }
    if kingdom_id:  params["kingdomId"] = kingdom_id
    if kid_min:     params["kidMin"]    = kid_min
    if kid_max:     params["kidMax"]    = kid_max
    if power_min:   params["powerMin"]  = power_min
    if power_max:   params["powerMax"]  = power_max
    if kill_min:    params["killMin"]   = kill_min
    if kill_max:    params["killMax"]   = kill_max
    if dead_min:    params["deadMin"]   = dead_min
    if dead_max:    params["deadMax"]   = dead_max
    if kvk_status:  params["kvkStatus"] = kvk_status
    if kvk_season:  params["kvkSeason"] = kvk_season
    if kvk_story:   params["kvkStory"]  = kvk_story

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{API_BASE}/rok/seeds", params=params, headers=HEADERS)
        resp.raise_for_status()
        return resp.json()


def fmt_num(n) -> str:
    """Format angka besar: 1234567 → 1.23M"""
    if n is None:
        return "N/A"
    n = int(n)
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def kingdom_card(k: dict) -> str:
    """Render satu Kingdom jadi teks Telegram (Markdown)."""
    return (
        f"👑 *Kingdom #{k.get('kingdomId', '?')}*\n"
        f"🏆 Rank: `{k.get('rank', 'N/A')}`\n"
        f"⚡ Power: `{fmt_num(k.get('power'))}`\n"
        f"🗡️ Kill Points: `{fmt_num(k.get('killPoints'))}`\n"
        f"💀 Deads: `{fmt_num(k.get('deads'))}`\n"
        f"🌐 KvK Status: `{k.get('kvkStatus', 'N/A')}`\n"
        f"📅 Season: `{k.get('kvkSeason', 'N/A')}`\n"
        f"📖 Story: `{k.get('kvkStory', 'N/A')}`\n"
    )


# ════════════════════════════════════════════════════════════════════════════
#  COMMAND HANDLERS
# ════════════════════════════════════════════════════════════════════════════

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🔍 Cari Kingdom by ID", callback_data="menu_search")],
        [InlineKeyboardButton("🏆 Top Kingdom",         callback_data="menu_top")],
        [InlineKeyboardButton("⚙️ Filter Kingdom",     callback_data="menu_filter")],
        [InlineKeyboardButton("❓ Bantuan",             callback_data="menu_help")],
    ]
    await update.message.reply_text(
        "🏰 *RoK Kingdom Seeds Bot*\n\n"
        "Selamat datang! Bot ini mengambil data Kingdom langsung dari "
        "[HeroScrolls](https://heroscroll.com/rok/seeds).\n\n"
        "Pilih menu di bawah:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = (
        "📖 *Cara pakai bot ini:*\n\n"
        "/start — Menu utama\n"
        "/kingdom `<ID>` — Info kingdom tertentu, cth: `/kingdom 1001`\n"
        "/top — Top 10 kingdom berdasarkan rank\n"
        "/filter — Filter kingdom dengan berbagai parameter\n"
        "/help — Tampilkan bantuan ini\n\n"
        "💡 _Sumber data: heroscroll.com/rok/seeds_"
    )
    await update.message.reply_text(txt, parse_mode="Markdown")


# ─── /kingdom <ID> ──────────────────────────────────────────────────────────

async def kingdom_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args or not args[0].isdigit():
        await update.message.reply_text(
            "⚠️ Masukkan ID Kingdom yang valid.\nContoh: `/kingdom 1001`",
            parse_mode="Markdown",
        )
        return

    kid = int(args[0])
    msg = await update.message.reply_text(f"⏳ Mencari Kingdom #{kid}...")
    try:
        data = await fetch_kingdoms(kingdom_id=kid, limit=1)
        items = data.get("data") or data.get("kingdoms") or []
        if not items:
            await msg.edit_text(f"❌ Kingdom #{kid} tidak ditemukan.")
            return
        await msg.edit_text(kingdom_card(items[0]), parse_mode="Markdown")
    except Exception as e:
        log.error(e)
        await msg.edit_text(
            f"❌ Gagal mengambil data. Kemungkinan API heroscroll sedang berubah.\n"
            f"Kunjungi langsung: https://heroscroll.com/rok/seeds"
        )


# ─── /top ───────────────────────────────────────────────────────────────────

async def top_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Mengambil Top 10 Kingdom...")
    try:
        data = await fetch_kingdoms(limit=10, sort_by="rank", sort_dir="asc")
        items = data.get("data") or data.get("kingdoms") or []
        if not items:
            await msg.edit_text("❌ Tidak ada data yang bisa diambil saat ini.")
            return
        lines = [f"🏆 *Top {len(items)} Kingdom RoK*\n"]
        for k in items:
            lines.append(
                f"#{k.get('rank','?')} — Kingdom `{k.get('kingdomId','?')}` "
                f"| Power: `{fmt_num(k.get('power'))}`"
            )
        await msg.edit_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        log.error(e)
        await msg.edit_text("❌ Gagal mengambil data Top Kingdom.")


# ─── /filter — ConversationHandler ─────────────────────────────────────────

async def filter_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Mulai alur filter."""
    kb = [
        [InlineKeyboardButton("⚡ Power Range",      callback_data="f_power")],
        [InlineKeyboardButton("🗡️ Kill Points Range", callback_data="f_kill")],
        [InlineKeyboardButton("💀 Deads Range",      callback_data="f_dead")],
        [InlineKeyboardButton("🌐 KvK Status",       callback_data="f_kvkstatus")],
        [InlineKeyboardButton("📅 KvK Season",       callback_data="f_kvkseason")],
        [InlineKeyboardButton("❌ Batal",            callback_data="f_cancel")],
    ]
    # reset filter ctx
    ctx.user_data["filters"] = {}
    await update.message.reply_text(
        "⚙️ *Filter Kingdom*\n\nPilih parameter filter:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )
    return WAITING_RANGE


async def filter_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    prompts = {
        "f_power":     ("power",     "💪 Ketik range Power (min-max)\nContoh: `10000000-500000000`"),
        "f_kill":      ("killPoints","🗡️ Ketik range Kill Points (min-max)\nContoh: `5500-5031200000000`"),
        "f_dead":      ("deads",     "💀 Ketik range Deads (min-max)\nContoh: `3900-13600000000`"),
        "f_kvkstatus": ("kvkStatus", "🌐 Ketik KvK Status\nContoh: `active` atau `inactive`"),
        "f_kvkseason": ("kvkSeason", "📅 Ketik KvK Season\nContoh: `Season 1`"),
    }

    if data == "f_cancel":
        await query.edit_message_text("❌ Filter dibatalkan.")
        return ConversationHandler.END

    if data == "f_apply":
        await apply_filter(update, ctx)
        return ConversationHandler.END

    if data in prompts:
        key, prompt = prompts[data]
        ctx.user_data["filter_key"] = key
        await query.edit_message_text(prompt, parse_mode="Markdown")
        return WAITING_RANGE

    return WAITING_RANGE


async def filter_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Terima input teks untuk filter."""
    text = update.message.text.strip()
    key  = ctx.user_data.get("filter_key")

    if key in ("power", "killPoints", "deads"):
        parts = text.replace(" ", "").split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            ctx.user_data["filters"][f"{key}Min"] = int(parts[0])
            ctx.user_data["filters"][f"{key}Max"] = int(parts[1])
            await update.message.reply_text(f"✅ Filter `{key}` disimpan: {parts[0]} – {parts[1]}")
        else:
            await update.message.reply_text("⚠️ Format salah. Gunakan: `min-max`", parse_mode="Markdown")
    elif key:
        ctx.user_data["filters"][key] = text
        await update.message.reply_text(f"✅ Filter `{key}` disimpan: {text}")

    kb = [
        [InlineKeyboardButton("➕ Tambah filter lagi", callback_data="f_more")],
        [InlineKeyboardButton("🔎 Terapkan Filter",    callback_data="f_apply")],
        [InlineKeyboardButton("❌ Batal",              callback_data="f_cancel")],
    ]
    saved = ctx.user_data.get("filters", {})
    summary = "\n".join(f"• `{k}` = `{v}`" for k, v in saved.items()) or "_Belum ada_"
    await update.message.reply_text(
        f"📋 *Filter tersimpan:*\n{summary}",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )
    return WAITING_RANGE


async def apply_filter(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Eksekusi pencarian dengan filter yang sudah dikumpulkan."""
    f = ctx.user_data.get("filters", {})
    query = update.callback_query
    await query.edit_message_text("⏳ Mencari dengan filter...")
    try:
        data = await fetch_kingdoms(
            limit=10,
            power_min=f.get("powerMin"),
            power_max=f.get("powerMax"),
            kill_min=f.get("killPointsMin"),
            kill_max=f.get("killPointsMax"),
            dead_min=f.get("deadsMin"),
            dead_max=f.get("deadsMax"),
            kvk_status=f.get("kvkStatus"),
            kvk_season=f.get("kvkSeason"),
        )
        items = data.get("data") or data.get("kingdoms") or []
        if not items:
            await query.edit_message_text("❌ Tidak ada kingdom yang cocok dengan filter ini.")
            return
        lines = [f"🔎 *Hasil Filter ({len(items)} kingdom):*\n"]
        for k in items:
            lines.append(
                f"• Kingdom `{k.get('kingdomId','?')}` "
                f"| Rank `{k.get('rank','?')}` "
                f"| Power `{fmt_num(k.get('power'))}`"
            )
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        log.error(e)
        await query.edit_message_text("❌ Gagal menerapkan filter. Silakan coba lagi.")


# ─── Callback menu utama ────────────────────────────────────────────────────

async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_search":
        await query.edit_message_text(
            "🔍 Ketik ID Kingdom yang ingin kamu cari.\nContoh: `/kingdom 1001`",
            parse_mode="Markdown",
        )
    elif query.data == "menu_top":
        await query.edit_message_text("⏳ Mengambil Top 10...")
        try:
            data = await fetch_kingdoms(limit=10, sort_by="rank", sort_dir="asc")
            items = data.get("data") or data.get("kingdoms") or []
            lines = [f"🏆 *Top {len(items)} Kingdom RoK*\n"]
            for k in items:
                lines.append(
                    f"#{k.get('rank','?')} — Kingdom `{k.get('kingdomId','?')}` "
                    f"| Power: `{fmt_num(k.get('power'))}`"
                )
            await query.edit_message_text("\n".join(lines), parse_mode="Markdown")
        except Exception as e:
            log.error(e)
            await query.edit_message_text("❌ Gagal mengambil data Top Kingdom.")
    elif query.data == "menu_filter":
        await query.edit_message_text(
            "⚙️ Gunakan command `/filter` untuk membuka menu filter interaktif.",
            parse_mode="Markdown",
        )
    elif query.data == "menu_help":
        txt = (
            "📖 *Panduan Bot:*\n\n"
            "/start — Menu utama\n"
            "/kingdom `<ID>` — Info kingdom\n"
            "/top — Top 10 kingdom\n"
            "/filter — Filter interaktif\n"
            "/help — Bantuan\n\n"
            "🌐 _Data dari heroscroll.com_"
        )
        await query.edit_message_text(txt, parse_mode="Markdown")


# ════════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Filter ConversationHandler
    filter_conv = ConversationHandler(
        entry_points=[CommandHandler("filter", filter_start)],
        states={
            WAITING_RANGE: [
                CallbackQueryHandler(filter_callback, pattern="^f_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, filter_input),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("help",    help_cmd))
    app.add_handler(CommandHandler("kingdom", kingdom_cmd))
    app.add_handler(CommandHandler("top",     top_cmd))
    app.add_handler(filter_conv)
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))

    log.info("🤖 Bot RoK berjalan...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
