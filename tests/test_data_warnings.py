import pytest
import logging
import datetime
from unittest.mock import MagicMock, patch
from src.data.news_engine import NewsEngine
from src.data.news_fetcher import NewsFetcher

class TestDataWarnings:
    
    @pytest.fixture
    def mock_translator(self):
        translator = MagicMock()
        # Mock translate_batch to return a list of "Translated: " + text
        def side_effect(texts):
            return [f"Translated: {t}" for t in texts]
        translator.translate_batch.side_effect = side_effect
        return translator

    def test_translation_logging(self, caplog, mock_translator):
        """
        Action Item 1: Verify debug logs are emitted during translation.
        """
        caplog.set_level(logging.DEBUG)
        
        # Setup Engine with mocked translator
        engine = NewsEngine(translator=mock_translator)
        
        # Input with Chinese characters to trigger translation
        items = [{'title': '台積電營收創新高', 'link': 'http://example.com'}]
        
        # Execute
        engine._process_translation(items)
        
        # Verify
        # Check if logs contain the "Original Text" and "Translated Text" (which we will implement)
        # Currently, the code DOES NOT have these logs, so this test MUST FAIL.
        
        assert "DEBUG" in [r.levelname for r in caplog.records], "Should have DEBUG logs"
        
        # Check specific log content we expect to implement
        found_original = any("Original Text: 台積電營收創新高" in r.message for r in caplog.records)
        found_translated = any("Translated Text: Translated: 台積電營收創新高" in r.message for r in caplog.records)
        
        assert found_original, "Missing log for Original Text"
        assert found_translated, "Missing log for Translated Text"

    def test_history_limit_warning(self, caplog):
        """
        Action Item 2: Verify warning when fetching historical data > 30 days old.
        """
        caplog.set_level(logging.WARNING)
        
        fetcher = NewsFetcher()
        
        # Date > 30 days ago
        old_date = (datetime.datetime.now() - datetime.timedelta(days=40)).strftime('%Y-%m-%d')
        
        # Execute (passing start_date which we will implement)
        # Currently fetch_headlines does not accept start_date, so we might need to update the test 
        # to match the planned signature change. 
        # Python allows passing extra kwargs if we update the definition, 
        # but calling it now with an unexpected argument will raise TypeError.
        # So we expect this test to fail either due to TypeError or missing log.
        
        try:
            fetcher.fetch_headlines(ticker="AAPL", start_date=old_date)
        except TypeError:
            pytest.fail("fetch_headlines() does not accept start_date yet (TDD Red Phase)")
            
        # Verify warning
        found_warning = any("NewsFetcher limitations - Historical news" in r.message for r in caplog.records)
        assert found_warning, "Missing warning validation for historical data limit"

