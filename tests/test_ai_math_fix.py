
import pytest
from src.ai.llm_client import LLMClient

class TestAIMathFix:
    def setup_method(self):
        # We assume LLMClient can be instantiated without API key if we don't call generate
        # But looking at code, it might try to check env vars. 
        # clean_code is a static-like utility method, so it should be fine.
        self.client = LLMClient(api_key="dummy")

    def test_clean_code_math_symbols(self):
        """Case 1: Unicode math operators should be normalized"""
        
        dirty_code = """
        def logic(a, b):
            if a ≤ b:
                return a × b
            if a ≥ b:
                return a ÷ b
            if a ≠ b:
                return 0
        """
        
        expected_code = """
        def logic(a, b):
            if a <= b:
                return a * b
            if a >= b:
                return a / b
            if a != b:
                return 0
        """
        
        # We need to strip standard formatting from expected to compare accurately
        # But clean_code mostly replaces symbols. 
        # Let's check by containment or direct string replacement verification
        
        cleaned = self.client.clean_code(dirty_code)
        
        assert "<=" in cleaned
        assert ">=" in cleaned
        assert "!=" in cleaned
        assert "*" in cleaned  # Careful, * could be in args
        assert "/" in cleaned
        
        assert "≤" not in cleaned
        assert "≥" not in cleaned
        assert "≠" not in cleaned
        assert "×" not in cleaned
        assert "÷" not in cleaned
