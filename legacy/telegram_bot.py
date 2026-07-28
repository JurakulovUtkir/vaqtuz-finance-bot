"""
To'lov so'rovlarini kuzatuvchi Telegram bot
=============================================

VAZIFASI:
    Guruhda quyidagi ko'rinishdagi xabarlarni o'qiydi:

        Resurs: https://t.me/Bukhara
        Proyekt: Garant Bank
        Summa: 60 000 сум
        Karta: 5614681255855243

    Har bir so'rovni bazaga saqlaydi ("kutilmoqda" holatida).
    Admin o'sha xabarga JAVOB (reply) qilib chek (rasm) tashlaganda,
    so'rov "to'landi" deb belgilanadi.

    Kunlik, haftalik va oylik hisobotlar avtomatik ravishda
    belgilangan vaqtda yuboriladi.

O'RNATISH:
    pip install "python-telegram-bot[job-queue]" --upgrade
    pip install anthropic --upgrade   # AI tahlil uchun (ixtiyoriy)

SOZLASH (quyidagi konfiguratsiya bo'limiga qarang yoki muhit
o'zgaruvchilari orqali bering):
    TELEGRAM_BOT_TOKEN   - @BotFather'dan olingan token
    ADMIN_ID             - sizning Telegram user ID'ingiz (raqam)
    GROUP_CHAT_ID         - so'rovlar keladigan guruh ID'si (ixtiyoriy,
                            bo'sh qoldirsangiz bot qo'shilgan har qanday
                            guruhdan so'rovlarni qabul qiladi)
    REPORT_CHAT_ID        - hisobotlar yuboriladigan chat (bo'sh bo'lsa,
                            ADMIN_ID'ga shaxsiy xabar sifatida yuboriladi)
    ANTHROPIC_API_KEY     - console.anthropic.com'dan olingan API kalit
                            (ixtiyoriy — bo'sh qoldirsangiz hisobotlar
                            AI tahlilisiz, faqat raqamlar bilan yuboriladi)

    User ID'ni bilish uchun Telegram'da @userinfobot ga yozing.
    Guruh ID'ni bilish uchun botni guruhga qo'shib, guruhda biror
    xabar yozing va konsoldagi log'larda chat_id'ni ko'rasiz.

ISHGA TUSHIRISH:
    python telegram_bot.py
"""

import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

try:
    import anthropic
except ImportError:
    anthropic = None  # AI tahlil ixtiyoriy — kutubxona bo'lmasa ham bot ishlayveradi

# ---------------------------------------------------------------------------
# KONFIGURATSIYA
# ---------------------------------------------------------------------------

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "BU_YERGA_TOKENINGIZNI_QOYING")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # 0 = hali sozlanmagan
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")  # ixtiyoriy, string yoki None
REPORT_CHAT_ID = os.getenv("REPORT_CHAT_ID")  # bo'sh bo'lsa ADMIN_ID ishlatiladi

# AI tahlil (ixtiyoriy). Bo'sh qoldirsangiz, hisobotlar AI izohisiz yuboriladi.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AI_MODEL = "claude-haiku-4-5-20251001"  # tez va arzon model, hisobot tahlili uchun yetarli

TIMEZONE = ZoneInfo("Asia/Tashkent")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "payments.db")

# Hisobotlar qaysi vaqtda yuborilishi (mahalliy vaqt bo'yicha)
DAILY_REPORT_TIME = dtime(hour=23, minute=0, tzinfo=TIMEZONE)
WEEKLY_REPORT_TIME = dtime(hour=23, minute=5, tzinfo=TIMEZONE)  # yakshanba kuni
MONTHLY_CHECK_TIME = dtime(hour=23, minute=10, tzinfo=TIMEZONE)  # har kuni tekshiradi, faqat 1-sanada yuboradi

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# BAZA (SQLite)
# ---------------------------------------------------------------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            resurs TEXT,
            proyekt TEXT,
            summa_raw TEXT,
            summa_value INTEGER,
            karta TEXT,
            status TEXT DEFAULT 'kutilmoqda',
            requested_by TEXT,
            created_at TEXT NOT NULL,
            paid_at TEXT,
            paid_photo_file_id TEXT,
            actual_summa INTEGER DEFAULT 0,
            komissiya INTEGER DEFAULT 0
        )
        """
    )
    # Eski bazalarda bu ustunlar bo'lmasligi mumkin — xavfsiz qo'shamiz
    for column_def in ("actual_summa INTEGER DEFAULT 0", "komissiya INTEGER DEFAULT 0"):
        try:
            conn.execute(f"ALTER TABLE requests ADD COLUMN {column_def}")
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud
    conn.commit()
    conn.close()


def add_request(chat_id, message_id, resurs, proyekt, summa_raw, summa_value, karta, requested_by):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        """
        INSERT INTO requests (chat_id, message_id, resurs, proyekt, summa_raw,
                               summa_value, karta, requested_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            chat_id, message_id, resurs, proyekt, summa_raw, summa_value, karta,
            requested_by, datetime.now(TIMEZONE).isoformat(),
        ),
    )
    conn.commit()
    request_id = cur.lastrowid
    conn.close()
    return request_id


def find_request_by_message(chat_id, message_id):
    """Reply qilingan xabar bo'yicha so'rovni topadi."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM requests WHERE chat_id = ? AND message_id = ?",
        (chat_id, message_id),
    ).fetchone()
    conn.close()
    return row


def mark_paid(request_id, photo_file_id, actual_summa=None):
    """To'lovni tasdiqlaydi.

    actual_summa — komissiya bilan birga haqiqiy o'tkazilgan summa.
    Agar berilmasa, so'ralgan summaning o'zi ishlatiladi (komissiya = 0).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    req = conn.execute("SELECT summa_value FROM requests WHERE id = ?", (request_id,)).fetchone()
    requested = req["summa_value"] if req else 0

    if actual_summa is None:
        actual_summa = requested
    komissiya = actual_summa - requested

    conn.execute(
        """
        UPDATE requests
        SET status = 'tolandi', paid_at = ?, paid_photo_file_id = ?,
            actual_summa = ?, komissiya = ?
        WHERE id = ?
        """,
        (datetime.now(TIMEZONE).isoformat(), photo_file_id, actual_summa, komissiya, request_id),
    )
    conn.commit()
    conn.close()
    return komissiya


def get_requests_between(start_dt, end_dt):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM requests WHERE created_at >= ? AND created_at < ? ORDER BY created_at",
        (start_dt.isoformat(), end_dt.isoformat()),
    ).fetchall()
    conn.close()
    return rows


def get_pending_requests():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM requests WHERE status = 'kutilmoqda' ORDER BY created_at"
    ).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# XABARNI TAHLIL QILISH (PARSING)
# ---------------------------------------------------------------------------

# Uzbek va rus tilidagi belgilarni qo'llab-quvvatlaydi
LABEL_PATTERNS = {
    "resurs": r"(?:resurs|ресурс)",
    "proyekt": r"(?:proyekt|loyiha|проект)",
    "summa": r"(?:summa|сумма)",
    "karta": r"(?:karta|карта)",
}


def parse_request(text: str):
    """Xabar matnidan resurs/proyekt/summa/karta maydonlarini ajratib oladi.

    Qiymat bir xil qatorda ("Karta: 123...") yoki keyingi qatorda
    bo'lishi mumkin.
    """
    if not text:
        return None

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    values = {}

    i = 0
    while i < len(lines):
        line = lines[i]
        matched_field = None
        remainder = ""
        for field, pattern in LABEL_PATTERNS.items():
            m = re.match(rf"^{pattern}\s*:?\s*(.*)$", line, re.IGNORECASE)
            if m:
                matched_field = field
                remainder = m.group(1).strip()
                break
        if matched_field:
            if remainder:
                values[matched_field] = remainder
            elif i + 1 < len(lines):
                # qiymat keyingi qatorda
                values[matched_field] = lines[i + 1]
                i += 1
        i += 1

    if not all(k in values for k in ("resurs", "proyekt", "summa", "karta")):
        return None

    summa_raw = values["summa"]
    summa_digits = re.sub(r"[^\d]", "", summa_raw)
    summa_value = int(summa_digits) if summa_digits else 0

    karta_digits = re.sub(r"[^\d]", "", values["karta"])

    return {
        "resurs": values["resurs"],
        "proyekt": values["proyekt"],
        "summa_raw": summa_raw,
        "summa_value": summa_value,
        "karta": karta_digits if karta_digits else values["karta"],
    }


def format_sum(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " so'm"


# ---------------------------------------------------------------------------
# HANDLER: GURUHDAGI SO'ROV XABARLARI
# ---------------------------------------------------------------------------

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat

    if GROUP_CHAT_ID and str(chat.id) != str(GROUP_CHAT_ID):
        return  # faqat belgilangan guruhni tinglaymiz

    parsed = parse_request(message.text)
    if not parsed:
        return  # bu xabar so'rov formatida emas, e'tiborsiz qoldiramiz

    requested_by = message.from_user.full_name if message.from_user else "noma'lum"

    request_id = add_request(
        chat_id=chat.id,
        message_id=message.message_id,
        resurs=parsed["resurs"],
        proyekt=parsed["proyekt"],
        summa_raw=parsed["summa_raw"],
        summa_value=parsed["summa_value"],
        karta=parsed["karta"],
        requested_by=requested_by,
    )

    await message.reply_text(
        f"✅ So'rov qabul qilindi (#{request_id})\n"
        f"Proyekt: {parsed['proyekt']}\n"
        f"Summa: {format_sum(parsed['summa_value'])}\n"
        f"Karta: {parsed['karta']}\n\n"
        f"To'lov amalga oshirilgach, shu xabarga javob (reply) qilib "
        f"chekni rasm sifatida tashlang.\n"
        f"Agar komissiya yechilgan bo'lsa, rasmning izohiga (caption) "
        f"haqiqiy o'tkazilgan summani yozing (masalan: 606000)."
    )


# ---------------------------------------------------------------------------
# HANDLER: ADMIN CHEK (RASM) YUBORGANDA
# ---------------------------------------------------------------------------

async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not user or user.id != ADMIN_ID:
        return  # faqat admin to'lovni tasdiqlay oladi

    if not message.reply_to_message:
        return  # so'rovga javob tariqasida yuborilmagan

    replied_id = message.reply_to_message.message_id
    chat_id = message.chat_id

    request_row = find_request_by_message(chat_id, replied_id)

    if not request_row:
        await message.reply_text(
            "⚠️ Bu rasm qaysi so'rovga tegishli ekanini topa olmadim.\n"
            "Iltimos, ORIGINAL so'rov xabariga (Resurs/Proyekt/Summa/Karta "
            "yozilgan xabarga) to'g'ridan-to'g'ri javob (reply) qilib "
            "chekni yuboring."
        )
        return

    if request_row["status"] == "tolandi":
        await message.reply_text(f"ℹ️ So'rov #{request_row['id']} allaqachon to'langan deb belgilangan.")
        return

    photo_file_id = message.photo[-1].file_id if message.photo else None

    # Agar rasm izohida (caption) raqam bo'lsa — bu komissiya bilan
    # birga o'tkazilgan HAQIQIY summa deb qabul qilinadi.
    actual_summa = None
    if message.caption:
        digits = re.sub(r"[^\d]", "", message.caption)
        if digits:
            actual_summa = int(digits)

    komissiya = mark_paid(request_row["id"], photo_file_id, actual_summa)

    result_lines = [
        f"✅ So'rov #{request_row['id']} \"to'landi\" deb belgilandi.",
        f"Proyekt: {request_row['proyekt']} | So'ralgan: {format_sum(request_row['summa_value'])}",
    ]
    if komissiya:
        result_lines.append(f"Haqiqiy o'tkazilgan: {format_sum(actual_summa)}")
        result_lines.append(f"Komissiya: {format_sum(komissiya)}")
    await message.reply_text("\n".join(result_lines))


# ---------------------------------------------------------------------------
# HISOBOT YASASH
# ---------------------------------------------------------------------------

def build_report_text(title: str, rows) -> str:
    if not rows:
        return f"📊 {title}\n\nBu davrda so'rovlar bo'lmadi."

    total_sum = sum(r["summa_value"] for r in rows)
    paid_rows = [r for r in rows if r["status"] == "tolandi"]
    pending_rows = [r for r in rows if r["status"] == "kutilmoqda"]
    paid_sum = sum(r["summa_value"] for r in paid_rows)
    pending_sum = sum(r["summa_value"] for r in pending_rows)
    total_komissiya = sum(r["komissiya"] or 0 for r in paid_rows)
    total_actual_paid = sum((r["actual_summa"] or r["summa_value"]) for r in paid_rows)

    by_project = {}
    for r in rows:
        by_project.setdefault(r["proyekt"], {"count": 0, "sum": 0})
        by_project[r["proyekt"]]["count"] += 1
        by_project[r["proyekt"]]["sum"] += r["summa_value"]

    lines = [f"📊 {title}", ""]
    lines.append(f"Jami so'rovlar: {len(rows)} ta")
    lines.append(f"Jami summa (so'ralgan): {format_sum(total_sum)}")
    lines.append(f"✅ To'langan: {len(paid_rows)} ta — {format_sum(paid_sum)}")
    lines.append(f"⏳ Kutilmoqda: {len(pending_rows)} ta — {format_sum(pending_sum)}")
    if total_komissiya:
        lines.append(f"💳 Haqiqiy o'tkazilgan (komissiya bilan): {format_sum(total_actual_paid)}")
        lines.append(f"💸 Jami komissiya xarajati: {format_sum(total_komissiya)}")
    lines.append("")
    lines.append("Proyektlar bo'yicha:")
    for proyekt, data in sorted(by_project.items(), key=lambda x: -x[1]["sum"]):
        lines.append(f"  • {proyekt}: {data['count']} ta — {format_sum(data['sum'])}")

    if pending_rows:
        lines.append("")
        lines.append("⏳ Hali to'lanmagan so'rovlar:")
        for r in pending_rows:
            lines.append(f"  #{r['id']} {r['proyekt']} — {format_sum(r['summa_value'])} — karta: {r['karta']}")

    return "\n".join(lines)


def get_ai_insight(report_text: str) -> str:
    """Hisobot matnini Claude AI'ga yuborib, qisqa tahlil/tushuntirish oladi.

    Agar ANTHROPIC_API_KEY sozlanmagan yoki xatolik yuz bersa, bo'sh
    matn qaytaradi va hisobot AI izohisiz yuboriladi (bot ishlashda
    davom etadi).
    """
    if not ANTHROPIC_API_KEY or anthropic is None:
        return ""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=AI_MODEL,
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Quyida to'lovlar hisobotining raqamlari berilgan. "
                        "Buni o'qib, 3-4 gapda oddiy o'zbek tilida qisqa tahlil "
                        "va muhim kuzatuvlar yoz (masalan, qaysi loyiha eng ko'p "
                        "xarajat qilgani, kutilmoqda holatidagi to'lovlar ko'p "
                        "bo'lsa ogohlantirish va h.k.). Faqat tahlil matnini yoz, "
                        "sarlavha yoki qo'shimcha izohsiz:\n\n" + report_text
                    ),
                }
            ],
        )
        text_parts = [block.text for block in response.content if block.type == "text"]
        return "\n".join(text_parts).strip()
    except Exception as e:  # noqa: BLE001 - AI xatoligi hisobotni to'xtatmasligi kerak
        logger.warning("AI tahlil olishda xatolik: %s", e)
        return ""


def get_report_chat_id():
    if REPORT_CHAT_ID:
        return REPORT_CHAT_ID
    return ADMIN_ID


async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TIMEZONE)
    start = datetime.combine(now.date(), dtime.min, tzinfo=TIMEZONE)
    end = start + timedelta(days=1)
    rows = get_requests_between(start, end)
    text = build_report_text(f"Kunlik hisobot — {now.strftime('%d.%m.%Y')}", rows)
    insight = get_ai_insight(text)
    if insight:
        text += f"\n\n🤖 AI tahlili:\n{insight}"
    await context.bot.send_message(chat_id=get_report_chat_id(), text=text)


async def send_weekly_report(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TIMEZONE)
    start = datetime.combine(now.date() - timedelta(days=now.weekday()), dtime.min, tzinfo=TIMEZONE)
    end = start + timedelta(days=7)
    rows = get_requests_between(start, end)
    text = build_report_text(
        f"Haftalik hisobot — {start.strftime('%d.%m')} dan {(end - timedelta(days=1)).strftime('%d.%m.%Y')} gacha",
        rows,
    )
    insight = get_ai_insight(text)
    if insight:
        text += f"\n\n🤖 AI tahlili:\n{insight}"
    await context.bot.send_message(chat_id=get_report_chat_id(), text=text)


async def check_and_send_monthly_report(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TIMEZONE)
    if now.day != 1:
        return  # faqat oyning 1-kunida o'tgan oy hisobotini yuboramiz

    last_day_prev_month = now.date().replace(day=1) - timedelta(days=1)
    start = datetime.combine(last_day_prev_month.replace(day=1), dtime.min, tzinfo=TIMEZONE)
    end = datetime.combine(now.date().replace(day=1), dtime.min, tzinfo=TIMEZONE)
    rows = get_requests_between(start, end)
    text = build_report_text(f"Oylik hisobot — {start.strftime('%B %Y')}", rows)
    insight = get_ai_insight(text)
    if insight:
        text += f"\n\n🤖 AI tahlili:\n{insight}"
    await context.bot.send_message(chat_id=get_report_chat_id(), text=text)


# ---------------------------------------------------------------------------
# QO'LDA CHAQIRILADIGAN BUYRUQLAR
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 To'lov nazorati boti ishga tushdi.\n\n"
        "Guruhda quyidagi formatdagi xabarlarni kuzataman:\n"
        "Resurs: ...\nProyekt: ...\nSumma: ...\nKarta: ...\n\n"
        "Buyruqlar:\n"
        "/bugun - bugungi hisobot\n"
        "/hafta - shu haftalik hisobot\n"
        "/oy - shu oylik hisobot\n"
        "/kutilmoqda - hali to'lanmagan so'rovlar"
    )


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TIMEZONE)
    start = datetime.combine(now.date(), dtime.min, tzinfo=TIMEZONE)
    end = start + timedelta(days=1)
    rows = get_requests_between(start, end)
    text = build_report_text(f"Kunlik hisobot — {now.strftime('%d.%m.%Y')}", rows)
    insight = get_ai_insight(text)
    if insight:
        text += f"\n\n🤖 AI tahlili:\n{insight}"
    await update.message.reply_text(text)


async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TIMEZONE)
    start = datetime.combine(now.date() - timedelta(days=now.weekday()), dtime.min, tzinfo=TIMEZONE)
    end = start + timedelta(days=7)
    rows = get_requests_between(start, end)
    text = build_report_text(
        f"Haftalik hisobot — {start.strftime('%d.%m')} dan {(end - timedelta(days=1)).strftime('%d.%m.%Y')} gacha",
        rows,
    )
    insight = get_ai_insight(text)
    if insight:
        text += f"\n\n🤖 AI tahlili:\n{insight}"
    await update.message.reply_text(text)


async def cmd_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TIMEZONE)
    start = datetime.combine(now.date().replace(day=1), dtime.min, tzinfo=TIMEZONE)
    if now.month == 12:
        end = start.replace(year=now.year + 1, month=1)
    else:
        end = start.replace(month=now.month + 1)
    rows = get_requests_between(start, end)
    text = build_report_text(f"Oylik hisobot — {start.strftime('%B %Y')}", rows)
    insight = get_ai_insight(text)
    if insight:
        text += f"\n\n🤖 AI tahlili:\n{insight}"
    await update.message.reply_text(text)


async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = get_pending_requests()
    if not rows:
        await update.message.reply_text("✅ Hozircha kutilayotgan to'lovlar yo'q.")
        return
    lines = ["⏳ Kutilayotgan to'lovlar:", ""]
    total = 0
    for r in rows:
        lines.append(f"#{r['id']} {r['proyekt']} — {format_sum(r['summa_value'])} — karta: {r['karta']}")
        total += r["summa_value"]
    lines.append("")
    lines.append(f"Jami: {format_sum(total)}")
    await update.message.reply_text("\n".join(lines))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Xatolik yuz berdi: %s", context.error, exc_info=context.error)


# ---------------------------------------------------------------------------
# ASOSIY FUNKSIYA
# ---------------------------------------------------------------------------

def main():
    init_db()

    if BOT_TOKEN == "BU_YERGA_TOKENINGIZNI_QOYING" or ADMIN_ID == 0:
        print(
            "⚠️  Diqqat: BOT_TOKEN yoki ADMIN_ID sozlanmagan!\n"
            "   Fayl boshidagi KONFIGURATSIYA bo'limiga qarang."
        )

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bugun", cmd_today))
    app.add_handler(CommandHandler("hafta", cmd_week))
    app.add_handler(CommandHandler("oy", cmd_month))
    app.add_handler(CommandHandler("kutilmoqda", cmd_pending))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUPS),
            handle_group_message,
        )
    )

    app.add_handler(MessageHandler(filters.PHOTO, handle_admin_photo))

    app.add_error_handler(error_handler)

    job_queue = app.job_queue
    job_queue.run_daily(send_daily_report, time=DAILY_REPORT_TIME, name="daily_report")
    job_queue.run_daily(send_weekly_report, time=WEEKLY_REPORT_TIME, days=(6,), name="weekly_report")
    job_queue.run_daily(check_and_send_monthly_report, time=MONTHLY_CHECK_TIME, name="monthly_report_check")

    print("🤖 Bot ishga tushdi... To'xtatish uchun Ctrl+C bosing.")
    app.run_polling()


if __name__ == "__main__":
    main()
