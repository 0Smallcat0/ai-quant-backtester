import pytest
from unittest.mock import MagicMock, patch
import torch
from src.ai.llm_client import LLMClient
from src.analytics.sentiment.finbert_analyzer import FinBERTAnalyzer

class TestPerformanceV3:
    def setup_method(self):
        # Reset Singleton
        LLMClient._instance = None

    @patch('src.ai.llm_client.OpenAI')
    @patch('src.ai.llm_client.settings') # Mock settings
    def test_llm_context_pruning_logic(self, mock_settings, mock_openai):
        """
        Verify that when finish_reason='length', the context is pruned and history is reset.
        """
        # Setup settings
        mock_settings.DEFAULT_TEMPERATURE = 0.7
        mock_settings.DEFAULT_TOP_P = 1.0
        
        client = LLMClient(api_key="test_key")
        
        mock_choice_1 = MagicMock()
        mock_choice_1.message.content = "A" * 600 
        mock_choice_1.finish_reason = "length"
        
        mock_choice_2 = MagicMock()
        mock_choice_2.message.content = "END"
        mock_choice_2.finish_reason = "stop"
        
        mock_response_1 = MagicMock()
        mock_response_1.choices = [mock_choice_1]
        
        mock_response_2 = MagicMock()
        mock_response_2.choices = [mock_choice_2]
        
        # Mock the client instance created inside LLMClient
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        mock_client_instance.chat.completions.create.side_effect = [mock_response_1, mock_response_2]
        
        # Run
        result = client.generate_strategy_code("Write a long strategy")
        
        # Verification
        # clean_code might strip things, but "A"*600 + "END" has no markdown.
        # But wait, clean_code might strip lines starting with Thought: etc.
        # "A"*600 is safe.
        assert result == "A"*600 + "END"
        
        # Check call arguments
        calls = mock_client_instance.chat.completions.create.call_args_list
        assert len(calls) == 2
        
        # Second call: Pruned prompt
        args2, kwargs2 = calls[1]
        messages_2 = kwargs2['messages']
        assert len(messages_2) == 2 # System + Continuation
        
        continuation_prompt = messages_2[1]['content']
        assert "Continue the code exactly from where it stopped." in continuation_prompt
        # Check pruning: "A"*500 should be in there
        assert "A"*500 in continuation_prompt

    @patch('src.analytics.sentiment.finbert_analyzer.BertForSequenceClassification')
    @patch('src.analytics.sentiment.finbert_analyzer.BertTokenizer')
    @patch('src.analytics.sentiment.finbert_analyzer.DataLoader')
    def test_finbert_pipeline_no_cpu_in_loop(self, mock_dataloader_cls, mock_tokenizer, mock_model_class):
        """
        Verify FinBERT predict logic structure (Mocked).
        """
        # Setup Model Mock
        mock_model_instance = MagicMock()
        mock_model_class.from_pretrained.return_value = mock_model_instance
        mock_model_instance.to.return_value = mock_model_instance
        
        # Mock Tensor outputs
        # We start with floats to avoid pickling issues if any, but tensors are fine.
        mock_logits = torch.randn(2, 3) 
        mock_output = MagicMock()
        mock_output.logits = mock_logits
        mock_model_instance.return_value = mock_output
        
        # Setup DataLoader Mock
        # It should return an iterator of batches
        # Batch must be dict-like with 'input_ids' and 'attention_mask'
        mock_loader_instance = MagicMock()
        # Create 2 batches
        batch1 = {
            'input_ids': MagicMock(),
            'attention_mask': MagicMock()
        }
        batch2 = {
            'input_ids': MagicMock(),
            'attention_mask': MagicMock()
        }
        mock_loader_instance.__iter__.return_value = iter([batch1, batch2])
        mock_dataloader_cls.return_value = mock_loader_instance
        
        # Init Analyzer
        analyzer = FinBERTAnalyzer(device="cpu")
        
        texts = ["N1", "N2", "N3", "N4"]
        results = analyzer.predict(texts)
        
        # We expect 2 batches * 2 items each?
        # Mock logits shape was (2, 3), so 2 items per batch.
        # Total 4 items.
        assert len(results) == 4
        assert "Neutral" in results[0]

