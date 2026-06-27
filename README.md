# 🏰 RoK Kingdom Seeds Bot

Bot Telegram untuk mengakses informasi Kingdom dari game **Rise of Kingdoms**  
Data bersumber dari: [heroscroll.com/rok/seeds](https://heroscroll.com/rok/seeds)

---

## 🚀 CARA SETUP (Step by Step)

### Langkah 1 — Buat Bot di Telegram

1. Buka Telegram, cari **@BotFather**
2. Ketik `/newbot`
3. Masukkan **nama bot** (contoh: `RoK Kingdom Info`)
4. Masukkan **username bot** (harus diakhiri `bot`, contoh: `rok_kingdom_bot`)
5. BotFather akan memberikan **TOKEN** seperti:
   ```
   1234567890:AAHdqTcvCH1vGWJxfSeofSoGb3Zl5M9Y-F8
   ```
6. **Salin token tersebut** — kamu butuhkan di Langkah 3

---

### Langkah 2 — Instal Python & Dependencies

**Pastikan Python 3.10+ sudah terinstal:**
```bash
python --version
```

**Instal library yang dibutuhkan:**
```bash
pip install -r requirements.txt
```

---

### Langkah 3 — Set Token Bot

**Opsi A: Via environment variable (direkomendasikan)**
```bash
# Linux / Mac
export BOT_TOKEN="TOKEN_KAMU_DI_SINI"

# Windows (CMD)
set BOT_TOKEN=TOKEN_KAMU_DI_SINI
```

**Opsi B: Edit langsung di bot.py**

Buka `bot.py`, cari baris ini:
```python
BOT_TOKEN = os.getenv("BOT_TOKEN", "MASUKKAN_TOKEN_DI_SINI")
```
Ganti `MASUKKAN_TOKEN_DI_SINI` dengan token kamu:
```python
BOT_TOKEN = "1234567890:AAHdqTcvCH1vGWJxfSeofSoGb3Zl5M9Y-F8"
```

---

### Langkah 4 — Jalankan Bot

```bash
python bot.py
```

Kalau berhasil, akan muncul:
```
🤖 Bot RoK berjalan...
```

---

## 📋 FITUR BOT

| Command | Fungsi |
|---------|--------|
| `/start` | Menu utama dengan tombol interaktif |
| `/kingdom 1001` | Info lengkap Kingdom #1001 |
| `/top` | Top 10 kingdom berdasarkan rank |
| `/filter` | Filter kingdom (power, kill points, deads, KvK status, dll) |
| `/help` | Panduan penggunaan |

### Contoh penggunaan:
```
/kingdom 1001   → Info Kingdom #1001
/kingdom 3050   → Info Kingdom #3050
/top            → Lihat Top 10 kingdom
/filter         → Buka menu filter interaktif
```

---

## ⚠️ CATATAN PENGEMBANG

Heroscroll adalah website berbasis JavaScript (SPA/Next.js).  
Bot ini menggunakan **endpoint JSON internal** yang ditemukan via browser DevTools.

**Jika data tidak muncul / error API:**
1. Buka heroscroll.com di browser
2. Tekan `F12` → tab **Network**
3. Filter: `Fetch/XHR`
4. Refresh halaman → cari request ke `/api/...`
5. Update nilai `API_BASE` di `bot.py` sesuai endpoint baru

---

## 🖥️ Menjalankan Bot 24/7

### Opsi A: VPS (Ubuntu)
```bash
# Install screen
sudo apt install screen

# Jalankan di background
screen -S rokbot
python bot.py
# Tekan Ctrl+A lalu D untuk detach
```

### Opsi B: Systemd Service
```ini
# /etc/systemd/system/rokbot.service
[Unit]
Description=RoK Kingdom Bot
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/bot.py
Environment=BOT_TOKEN=TOKEN_KAMU
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable rokbot
sudo systemctl start rokbot
```

### Opsi C: Railway / Render (Cloud Gratis)
1. Upload folder ini ke GitHub
2. Connect ke [railway.app](https://railway.app) atau [render.com](https://render.com)
3. Set environment variable `BOT_TOKEN`
4. Deploy!

---

## 📁 Struktur File

```
rok_bot/
├── bot.py           ← File utama bot
├── requirements.txt ← Library yang dibutuhkan
└── README.md        ← Panduan ini
```
