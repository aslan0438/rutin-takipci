# 🎯 Rutin Takipçi

Alışkanlıklarını takip et, XP kazan, seviye atla. Full-stack web uygulaması.

**Canlı Demo:** https://rutin-takipci.onrender.com

---

## 🚀 Özellikler

**Gamification**
- ⚡ XP / Seviye sistemi (her tamamlama +20 XP)
- 🔥 Streak takibi ve streak freeze
- ⚡ Streak recovery (XP harcayarak streak kurtar)
- 🏅 Rozet sistemi (3/7/14/30 gün milestone'ları)
- 🏆 Arkadaş liderboardu

**Alışkanlık Yönetimi**
- ✅ Günlük alışkanlık takibi
- 🎯 Haftalık hedef belirleme
- 📊 İstatistik detayı (en verimli gün, ortalama, tamamlama oranı)
- 📦 Alışkanlık arşivi
- 🔴 Öncelik sistemi (Yüksek/Normal/Düşük)
- 📅 Takvim görünümü (ay ay geçmiş düzenleme)

**Verimlilik**
- 🍅 Pomodoro zamanlayıcı (SVG arc, sürükle-bırak)
- 🎵 Odak müziği (Web Audio API — yağmur, okyanus, orman, binaural)
- 🔔 Özel bildirim mesajı ile hatırlatıcı
- ✅ Günlük todo listesi

**AI & Sosyal**
- ✨ AI alışkanlık önerisi (Anthropic Claude API)
- 🎯 Motivasyon puanı (haftalık performans skoru)
- 👥 Arkadaş sistemi
- 🔗 Herkese açık profil linki (/u/kullaniciadi)
- 📤 Paylaşım kartı (Canvas API, PNG indir)

**Kişiselleştirme**
- 👤 Avatar (emoji + renk seçimi)
- 🎨 5 tema (Koyu, Açık, Orman, Gül, Altın)
- 🌙 Otomatik sistem teması

**Teknik**
- 📧 Haftalık email raporu (Resend API)
- 🔔 Bildirim geçmişi
- 📱 PWA desteği
- 🔐 Google OAuth girişi
- ⚡ Loading screen animasyonu

## 🛠 Teknolojiler

| Katman | Teknoloji |
|--------|-----------|
| Backend | Python, Flask, SQLAlchemy |
| Database | PostgreSQL (Render) |
| Frontend | HTML, CSS, JavaScript, Tailwind CSS |
| Auth | Flask-Login, Flask-Dance (Google OAuth) |
| AI | Anthropic Claude API |
| Email | Resend API |
| Deploy | Render.com |
| PWA | Service Worker, Web Manifest |

## ⚙️ Kurulum
```bash
git clone https://github.com/aslan0438/rutin-takipci.git
cd rutin-takipci/rutin-takipci
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

`.env` dosyası oluştur:
```
SECRET_KEY=your-secret-key
ANTHROPIC_API_KEY=your-api-key
RESEND_API_KEY=your-resend-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

## 📁 Proje Yapısı
```
rutin-takipci/
├── app.py              # Flask backend, tüm route'lar
├── requirements.txt
├── Procfile
├── templates/
│   ├── index.html      # Ana sayfa (alışkanlık takibi)
│   ├── landing.html    # Landing page
│   ├── login.html      # Giriş
│   ├── register.html   # Kayıt
│   ├── profile.html    # Profil
│   └── public_profile.html  # Herkese açık profil
└── static/
    ├── manifest.json   # PWA manifest
    └── sw.js           # Service worker
```

## 🗄 Veritabanı Modelleri

- **User** — kullanıcı, XP, level, avatar, freeze_count
- **Habit** — alışkanlık, kategori, öncelik, haftalık hedef, arşiv
- **HabitLog** — günlük tamamlama kayıtları
- **Todo** — günlük görevler
- **Friendship** — arkadaşlık ilişkileri
- **Notification** — bildirim geçmişi

---

Geliştirici: [@aslan0438](https://github.com/aslan0438)  
Stack: Flask · PostgreSQL · Anthropic Claude · Render.com
