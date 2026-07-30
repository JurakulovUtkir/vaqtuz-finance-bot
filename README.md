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
| `ADMIN_IDS` | ha | — | Vergul bilan bir nechta: `279025908,1411561011`. Eski `ADMIN_ID` ham ishlaydi |
| `GROUP_CHAT_ID` | yo'q | — | So'rovlar keladigan guruh (manfiy raqam). Bo'sh bo'lsa — har qanday guruh |
| `REPORT_CHAT_ID` | yo'q | barcha adminlar | Hisobotlar yuboriladigan chat |
| `BACKUP_TIME` | yo'q | `02:00` | Zaxira adminlarga yuboriladigan vaqt |
| `ANTHROPIC_API_KEY` | yo'q | — | Bo'sh bo'lsa AI tahlil ham, chekni avtomatik o'qish ham o'chiq |
| `AI_MODEL` | yo'q | `claude-haiku-4-5` | Aniqroq kerak bo'lsa: `claude-sonnet-5`, `claude-opus-5` |
| `TZ` | yo'q | `Asia/Tashkent` | |
| `DAILY_REPORT_TIME` | yo'q | `23:00` | HH:MM |
| `WEEKLY_REPORT_TIME` | yo'q | `23:05` | Yakshanba kuni |
| `MONTHLY_CHECK_TIME` | yo'q | `23:10` | Har oyning 1-sanasida o'tgan oy hisoboti |
| `REACTION_RECEIVED` | yo'q | `👀` | So'rov qabul qilinganda |
| `REACTION_PAID` | yo'q | `👌` | To'lov tasdiqlanganda |
| `NETWORK_TIMEOUT` | yo'q | `30` | Soniya. Telegram'ga yo'l beqaror bo'lsa oshiring |
| `SEND_RETRIES` | yo'q | `3` | Yuborish necha marta qayta urinilsin |
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

So'rovni ko'rgach bot xabarga **👀** reaksiyasini qo'yadi — guruhni matn bilan
to'ldirmaslik uchun javob yozmaydi.

**To'lovni tasdiqlash** (faqat admin): **original so'rov xabariga** reply qilib
chek rasmini yuboring (botning javobiga emas). Bot reaksiyani **👌** ga
almashtiradi va qisqa tasdiq yozadi.

**Summa qayerdan olinadi** (shu tartibda):

1. Rasm izohiga (caption) raqam yozsangiz — o'sha ishlatiladi
2. Izoh bo'lmasa va `ANTHROPIC_API_KEY` sozlangan bo'lsa — bot chek rasmidan
   summani o'zi o'qiydi
3. Ikkalasi ham bo'lmasa — so'ralgan summa yoziladi, komissiya 0

**Nomuvofiqlik nazorati**: o'tkazilgan summa so'ralganidan 5% dan ko'proq farq
qilsa yoki kam bo'lsa, bot ⚠️ bilan ogohlantiradi. Kichik ortiqcha farq
komissiya deb hisoblanadi.

Bitta so'rovga bir nechta chek tashlansa — **oxirgisi** kuchda qoladi.

## Admin menyusi

Admin botga shaxsiy `/start` (yoki `/menu`) yozsa tugmali menyu chiqadi —
buyruqlarni eslab qolish shart emas:

```
[📅 Bugun]  [🗓 Hafta]  [📆 Oy]
[⏳ Kutilayotgan to'lovlar]
— Excel yuklab olish —
[📥 Joriy oy]  [📥 O'tgan oy]
[📥 Butun tarix]
```

Excel faylida 7 ta varaq bor. Eng muhimi — **Kanal narxlari**: qatorlar kanallar,
ustunlar oylar, katakda o'sha oydagi o'rtacha post narxi, oxirgi ustunda umumiy
o'zgarish foizda. Shu jadval "bu kanalga avval qancha to'lardik, hozir qancha"
degan savolga bir qarashda javob beradi.

Qolgan varaqlar: `Umumiy`, `Kanallar`, `Oylar`, `Haftalar`, `Mijozlar`,
`Barcha so'rovlar`.

**Buyruqlar** (faqat adminlar uchun): `/menu`, `/bugun`, `/hafta`, `/oy`,
`/kutilmoqda`, `/chek 14`

## Zaxira nusxa

Ikki qatlam:

1. **Serverda** — har kuni 03:00 da `backups/` ga, 14 kun saqlanadi (cron)
2. **Adminlarga** — har kuni `BACKUP_TIME` (sukut 02:00) da `.tar.gz` bo'lib
   Telegram orqali yuboriladi

Ikkinchisi muhim: server yo'qolsa birinchi qatlam ham u bilan yo'qoladi.
Telegram'dagi nusxa esa serverdan tashqarida turadi.

Tiklash: arxivni yechib, ichidagi `payments.db` ni serverga qo'ying —

```bash
make restore FILE=backups/payments-20260731-0200.db
```

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
│   ├── formatting.py    summa, kanal linki, foiz
│   ├── periods.py       kun/hafta/oy oraliqlari
│   ├── analytics.py     kanal/mijoz kesimi, narx dinamikasi
│   ├── reconciliation.py summalarni solishtirish, tasdiq matni
│   └── reports.py       hisobot matni
├── ai/
│   ├── insight.py       hisobot tahlili (ixtiyoriy)
│   └── vision.py        chek rasmidan summa o'qish (ixtiyoriy)
└── bot/
    ├── application.py   handler va job'larni ro'yxatga olish
    ├── deps.py          umumiy bog'liqliklar
    ├── net.py           tarmoq xatoligida qayta urinish
    ├── reporting.py     hisobot + AI izohi
    ├── jobs.py          avtomatik hisobotlar
    └── handlers/
        ├── requests.py  guruhdagi so'rovlar
        ├── receipts.py  admin cheki
        ├── commands.py  /bugun, /hafta, /oy, /kutilmoqda, /chek
        └── errors.py
tests/                   83 ta test
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
