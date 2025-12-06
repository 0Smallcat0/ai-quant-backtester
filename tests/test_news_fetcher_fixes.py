import pytest
from unittest.mock import MagicMock, patch
from src.data.news_fetcher import NewsFetcher
from src.config.settings import settings

class TestNewsFetcherFixes:
    
    @patch('src.data.news_fetcher.requests.get')
    def test_fetch_headlines_tw_encoding_fix(self, mock_get):
        """
        Test that TW headlines force Big5 encoding if not UTF-8.
        """
        # Mock Response
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Simulating requests default behavior for non-explicit headers
        mock_response.encoding = 'ISO-8859-1' 
        
        # Helper to simulate read content requiring Big5 (Simulated Mojibake if wrong)
        # But here we just check if encoding is set correctly.
        mock_response.content = b'' 
        mock_response.text = "" # Simplified
        
        mock_get.return_value = mock_response
        
        fetcher = NewsFetcher()
        
        # Test Case 1: TW market with default ISO-8859-1 -> Should Switch to Big5
        try:
             fetcher.fetch_headlines("2330.TW", "TSMC", market="TW")
        except:
             pass # We just want to check the encoding property set on response
             
        # Check if the code attempted to fix encoding
        assert mock_response.encoding == 'big5', "Should verify TW encoding is forced to Big5 when default is ISO-8859-1"
        
    @patch('src.data.news_fetcher.requests.get')
    def test_fetch_headlines_crypto_limit(self, mock_get):
        """
        Test that Crypto market overrides limit to 30.
        """
        # Mock Response with many entries
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.encoding = 'utf-8'
        
        # Generate fake RSS with DISTINCT titles to avoid fuzzy filter (>0.7 similarity)
        # Using numbers is not enough usually for fuzzy match if the prefix is long.
        unique_words = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", 
                        "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi", 
                        "Rho", "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega",
                        "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
                        "Red", "Blue", "Green", "Yellow", "Purple", "Orange"]
                        
        # Generate fake RSS with COMPLETELY DISTINCT titles
        # No common prefix/suffix to trigger fuzzy match > 0.7
        distinct_titles = [
            "Apple", "Banana", "Cherry", "Date", "Elderberry", "Fig", "Grape", "Honeydew",
            "Indian Fig", "Jackfruit", "Kiwi", "Lemon", "Mango", "Nectarine", "Orange",
            "Papaya", "Quince", "Raspberry", "Strawberry", "Tangerine", "Ugli Fruit", "Vanilla",
            "Watermelon", "Xigua", "Yellow Passion Fruit", "Zucchini", "Apricot", "Blueberry",
            "Cantaloupe", "Durian", "Eggplant", "Feijoa", "Guava", "Huckleberry", "Ice Cream Bean"
        ]
        
        entries = ""
        for i, title in enumerate(distinct_titles):
             if i >= 35: break
             entries += f"""
             <item>
                <title>{title}</title> 
                <link>http://example.com/{i}</link>
                <pubDate>Fri, 06 Dec 2024 10:00:00 GMT</pubDate>
             </item>
             """
             
        rss_content = f"""
        <rss version="2.0">
        <channel>
            <title>Test Feed</title>
            {entries}
        </channel>
        </rss>
        """
        mock_response.text = rss_content
        mock_get.return_value = mock_response
        
        fetcher = NewsFetcher()
        
        # Verify Crypto gets 30
        headlines = fetcher.fetch_headlines("BTC-USD", "Bitcoin", market="CRYPTO")
        
        # Note: fetch_headlines logic might filter noise or duplicate, 
        # but with unique titles and no filter keywords matching "Crypto News", 
        # we should get max limit.
        
        assert len(headlines) == 30, f"Expected 30 headlines for Crypto, got {len(headlines)}"
        
        # Verify US gets default (10)
        settings.NEWS_TOP_N_LIMIT = 10 # Reset just in case
        headlines_us = fetcher.fetch_headlines("AAPL", "Apple", market="US")
        assert len(headlines_us) == 10, f"Expected 10 headlines for US, got {len(headlines_us)}"

if __name__ == "__main__":
    pytest.main([__file__])
