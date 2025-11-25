import unittest
from unittest.mock import patch, mock_open
from src.ai.tools import read_file, write_file, list_files
import os

class TestToolPerformance(unittest.TestCase):
    
    def setUp(self):
        # Clear caches before each test if they exist
        if hasattr(read_file, 'cache_clear'):
            read_file.cache_clear()
        if hasattr(list_files, 'cache_clear'):
            list_files.cache_clear()

    @patch('builtins.open', new_callable=mock_open, read_data="content")
    @patch('os.path.abspath', return_value=os.path.join(os.getcwd(), "test.txt"))
    @patch('os.path.splitext', return_value=("test", ".txt"))
    @patch('src.ai.tools._validate_path', return_value=True)
    def test_read_file_caching(self, mock_validate, mock_splitext, mock_abspath, mock_file):
        """
        Case A: Verify read_file is cached.
        """
        # First call
        read_file("test.txt")
        # Second call
        read_file("test.txt")
        
        # Open should be called only once due to caching
        self.assertEqual(mock_file.call_count, 1)

    @patch('builtins.open', new_callable=mock_open, read_data="content")
    @patch('os.path.abspath', return_value=os.path.join(os.getcwd(), "test.txt"))
    @patch('os.path.splitext', return_value=("test", ".txt"))
    @patch('src.ai.tools._validate_path', return_value=True)
    @patch('os.makedirs')
    def test_write_file_clears_cache(self, mock_makedirs, mock_validate, mock_splitext, mock_abspath, mock_file):
        """
        Case B: Verify write_file clears the cache.
        """
        # First read
        read_file("test.txt")
        self.assertEqual(mock_file.call_count, 1)
        
        # Write (should clear cache)
        write_file("test.txt", "new content")
        
        # Second read
        read_file("test.txt")
        # Open should be called twice (once for first read, once for second read after invalidation)
        # Note: write_file also calls open, so total open calls = 1 (read) + 1 (write) + 1 (read) = 3
        # But we are checking read_file's impact. 
        # Let's check the mock_file call count carefully.
        # mock_file is the mock object for 'open'.
        
        # 1. read_file -> open('r')
        # 2. write_file -> open('w')
        # 3. read_file -> open('r')
        
        self.assertEqual(mock_file.call_count, 3)

if __name__ == '__main__':
    unittest.main()
