"""
@Sawitrok_bot — RoK Kingdom Seeds Bot
Fitur: Stats/Graph foto, Seed Kingdom data, Menu Developer
"""

import os, io, json, logging, csv, re
from datetime import datetime
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.ticker as mticker

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler,
)

# ── Config ──────────────────────────────────────────────────────────────────
BOT_TOKEN      = os.getenv("BOT_TOKEN", "8991221360:AAE-7K2ZKHIZG49FqvViFqeCeK0pDvf3VWY")
DEVELOPER_IDS  = {6132556648}          # tambah ID lain jika perlu
DEV_PASSWORD   = os.getenv("DEV_PASSWORD", "sawit2024")   # ganti via env var
DATA_FILE      = Path("seed_data.json")

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# States
ASK_DEV_PASS, WAIT_CSV, WAIT_UPDATE_KD, WAIT_UPDATE_FIELD = range(4)

# ── Data store ───────────────────────────────────────────────────────────────
def load_data() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {"kingdoms": {}, "last_update": None, "history": []}

def save_data(d: dict):
    DATA_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2))

def get_df() -> pd.DataFrame:
    d = load_data()
    rows = list(d["kingdoms"].values())
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)

# ── Helpers ──────────────────────────────────────────────────────────────────
def fmt(n, suffix="") -> str:
    try:
        n = float(str(n).replace(",",""))
    except:
        return str(n)
    if n >= 1e12: return f"{n/1e12:.2f}T{suffix}"
    if n >= 1e9:  return f"{n/1e9:.2f}B{suffix}"
    if n >= 1e6:  return f"{n/1e6:.2f}M{suffix}"
    if n >= 1e3:  return f"{n/1e3:.1f}K{suffix}"
    return str(int(n))

def is_dev(uid: int, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    return uid in DEVELOPER_IDS or ctx.user_data.get("dev_auth")

def group_color(g):
    return {"A":"#FFD700","B":"#C0C0C0","C":"#CD7F32","D":"#78C8FF"}.get(str(g),"#AAAAAA")

# ── CSV importer ─────────────────────────────────────────────────────────────
def import_csv(text: str) -> dict:
    """Parse CSV text → dict keyed by kingdom id (str)"""
    reader = csv.DictReader(io.StringIO(text))
    kingdoms = {}
    for row in reader:
        kid = str(row.get("Kingdom","")).strip()
        if not kid: continue
        kingdoms[kid] = {
            "rank":       int(row.get("Rank",0) or 0),
            "kingdom":    int(kid),
            "group":      row.get("Group","").strip(),
            "kvk":        row.get("KvK","").strip(),
            "kvk_start":  (row.get("KvK Start","") or "")[:10],
            "kvk_end":    (row.get("KvK End","") or "")[:10],
            "power":      int(float(row.get("Power",0) or 0)),
            "power_cap":  int(float(row.get("Power Capped",0) or 0)),
            "kp":         int(float(str(row.get("KP",0) or 0).replace("E+","e+")
                              .replace(",","")) if row.get("KP") else 0),
            "dead":       int(float(row.get("Dead",0) or 0)),
            "ch25":       int(row.get("CH25",0) or 0),
            "updated_at": datetime.utcnow().isoformat()[:10],
        }
    return kingdoms

# ════════════════════════════════════════════════════════════════════════════
# GRAPH GENERATORS
# ════════════════════════════════════════════════════════════════════════════

DARK = "#0f1117"
CARD = "#1a1d27"
ACCENT = "#7c5cbf"

def apply_dark(fig, axes):
    fig.patch.set_facecolor(DARK)
    for ax in (axes if hasattr(axes,'__iter__') else [axes]):
        ax.set_facecolor(CARD)
        ax.tick_params(colors="#cccccc", labelsize=8)
        ax.xaxis.label.set_color("#cccccc")
        ax.yaxis.label.set_color("#cccccc")
        ax.title.set_color("#ffffff")
        for spine in ax.spines.values():
            spine.set_edgecolor("#333344")

def buf(fig) -> io.BytesIO:
    b = io.BytesIO()
    fig.savefig(b, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    b.seek(0)
    return b

# ── Graph 1: Top 20 Power ────────────────────────────────────────────────────
def graph_top_power(df: pd.DataFrame, n=20) -> io.BytesIO:
    top = df.nlargest(n, "power")[["kingdom","group","power"]].copy()
    top = top.sort_values("power")
    colors = [group_color(g) for g in top["group"]]
    fig, ax = plt.subplots(figsize=(9,6))
    apply_dark(fig, ax)
    bars = ax.barh(top["kingdom"].astype(str), top["power"]/1e9, color=colors, edgecolor="#00000044", linewidth=0.5)
    ax.set_xlabel("Power (Billions)")
    ax.set_title(f"🏆 Top {n} Kingdoms by Power", fontweight="bold", fontsize=13)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.0f}B"))
    for bar, val in zip(bars, top["power"]):
        ax.text(bar.get_width()+0.1, bar.get_y()+bar.get_height()/2,
                fmt(val), va="center", ha="left", color="#dddddd", fontsize=7)
    patches=[mpatches.Patch(color=group_color(g),label=f"Group {g}") for g in ["A","B","C","D"]]
    ax.legend(handles=patches, loc="lower right", fontsize=8,
              facecolor=CARD, edgecolor="#444", labelcolor="#ccc")
    fig.tight_layout()
    return buf(fig)

# ── Graph 2: Top 20 KP ───────────────────────────────────────────────────────
def graph_top_kp(df: pd.DataFrame, n=20) -> io.BytesIO:
    top = df.nlargest(n, "kp")[["kingdom","group","kp"]].copy()
    top = top.sort_values("kp")
    colors = [group_color(g) for g in top["group"]]
    fig, ax = plt.subplots(figsize=(9,6))
    apply_dark(fig, ax)
    bars = ax.barh(top["kingdom"].astype(str), top["kp"]/1e9, color=colors, edgecolor="#00000044", linewidth=0.5)
    ax.set_xlabel("Kill Points (Billions)")
    ax.set_title(f"⚔️ Top {n} Kingdoms by Kill Points", fontweight="bold", fontsize=13)
    for bar, val in zip(bars, top["kp"]):
        ax.text(bar.get_width()+0.05, bar.get_y()+bar.get_height()/2,
                fmt(val), va="center", ha="left", color="#dddddd", fontsize=7)
    patches=[mpatches.Patch(color=group_color(g),label=f"Group {g}") for g in ["A","B","C","D"]]
    ax.legend(handles=patches, loc="lower right", fontsize=8,
              facecolor=CARD, edgecolor="#444", labelcolor="#ccc")
    fig.tight_layout()
    return buf(fig)

# ── Graph 3: Group Distribution ──────────────────────────────────────────────
def graph_group_dist(df: pd.DataFrame) -> io.BytesIO:
    grp = df.groupby("group").agg(
        count=("kingdom","count"),
        avg_power=("power","mean"),
        avg_kp=("kp","mean"),
    ).reset_index()
    fig, axes = plt.subplots(1, 3, figsize=(13,5))
    apply_dark(fig, axes)

    colors = [group_color(g) for g in grp["group"]]
    # pie
    axes[0].pie(grp["count"], labels=[f"Group {g}\n({c})" for g,c in zip(grp["group"],grp["count"])],
                colors=colors, autopct="%1.0f%%", textprops={"color":"#ccc","fontsize":9},
                wedgeprops={"edgecolor":"#0f1117","linewidth":1.5})
    axes[0].set_title("Kingdom Count per Group", fontsize=11)

    axes[1].bar(grp["group"], grp["avg_power"]/1e9, color=colors, edgecolor="#00000033")
    axes[1].set_title("Avg Power per Group", fontsize=11)
    axes[1].set_ylabel("Power (B)")
    axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_:f"{x:.0f}B"))

    axes[2].bar(grp["group"], grp["avg_kp"]/1e9, color=colors, edgecolor="#00000033")
    axes[2].set_title("Avg Kill Points per Group", fontsize=11)
    axes[2].set_ylabel("KP (B)")
    axes[2].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_:f"{x:.0f}B"))

    fig.suptitle("📊 Group Statistics Overview", fontsize=14, color="white", fontweight="bold")
    fig.tight_layout()
    return buf(fig)

# ── Graph 4: Power vs KP scatter ─────────────────────────────────────────────
def graph_scatter(df: pd.DataFrame) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(9,6))
    apply_dark(fig, ax)
    for g in ["A","B","C","D"]:
        sub = df[df["group"]==g]
        ax.scatter(sub["power"]/1e9, sub["kp"]/1e9,
                   c=group_color(g), label=f"Group {g}", alpha=0.75,
                   edgecolors="#ffffff22", linewidths=0.4, s=50)
    ax.set_xlabel("Power (B)")
    ax.set_ylabel("Kill Points (B)")
    ax.set_title("⚡ Power vs Kill Points", fontweight="bold", fontsize=13)
    ax.legend(facecolor=CARD, edgecolor="#444", labelcolor="#ccc", fontsize=9)
    fig.tight_layout()
    return buf(fig)

# ── Graph 5: Kingdom stats card ───────────────────────────────────────────────
def graph_kingdom_card(kd: dict) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(7,4.5))
    apply_dark(fig, ax)
    ax.axis("off")
    gc = group_color(kd.get("group",""))
    fig.patch.set_facecolor(DARK)

    # header band
    ax.add_patch(plt.Rectangle((0,0.82),1,0.18, transform=ax.transAxes,
                                color=gc, zorder=0, clip_on=False))
    ax.text(0.5, 0.91, f"Kingdom #{kd['kingdom']}", transform=ax.transAxes,
            ha="center", va="center", fontsize=17, fontweight="bold", color="#111")
    ax.text(0.5, 0.83, f"Group {kd.get('group','?')}  •  Rank #{kd.get('rank','?')}",
            transform=ax.transAxes, ha="center", va="center", fontsize=10, color="#333")

    stats = [
        ("⚡ Power",      fmt(kd.get("power",0))),
        ("🗡️ Kill Points", fmt(kd.get("kp",0))),
        ("💀 Deads",       fmt(kd.get("dead",0))),
        ("🏰 CH25",        str(kd.get("ch25","?"))),
        ("🌐 KvK",         kd.get("kvk","N/A") or "N/A"),
        ("📅 KvK End",     kd.get("kvk_end","N/A") or "N/A"),
    ]
    for i,(label,val) in enumerate(stats):
        y = 0.72 - i*0.115
        ax.text(0.07, y, label, transform=ax.transAxes,
                fontsize=11, color="#aaaaaa")
        ax.text(0.93, y, val, transform=ax.transAxes,
                fontsize=11, color="#ffffff", ha="right", fontweight="bold")
        ax.axhline(y=y-0.03, xmin=0.05, xmax=0.95, color="#333344",
                   linewidth=0.6, transform=ax.transAxes)

    ax.text(0.5, 0.02, f"Updated: {kd.get('updated_at','?')}  •  @Sawitrok_bot",
            transform=ax.transAxes, ha="center", va="bottom",
            fontsize=7, color="#555566")
    fig.tight_layout(pad=0.3)
    return buf(fig)

# ════════════════════════════════════════════════════════════════════════════
# HANDLERS
# ════════════════════════════════════════════════════════════════════════════

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load_data()
    total = len(d["kingdoms"])
    last  = d.get("last_update","Belum ada data")
    kb = [
        [InlineKeyboardButton("🔍 Cari Kingdom",   callback_data="menu_search"),
         InlineKeyboardButton("📊 Stats & Graph",  callback_data="menu_graph")],
        [InlineKeyboardButton("🏆 Top Kingdom",    callback_data="menu_top"),
         InlineKeyboardButton("🌐 Seed Kingdoms",  callback_data="menu_seed")],
        [InlineKeyboardButton("⚙️ Developer",      callback_data="menu_dev")],
    ]
    await update.message.reply_text(
        f"🏰 *RoK Kingdom Seeds Bot*\n\n"
        f"📦 Data: *{total}* kingdoms\n"
        f"🕒 Update terakhir: `{last}`\n\n"
        "Pilih menu:",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

# ── Kingdom search ────────────────────────────────────────────────────────────
async def kingdom_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text("Contoh: `/kingdom 3908`", parse_mode="Markdown")
        return
    kid = args[0].strip()
    d = load_data()
    kd = d["kingdoms"].get(kid)
    if not kd:
        await update.message.reply_text(f"❌ Kingdom #{kid} tidak ditemukan dalam data.")
        return
    img = graph_kingdom_card(kd)
    await update.message.reply_photo(photo=img, caption=f"Kingdom #{kid} | Rank #{kd['rank']}")

# ── Top command ───────────────────────────────────────────────────────────────
async def top_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    df = get_df()
    if df.empty:
        await update.message.reply_text("❌ Belum ada data. Developer perlu upload CSV dulu.")
        return
    msg = await update.message.reply_text("⏳ Membuat grafik Top 20...")
    img = graph_top_power(df)
    await update.message.reply_photo(photo=img, caption="🏆 Top 20 Kingdoms by Power")
    await msg.delete()

# ── Stats/Graph menu ──────────────────────────────────────────────────────────
async def graph_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🏆 Top 20 Power",    callback_data="graph_power")],
        [InlineKeyboardButton("⚔️ Top 20 Kill Points", callback_data="graph_kp")],
        [InlineKeyboardButton("📊 Group Overview",   callback_data="graph_group")],
        [InlineKeyboardButton("⚡ Power vs KP",      callback_data="graph_scatter")],
        [InlineKeyboardButton("« Kembali",           callback_data="menu_main")],
    ]
    txt = "📊 *Pilih grafik yang ingin ditampilkan:*"
    if update.callback_query:
        await update.callback_query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# ── Seed overview ─────────────────────────────────────────────────────────────
async def seed_overview(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    df = get_df()
    q = update.callback_query
    if df.empty:
        await q.edit_message_text("❌ Belum ada data seed. Hubungi developer.")
        return
    grp = df.groupby("group").agg(count=("kingdom","count"),
        avg_power=("power","mean"), avg_kp=("kp","mean")).reset_index()
    lines = ["🌐 *Seed Kingdom Overview*\n"]
    for _, r in grp.iterrows():
        lines.append(
            f"*Group {r['group']}* — {int(r['count'])} kingdoms\n"
            f"  Avg Power: `{fmt(r['avg_power'])}` | Avg KP: `{fmt(r['avg_kp'])}`"
        )
    d = load_data()
    lines.append(f"\n📦 Total: *{len(d['kingdoms'])}* kingdoms")
    lines.append(f"🕒 Update: `{d.get('last_update','?')}`")
    kb = [[InlineKeyboardButton("📊 Lihat Graph Group", callback_data="graph_group"),
           InlineKeyboardButton("« Kembali", callback_data="menu_main")]]
    await q.edit_message_text("\n".join(lines), parse_mode="Markdown",
                               reply_markup=InlineKeyboardMarkup(kb))

# ════════════════════════════════════════════════════════════════════════════
# DEVELOPER MENU
# ════════════════════════════════════════════════════════════════════════════

async def dev_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    q   = update.callback_query
    if not is_dev(uid, ctx):
        await q.answer("🔒 Akses ditolak.", show_alert=True)
        await q.edit_message_text(
            "🔒 *Menu Developer*\n\nMasukkan password developer:",
            parse_mode="Markdown"
        )
        ctx.user_data["awaiting_dev_pass"] = True
        return

    await show_dev_panel(q)

async def show_dev_panel(q):
    kb = [
        [InlineKeyboardButton("📤 Upload CSV baru",     callback_data="dev_upload_csv")],
        [InlineKeyboardButton("✏️ Update data kingdom", callback_data="dev_update_kd")],
        [InlineKeyboardButton("📋 Lihat log update",    callback_data="dev_log")],
        [InlineKeyboardButton("« Kembali",              callback_data="menu_main")],
    ]
    await q.edit_message_text(
        "⚙️ *Developer Panel*\n\nApa yang ingin kamu lakukan?",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

async def handle_dev_password(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.user_data.get("awaiting_dev_pass"):
        return
    if update.message.text.strip() == DEV_PASSWORD:
        ctx.user_data["dev_auth"] = True
        ctx.user_data["awaiting_dev_pass"] = False
        await update.message.reply_text("✅ Password benar! Akses developer diberikan.")
        kb = [
            [InlineKeyboardButton("📤 Upload CSV baru",     callback_data="dev_upload_csv")],
            [InlineKeyboardButton("✏️ Update data kingdom", callback_data="dev_update_kd")],
            [InlineKeyboardButton("📋 Lihat log update",    callback_data="dev_log")],
        ]
        await update.message.reply_text("⚙️ *Developer Panel*", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        ctx.user_data["awaiting_dev_pass"] = False
        await update.message.reply_text("❌ Password salah.")

async def handle_csv_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Terima file CSV dari developer"""
    if not is_dev(update.effective_user.id, ctx):
        return
    if not ctx.user_data.get("waiting_csv"):
        return
    ctx.user_data["waiting_csv"] = False
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".csv"):
        await update.message.reply_text("❌ Kirim file .csv ya.")
        return
    msg = await update.message.reply_text("⏳ Memproses CSV...")
    f = await doc.get_file()
    raw = await f.download_as_bytearray()
    text = raw.decode("utf-8", errors="replace")
    try:
        kingdoms = import_csv(text)
        d = load_data()
        d["kingdoms"].update(kingdoms)
        d["last_update"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        d["history"].append({"action":"csv_upload","count":len(kingdoms),
                              "at":d["last_update"],"by":update.effective_user.id})
        save_data(d)
        await msg.edit_text(
            f"✅ *Berhasil import {len(kingdoms)} kingdoms!*\n"
            f"🕒 Update: `{d['last_update']}`", parse_mode="Markdown"
        )
    except Exception as e:
        await msg.edit_text(f"❌ Gagal proses CSV: {e}")

# ── Callback router ───────────────────────────────────────────────────────────
async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    df = get_df()

    if data == "menu_main":
        d = load_data()
        kb = [
            [InlineKeyboardButton("🔍 Cari Kingdom",  callback_data="menu_search"),
             InlineKeyboardButton("📊 Stats & Graph", callback_data="menu_graph")],
            [InlineKeyboardButton("🏆 Top Kingdom",   callback_data="menu_top"),
             InlineKeyboardButton("🌐 Seed Overview", callback_data="menu_seed")],
            [InlineKeyboardButton("⚙️ Developer",     callback_data="menu_dev")],
        ]
        await q.edit_message_text(
            f"🏰 *RoK Kingdom Seeds Bot*\n📦 {len(d['kingdoms'])} kingdoms | 🕒 {d.get('last_update','?')}",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
        )

    elif data == "menu_graph":
        await graph_menu(update, ctx)

    elif data == "menu_seed":
        await seed_overview(update, ctx)

    elif data == "menu_search":
        await q.edit_message_text("🔍 Ketik: `/kingdom <ID>`\nContoh: `/kingdom 3908`",
                                   parse_mode="Markdown")

    elif data == "menu_top":
        if df.empty:
            await q.edit_message_text("❌ Belum ada data.")
            return
        await q.edit_message_text("⏳ Membuat grafik...")
        img = graph_top_power(df)
        await q.message.reply_photo(photo=img, caption="🏆 Top 20 Kingdoms by Power")

    elif data == "menu_dev":
        await dev_menu(update, ctx)

    elif data == "dev_upload_csv":
        if not is_dev(update.effective_user.id, ctx):
            await q.answer("🔒 Akses ditolak", show_alert=True); return
        ctx.user_data["waiting_csv"] = True
        await q.edit_message_text("📤 Kirim file CSV seed data sekarang.\n_(Format: Rank,Kingdom,Group,KvK,...)_",
                                   parse_mode="Markdown")

    elif data == "dev_update_kd":
        if not is_dev(update.effective_user.id, ctx):
            await q.answer("🔒 Akses ditolak", show_alert=True); return
        ctx.user_data["awaiting_update_kd"] = True
        await q.edit_message_text("✏️ Ketik ID Kingdom yang ingin diupdate:\nContoh: `3908`",
                                   parse_mode="Markdown")

    elif data == "dev_log":
        if not is_dev(update.effective_user.id, ctx):
            await q.answer("🔒 Akses ditolak", show_alert=True); return
        d = load_data()
        hist = d.get("history",[])[-10:]
        if not hist:
            await q.edit_message_text("📋 Belum ada log update.")
            return
        lines = ["📋 *Log Update Terakhir:*\n"]
        for h in reversed(hist):
            lines.append(f"• `{h.get('at','?')}` — {h.get('action','?')} ({h.get('count','?')} kingdoms)")
        await q.edit_message_text("\n".join(lines), parse_mode="Markdown")

    # ── Graph callbacks ──────────────────────────────────────────────────────
    elif data in ("graph_power","graph_kp","graph_group","graph_scatter"):
        if df.empty:
            await q.edit_message_text("❌ Belum ada data. Upload CSV dulu.")
            return
        await q.edit_message_text("⏳ Membuat grafik...")
        if data == "graph_power":
            img = graph_top_power(df)
            cap = "🏆 Top 20 Kingdoms by Power"
        elif data == "graph_kp":
            img = graph_top_kp(df)
            cap = "⚔️ Top 20 Kingdoms by Kill Points"
        elif data == "graph_group":
            img = graph_group_dist(df)
            cap = "📊 Group Distribution Overview"
        elif data == "graph_scatter":
            img = graph_scatter(df)
            cap = "⚡ Power vs Kill Points"
        await q.message.reply_photo(photo=img, caption=cap)

# ── Text handler (password + update field) ────────────────────────────────────
async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # Password check
    if ctx.user_data.get("awaiting_dev_pass"):
        await handle_dev_password(update, ctx)
        return

    # Manual update: waiting for kingdom ID
    if ctx.user_data.get("awaiting_update_kd") and is_dev(uid, ctx):
        kid = update.message.text.strip()
        d = load_data()
        if kid not in d["kingdoms"]:
            await update.message.reply_text(f"❌ Kingdom #{kid} tidak ditemukan.")
            ctx.user_data.pop("awaiting_update_kd", None)
            return
        ctx.user_data["update_kid"] = kid
        ctx.user_data.pop("awaiting_update_kd", None)
        ctx.user_data["awaiting_update_field"] = True
        kd = d["kingdoms"][kid]
        await update.message.reply_text(
            f"Kingdom #{kid} ditemukan.\n\n"
            f"Kirim update dalam format:\n`field=nilai`\n\n"
            f"Field tersedia: `power`, `kp`, `dead`, `ch25`, `kvk`, `group`, `rank`\n\n"
            f"Contoh: `power=12500000000`\natau multi: `power=12500000000 kp=50000000000`",
            parse_mode="Markdown"
        )
        return

    # Manual update: waiting for field=value
    if ctx.user_data.get("awaiting_update_field") and is_dev(uid, ctx):
        kid = ctx.user_data.get("update_kid")
        pairs = re.findall(r'(\w+)=(\S+)', update.message.text)
        if not pairs:
            await update.message.reply_text("❌ Format salah. Gunakan `field=nilai`", parse_mode="Markdown")
            return
        d = load_data()
        kd = d["kingdoms"].get(kid, {})
        changes = []
        for field, val in pairs:
            if field in ("power","kp","dead","ch25","rank"):
                kd[field] = int(float(val.replace(",","")))
            else:
                kd[field] = val
            changes.append(f"`{field}` → `{val}`")
        kd["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d")
        d["kingdoms"][kid] = kd
        d["last_update"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        d["history"].append({"action":"manual_update","kingdom":kid,
                              "fields":[p[0] for p in pairs],
                              "at":d["last_update"],"by":uid})
        save_data(d)
        ctx.user_data.pop("awaiting_update_field", None)
        ctx.user_data.pop("update_kid", None)
        await update.message.reply_text(
            f"✅ Kingdom #{kid} diupdate:\n" + "\n".join(changes),
            parse_mode="Markdown"
        )
        return

# ── Document handler (CSV upload) ─────────────────────────────────────────────
async def doc_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await handle_csv_upload(update, ctx)

# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("kingdom", kingdom_cmd))
    app.add_handler(CommandHandler("top",     top_cmd))
    app.add_handler(CommandHandler("graph",   graph_menu))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, doc_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    log.info("🤖 @Sawitrok_bot berjalan...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
