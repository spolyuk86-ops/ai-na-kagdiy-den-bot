"""Low-ticket, implementation-ready tools sold by the Telegram bot."""

from pathlib import Path
from typing import Optional

PRODUCT_DIR = Path(__file__).resolve().parent / "business_tools"
PRODUCTS = {
    "sales_operator": {
        "title": "AI-оператор продажів", "price_uah": 290,
        "file": "01_ai_sales_operator.md",
        "pain": "перетворює хаотичні звернення на сценарій діалогу й наступний крок",
    },
    "lead_warmup": {
        "title": "Автопрогрів лідів", "price_uah": 290,
        "file": "02_lead_warmup.md",
        "pain": "відповідає на типові питання та повертає теплих лідів у діалог",
    },
    "content_factory": {
        "title": "Контент-фабрика на 30 днів", "price_uah": 290,
        "file": "03_content_factory.md",
        "pain": "скорочує підготовку контенту до одного щотижневого процесу",
    },
    "client_research": {
        "title": "AI-дослідження клієнта", "price_uah": 290,
        "file": "04_client_research.md",
        "pain": "знаходить реальні болі клієнтів без дорогого маркетингового дослідження",
    },
    "visual_brief": {
        "title": "Конструктор продаючих візуалів", "price_uah": 290,
        "file": "05_visual_brief.md",
        "pain": "дає дизайнеру або AI чіткі брифи без нескінченних правок",
    },
    "crm_followup": {
        "title": "CRM + follow-up без менеджера", "price_uah": 490,
        "file": "06_crm_followup.md",
        "pain": "не дає заявкам губитися та нагадує менеджеру про наступну дію",
    },
    "automation_map": {
        "title": "Карта 7 автоматизацій", "price_uah": 490,
        "file": "07_automation_map.md",
        "pain": "прибирає ручне копіювання даних між заявкою, CRM і командою",
    },
    "offer_builder": {
        "title": "Конструктор мініпродукту", "price_uah": 490,
        "file": "08_offer_builder.md",
        "pain": "допомагає перетворити експертизу на продукт, який можна продати",
    },
    "email_funnel": {
        "title": "Email-воронка на 5 листів", "price_uah": 490,
        "file": "09_email_funnel.md",
        "pain": "прогріває підписника після лідмагніту без ручних повідомлень",
    },
    "pricing_closer": {
        "title": "Ціна та закриття заперечень", "price_uah": 290,
        "file": "10_pricing_closer.md",
        "pain": "допомагає назвати ціну та провести діалог без знижок і тиску",
    },
}


def product(slug: str):
    """Return a product only when the callback payload names a known product."""
    return PRODUCTS.get(slug)


def product_file(slug: str) -> Optional[Path]:
    item = product(slug)
    return PRODUCT_DIR / item["file"] if item else None
