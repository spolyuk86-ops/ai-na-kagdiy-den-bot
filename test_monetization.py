"""Unit tests for the revenue-critical conversion helpers."""

import os
import unittest
from unittest.mock import patch

import monetization as bot
from lead_magnets import LEAD_MAGNET_DIR, LEAD_MAGNETS, lead_magnet
from products import PRODUCT_DIR, PRODUCTS, product, product_file


class MonetizationHelpersTests(unittest.TestCase):
    def test_personal_affiliate_url_overrides_generic_url(self):
        with patch.dict(os.environ, {"AFFILIATE_URL_COPY_AI": "https://ref.example/copy"}):
            self.assertEqual(
                bot.affiliate_url("copy_ai", "https://www.copy.ai/"),
                "https://ref.example/copy",
            )

    def test_generic_url_is_fallback_until_personal_link_is_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                bot.affiliate_url("midjourney", "https://www.midjourney.com/"),
                "https://www.midjourney.com/",
            )

    def test_lead_magnet_deep_link_uses_bot_username(self):
        self.assertEqual(bot.lead_magnet_url("ai_daily_bot"), "https://t.me/ai_daily_bot?start=guide")

    def test_disclosure_is_added_only_once(self):
        text = bot.affiliate_disclosure("Корисний пост", True)
        self.assertIn("партнерською", text)
        self.assertEqual(text, bot.affiliate_disclosure(text, True))

    def test_status_detects_partner_without_personal_referral_url(self):
        posts = [
            {"buttons": [{"partner": "copy_ai"}]},
            {"buttons": [{"partner": "midjourney"}]},
        ]
        with patch.dict(os.environ, {"AFFILIATE_URL_COPY_AI": "https://ref.example/copy"}, clear=True):
            self.assertEqual(bot.missing_affiliate_configuration(posts), ["midjourney"])

    def test_all_ten_lead_magnets_are_present_and_resolvable(self):
        self.assertEqual(len(LEAD_MAGNETS), 10)
        for slug, (_, filename) in LEAD_MAGNETS.items():
            self.assertEqual(lead_magnet(slug), LEAD_MAGNETS[slug])
            self.assertTrue((LEAD_MAGNET_DIR / filename).is_file())

    def test_all_paid_tools_have_a_valid_price_and_delivery_file(self):
        self.assertEqual(len(PRODUCTS), 10)
        for slug, item in PRODUCTS.items():
            self.assertEqual(product(slug), item)
            self.assertGreater(item["price_uah"], 0)
            self.assertEqual(product_file(slug), PRODUCT_DIR / item["file"])
            self.assertTrue(product_file(slug).is_file())


if __name__ == "__main__":
    unittest.main()
