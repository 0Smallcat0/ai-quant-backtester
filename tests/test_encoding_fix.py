
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.news_fetcher import NewsFetcher

class TestEncodingFix(unittest.TestCase):
    def setUp(self):
        self.fetcher = NewsFetcher()

    @patch('src.data.news_fetcher.requests.get')
    def test_fetch_headlines_big5_encoding(self, mock_get):
        """
        Test that Big5 encoded content (common in Taiwan legacy sites) 
        is correctly decoded and not displayed as Mojibake.
        """
        # 1. Create a mocked response with Big5 content
        # "台積電" in Big5
        big5_content = "<?xml version='1.0' encoding='Big5'?><rss><channel><item><title>台積電法說會</title><link>http://example.com</link><pubDate>Fri, 06 Dec 2025 10:00:00 GMT</pubDate></item></channel></rss>".encode('big5')
        
        mock_response = MagicMock()
        mock_response.content = big5_content
        # Initial encoding might be guessed wrong or ISO-8859-1 by requests default
        mock_response.encoding = 'ISO-8859-1' 
        
        # When .text is accessed, it should use the adjusted encoding
        # We need to ensure our logic sets response.encoding = 'big5' (or detected)
        # And then feedparser reads .text
        
        # However, we can't easily mock the *behavior* of the property setter on a MagicMock unless we use a real Response object or side_effect.
        # But our code does:
        # if response.encoding not in utf-8:
        #    detected = ...
        #    response.encoding = ...
        # feedparser.parse(response.text)
        
        # Let's mock the text property to return the correctly decoded string *after* we correct the encoding?
        # Actually, it's easier to verify that our logic *called* chardet or set the encoding.
        
        # But for an integration-like test, let's trust the logic structure and just verify the flow.
        # To truly test "decoding", we need `response.text` to rely on `response.encoding`.
        
        # Let's construct a minimal Real response or a better mock
        type(mock_response).text = property(lambda x: x.content.decode(x.encoding))
        
        mock_get.return_value = mock_response
        
        # 2. Run the fetch
        headlines = self.fetcher.fetch_headlines("2330.TW", market="TW")
        
        # 3. Verify
        # If encoding logic failed, "台積電" would be mojibake when decoded as ISO-8859-1 (default)
        # If passed, we should see "台積電"
        
        found = False
        for h in headlines:
            if "台積電" in h['title']:
                found = True
                break
        
        self.assertTrue(found, f"Failed to correctly decode Chinese characters. Headlines: {headlines}")

if __name__ == '__main__':
    unittest.main()
