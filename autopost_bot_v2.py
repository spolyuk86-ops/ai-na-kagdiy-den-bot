#!/usr/bin/env python3
"""
AutoPost Bot v2.0 - Telegram канал @AI_NA_KAGDIY_DEN
Автопостинг 3x день + Отслеживание кликов + Монетизация
"""

import json
import os
import re
import logging
from datetime import datetime, time as dtime
from pathlib import Path

import pytz
import aiohttp
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
)

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

# Используем Railway Volume для персистентности
STATE_DIR = Path(os.getenv("STATE_DIR", "/data"))
STATE_DIR.mkdir(exist_ok=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1001234567890"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Посилання на канал (окрема змінна оточення — не хардкодимо в коді,
# бо канал не має публічного @username, тільки числовий CHANNEL_ID).
# Якщо не задано — кнопка "Перейти в канал" просто не показується.
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "").strip()

# Файлы состояния
POSTS_FILE = STATE_DIR / "posts.json"
POSTED_INDEX_FILE = STATE_DIR / "posted_index.json"
CLICKS_FILE = STATE_DIR / "clicks.json"
AFFILIATE_TRACKING_FILE = STATE_DIR / "affiliate_tracking.json"
EMAILS_FILE = STATE_DIR / "emails.json"

# Копія posts.json, що постачається разом з кодом у репозиторії
# (використовується як джерело для "посіву" Volume при першому запуску)
BUNDLED_POSTS_FILE = Path(__file__).resolve().parent / "posts.json"

# MailerLite — пряма синхронізація email-підписок (без ручного експорту)
MAILERLITE_API_KEY = os.getenv("MAILERLITE_API_KEY", "").strip()
MAILERLITE_GROUP_ID = os.getenv("MAILERLITE_GROUP_ID", "198654174922016019").strip()
MAILERLITE_API_URL = "https://connect.mailerlite.com/api/subscribers"

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Временные пояса (Киев)
POSTING_TIMES = [
    ("08:00", "Europe/Kyiv"),  # Утро
    ("11:00", "Europe/Kyiv"),  # Полдень
    ("15:00", "Europe/Kyiv"),  # Вечер
]

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def load_json(file_path, default=None):
    """Загрузить JSON с fallback"""
    try:
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки {file_path}: {e}")
    return default if default else {}

def seed_posts_if_needed():
    """
    Скопіювати posts.json з репозиторію на Volume при першому запуску.

    ВАЖЛИВО: POSTS_FILE (/data/posts.json) живе на persistent Volume і
    спочатку ПОРОЖНІЙ — Volume не знає нічого про файли з git-репозиторію.
    Без цього кроку get_next_post() завжди отримує порожній список і
    publish_post() щоразу мовчки (з точки зору Telegram) падає з
    "Нет постов в очереди", хоча планувальник при цьому спрацьовує
    абсолютно вчасно — саме так і сталось на проді 13-14 вересня.

    Копіюємо лише якщо на Volume ще НІЧОГО немає — якщо там вже є
    posts.json (з попереднім прогресом посту), він має пріоритет і не
    перезаписується автоматично при кожному деплої.
    """
    if POSTS_FILE.exists():
        try:
            existing = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
            logger.info(f"📋 posts.json вже є на Volume ({len(existing)} постів) — залишаємо як є")
            return
        except Exception as e:
            logger.warning(f"⚠️ posts.json на Volume пошкоджений ({e}), пересіваємо з репозиторію")

    if BUNDLED_POSTS_FILE.exists():
        import shutil
        shutil.copy(BUNDLED_POSTS_FILE, POSTS_FILE)
        posts = json.loads(BUNDLED_POSTS_FILE.read_text(encoding="utf-8"))
        logger.info(f"✅ posts.json посіяно на Volume з репозиторію ({len(posts)} постів)")
    else:
        logger.error(
            f"❌ Немає posts.json ні на Volume ({POSTS_FILE}), "
            f"ні в репозиторії ({BUNDLED_POSTS_FILE}) — черга буде порожньою!"
        )

def save_json(file_path, data):
    """Сохранить JSON безопасно"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Ошибка сохранения {file_path}: {e}")

def get_next_post():
    """Получить следующий пост из очереди"""
    posts = load_json(POSTS_FILE, [])
    posted_index = load_json(POSTED_INDEX_FILE, {"index": 0})
    
    current_index = posted_index.get("index", 0)
    
    if current_index >= len(posts):
        logger.warning("⚠️ Очередь постов исчерпана! Перезагрузка...")
        posted_index["index"] = 0
        save_json(POSTED_INDEX_FILE, posted_index)
        current_index = 0
    
    if posts and current_index < len(posts):
        return posts[current_index], current_index
    return None, current_index

def mark_post_published(index):
    """Отметить пост как опубликованный"""
    posted_index = load_json(POSTED_INDEX_FILE, {"index": 0})
    posted_index["index"] = index + 1
    posted_index["last_published"] = datetime.now().isoformat()
    save_json(POSTED_INDEX_FILE, posted_index)

def create_affiliate_link(partner_code, post_id):
    """Создать отслеживаемую affiliate ссылку"""
    tracking_code = f"{partner_code}_{post_id}_{int(datetime.now().timestamp())}"
    return tracking_code

def track_click(button_text, partner, post_id):
    """Отследить клик по кнопке"""
    clicks = load_json(CLICKS_FILE, {})
    tracking_code = create_affiliate_link(partner, post_id)
    
    clicks[tracking_code] = {
        "button": button_text,
        "partner": partner,
        "post_id": post_id,
        "timestamp": datetime.now().isoformat(),
        "status": "clicked"
    }
    save_json(CLICKS_FILE, clicks)
    logger.info(f"✅ Клик отслежен: {button_text} ({partner})")

# ============================================================================
# КОМАНДЫ БОТА
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start для нового підписника"""
    user = update.effective_user
    user_id = user.id

    # Зберегти в список підписників
    subscribers = load_json(STATE_DIR / "subscribers.json", {})
    subscribers[str(user_id)] = {
        "name": user.first_name,
        "joined": datetime.now().isoformat(),
        "status": "active"
    }
    save_json(STATE_DIR / "subscribers.json", subscribers)

    welcome_text = (
        f"👋 Привіт, {user.first_name}!\n\n"
        "🤖 Я допомагаю знайти найкращі AI-інструменти для заробітку\n\n"
        "📚 Тут щодня публікуємо:\n"
        "• Промпти для ChatGPT\n"
        "• Гайди по Midjourney\n"
        "• Способи заробітку на AI\n\n"
        "📧 Хочете отримувати найкорисніші поради ще й на email?\n"
        "Просто напишіть мені сюди свою пошту одним повідомленням "
        "(наприклад: ivan@gmail.com) — і я додам вас у розсилку."
    )

    buttons = []
    if CHANNEL_LINK:
        buttons.append([InlineKeyboardButton("📢 Перейти в канал", url=CHANNEL_LINK)])
    keyboard = InlineKeyboardMarkup(buttons) if buttons else None

    await update.message.reply_text(welcome_text, reply_markup=keyboard)

async def add_to_mailerlite(email: str, name: str = "") -> bool:
    """
    Додати підписника напряму в MailerLite через Connect API.

    Best-effort: якщо MailerLite недоступний, ключ не заданий, чи стався
    будь-який мережевий збій — функція просто повертає False і пише в
    лог, НЕ кидає виняток. Локальний запис в emails.json (джерело
    правди) відбувається окремо і завжди спрацьовує незалежно від
    результату цього виклику.
    """
    if not MAILERLITE_API_KEY:
        logger.warning("⚠️ MAILERLITE_API_KEY не задано — синхронізація пропущена")
        return False

    headers = {
        "Authorization": f"Bearer {MAILERLITE_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"email": email, "groups": [MAILERLITE_GROUP_ID]}
    if name:
        payload["fields"] = {"name": name}

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(MAILERLITE_API_URL, json=payload, headers=headers) as resp:
                if resp.status in (200, 201):
                    logger.info(f"✅ {email} синхронізовано в MailerLite")
                    return True
                body = await resp.text()
                logger.error(f"❌ MailerLite API помилка {resp.status}: {body[:300]}")
                return False
    except Exception as e:
        logger.error(f"❌ Не вдалось з'єднатись з MailerLite: {e}")
        return False

async def delete_from_mailerlite(email: str) -> bool:
    """Видалити підписника з MailerLite (використовується для прибирання тестових записів)."""
    if not MAILERLITE_API_KEY:
        return False
    headers = {
        "Authorization": f"Bearer {MAILERLITE_API_KEY}",
        "Accept": "application/json",
    }
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"{MAILERLITE_API_URL}/{email}"
            async with session.delete(url, headers=headers) as resp:
                ok = resp.status in (200, 204)
                if not ok:
                    body = await resp.text()
                    logger.warning(f"⚠️ Не вдалось видалити {email} з MailerLite: {resp.status} {body[:200]}")
                return ok
    except Exception as e:
        logger.warning(f"⚠️ Помилка видалення {email} з MailerLite: {e}")
        return False

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка звичайного тексту в ДМ боту.
    Єдиний сценарій зараз — людина ділиться поштою для email-розсилки.
    """
    user = update.effective_user
    text = (update.message.text or "").strip().lower()

    if not EMAIL_REGEX.match(text):
        await update.message.reply_text(
            "🤔 Не схоже на email.\n\n"
            "Якщо хочете отримувати поради на пошту — просто напишіть "
            "її одним повідомленням, наприклад: ivan@gmail.com"
        )
        return

    emails = load_json(EMAILS_FILE, {})
    is_new = text not in emails
    emails[text] = {
        "telegram_id": user.id,
        "name": user.first_name,
        "joined": emails.get(text, {}).get("joined", datetime.now().isoformat()),
    }
    save_json(EMAILS_FILE, emails)

    if is_new:
        logger.info(f"📧 Нова email-підписка: {text}")
        await add_to_mailerlite(text, user.first_name)
        await update.message.reply_text(
            "✅ Готово! Додав вас у розсилку.\n\n"
            "Перший лист із добіркою промптів надішлю найближчим часом. "
            "Дякую, що приєднались 💜"
        )
    else:
        await update.message.reply_text("✅ Ця пошта вже є у розсилці — все гаразд!")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats для адміністратора"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ заборонено")
        return

    subscribers = load_json(STATE_DIR / "subscribers.json", {})
    clicks = load_json(CLICKS_FILE, {})
    emails = load_json(EMAILS_FILE, {})
    posted_index = load_json(POSTED_INDEX_FILE, {})

    stats_text = (
        f"📊 СТАТИСТИКА КАНАЛУ\n\n"
        f"👥 Підписників (ДМ боту): {len(subscribers)}\n"
        f"📧 Email-підписників: {len(emails)}\n"
        f"🖱️ Кліків по кнопках: {len(clicks)}\n"
        f"📝 Постів опубліковано: {posted_index.get('index', 0)}\n"
        f"📅 Останній пост: {posted_index.get('last_published', 'немає даних')}\n"
    )

    await update.message.reply_text(stats_text)

async def selftest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Адмін-команда: наскрізна діагностика email → MailerLite на РЕАЛЬНОМУ
    продакшн-оточенні (справжній ключ, справжній API-виклик, не мок).

    Навіщо це потрібно: єдиний спосіб змусити handle_text() реально
    спрацювати — щоб хтось написав боту повідомлення як звичайний
    Telegram-користувач. Ані Railway API, ані GitHub API, ані MailerLite
    API не дають змоги симулювати "користувач написав в Telegram" ззовні
    — це вимагає живого акаунту. /selftest — найближче до цього, що можна
    автоматизувати: один рядок від адміна замість повного ручного сценарію,
    і перевіряється справжній продакшн-виклик, а не локальний мок.
    """
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ заборонено")
        return

    test_email = f"selftest-{int(datetime.now().timestamp())}@example.com"
    await update.message.reply_text(f"🔬 Запускаю самоперевірку ({test_email})...")

    # 1. Локальне збереження — та сама логіка, що й у handle_text
    emails = load_json(EMAILS_FILE, {})
    emails[test_email] = {
        "telegram_id": update.effective_user.id,
        "name": "SelfTest",
        "joined": datetime.now().isoformat(),
    }
    save_json(EMAILS_FILE, emails)
    local_ok = test_email in load_json(EMAILS_FILE, {})

    # 2. РЕАЛЬНИЙ виклик MailerLite API (продакшн-ключ, не мок)
    ml_ok = await add_to_mailerlite(test_email, "SelfTest")

    # 3. Прибрати за собою — і локально, і в MailerLite
    emails = load_json(EMAILS_FILE, {})
    emails.pop(test_email, None)
    save_json(EMAILS_FILE, emails)

    ml_cleanup_ok = True
    if ml_ok:
        ml_cleanup_ok = await delete_from_mailerlite(test_email)

    all_ok = local_ok and ml_ok
    result_text = (
        "🔬 РЕЗУЛЬТАТ САМОПЕРЕВІРКИ\n\n"
        f"{'✅' if local_ok else '❌'} Локальне збереження (emails.json на Volume)\n"
        f"{'✅' if ml_ok else '❌'} Синхронізація з MailerLite (справжній API-виклик)\n"
        f"{'✅' if ml_cleanup_ok else '⚠️'} Тестовий запис прибрано\n\n"
    )
    if all_ok:
        result_text += (
            "✅ Все працює на продакшені. Коли реальна людина напише "
            "email боту — станеться те саме, що й тут."
        )
    else:
        result_text += "⚠️ Є проблема — перевір логи Railway для деталей (get-logs)."

    await update.message.reply_text(result_text)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка клика по кнопке"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("|")  # Формат: partner|post_id|url
    
    if len(data) >= 3:
        partner, post_id, url = data[0], data[1], data[2]
        track_click(partner, partner, post_id)
        
        await query.edit_message_text(
            f"✅ Переход на {partner}...\n"
            f"<a href='{url}'>Нажмите здесь если не открылось</a>",
            parse_mode="HTML"
        )

# ============================================================================
# АВТОПОСТИНГ
# ============================================================================

async def publish_post(context: ContextTypes.DEFAULT_TYPE):
    """Опубликовать следующий пост в канал (вызывается PTB JobQueue)"""
    bot = context.bot
    post_data, index = get_next_post()
    
    if not post_data:
        logger.error("❌ Нет постов в очереди!")
        return
    
    try:
        # Получить текст поста
        text = post_data.get("text", "")
        buttons = post_data.get("buttons", [])
        image_url = post_data.get("image", None)
        
        # Построить клавиатуру
        keyboard = None
        if buttons:
            button_rows = []
            for btn in buttons:
                callback_data = f"{btn['partner']}|{index}|{btn['url']}"
                button_rows.append([
                    InlineKeyboardButton(btn["text"], callback_data=callback_data)
                ])
            keyboard = InlineKeyboardMarkup(button_rows)
        
        # Опубликовать
        if image_url and image_url.startswith("http"):
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=image_url,
                caption=text,
                parse_mode=None,  # Поддержка украинского текста
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=text,
                parse_mode=None,
                reply_markup=keyboard
            )
        
        mark_post_published(index)
        logger.info(f"✅ Пост #{index + 1} опубликован в {datetime.now().strftime('%H:%M')}")
        
    except TelegramError as e:
        logger.error(f"❌ Ошибка публикации: {e}")

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ ПЛАНИРОВЩИКА
# ============================================================================

def setup_scheduler(app: Application):
    """
    Настроить автопостинг через встроенный JobQueue бота (PTB v20).

    ВАЖНО: раньше здесь использовался отдельный apscheduler.BackgroundScheduler
    с async-функцией publish_post в качестве колбэка. BackgroundScheduler
    синхронный и не умеет await'ить корутины — job "выполнялся", но тело
    publish_post никогда реально не запускалось (корутина создавалась и
    сразу отбрасывалась). JobQueue бота — это тот же APScheduler, но
    интегрированный с event loop-ом PTB, поэтому async-колбэки работают
    корректно "из коробки".
    """
    if app.job_queue is None:
        raise RuntimeError(
            "❌ JobQueue недоступен. Проверьте что APScheduler установлен "
            "(требуется для python-telegram-bot[job-queue])."
        )

    for time_str, tz in POSTING_TIMES:
        hours, minutes = map(int, time_str.split(":"))
        app.job_queue.run_daily(
            publish_post,
            time=dtime(hour=hours, minute=minutes, tzinfo=pytz.timezone(tz)),
            name=f"post_{time_str}",
        )
        logger.info(f"⏰ Запланирован пост на {time_str} ({tz})")

    logger.info("✅ Планировщик запущен!")

# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    """
    Запустить бота.

    ВАЖНО: эта функция синхронная и вызывается напрямую (без asyncio.run).
    Application.run_polling() в python-telegram-bot v20 сам создаёт и
    полностью управляет своим event loop-ом внутри. Оборачивание её в
    asyncio.run(...) + await приводит к "RuntimeError: This event loop
    is already running", так как получаются два конфликтующих loop-а.
    """
    logger.info("🚀 Запуск AutoPost Bot v2.0...")

    # Проверить конфиг
    if not BOT_TOKEN or not CHANNEL_ID:
        raise ValueError("❌ Отсутствуют BOT_TOKEN или CHANNEL_ID!")

    # Создать приложение
    app = Application.builder().token(BOT_TOKEN).build()

    # Посіяти posts.json на Volume, якщо його там ще немає
    seed_posts_if_needed()

    # Добавить обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("selftest", selftest))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Запустить планировщик (использует app.job_queue)
    setup_scheduler(app)

    # Запустить polling — БЛОКИРУЮЩИЙ синхронный вызов, не await!
    app.run_polling()

if __name__ == "__main__":
    main()
