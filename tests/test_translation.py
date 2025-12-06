import unittest
from unittest.mock import MagicMock, patch
from src.ai.translator import TextTranslator
from src.data.news_engine import NewsEngine
from src.ai.llm_client import LLMClient

class TestTranslation(unittest.TestCase):

    def setUp(self):
        self.mock_llm = MagicMock(spec=LLMClient)
        self.translator = TextTranslator(llm_client=self.mock_llm)

    def test_translate_batch_success(self):
        """Test that batch translation works correctly."""
        inputs = ["外資買超台積電", "營收創新高"]
        # Mock LLM response
        self.mock_llm.generate_strategy_code.return_value = "Foreign investors bought over TSMC\nRevenue hits record high"
        
        results = self.translator.translate_batch(inputs)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], "Foreign investors bought over TSMC")
        self.assertEqual(results[1], "Revenue hits record high")
        
        # Verify prompt contained inputs
        call_args = self.mock_llm.generate_strategy_code.call_args[0][0]
        self.assertIn("外資買超台積電", call_args)

    def test_translate_batch_mismatch_fallback(self):
        """Test fallback when LLM returns wrong number of lines."""
        inputs = ["A", "B", "C"]
        self.mock_llm.generate_strategy_code.return_value = "A\nB" # Only 2 lines
        
        results = self.translator.translate_batch(inputs)
        
        # Should return originals
        self.assertEqual(results, inputs)

    def test_news_engine_integration_chinese(self):
        """Test that NewsEngine correctly identifies and translates Chinese items."""
        # Mock dependencies
        mock_fetcher = MagicMock()
        mock_analyzer = MagicMock()
        mock_decay = MagicMock()
        
        # Setup NewsEngine with mocked translator
        engine = NewsEngine(
            fetcher=mock_fetcher,
            analyzer=mock_analyzer,
            decay_model=mock_decay,
            translator=self.translator
        )
        
        # Input items (mixed)
        items = [
            {'title': '外資買超台積電', 'summary': '...'}, # Chinese
            {'title': 'Apple stock soars', 'summary': '...'}, # English
            {'title': '營收創新高', 'summary': '...'} # Chinese
        ]
        
        # Mock Translator response for the 2 Chinese items
        self.mock_llm.generate_strategy_code.return_value = "Foreign investors bought over TSMC\nRevenue hits record high"
        
        # Call the protected method directly to verify logic
        processed_items = engine._process_translation(items)
        
        # Verify Chinese items were translated
        self.assertEqual(processed_items[0]['title'], "Foreign investors bought over TSMC")
        self.assertEqual(processed_items[2]['title'], "Revenue hits record high")
        # Verify English item was untouched
        self.assertEqual(processed_items[1]['title'], "Apple stock soars")
        
    def test_news_engine_no_translation_needed(self):
        """Test that pure English items skip translation."""
        mock_fetcher = MagicMock()
        engine = NewsEngine(fetcher=mock_fetcher, translator=self.translator)
        
        items = [{'title': 'Apple stock soars'}, {'title': 'Markets down'}]
        
        processed_items = engine._process_translation(items)
        
        # Should be identical
        self.assertEqual(processed_items, items)
        # LLM should NOT have been called
        self.mock_llm.generate_strategy_code.assert_not_called()

if __name__ == '__main__':
    unittest.main()
