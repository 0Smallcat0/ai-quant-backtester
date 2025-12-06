import unittest
from unittest.mock import patch, MagicMock
from src.data.news_fetcher import NewsFetcher

class TestNewsFetcher(unittest.TestCase):
    def setUp(self):
        self.fetcher = NewsFetcher()

    def test_url_generation_tw(self):
        """Case A: Verify URL generation for TW market"""
        # Input: market='TW', ticker='2330', name='台積電'
        # Expected: site:cnyes.com, hl=zh-TW
        url = self.fetcher._build_query(ticker='2330', name='台積電', market='TW')
        
        self.assertIn('site%3Acnyes.com', url)
        self.assertIn('site%3Actee.com.tw', url) # New source
        self.assertIn('hl=zh-TW', url)
        self.assertIn('gl=TW', url)
        # Check if name and ticker are in the query (encoded)
        # 台積電 encoded is %E5%8F%B0%E7%A9%8D%E9%9B%BB
        self.assertIn('%E5%8F%B0%E7%A9%8D%E9%9B%BB', url)
        self.assertIn('2330', url)

    def test_crypto_query(self):
        """Case B: Verify query building for CRYPTO market"""
        # Input: market='CRYPTO', ticker='BTC'
        # Expected: site:coindesk.com
        url = self.fetcher._build_query(ticker='BTC', name='Bitcoin', market='CRYPTO')
        
        self.assertIn('site%3Acoindesk.com', url)
        self.assertIn('site%3Adecrypt.co', url) # New source
        self.assertIn('site%3Ablockworks.co', url) # New source
        self.assertIn('hl=en-US', url)

    @patch('src.data.news_fetcher.feedparser.parse')
    def test_mock_fetching_and_limiting(self, mock_parse):
        """Case C: Verify fetching, parsing and top-5 limiting"""
        # Mock feedparser response with 10 entries
        mock_entries = []
        # Use distinct titles to avoid fuzzy deduplication
        distinct_titles = [
            "Apple releases new iPhone", "Google announces AI model", "Tesla stock surges", 
            "Amazon earnings beat", "Microsoft acquires Blizzard", "Netflix subscriber growth",
            "Meta launches VR headset", "Nvidia GPU demand spikes", "AMD challenges Intel",
            "Intel delays chip", "Samsung profits drop", "Sony playstation sales",
            "Nintendo switch successor", "Uber profits rise", "Airbnb bookings record"
        ]
        for i in range(15):
            mock_entries.append({
                'title': distinct_titles[i],
                'link': f'http://example.com/{i}',
                'published': '2023-01-01',
                'summary': 'Summary'
            })
        
        mock_feed = MagicMock()
        mock_feed.entries = mock_entries
        mock_parse.return_value = mock_feed

        headlines = self.fetcher.fetch_headlines(ticker='AAPL', market='US')

        # Assert limiting to 10 (Updated from 5)
        self.assertEqual(len(headlines), 10)
        # Check that returned titles are from our input list
        returned_titles = [h['title'] for h in headlines]
        for t in returned_titles:
            self.assertIn(t, distinct_titles)
        
        
        # Should return empty list and not crash


    def test_noise_filtering(self):
        """Case E: Verify noise filtering logic"""
        # Mock entries with noise
        entries = [
            {'title': 'TSMC reports strong Q3 earnings results', 'link': 'http://valid1.com', 'published': '2023-01-01', 'summary': 'Summary'},
            {'title': '鉅亨速報：外資賣超前十名', 'link': 'http://noise1.com', 'published': '2023-01-01', 'summary': 'Noise'},
            {'title': '盤後統整：今日熱門股', 'link': 'http://noise2.com', 'published': '2023-01-01', 'summary': 'Noise'},
            {'title': 'TSMC announces new Arizona plant expansion', 'link': 'http://valid2.com', 'published': '2023-01-01', 'summary': 'Summary'}
        ]
        
        # We need to access the private method _filter_noise, or mock fetch_headlines internals.
        # Since we are testing logic, let's test _filter_noise directly if possible, 
        # but it's private. So we will rely on the fact that we are implementing it.
        # Alternatively, we can mock feedparser and check the output of fetch_headlines.
        
        with patch('src.data.news_fetcher.feedparser.parse') as mock_parse:
            mock_feed = MagicMock()
            mock_feed.entries = entries
            mock_parse.return_value = mock_feed
            
            headlines = self.fetcher.fetch_headlines(ticker='2330', market='TW')
            
            titles = [h['title'] for h in headlines]
            self.assertIn('TSMC reports strong Q3 earnings results', titles)
            self.assertIn('TSMC announces new Arizona plant expansion', titles)
            self.assertNotIn('鉅亨速報：外資賣超前十名', titles)
            self.assertNotIn('盤後統整：今日熱門股', titles)

    def test_source_check_us(self):
        """Case F: Verify US sources update"""
        url = self.fetcher._build_query(ticker='AAPL', market='US')
        self.assertIn('site%3Afinance.yahoo.com', url)
        self.assertIn('site%3Amarketwatch.com', url)
        self.assertIn('site%3Abarrons.com', url) # New source
        self.assertIn('site%3Afool.com', url)    # New source
        self.assertIn('site%3Aseekingalpha.com', url) # New source
        self.assertIn('site%3Abenzinga.com', url) # New source
        self.assertNotIn('site%3Awsj.com', url)

    @patch('src.data.news_fetcher.feedparser.parse')
    def test_ranking_and_dedup(self, mock_parse):
        """Case G: Verify ranking (top 5) and deduplication"""
        entries = []
        # Add 20 entries
        # Add 20 entries with distinct titles
        distinct_titles = [f"Unique News {i} {chr(65+i)}" for i in range(20)] # Still might be similar?
        # "Unique News 0 A", "Unique News 1 B".
        # "Unique News " (12 chars). "0 A" (3 chars).
        # Ratio ~ 24/30 = 0.8. Too similar.
        # Let's use numbers as prefix.
        distinct_titles = [f"{i} is a unique number for news headline" for i in range(20)]
        # "0 is a unique..." vs "1 is a unique...".
        # " is a unique..." is common.
        # We need completely different strings.
        # Let's just use a list of 20 distinct words repeated? No.
        # How about:
        distinct_titles = [
            "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India", "Juliet",
            "Kilo", "Lima", "Mike", "November", "Oscar", "Papa", "Quebec", "Romeo", "Sierra", "Tango"
        ]
        
        for i in range(20):
            entries.append({
                'title': distinct_titles[i],
                'link': f'http://example.com/{i}',
                'published': '2023-01-01',
                'summary': 'Summary'
            })
        # Add duplicate
        # Add duplicate
        entries.append({
            'title': 'Alpha', # Duplicate of first one
            'link': 'http://example.com/dup',
            'published': '2023-01-01',
            'summary': 'Summary'
        })
            
        mock_feed = MagicMock()
        mock_feed.entries = entries
        mock_parse.return_value = mock_feed
        
        headlines = self.fetcher.fetch_headlines(ticker='AAPL', market='US')
        
        # Should be capped at 10 (Updated from 5)
        self.assertEqual(len(headlines), 10)
        # Should be unique (News 0 should appear only once)
        titles = [h['title'] for h in headlines]
        self.assertEqual(len(set(titles)), 10)

    @patch('src.data.news_fetcher.feedparser.parse')
    def test_volume_resilience(self, mock_parse):
        """Case H: Verify volume resilience (45 noise, 5 valid)"""
        entries = []
        # Add 45 noise entries
        for i in range(45):
            entries.append({
                'title': f'鉅亨速報：外資賣超前十名 {i}',
                'link': f'http://noise.com/{i}',
                'published': '2023-01-01',
                'summary': 'Noise'
            })
        # Add 5 valid entries with distinct titles
        valid_titles = ["Apple", "Banana", "Cherry", "Date", "Elderberry"]
        for i in range(5):
            entries.append({
                'title': valid_titles[i],
                'link': f'http://valid.com/{i}',
                'published': '2023-01-01',
                'summary': 'Summary'
            })
            
        mock_feed = MagicMock()
        mock_feed.entries = entries
        mock_parse.return_value = mock_feed
        
        headlines = self.fetcher.fetch_headlines(ticker='2330', market='TW')
        
        # Should return 5 valid entries (since we only added 5 valid ones)
        self.assertEqual(len(headlines), 5)
        titles = [h['title'] for h in headlines]
        titles = [h['title'] for h in headlines]
        for t in valid_titles:
            self.assertIn(t, titles)

    @patch('src.data.news_fetcher.feedparser.parse')
    def test_high_volume_resilience(self, mock_parse):
        """Case I: Verify high volume resilience (100 items, 90 noise)"""
        entries = []
        # Add 90 noise entries
        for i in range(90):
            entries.append({
                'title': f'鉅亨速報：外資賣超前十名 {i}',
                'link': f'http://noise.com/{i}',
                'published': '2023-01-01',
                'summary': 'Noise'
            })
        # Add 10 valid entries
        valid_titles = [
            "Apple", "Banana", "Cherry", "Date", "Elderberry",
            "Fig", "Grape", "Honeydew", "Kiwi", "Lemon"
        ]
        for i in range(10):
            entries.append({
                'title': valid_titles[i],
                'link': f'http://valid.com/{i}',
                'published': '2023-01-01',
                'summary': 'Summary'
            })
            
        mock_feed = MagicMock()
        mock_feed.entries = entries
        mock_parse.return_value = mock_feed
        
        headlines = self.fetcher.fetch_headlines(ticker='2330', market='TW')
        
        # Should return 5 valid entries (top 5 from the 10 valid ones) -> Now top 10
        # We added 10 valid entries. So we should get 10.
        self.assertEqual(len(headlines), 10)
        titles = [h['title'] for h in headlines]
        # Since we append valid news AFTER noise in the mock list, and fetcher takes first 100,
        # we need to make sure the valid news are within the first 100.
        # In this test case, 90+10 = 100, so all are considered.
        # The valid news are at the end.
        # The fetcher takes entries[:100].
        # Then filters noise.
        # Then takes top 5.
        
        # Verify that we got valid news
        # Since we have distinct fruit names, just check if they are in valid_titles
        for title in titles:
            self.assertIn(title, valid_titles)
    @patch('src.data.news_fetcher.feedparser.parse')
    def test_impact_ranking(self, mock_parse):
        """Case J: Verify Impact Ranking Algorithm"""
        # Create 3 news items
        # 1. Low impact (latest)
        # 2. High impact (older) - Tier 1 Keyword "EPS"
        # 3. Medium impact (older) - Tier 2 Keyword "大漲"
        
        entries = [
            {
                'title': '台積電盤中微幅震盪', 
                'link': 'http://news1.com', 
                'published': '2025-11-28T12:00:00Z', 
                'summary': 'Normal news'
            },
            {
                'title': '台積電公布 Q3 財報，EPS 創新高', 
                'link': 'http://news2.com', 
                'published': '2025-11-28T10:00:00Z', 
                'summary': 'High impact'
            },
            {
                'title': '台積電股價大漲 5%', 
                'link': 'http://news3.com', 
                'published': '2025-11-28T11:00:00Z', 
                'summary': 'Medium impact'
            }
        ]
        
        mock_feed = MagicMock()
        mock_feed.entries = entries
        mock_parse.return_value = mock_feed
        
        headlines = self.fetcher.fetch_headlines(ticker='2330', market='TW')
        
        # Expected Order:
        # 1. EPS (Tier 1) -> Highest Score
        # 2. 大漲 (Tier 2) -> Medium Score
        # 3. 震盪 (No Keyword) -> Lowest Score
        
        self.assertEqual(len(headlines), 3)
        self.assertIn('EPS', headlines[0]['title'])
        self.assertIn('大漲', headlines[1]['title'])
        self.assertIn('震盪', headlines[2]['title'])

    @patch('src.data.news_fetcher.feedparser.parse')
    def test_impact_ranking_cross_market(self, mock_parse):
        """Case K: Verify Impact Ranking Cross Market (US)"""
        entries = [
            {'title': 'Apple stock moves sideways', 'link': 'http://n1.com', 'published': '2025-11-28T12:00:00Z', 'summary': '.'},
            {'title': 'Apple reports record Revenue', 'link': 'http://n2.com', 'published': '2025-11-28T10:00:00Z', 'summary': '.'}
        ]
        
        mock_feed = MagicMock()
        mock_feed.entries = entries
        mock_parse.return_value = mock_feed
        
        headlines = self.fetcher.fetch_headlines(ticker='AAPL', market='US')
        
        # Revenue (Tier 1) should be first
        self.assertIn('Revenue', headlines[0]['title'])

    @patch('src.data.news_fetcher.feedparser.parse')
    def test_fuzzy_deduplication(self, mock_parse):
        """Case L: Verify Fuzzy Deduplication"""
        entries = [
            {'title': 'TSMC revenue jumps 10%', 'link': 'http://n1.com', 'published': '2025-11-28T12:00:00Z', 'summary': '.'},
            {'title': 'TSMC revenue surges 10%', 'link': 'http://n2.com', 'published': '2025-11-28T12:05:00Z', 'summary': '.'}, # Similar (>0.8)
            {'title': 'Different news', 'link': 'http://n3.com', 'published': '2025-11-28T10:00:00Z', 'summary': '.'}
        ]
        
        mock_feed = MagicMock()
        mock_feed.entries = entries
        mock_parse.return_value = mock_feed
        
        headlines = self.fetcher.fetch_headlines(ticker='TSM', market='US')
        
        # Should have 2 entries (1 deduped, 1 different)
        self.assertEqual(len(headlines), 2)
        titles = [h['title'] for h in headlines]
        self.assertIn('Different news', titles)
        # One of the similar ones should be present
        self.assertTrue('TSMC revenue jumps 10%' in titles or 'TSMC revenue surges 10%' in titles)

if __name__ == '__main__':
    unittest.main()
