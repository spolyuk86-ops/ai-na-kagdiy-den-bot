"""Metadata for the downloadable Ukrainian lead magnets bundled with the bot."""

from pathlib import Path

LEAD_MAGNET_DIR = Path(__file__).resolve().parent / "lead_magnets"
LEAD_MAGNETS = {
    "prompts": ("25 промптів для продажів", "01_25_prompts_for_sales.md"),
    "first100": ("План першого $100 з AI", "02_first_100_with_ai.md"),
    "freelance": ("Профіль фрілансера, що продає", "03_freelancer_profile.md"),
    "content": ("30 днів контенту за 30 хвилин", "04_content_calendar.md"),
    "research": ("Дослідження клієнта з AI", "05_customer_research.md"),
    "visual": ("Візуали, що продають", "06_selling_visuals.md"),
    "automation": ("7 автоматизацій для соло-бізнесу", "07_solo_automations.md"),
    "product": ("Упакуй експертизу в продукт", "08_productize_expertise.md"),
    "email": ("Email-серія, що веде до продажу", "09_email_sales_sequence.md"),
    "pricing": ("Ціна та відповіді на заперечення", "10_pricing_and_objections.md"),
}


def lead_magnet(slug: str):
    """Return a configured lead magnet only for a known, safe deep-link slug."""
    return LEAD_MAGNETS.get(slug)
