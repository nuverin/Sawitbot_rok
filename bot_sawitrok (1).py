"""
@Sawitrok_bot — RoK Kingdom Seeds Bot v2
No pandas dependency - pure Python + matplotlib only
"""

import os, io, json, logging, csv, re
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)

# ── Config ───────────────────────────────────────────────────────────────────
BOT_TOKEN    = os.getenv("BOT_TOKEN", "8991221360:AAE-7K2ZKHIZG49FqvViFqeCeK0pDvf3VWY")
DEVELOPER_IDS = {6132556648}
DEV_PASSWORD  = os.getenv("DEV_PASSWORD", "sawit2024")
DATA_FILE     = Path("seed_data.json")

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

DARK = "#0f1117"
CARD = "#1a1d27"

# ── Data ─────────────────────────────────────────────────────────────────────
def load_data() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {"kingdoms": {}, "last_update": None, "history": []}

def save_data(d: dict):
    DATA_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2))

def get_kingdoms() -> list:
    return list(load_data()["kingdoms"].values())

def fmt(n) -> str:
    try: n = float(str(n).replace(",",""))
    except: return str(n)
    if n >= 1e12: return f"{n/1e12:.2f}T"
    if n >= 1e9:  return f"{n/1e9:.2f}B"
    if n >= 1e6:  return f"{n/1e6:.2f}M"
    if n >= 1e3:  return f"{n/1e3:.1f}K"
    return str(int(n))

def is_dev(uid, ctx): 
    return uid in DEVELOPER_IDS or ctx.user_data.get("dev_auth")

def group_color(g):
    return {"A":"#FFD700","B":"#C0C0C0","C":"#CD7F32","D":"#78C8FF"}.get(str(g),"#AAA")

def apply_dark(fig, axes):
    fig.patch.set_facecolor(DARK)
    for ax in (axes if hasattr(axes,'__iter__') else [axes]):
        ax.set_facecolor(CARD)
        ax.tick_params(colors="#cccccc", labelsize=8)
        ax.xaxis.label.set_color("#cccccc")
        ax.yaxis.label.set_color("#cccccc")
        ax.title.set_color("#ffffff")
        for s in ax.spines.values(): s.set_edgecolor("#333344")

def buf(fig) -> io.BytesIO:
    b = io.BytesIO()
    fig.savefig(b, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    b.seek(0)
    return b

# ── CSV import ────────────────────────────────────────────────────────────────
def import_csv(text: str) -> dict:
    reader = csv.DictReader(io.StringIO(text))
    kingdoms = {}
    for row in reader:
        kid = str(row.get("Kingdom","")).strip()
        if not kid: continue
        try:
            kp_raw = str(row.get("KP",0) or 0).replace(",","").upper()
            if "E+" in kp_raw:
                kp = int(float(kp_raw))
            else:
                kp = int(float(kp_raw))
        except: kp = 0
        kingdoms[kid] = {
            "rank":      int(row.get("Rank",0) or 0),
            "kingdom":   int(kid),
            "group":     row.get("Group","").strip(),
            "kvk":       row.get("KvK","").strip(),
            "kvk_start": (row.get("KvK Start","") or "")[:10],
            "kvk_end":   (row.get("KvK End","") or "")[:10],
            "power":     int(float(row.get("Power",0) or 0)),
            "power_cap": int(float(row.get("Power Capped",0) or 0)),
            "kp":        kp,
            "dead":      int(float(row.get("Dead",0) or 0)),
            "ch25":      int(row.get("CH25",0) or 0),
            "updated_at": datetime.utcnow().isoformat()[:10],
        }
    return kingdoms

# ── Graphs ────────────────────────────────────────────────────────────────────
def graph_top_power(rows, n=20) -> io.BytesIO:
    top = sorted(rows, key=lambda x: x.get("power",0), reverse=True)[:n]
    top = sorted(top, key=lambda x: x.get("power",0))
    labels = [str(k["kingdom"]) for k in top]
    values = [k["power"]/1e9 for k in top]
    colors = [group_color(k["group"]) for k in top]
    fig, ax = plt.subplots(figsize=(9,6))
    apply_dark(fig, ax)
    bars = ax.barh(labels, values, color=colors, edgecolor="#00000044", linewidth=0.5)
    ax.set_xlabel("Power (Billions)", color="#cccccc")
    ax.set_title("Top 20 Kingdoms by Power", fontweight="bold", fontsize=13, color="white")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.0f}B"))
    for bar, k in zip(bars, top):
        ax.text(bar.get_width()+0.1, bar.get_y()+bar.get_height()/2,
                fmt(k["power"]), va="center", ha="left", color="#dddddd", fontsize=7)
    patches = [mpatches.Patch(color=group_color(g), label=f"Group {g}") for g in ["A","B","C","D"]]
    ax.legend(handles=patches, loc="lower right", fontsize=8, facecolor=CARD, edgecolor="#444", labelcolor="#ccc")
    fig.tight_layout()
    return buf(fig)

def graph_top_kp(rows, n=20) -> io.BytesIO:
    top = sorted(rows, key=lambda x: x.get("kp",0), reverse=True)[:n]
    top = sorted(top, key=lambda x: x.get("kp",0))
    labels = [str(k["kingdom"]) for k in top]
    values = [k["kp"]/1e9 for k in top]
    colors = [group_color(k["group"]) for k in top]
    fig, ax = plt.subplots(figsize=(9,6))
    apply_dark(fig, ax)
    bars = ax.barh(labels, values, color=colors, edgecolor="#00000044", linewidth=0.5)
    ax.set_xlabel("Kill Points (Billions)", color="#cccccc")
    ax.set_title("Top 20 Kingdoms by Kill Points", fontweight="bold", fontsize=13, color="white")
    for bar, k in zip(bars, top):
        ax.text(bar.get_width()+0.05, bar.get_y()+bar.get_height()/2,
                fmt(k["kp"]), va="center", ha="left", color="#dddddd", fontsize=7)
    patches = [mpatches.Patch(color=group_color(g), label=f"Group {g}") for g in ["A","B","C","D"]]
    ax.legend(handles=patches, loc="lower right", fontsize=8, facecolor=CARD, edgecolor="#444", labelcolor="#ccc")
    fig.tight_layout()
    return buf(fig)

def graph_group_dist(rows) -> io.BytesIO:
    groups = {}
    for k in rows:
        g = k.get("group","?")
        if g not in groups: groups[g] = {"count":0,"power":[],"kp":[]}
        groups[g]["count"] += 1
        groups[g]["power"].append(k.get("power",0))
        groups[g]["kp"].append(k.get("kp",0))
    grp_labels = sorted(groups.keys())
    counts  = [groups[g]["count"] for g in grp_labels]
    avg_pow = [sum(groups[g]["power"])/len(groups[g]["power"])/1e9 for g in grp_labels]
    avg_kp  = [sum(groups[g]["kp"])/len(groups[g]["kp"])/1e9 for g in grp_labels]
    colors  = [group_color(g) for g in grp_labels]
    fig, axes = plt.subplots(1, 3, figsize=(13,5))
    apply_dark(fig, axes)
    axes[0].pie(counts, labels=[f"Group {g}\n({c})" for g,c in zip(grp_labels,counts)],
                colors=colors, autopct="%1.0f%%",
                textprops={"color":"#ccc","fontsize":9},
                wedgeprops={"edgecolor":"#0f1117","linewidth":1.5})
    axes[0].set_title("Kingdom Count per Group", fontsize=11, color="white")
    axes[1].bar(grp_labels, avg_pow, color=colors, edgecolor="#00000033")
    axes[1].set_title("Avg Power per Group", fontsize=11, color="white")
    axes[1].set_ylabel("Power (B)", color="#cccccc")
    axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_:f"{x:.0f}B"))
    axes[2].bar(grp_labels, avg_kp, color=colors, edgecolor="#00000033")
    axes[2].set_title("Avg Kill Points per Group", fontsize=11, color="white")
    axes[2].set_ylabel("KP (B)", color="#cccccc")
    axes[2].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_:f"{x:.0f}B"))
    fig.suptitle("Group Statistics Overview", fontsize=14, color="white", fontweight="bold")
    fig.tight_layout()
    return buf(fig)

def graph_scatter(rows) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(9,6))
    apply_dark(fig, ax)
    for g in ["A","B","C","D"]:
        sub = [k for k in rows if k.get("group")==g]
        if not sub: continue
        ax.scatter([k["power"]/1e9 for k in sub], [k["kp"]/1e9 for k in sub],
                   c=group_color(g), label=f"Group {g}", alpha=0.75,
                   edgecolors="#ffffff22", linewidths=0.4, s=50)
    ax.set_xlabel("Power (B)", color="#cccccc")
    ax.set_ylabel("Kill Points (B)", color="#cccccc")
    ax.set_title("Power vs Kill Points", fontweight="bold", fontsize=13, color="white")
    ax.legend(facecolor=CARD, edgecolor="#444", labelcolor="#ccc", fontsize=9)
    fig.tight_layout()
    return buf(fig)

def graph_kingdom_card(kd: dict) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(7,4.5))
    apply_dark(fig, ax)
    ax.axis("off")
    gc = group_color(kd.get("group",""))
    ax.add_patch(plt.Rectangle((0,0.82),1,0.18, transform=ax.transAxes,
                                color=gc, zorder=0, clip_on=False))
    ax.text(0.5, 0.91, f"Kingdom #{kd['kingdom']}", transform=ax.transAxes,
            ha="center", va="center", fontsize=17, fontweight="bold", color="#111")
    ax.text(0.5, 0.83, f"Group {kd.get('group','?')}  |  Rank #{kd.get('rank','?')}",
            transform=ax.transAxes, ha="center", va="center", fontsize=10, color="#333")
    stats = [
        ("Power",       fmt(kd.get("power",0))),
        ("Kill Points", fmt(kd.get("kp",0))),
        ("Deads",       fmt(kd.get("dead",0))),
        ("CH25",        str(kd.get("ch25","?"))),
        ("KvK",         kd.get("kvk","N/A") or "N/A"),
        ("KvK End",     kd.get("kvk_end","N/A") or "N/A"),
    ]
    for i,(label,val) in enumerate(stats):
        y = 0.72 - i*0.115
        ax.text(0.07, y, label, transform=ax.transAxes, fontsize=11, color="#aaaaaa")
        ax.text(0.93, y, val, transform=ax.transAxes, fontsize=11,
                color="#ffffff", ha="right", fontweight="bold")
        ax.axhline(y=y-0.03, xmin=0.05, xmax=0.95, color="#333344",
                   linewidth=0.6, transform=ax.transAxes)
    ax.text(0.5, 0.02, f"Updated: {kd.get('updated_at','?')}  |  @Sawitrok_bot",
            transform=ax.transAxes, ha="center", fontsize=7, color="#555566")
    fig.tight_layout(pad=0.3)
    return buf(fig)

# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load_data()
    kb = [
        [InlineKeyboardButton("Search Kingdom", callback_data="menu_search"),
         InlineKeyboardButton("Stats & Graph",  callback_data="menu_graph")],
        [InlineKeyboardButton("Top Kingdom",    callback_data="menu_top"),
         InlineKeyboardButton("Seed Overview",  callback_data="menu_seed")],
        [InlineKeyboardButton("Developer",      callback_data="menu_dev")],
    ]
    await update.message.reply_text(
        f"*RoK Kingdom Seeds Bot*\n\n"
        f"Data: *{len(d['kingdoms'])}* kingdoms\n"
        f"Update: `{d.get('last_update','Belum ada data')}`\n\nPilih menu:",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

async def kingdom_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text("Contoh: `/kingdom 3908`", parse_mode="Markdown"); return
    kid = args[0].strip()
    d = load_data()
    kd = d["kingdoms"].get(kid)
    if not kd:
        await update.message.reply_text(f"Kingdom #{kid} tidak ditemukan."); return
    msg = await update.message.reply_text("Membuat kartu...")
    img = graph_kingdom_card(kd)
    await update.message.reply_photo(photo=img, caption=f"Kingdom #{kid} | Rank #{kd['rank']}")
    await msg.delete()

async def top_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = get_kingdoms()
    if not rows:
        await update.message.reply_text("Belum ada data."); return
    msg = await update.message.reply_text("Membuat grafik...")
    img = graph_top_power(rows)
    await update.message.reply_photo(photo=img, caption="Top 20 Kingdoms by Power")
    await msg.delete()

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    rows = get_kingdoms()
    d = load_data()

    if data == "menu_main":
        kb = [
            [InlineKeyboardButton("Search Kingdom", callback_data="menu_search"),
             InlineKeyboardButton("Stats & Graph",  callback_data="menu_graph")],
            [InlineKeyboardButton("Top Kingdom",    callback_data="menu_top"),
             InlineKeyboardButton("Seed Overview",  callback_data="menu_seed")],
            [InlineKeyboardButton("Developer",      callback_data="menu_dev")],
        ]
        await q.edit_message_text(
            f"*RoK Kingdom Seeds Bot*\n{len(d['kingdoms'])} kingdoms | {d.get('last_update','?')}",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_search":
        await q.edit_message_text("Ketik: `/kingdom <ID>`\nContoh: `/kingdom 3908`", parse_mode="Markdown")

    elif data == "menu_graph":
        kb = [
            [InlineKeyboardButton("Top 20 Power",      callback_data="graph_power")],
            [InlineKeyboardButton("Top 20 Kill Points", callback_data="graph_kp")],
            [InlineKeyboardButton("Group Overview",     callback_data="graph_group")],
            [InlineKeyboardButton("Power vs KP",        callback_data="graph_scatter")],
            [InlineKeyboardButton("Kembali",            callback_data="menu_main")],
        ]
        await q.edit_message_text("*Pilih grafik:*", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_top":
        if not rows: await q.edit_message_text("Belum ada data."); return
        await q.edit_message_text("Membuat grafik...")
        img = graph_top_power(rows)
        await q.message.reply_photo(photo=img, caption="Top 20 Kingdoms by Power")

    elif data == "menu_seed":
        if not rows: await q.edit_message_text("Belum ada data."); return
        groups = {}
        for k in rows:
            g = k.get("group","?")
            if g not in groups: groups[g] = {"count":0,"power":[],"kp":[]}
            groups[g]["count"] += 1
            groups[g]["power"].append(k.get("power",0))
            groups[g]["kp"].append(k.get("kp",0))
        lines = ["*Seed Kingdom Overview*\n"]
        for g in sorted(groups):
            ap = sum(groups[g]["power"])/len(groups[g]["power"])
            ak = sum(groups[g]["kp"])/len(groups[g]["kp"])
            lines.append(f"*Group {g}* — {groups[g]['count']} kingdoms\n  Avg Power: `{fmt(ap)}` | Avg KP: `{fmt(ak)}`")
        lines.append(f"\nTotal: *{len(rows)}* kingdoms\nUpdate: `{d.get('last_update','?')}`")
        kb = [[InlineKeyboardButton("Graph Group", callback_data="graph_group"),
               InlineKeyboardButton("Kembali",     callback_data="menu_main")]]
        await q.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "menu_dev":
        uid = update.effective_user.id
        if not is_dev(uid, ctx):
            ctx.user_data["awaiting_dev_pass"] = True
            await q.edit_message_text("*Developer Panel*\n\nMasukkan password:", parse_mode="Markdown"); return
        await show_dev_panel(q)

    elif data == "dev_upload_csv":
        if not is_dev(update.effective_user.id, ctx): return
        ctx.user_data["waiting_csv"] = True
        await q.edit_message_text("Kirim file CSV seed data sekarang.")

    elif data == "dev_update_kd":
        if not is_dev(update.effective_user.id, ctx): return
        ctx.user_data["awaiting_update_kd"] = True
        await q.edit_message_text("Ketik ID Kingdom yang ingin diupdate:\nContoh: `3908`", parse_mode="Markdown")

    elif data == "dev_log":
        if not is_dev(update.effective_user.id, ctx): return
        hist = d.get("history",[])[-10:]
        if not hist: await q.edit_message_text("Belum ada log."); return
        lines = ["*Log Update:*\n"]
        for h in reversed(hist):
            lines.append(f"• `{h.get('at','?')}` — {h.get('action','?')}")
        await q.edit_message_text("\n".join(lines), parse_mode="Markdown")

    elif data == "graph_power":
        if not rows: await q.edit_message_text("Belum ada data."); return
        await q.edit_message_text("Membuat grafik...")
        await q.message.reply_photo(photo=graph_top_power(rows), caption="Top 20 Kingdoms by Power")

    elif data == "graph_kp":
        if not rows: await q.edit_message_text("Belum ada data."); return
        await q.edit_message_text("Membuat grafik...")
        await q.message.reply_photo(photo=graph_top_kp(rows), caption="Top 20 Kingdoms by Kill Points")

    elif data == "graph_group":
        if not rows: await q.edit_message_text("Belum ada data."); return
        await q.edit_message_text("Membuat grafik...")
        await q.message.reply_photo(photo=graph_group_dist(rows), caption="Group Distribution Overview")

    elif data == "graph_scatter":
        if not rows: await q.edit_message_text("Belum ada data."); return
        await q.edit_message_text("Membuat grafik...")
        await q.message.reply_photo(photo=graph_scatter(rows), caption="Power vs Kill Points")

async def show_dev_panel(q):
    kb = [
        [InlineKeyboardButton("Upload CSV baru",     callback_data="dev_upload_csv")],
        [InlineKeyboardButton("Update data kingdom", callback_data="dev_update_kd")],
        [InlineKeyboardButton("Lihat log update",    callback_data="dev_log")],
        [InlineKeyboardButton("Kembali",             callback_data="menu_main")],
    ]
    await q.edit_message_text("*Developer Panel*", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if ctx.user_data.get("awaiting_dev_pass"):
        if update.message.text.strip() == DEV_PASSWORD:
            ctx.user_data["dev_auth"] = True
            ctx.user_data.pop("awaiting_dev_pass", None)
            kb = [
                [InlineKeyboardButton("Upload CSV baru",     callback_data="dev_upload_csv")],
                [InlineKeyboardButton("Update data kingdom", callback_data="dev_update_kd")],
                [InlineKeyboardButton("Lihat log update",    callback_data="dev_log")],
            ]
            await update.message.reply_text("*Developer Panel*", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        else:
            ctx.user_data.pop("awaiting_dev_pass", None)
            await update.message.reply_text("Password salah.")
        return

    if ctx.user_data.get("awaiting_update_kd") and is_dev(uid, ctx):
        kid = update.message.text.strip()
        d = load_data()
        if kid not in d["kingdoms"]:
            await update.message.reply_text(f"Kingdom #{kid} tidak ditemukan.")
            ctx.user_data.pop("awaiting_update_kd", None); return
        ctx.user_data["update_kid"] = kid
        ctx.user_data.pop("awaiting_update_kd", None)
        ctx.user_data["awaiting_update_field"] = True
        await update.message.reply_text(
            f"Kingdom #{kid} ditemukan.\n\nKirim update:\n`field=nilai`\n\n"
            f"Field: `power`, `kp`, `dead`, `ch25`, `kvk`, `group`, `rank`\n\n"
            f"Contoh: `power=12500000000`", parse_mode="Markdown")
        return

    if ctx.user_data.get("awaiting_update_field") and is_dev(uid, ctx):
        kid = ctx.user_data.get("update_kid")
        pairs = re.findall(r'(\w+)=(\S+)', update.message.text)
        if not pairs:
            await update.message.reply_text("Format salah. Gunakan `field=nilai`", parse_mode="Markdown"); return
        d = load_data()
        kd = d["kingdoms"].get(kid, {})
        changes = []
        for field, val in pairs:
            if field in ("power","kp","dead","ch25","rank"):
                kd[field] = int(float(val.replace(",","")))
            else:
                kd[field] = val
            changes.append(f"`{field}` = `{val}`")
        kd["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d")
        d["kingdoms"][kid] = kd
        d["last_update"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        d["history"].append({"action":"manual_update","kingdom":kid,"at":d["last_update"],"by":uid})
        save_data(d)
        ctx.user_data.pop("awaiting_update_field", None)
        ctx.user_data.pop("update_kid", None)
        await update.message.reply_text("Berhasil update:\n" + "\n".join(changes), parse_mode="Markdown")
        return

async def doc_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_dev(uid, ctx) or not ctx.user_data.get("waiting_csv"): return
    ctx.user_data["waiting_csv"] = False
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".csv"):
        await update.message.reply_text("Kirim file .csv ya."); return
    msg = await update.message.reply_text("Memproses CSV...")
    try:
        f = await doc.get_file()
        raw = await f.download_as_bytearray()
        text = raw.decode("utf-8", errors="replace")
        kingdoms = import_csv(text)
        d = load_data()
        d["kingdoms"].update(kingdoms)
        d["last_update"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        d["history"].append({"action":"csv_upload","count":len(kingdoms),"at":d["last_update"],"by":uid})
        save_data(d)
        await msg.edit_text(f"Berhasil import *{len(kingdoms)}* kingdoms!\nUpdate: `{d['last_update']}`", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"Gagal proses CSV: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("kingdom", kingdom_cmd))
    app.add_handler(CommandHandler("top",     top_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, doc_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    log.info("Bot berjalan...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
