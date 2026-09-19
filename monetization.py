"""Pure helpers for configuring the channel's conversion funnel."""

import os
import re


def affiliate_url(partner: str, fallback_url: str) -> str:
    """Return the owner's configured referral URL, or the content fallback."""
    env_key = "AFFILIATE_URL_" + re.sub(r"[^A-Z0-9]", "_", partner.upper())
    return os.getenv(env_key, fallback_url).strip()


def lead_magnet_url(bot_username: str) -> str:
    """Create the source-tagged Telegram deep link for the lead magnet."""
    bot_username = bot_username.strip().lstrip("@")
    if not bot_username:
        return ""
    return f"https://t.me/{bot_username}?start=guide"


def affiliate_disclosure(text: str, has_affiliate_button: bool) -> str:
    """Add one concise affiliate disclosure when a sales link is present."""
    disclosure = "ℹ️ Частина посилань може бути партнерською — без доплати для вас."
    if has_affiliate_button and disclosure not in text:
        return f"{text.rstrip()}\n\n{disclosure}"
    return text


def missing_affiliate_configuration(posts: list) -> list:
    """Return promoted partners that do not yet have a personal referral URL."""
    partners = {
        button.get("partner", "")
        for post in posts
        for button in post.get("buttons", [])
        if button.get("partner")
    }
    return sorted(
        partner for partner in partners
        if not os.getenv("AFFILIATE_URL_" + re.sub(r"[^A-Z0-9]", "_", partner.upper()), "").strip()
    )
