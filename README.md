# ⚡ TikTok Auto DM Pro (24/7 Cloud & Local Automation)

Sistem otomasi Direct Message (DM) TikTok cerdas berbasis kata kunci (keyword triggers) yang dirancang untuk dapat berjalan **24/7 non-stop** di VPS/Cloud Server (Docker) maupun komputer lokal.

Dilengkapi dengan **Web Dashboard interaktif modern**, **Live Browser Preview** (bisa scan QR login langsung dari browser/VPS), simulasi pengetikan manusiawi (*human-like typing*), cooldown per pengguna, dan proteksi anti-spam.

---

## 🌟 Fitur Utama

1. **Pemicu Kata Kunci Cerdas (Keyword Trigger & Auto Reply)**:
   - **Contains**: Cocok jika kalimat pesan mengandung kata kunci (contoh: *"min info harga dong"* memicu keyword *"harga"*).
   - **Exact Match**: Hanya cocok jika pesan persis sama.
   - **Starts With**: Cocok jika pesan diawali dengan kata kunci tertentu.
   - **Regex**: Pola ekspresi reguler tingkat lanjut.
   - **Dynamic Tag `{username}`**: Menyapa nama akun pengirim secara otomatis.

2. **Dukungan Operasional 24/7 Non-Stop (Full Autonomous)**:
   - **Auto-Start Otomatis**: Bot langsung berjalan otomatis saat aplikasi, PC, atau VPS dinyalakan tanpa perlu menekan tombol Start secara manual.
   - **Auto-Recovery**: Jika terjadi gangguan jaringan atau browser error, bot akan otomatis memulihkan diri dalam 15 detik dan terus berjalan.
   - **Siap Docker & VPS**: Dilengkapi `Dockerfile` dan `docker-compose.yml` (`restart: unless-stopped`).
   - **Persistent Session**: Sekali login, cookie dan sesi browser tersimpan permanen di folder `user_data/` sehingga tidak perlu login ulang saat server restart.

3. **Live Browser Preview & Remote QR Scanner**:
   - Pada server VPS tanpa monitor (*headless*), Anda tetap bisa melihat tampilan browser secara langsung melalui Web Dashboard.
   - Jika butuh login, QR Code TikTok akan muncul di dashboard dan Anda tinggal melakukan scan dengan kamera aplikasi TikTok di smartphone!

4. **Proteksi Anti-Banned & Perilaku Manusiawi (Human-like)**:
   - Pengetikan bertahap dengan jeda acak (*typing delay jitter* 30-80ms per huruf).
   - Cooldown cerdas per pengguna (mencegah spam ke user yang sama berulang kali).
   - Pembatasan maksimal DM per jam (safeguard limit).

5. **Sandbox Simulator & Log Aktivitas**:
   - Uji coba kecocokan kata kunci dan preview balasan tanpa harus mengirim pesan riil.
   - Log histori lengkap (waktu, pengirim, pesan masuk, keyword cocok, balasan, dan status pengiriman).

---

## 🚀 Panduan Menjalankan

### Cara 1: Menjalankan di Komputer Lokal (Windows)

1. Buka folder proyek ini.
2. Klik ganda file **`run.bat`**.
   - Skrip akan otomatis membuat virtual environment dan menginstall seluruh dependensi jika belum ada.
3. Buka browser dan akses Web Dashboard di:
   ```
   http://localhost:8000
   ```
4. Di dashboard, klik tombol **"▶️ Mulai Bot (Start)"**.
5. Jika belum login, QR Code TikTok akan tampil di bagian **Live Browser Preview**. Buka aplikasi TikTok di HP > Menu Scan > Arahkan ke layar untuk login.

---

### Cara 2: Menjalankan 24/7 Menggunakan Docker (Rekomendasi VPS)

Pastikan Docker & Docker Compose sudah terpasang di VPS Anda:

1. Clone atau unggah folder proyek ke VPS.
2. Jalankan perintah:
   ```bash
   docker compose up -d --build
   ```
3. Akses dashboard melalui IP VPS Anda:
   ```
   http://<IP_VPS_ANDA>:8000
   ```
4. Bot akan berjalan terus menerus di latar belakang (*background*). Seluruh data login dan aturan tersimpan aman di folder `./user_data`.

Untuk melihat log kontainer:
```bash
docker compose logs -f
```

Untuk menghentikan:
```bash
docker compose down
```

---

### Cara 3: Menjalankan 24/7 di Ubuntu VPS (Tanpa Docker - PM2 / Systemd)

1. Berikan izin eksekusi skrip:
   ```bash
   chmod +x setup.sh run.sh
   ```
2. Jalankan setup otomatis:
   ```bash
   ./setup.sh
   ```
3. Jalankan 24 jam dengan **PM2**:
   ```bash
   npm install -g pm2
   pm2 start run.sh --name "tiktok-auto-dm"
   pm2 save
   pm2 startup
   ```

---

## 📂 Struktur Proyek

```
tiktok auto dm/
├── app/
│   ├── api/                  # REST API (Rules, Bot Control, Logs & Stats)
│   ├── bot/                  # Playwright Core Engine & Selector Resilient Logic
│   ├── static/               # CSS Glassmorphism & JavaScript Dashboard
│   ├── templates/            # index.html (Responsive Web UI)
│   ├── config.py             # Konfigurasi aplikasi & direktori
│   └── database.py           # SQLite asynchronous storage (aiosqlite)
├── user_data/                # (Persistent Volume) Sesi browser, database, screenshots
├── Dockerfile                # Image container dengan dependensi Chromium
├── docker-compose.yml        # Konfigurasi 1-click hosting 24/7
├── setup.bat / setup.sh      # Skrip instalasi otomatis
├── run.bat / run.sh          # Skrip peluncur instan
├── requirements.txt          # Library Python
└── main.py                   # FastAPI server entry point
```

---

## 🛡️ Praktik Terbaik & Tips Keamanan

- **Gunakan Interval yang Wajar**: Jangan menyetel pengecekan inbox terlalu agresif (disarankan 10 - 25 detik).
- **Atur Cooldown**: Berikan cooldown minimal 30 menit (1800 detik) hingga 1 jam (3600 detik) agar satu pengguna tidak menerima balasan otomatis berulang kali dalam waktu singkat.
- **Variasikan Balasan**: Buat pesan balasan yang sopan, ramah, dan mengarahkan pengguna ke link bio atau nomor customer service WhatsApp.
