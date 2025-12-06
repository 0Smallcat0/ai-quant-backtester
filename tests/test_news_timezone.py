import unittest
from datetime import datetime, timedelta
import pytz
from src.data.news_fetcher import NewsFetcher

class TestNewsTimezone(unittest.TestCase):
    def setUp(self):
        self.fetcher = NewsFetcher()

    def test_tw_normal(self):
        """Case A: TW Normal (Before 14:00)"""
        # Input: Fri, 28 Nov 2025 04:00:00 GMT (12:00 Taipei)
        # Should be same day: 2025-11-28
        published = "Fri, 28 Nov 2025 04:00:00 GMT"
        effective_date = self.fetcher._normalize_date(published, 'TW')
        self.assertEqual(effective_date, "2025-11-28")

    def test_tw_rollover(self):
        """Case B: TW Rollover (After 14:00)"""
        # Input: Fri, 28 Nov 2025 08:00:00 GMT (16:00 Taipei)
        # Should be next day: 2025-11-29
        published = "Fri, 28 Nov 2025 08:00:00 GMT"
        effective_date = self.fetcher._normalize_date(published, 'TW')
        self.assertEqual(effective_date, "2025-11-29")

    def test_us_pre_market(self):
        """Case C: US Pre-market (Before 16:00 ET)"""
        # Input: Fri, 28 Nov 2025 13:00:00 GMT (08:00 ET)
        # Should be same day: 2025-11-28
        published = "Fri, 28 Nov 2025 13:00:00 GMT"
        effective_date = self.fetcher._normalize_date(published, 'US')
        self.assertEqual(effective_date, "2025-11-28")

    def test_us_post_market(self):
        """Case D: US Post-market (After 16:00 ET)"""
        # Input: Fri, 28 Nov 2025 22:00:00 GMT (17:00 ET)
        # Should be next day: 2025-11-29
        published = "Fri, 28 Nov 2025 22:00:00 GMT"
        effective_date = self.fetcher._normalize_date(published, 'US')
        self.assertEqual(effective_date, "2025-11-29")

    def test_crypto_utc(self):
        """Case E: Crypto (UTC, Cutoff 00:00)"""
        # Crypto usually trades 24/7, but for daily candles we often align to UTC 00:00.
        # If news comes at 23:00 UTC, it's part of the current day's candle (which closes at 23:59:59).
        # Wait, the spec says "Rollover time: 00:00".
        # If logic is "if hour >= cutoff", and cutoff is 0.
        # Then ANY hour >= 0 triggers rollover? That would mean EVERYTHING rolls over.
        # Let's re-read spec: "CRYPTO: UTC. 滾動時間: 00:00 (通常以 UTC 0點換日)."
        # Usually for Crypto, we don't really 'rollover' in the same sense because markets don't close.
        # But if we are mapping to Daily Candles, a news at 23:50 UTC on Nov 28 belongs to the Nov 28 candle.
        # A news at 00:10 UTC on Nov 29 belongs to the Nov 29 candle.
        # So actually, for Crypto, we might NOT need rollover logic, or the cutoff is effectively 24 (never).
        # However, if the user wants to simulate "End of Day" processing, maybe they want to treat late news as next day?
        # But standard OHLCV for crypto is 00:00-23:59 UTC.
        # Let's assume for Crypto, we just take the UTC date as is.
        # So cutoff should be effectively disabled or set to 24.
        # Let's check the spec again.
        # "CRYPTO: UTC. 滾動時間: 00:00" -> This might imply the start of the day.
        # If I strictly follow "if hour >= cutoff", and cutoff is 0, then 0 >= 0 is True.
        # So 00:00 news rolls to next day? That seems wrong.
        # Maybe the user means "No Rollover" or "Rollover at 24:00".
        # I will implement it such that Crypto just uses the UTC date (no rollover).
        # Or maybe the user implies that for Crypto, the "Close" is 00:00 of the NEXT day.
        # Let's assume standard UTC date for now.
        
        # Input: Fri, 28 Nov 2025 23:00:00 GMT
        # Should be 2025-11-28
        published = "Fri, 28 Nov 2025 23:00:00 GMT"
        effective_date = self.fetcher._normalize_date(published, 'CRYPTO')
        self.assertEqual(effective_date, "2025-11-28")

if __name__ == '__main__':
    unittest.main()
