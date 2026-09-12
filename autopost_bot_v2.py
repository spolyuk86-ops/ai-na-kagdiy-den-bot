#!/usr/bin/env python3
"""
AutoPost Bot v2.0 - Telegram канал @AI_NA_KAGDIY_DEN
Автопостинг 3x день + Отслеживание кликов + Монетизация
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

# Используем Railway Volume для персистентности
STATE_DIR = Path(os.getenv("STATE_DIR", "/data"))
STATE_DIR.mkdir(exist_ok=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1001234567890"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Файлы состояния
POSTS_FILE = STATE_DIR / "posts.json"
POSTED_INDEX_FILE = STATE_DIR / "posted_index.json"
CLICKS_FILE = STATE_DIR / "clicks.json"
AFFILIATE_TRACKING_FILE = STATE_DIR / "affiliate_tracking.json"

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
    """Команда /start для нового подписчика"""
    user = update.effective_user
    user_id = user.id
    
    # Сохранить в список подписчиков
    subscribers = load_json(STATE_DIR / "subscribers.json", {})
    subscribers[str(user_id)] = {
        "name": user.first_name,
        "joined": datetime.now().isoformat(),
        "status": "active"
    }
    save_json(STATE_DIR / "subscribers.json", subscribers)
    
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "🤖 Я помогаю найти лучшие AI инструменты для заработка\n\n"
        "📌 Подписались на канал? Отлично!\n"
        "📚 Здесь вы найдёте:\n"
        "• Промпты для ChatGPT\n"
        "• Гайды по Midjourney\n"
        "• Способы заработка на AI\n\n"
        "🔗 Переходите в канал: @AI_NA_KAGDIY_DEN"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Перейти в канал", url="https://t.me/AI_NA_KAGDIY_DEN")],
        [InlineKeyboardButton("💬 Наша группа", url="https://t.me/ai_na_kagdiy_den_chat")],
    ])
    
    await update.message.reply_text(welcome_text, reply_markup=keyboard)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats для админа"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    
    subscribers = load_json(STATE_DIR / "subscribers.json", {})
    clicks = load_json(CLICKS_FILE, {})
    posted_index = load_json(POSTED_INDEX_FILE, {})
    
    stats_text = (
        f"📊 СТАТИСТИКА КАНАЛА\n\n"
        f"👥 Подписчиков (ДМ): {len(subscribers)}\n"
        f"🖱️ Кликов по кнопкам: {len(clicks)}\n"
        f"📝 Постов опубликовано: {posted_index.get('index', 0)}\n"
        f"📅 Последний пост: {posted_index.get('last_published', 'нет данных')}\n"
    )
    
    await update.message.reply_text(stats_text)

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

async def publish_post(bot: Bot):
    """Опубликовать следующий пост в канал"""
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
    """Настроить автопостинг по расписанию"""
    scheduler = BackgroundScheduler(timezone="Europe/Kyiv")
    bot = app.bot
    
    # Добавить задачи для каждого времени
    for time_str, tz in POSTING_TIMES:
        hours, minutes = map(int, time_str.split(":"))
        scheduler.add_job(
            publish_post,
            CronTrigger(hour=hours, minute=minutes, timezone=tz),
            args=[bot],
            id=f"post_{time_str}",
            name=f"Пост в {time_str}",
            replace_existing=True
        )
        logger.info(f"⏰ Запланирован пост на {time_str}")
    
    scheduler.start()
    logger.info("✅ Планировщик запущен!")

# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

async def main():
    """Запустить бота"""
    logger.info("🚀 Запуск AutoPost Bot v2.0...")
    
    # Проверить конфиг
    if not BOT_TOKEN or not CHANNEL_ID:
        raise ValueError("❌ Отсутствуют BOT_TOKEN или CHANNEL_ID!")
    
    # Создать приложение
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Добавить обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Запустить планировщик
    setup_scheduler(app)
    
    # Запустить polling
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
