#!/usr/bin/env python3
"""
Скрипт для анализа метрик телеграм канала
Показывает статистику кликов, подписчиков, ROI от affiliate
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

def load_json(file_path):
    """Загрузить JSON файл"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def analyze_clicks():
    """Анализ кликов по партнёрам"""
    print("\n" + "="*70)
    print("📊 АНАЛИЗ КЛИКОВ")
    print("="*70 + "\n")
    
    clicks = load_json('clicks.json')
    if not clicks:
        print("❌ Нет данных кликов")
        return
    
    # Группировать по партнёрам
    partner_clicks = defaultdict(int)
    partner_dates = defaultdict(list)
    
    for click_id, data in clicks.items():
        partner = data.get('partner', 'unknown')
        partner_clicks[partner] += 1
        partner_dates[partner].append(data.get('timestamp', ''))
    
    # Вывести статистику
    print(f"Всего кликов: {len(clicks)}\n")
    print("По партнёрам:")
    
    for partner in sorted(partner_clicks.keys(), key=lambda x: partner_clicks[x], reverse=True):
        count = partner_clicks[partner]
        percentage = (count / len(clicks)) * 100
        print(f"  {partner:.<40} {count:>3} кликов ({percentage:.1f}%)")
    
    # Клики по дням
    clicks_by_day = defaultdict(int)
    for click_id, data in clicks.items():
        timestamp = data.get('timestamp', '')
        if timestamp:
            date = timestamp.split('T')[0]
            clicks_by_day[date] += 1
    
    print("\n📅 Клики по дням (последние 7 дней):")
    for date in sorted(clicks_by_day.keys(), reverse=True)[:7]:
        count = clicks_by_day[date]
        bar = "█" * (count // 2)
        print(f"  {date}: {count:>3} {bar}")

def analyze_posts():
    """Анализ опубликованных постов"""
    print("\n" + "="*70)
    print("📝 АНАЛИЗ ПОСТОВ")
    print("="*70 + "\n")
    
    posts = load_json('posts.json')
    posted_index = load_json('posted_index.json')
    
    if not posts:
        print("❌ Нет данных постов")
        return
    
    total_posts = len(posts)
    published_count = posted_index.get('index', 0)
    
    print(f"Всего постов в очереди: {total_posts}")
    print(f"Опубликовано постов: {published_count}")
    print(f"Осталось: {total_posts - published_count}")
    
    if published_count > 0:
        percentage = (published_count / total_posts) * 100
        bar = "█" * int(percentage / 5)
        print(f"\nПрогресс публикации: [{bar:<20}] {percentage:.1f}%")
    
    last_published = posted_index.get('last_published', 'нет данных')
    print(f"\nПоследний пост: {last_published}")

def analyze_subscribers():
    """Анализ подписчиков"""
    print("\n" + "="*70)
    print("👥 АНАЛИЗ ПОДПИСЧИКОВ")
    print("="*70 + "\n")
    
    subscribers = load_json('subscribers.json')
    
    if not subscribers:
        print("❌ Нет данных подписчиков")
        return
    
    total = len(subscribers)
    active = sum(1 for s in subscribers.values() if s.get('status') == 'active')
    
    print(f"Всего подписчиков (ДМ): {total}")
    print(f"Активных: {active}")
    
    # Дата присоединения
    joined_dates = defaultdict(int)
    for sub in subscribers.values():
        joined = sub.get('joined', '')
        if joined:
            date = joined.split('T')[0]
            joined_dates[date] += 1
    
    print("\n📅 Новые подписчики по дням:")
    for date in sorted(joined_dates.keys(), reverse=True)[:7]:
        count = joined_dates[date]
        bar = "█" * count
        print(f"  {date}: {count:>3} {bar}")

def analyze_roi():
    """Анализ ROI от affiliate ссылок"""
    print("\n" + "="*70)
    print("💰 АНАЛИЗ ROI И ДОХОДОВ")
    print("="*70 + "\n")
    
    partners = load_json('AFFILIATE_PARTNERS.json')
    clicks = load_json('clicks.json')
    
    if not partners or 'partners' not in partners:
        print("❌ Нет данных партнёров")
        return
    
    # Загрузить партнёров в словарь
    partner_dict = {}
    for p in partners.get('partners', []):
        partner_dict[p['id']] = p
    
    # Посчитать клики по партнёрам
    partner_clicks = defaultdict(int)
    for click_id, data in clicks.items():
        partner = data.get('partner', 'unknown')
        partner_clicks[partner] += 1
    
    print("Прогноз доходов по партнёрам:\n")
    
    total_estimated = 0
    for partner_id, partner_data in partner_dict.items():
        click_count = partner_clicks.get(partner_id, 0)
        
        # Примерная конверсия 1-2% от кликов
        conversions_low = click_count * 0.01
        conversions_high = click_count * 0.02
        
        # Доход
        commission_rate = float(partner_data.get('affiliate_rate', '0%').rstrip('%')) / 100
        
        # Примерная цена продукта из description
        price_str = partner_data.get('price', '$20')
        try:
            price = float(price_str.replace('$', '').replace('/месяц', '').split()[0])
        except:
            price = 20
        
        income_low = conversions_low * price * commission_rate
        income_high = conversions_high * price * commission_rate
        
        if click_count > 0:
            print(f"{partner_data['name']}")
            print(f"  Кликов: {click_count}")
            print(f"  Комиссия: {partner_data.get('affiliate_rate', 'N/A')}")
            print(f"  Прогноз дохода: ${income_low:.0f} - ${income_high:.0f}/месяц")
            print()
            
            total_estimated += (income_low + income_high) / 2
    
    print(f"{'='*70}")
    print(f"💎 ОБЩИЙ ПРОГНОЗ ДОХОДА: ${total_estimated:.0f}/месяц")
    print(f"{'='*70}\n")

def analyze_conversion_funnel():
    """Анализ воронки конверсии"""
    print("\n" + "="*70)
    print("📈 АНАЛИЗ ВОРОНКИ КОНВЕРСИИ")
    print("="*70 + "\n")
    
    subscribers = load_json('subscribers.json')
    clicks = load_json('clicks.json')
    
    total_subscribers = len(subscribers)
    total_clicks = len(clicks)
    
    if total_subscribers == 0:
        print("❌ Нет данных подписчиков")
        return
    
    ctr = (total_clicks / total_subscribers * 100) if total_subscribers > 0 else 0
    
    print(f"Воронка конверсии:")
    print(f"  1. Подписчики: {total_subscribers}")
    bar1 = "█" * 20
    print(f"     {bar1} 100%\n")
    
    print(f"  2. Клики по кнопкам: {total_clicks}")
    bar2 = "█" * int(ctr)
    print(f"     {bar2:<20} {ctr:.1f}%\n")
    
    # Прогноз продаж (0.5-2% конверсия)
    expected_sales_low = total_clicks * 0.005
    expected_sales_high = total_clicks * 0.02
    
    print(f"  3. Ожидаемые продажи: {expected_sales_low:.0f} - {expected_sales_high:.0f}")
    bar3 = "█" * int((expected_sales_low / total_subscribers) * 20)
    percentage = ((expected_sales_low / total_subscribers) * 100) if total_subscribers > 0 else 0
    print(f"     {bar3:<20} {percentage:.1f}%\n")
    
    print("💡 Метрики:")
    print(f"  CTR (клики/подписчики): {ctr:.2f}%")
    print(f"  Ожидаемая конверсия: 0.5-2%")
    print(f"  Средний заказ: $20-100")

def show_summary():
    """Показать сводку"""
    print("\n" + "="*70)
    print("📊 СВОДКА МЕТРИК")
    print("="*70 + "\n")
    
    subscribers = len(load_json('subscribers.json'))
    posts = len(load_json('posts.json'))
    clicks = len(load_json('clicks.json'))
    published = load_json('posted_index.json').get('index', 0)
    
    print(f"👥 Подписчиков: {subscribers}")
    print(f"📝 Постов (опубликовано/всего): {published}/{posts}")
    print(f"🖱️  Кликов: {clicks}")
    
    if subscribers > 0:
        print(f"📊 CTR: {(clicks/subscribers)*100:.2f}%")
    
    print("\n💡 Метрика успеха:")
    if subscribers < 100:
        print("  Сосредоточьтесь на росте подписчиков (цель: 100)")
    elif subscribers < 500:
        print("  Хорошо! Начните платную рекламу ($100-150)")
    elif subscribers < 2000:
        print("  Отлично! Добавьте спонсорские посты")
    else:
        print("  Отличный рост! Пора создавать курсы и масштабировать")

def main():
    """Главная функция"""
    print("\n" + "🎯 " * 20)
    print("АНАЛИЗАТОР ТЕЛЕГРАМ КАНАЛА")
    print("🎯 " * 20)
    
    # Выполнить все анализы
    show_summary()
    analyze_posts()
    analyze_subscribers()
    analyze_clicks()
    analyze_conversion_funnel()
    analyze_roi()
    
    print("\n📌 Используйте эти данные для оптимизации контента и роста!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
