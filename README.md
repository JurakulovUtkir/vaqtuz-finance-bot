# Vaqtuz Finance Bot

Telegram guruhidagi to'lov so'rovlarini kuzatuvchi va avtomatik hisobot
beruvchi bot.

Guruhga `Resurs / Proyekt / Summa / Karta` formatida so'rov tashlanadi → bot uni
bazaga yozadi → admin o'sha xabarga **reply** qilib chek rasmini tashlaydi →
so'rov "to'landi" deb belgilanadi → kunlik/haftalik/oylik hisobotlar avtomatik
yuboriladi.

---

## Tez ishga tushirish

```bash
cp .env.example .env
```

`.env` faylini to'ldiring (kamida `TELEGRAM_BOT_TOKEN` va `ADMIN_ID`), keyin:

```bash
docker compose up -d --build
```

Log'larni ko'rish:

```bash
docker compose logs -f
```

Bot **polling** orqali ishlaydi — port ochish, domen yoki nginx **kerak emas**.

---

## ⚠️ Ishga tushirishdan oldin: BotFather'da privacy mode'ni o'chiring

Telegram botlari guruhda sukut bo'yicha **faqat o'ziga tegishli xabarlarni
ko'radi**. Buni o'chirmasangiz bot so'rovlarni umuman ko'rmaydi va **hech qanday
xato bermay jim turadi**.

@BotFather → `/setprivacy` → botni tanlang → **Disable**.

Shuningdek, kunlik hisobotlar shaxsiy xabarga kelishi uchun **admin botga bir
marta `/start` yozishi shart** — aks holda Telegram botga birinchi bo'lib yozishga
ruxsat bermaydi.

---

## Sozlamalar (`.env`)

| O'zgaruvchi | Majburiy | Sukut | Izoh |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ha | — | @BotFather'dan |
| `ADMIN_ID` | ha | — | @userinfobot'dan. Faqat shu odam chek tashlab to'lovni tasdiqlay oladi |
| `GROUP_CHAT_ID` | yo'q | — | So'rovlar keladigan guruh (manfiy raqam). Bo'sh bo'lsa — har qanday guruh |
| `REPORT_CHAT_ID` | yo'q | `ADMIN_ID` | Hisobotlar yuboriladigan chat |
| `ANTHROPIC_API_KEY` | yo'q | — | Bo'sh bo'lsa hisobotlar AI tahlilisiz ketadi |
| `AI_MODEL` | yo'q | `claude-haiku-4-5-20251001` | |
| `TZ` | yo'q | `Asia/Tashkent` | |
| `DAILY_REPORT_TIME` | yo'q | `23:00` | HH:MM |
| `WEEKLY_REPORT_TIME` | yo'q | `23:05` | Yakshanba kuni |
| `MONTHLY_CHECK_TIME` | yo'q | `23:10` | Har oyning 1-sanasida o'tgan oy hisoboti |
| `LOG_LEVEL` | yo'q | `INFO` | |

Sozlama noto'g'ri bo'lsa bot **darhol tushunarli xato bilan to'xtaydi**, yarim
ishlagan holatda qolmaydi.

---

## Ishlatish

**So'rov tashlash** (guruhda, istalgan xodim):

```
Resurs: https://t.me/Bukhara
Proyekt: Garant Bank
Summa: 60 000 сум
Karta: 5614681255855243
```

Yorliqlar o'zbekcha ham, ruscha ham bo'lishi mumkin (`Ресурс`, `Проект`/`Loyiha`,
`Сумма`, `Карта`), tartibi ahamiyatsiz, qiymat keyingi qatorda ham bo'lishi
mumkin. To'rttala maydon topilmasa bot xabarni e'tiborsiz qoldiradi.

**To'lovni tasdiqlash** (faqat admin): **original so'rov xabariga** reply qilib
chek rasmini yuboring (botning "qabul qilindi" javobiga emas).

**Komissiya**: bank 60 000 o'rniga 60 600 yechgan bo'lsa, chek rasmining izohiga
(caption) `60600` deb yozing — bot farqni komissiya sifatida hisoblab, hisobotda
alohida ko'rsatadi.

**Buyruqlar**: `/bugun`, `/hafta`, `/oy`, `/kutilmoqda`

---

## Loyiha tuzilishi

```
app/
├── __main__.py          kirish nuqtasi (python -m app)
├── config.py            .env o'qish va tekshirish
├── logging_config.py
├── db/
│   ├── models.py        PaymentRequest dataclass, statuslar
│   └── database.py      SQLite qatlami, migratsiyalar
├── domain/              sof mantiq — Telegram'ga bog'liq emas, test qilinadi
│   ├── parsing.py       xabardan maydonlarni ajratish
│   ├── formatting.py
│   ├── periods.py       kun/hafta/oy oraliqlari
│   └── reports.py       hisobot matni
├── ai/insight.py        Claude tahlili (ixtiyoriy, bloklamaydigan)
└── bot/
    ├── application.py   handler va job'larni ro'yxatga olish
    ├── deps.py          umumiy bog'liqliklar
    ├── reporting.py     hisobot + AI izohi
    ├── jobs.py          avtomatik hisobotlar
    └── handlers/
        ├── requests.py  guruhdagi so'rovlar
        ├── receipts.py  admin cheki
        ├── commands.py  /bugun, /hafta, /oy, /kutilmoqda
        └── errors.py
tests/                   49 ta test
legacy/telegram_bot.py   eski bitta faylli versiya (o'chirsa bo'ladi)
```

---

## Buyruqlar (Makefile)

```bash
make up        # ishga tushirish
make logs      # jonli log
make down      # to'xtatish
make restart
make backup    # bazani backups/ ga nusxalash
make test      # testlar
```

---

## Ma'lumotlar

Baza — `payments_data` nomli Docker volume ichidagi `payments.db` (SQLite).
Konteyner o'chirilsa ham saqlanadi; `docker compose down -v` esa **o'chirib
yuboradi** — ehtiyot bo'ling.

Zaxira nusxa:

```bash
make backup
```

Tiklash:

```bash
make restore FILE=backups/payments-20260728-052517.db
```

---

## Lokalda Docker'siz ishlatish

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
DB_PATH=./data/payments.db .venv/bin/python -m app
```

---

## Xavfsizlik

`.env` fayli git'ga tushmaydi. Token, API kalit va guruh ID'larini faqat shu
faylda saqlang va hech kimga (jumladan AI yordamchilarga) yubormang.
