import unittest
import threading
import time
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from src.data_engine import DataManager
from src.backtest_engine import BacktestEngine
from src.ai.llm_client import LLMClient

class TestPerformanceV2(unittest.TestCase):
    
    def test_db_connection_pooling(self):
        """
        Verify that each thread gets a unique connection object (Thread-Local).
        """
        dm = DataManager("test_perf.db")
        dm.init_db()
        
        results = {}
        
        def get_conn_id(thread_name):
            conn = dm.get_connection()
            results[thread_name] = id(conn)
            # Verify it's open
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            
        threads = []
        for i in range(5):
            t = threading.Thread(target=get_conn_id, args=(f"T{i}",))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        # All IDs should be unique
        ids = list(results.values())
        self.assertEqual(len(set(ids)), 5, "Each thread should have a unique connection ID")
        
        # Verify Reuse in same thread
        conn1 = dm.get_connection()
        conn2 = dm.get_connection()
        self.assertEqual(id(conn1), id(conn2), "Same thread should reuse connection")

    def test_backtest_performance(self):
        """
        Benchmark Backtest Engine Run < 0.2s for 5000 rows.
        """
        # Setup Data
        periods = 5000 # Approx 20 years of daily data
        dates = pd.date_range(start="2000-01-01", periods=periods)
        data = pd.DataFrame({
            "open": np.random.rand(periods) * 100,
            "high": np.random.rand(periods) * 100,
            "low": np.random.rand(periods) * 100,
            "close": np.random.rand(periods) * 100,
            "volume": np.random.rand(periods) * 1000000
        }, index=dates)
        
        signals = pd.Series(np.random.choice([0, 1, -1], size=periods), index=dates, name="signal")
        
        engine = BacktestEngine(initial_capital=100000)
        
        start_time = time.time()
        engine.run(data, signals)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"\n[Benchmark] Backtest 5000 rows: {duration:.4f}s")
        
        self.assertLess(duration, 0.20, f"Backtest too slow: {duration:.4f}s > 0.2s")

    @patch('src.ai.llm_client.OpenAI')
    @patch('src.ai.llm_client.os.getenv')
    def test_llm_context_pruning(self, mock_getenv, mock_openai):
        """
        Verify that LLMClient prunes context on 'length' finish reason.
        """
        mock_getenv.return_value = "fake_key"
        
        # Setup Mock Response behaviors
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        
        # Turn 1: Returns huge text, finish_reason='length'
        choice1 = MagicMock()
        choice1.finish_reason = "length"
        choice1.message.content = "A" * 1000 # Big chunk
        
        response1 = MagicMock()
        response1.choices = [choice1]
        
        # Turn 2: Returns "Done", finish_reason='stop'
        choice2 = MagicMock()
        choice2.finish_reason = "stop"
        choice2.message.content = "Done"
        
        response2 = MagicMock()
        response2.choices = [choice2]
        
        # Chain responses
        mock_client_instance.chat.completions.create.side_effect = [response1, response2]
        
        client = LLMClient(api_key="test")
        # We need to clear cache or use a fresh method call (cache is on method)
        # But we can verify by checking the calls to create
        
        # We invoke generate_strategy_code
        # Note: clean_code might fail on "A"*1000, so we wrap in try/except or ensure clean_code works
        try:
            client.generate_strategy_code("Test Prompt", model="gpt-4o")
        except:
            pass
            
        # Verify Call Args
        calls = mock_client_instance.chat.completions.create.call_args_list
        self.assertEqual(len(calls), 2)
        
        # Check 2nd call arguments
        # args[1] is kwargs (model, messages, etc)
        # In call_args, it's (args, kwargs)
        args2, kwargs2 = calls[1]
        messages2 = kwargs2['messages']
        
        # Expected: 2 messages (System, User-Continuation)
        self.assertEqual(len(messages2), 2)
        content2 = messages2[1]['content']
        
        # Check if prompts says "You stopped at..."
        self.assertIn("You stopped at", content2)
        # Check if it contains the pruning (last 500 chars of A's)
        self.assertIn("A"*500, content2)
        # Check if it DOES NOT contain full 1000 chars (implied by "A"*500 being the context, 
        # but wait - if I constructed it correctly, it should only have the tail)
        
        # Actually, "A"*500 is in there. What we verify is that we didn't send the FULL previous history 
        # appended as Assistant message.
        # Original (bad) behavior: messages would be [Sys, User, Assistant(1000 A's), User(Continue)]
        # New behavior: messages = [Sys, User(You stopped at... 500 A's)]
        
        self.assertNotEqual(messages2[0]['role'], 'user') # Should be system
        self.assertEqual(messages2[1]['role'], 'user') 

if __name__ == '__main__':
    unittest.main()
