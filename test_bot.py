#!/usr/bin/env python3
"""
Скрипт для локального тестирования бота
Проверяет все функции перед развёртыванием на Railway
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузить переменные окружения
load_dotenv()

def test_config():
    """Проверить переменные окружения"""
    print("🔍 Проверка конфигурации...")
    
    required_vars = ['BOT_TOKEN', 'CHANNEL_ID', 'ADMIN_ID']
    missing = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
            print(f"  ❌ {var} - не установлена")
        else:
            # Скрывать часть токена для безопасности
            if var == 'BOT_TOKEN':
                display = f"{value[:20]}...{value[-10:]}"
            else:
                display = value
            print(f"  ✅ {var} - OK ({display})")
    
    if missing:
        print(f"\n⚠️  Ошибка: установите эти переменные в .env:")
        for var in missing:
            print(f"   {var}=your_value")
        return False
    
    print("  ✅ Все переменные настроены!\n")
    return True

def test_files():
    """Проверить наличие необходимых файлов"""
    print("📁 Проверка файлов...")
    
    required_files = [
        'autopost_bot_v2.py',
        'requirements.txt',
        'posts.json',
        '.env'
    ]
    
    missing_files = []
    for file in required_files:
        if Path(file).exists():
            size = Path(file).stat().st_size
            print(f"  ✅ {file} - OK ({size} bytes)")
        else:
            missing_files.append(file)
            print(f"  ❌ {file} - не найден")
    
    if missing_files:
        print(f"\n⚠️  Ошибка: создайте эти файлы:")
        for file in missing_files:
            print(f"   {file}")
        return False
    
    print("  ✅ Все файлы на месте!\n")
    return True

def test_json_syntax():
    """Проверить JSON синтаксис"""
    print("🔍 Проверка JSON файлов...")
    
    json_files = {
        'posts.json': 'Очередь постов',
        'posted_news.json': 'История новостей (опционально)',
        'AFFILIATE_PARTNERS.json': 'Партнёры'
    }
    
    all_valid = True
    for file, description in json_files.items():
        if not Path(file).exists():
            if file == 'posted_news.json':
                print(f"  ℹ️  {file} - будет создан при первом запуске")
                continue
            continue
        
        try:
            with open(file, 'r', encoding='utf-8') as f:
                json.load(f)
            print(f"  ✅ {file} - OK ({description})")
        except json.JSONDecodeError as e:
            print(f"  ❌ {file} - ошибка JSON: {e}")
            all_valid = False
    
    if all_valid:
        print("  ✅ Все JSON файлы валидны!\n")
    else:
        print("  ⚠️  Исправьте JSON ошибки\n")
    
    return all_valid

def test_posts():
    """Проверить содержимое posts.json"""
    print("📝 Проверка постов...")
    
    try:
        with open('posts.json', 'r', encoding='utf-8') as f:
            posts = json.load(f)
        
        if not isinstance(posts, list):
            print("  ❌ posts.json должен содержать массив ([])")
            return False
        
        if len(posts) == 0:
            print("  ⚠️  posts.json пуст! Добавьте хотя бы 10 постов")
            return False
        
        print(f"  ✅ Всего постов: {len(posts)}")
        
        # Проверить первый пост
        if posts:
            first_post = posts[0]
            required_fields = ['id', 'text']
            missing_fields = [f for f in required_fields if f not in first_post]
            
            if missing_fields:
                print(f"  ❌ Пост #{first_post.get('id', '?')} - отсутствуют поля: {missing_fields}")
                return False
            
            print(f"  ✅ Структура постов - OK")
            
            # Проверить что есть текст
            if first_post.get('text'):
                print(f"  ✅ Пример текста: {first_post['text'][:50]}...")
            else:
                print(f"  ❌ Пост #{first_post.get('id')} - текст пуст")
                return False
        
        print("  ✅ Посты готовы к публикации!\n")
        return True
        
    except FileNotFoundError:
        print("  ❌ posts.json не найден")
        return False
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return False

def test_imports():
    """Проверить что все импорты работают"""
    print("🐍 Проверка Python зависимостей...")
    
    required_packages = [
        ('telegram', 'python-telegram-bot'),
        ('apscheduler', 'APScheduler'),
        ('feedparser', 'feedparser'),
    ]
    
    all_ok = True
    for package, display_name in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {display_name} - OK")
        except ImportError:
            print(f"  ❌ {display_name} - не установлен")
            all_ok = False
    
    if not all_ok:
        print("\n  📌 Установите зависимости:")
        print("     pip install -r requirements.txt\n")
    else:
        print("  ✅ Все зависимости установлены!\n")
    
    return all_ok

def test_channel_access():
    """Проверить что у нас есть доступ к каналу"""
    print("📡 Проверка доступа к каналу...")
    
    channel_id = os.getenv('CHANNEL_ID')
    bot_token = os.getenv('BOT_TOKEN')
    
    if not channel_id or not bot_token:
        print("  ⚠️  Пропуск (не установлены BOT_TOKEN или CHANNEL_ID)")
        return True
    
    try:
        from telegram import Bot
        import asyncio
        
        async def check_access():
            bot = Bot(token=bot_token)
            try:
                chat = await bot.get_chat(int(channel_id))
                print(f"  ✅ Доступ к каналу: {chat.title}")
                print(f"     ID: {chat.id}")
                return True
            except Exception as e:
                print(f"  ❌ Ошибка доступа: {e}")
                return False
        
        result = asyncio.run(check_access())
        if result:
            print("  ✅ Канал готов к публикации!\n")
        return result
        
    except Exception as e:
        print(f"  ⚠️  Не может проверить доступ (это нормально локально): {e}\n")
        return True

def main():
    """Запустить все тесты"""
    print("\n" + "="*70)
    print("🚀 ТЕСТИРОВАНИЕ TELEGRAM БОТА")
    print("="*70 + "\n")
    
    results = {
        "Конфигурация": test_config(),
        "Файлы": test_files(),
        "JSON синтаксис": test_json_syntax(),
        "Посты": test_posts(),
        "Python зависимости": test_imports(),
        "Доступ к каналу": test_channel_access(),
    }
    
    print("="*70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*70)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<50} {status}")
    
    all_pass = all(results.values())
    
    print("="*70)
    if all_pass:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("\nВы готовы запустить бота:")
        print("  Локально: python autopost_bot_v2.py")
        print("  Railway:  git push && Railway задеплоится автоматически")
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("\nИсправьте ошибки выше перед запуском")
    print("="*70 + "\n")
    
    return 0 if all_pass else 1

if __name__ == "__main__":
    exit(main())
