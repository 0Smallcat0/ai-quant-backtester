import pytest
from unittest.mock import MagicMock, patch
from src.ai.reflexion_loop import ReflexionLoop
from src.ai.sandbox.local_executor import ExecutionResult

class TestReflexionLoop:
    def setup_method(self):
        self.mock_llm = MagicMock()
        self.mock_executor = MagicMock()
        self.loop = ReflexionLoop(llm_client=self.mock_llm, executor=self.mock_executor)

    def test_run_success_first_try(self):
        # Scenario: Generates valid code immediately
        target_code = "print('success')"
        self.mock_llm.generate_strategy_code.return_value = target_code
        self.mock_executor.execute_safe.return_value = ExecutionResult(0, "success", "")

        result = self.loop.run("Task: Create strategy")
        
        assert result == target_code
        self.mock_llm.generate_strategy_code.assert_called_once()
        # Reflexion should NOT be called
        self.mock_llm.get_completion.assert_not_called()

    def test_run_fail_then_success(self):
        # Scenario: 1st attempt fails, 2nd passes
        bad_code = "print('error')"
        good_code = "print('fixed')"
        
        # Mock LLM sequence: 
        # 1. generate (first try) -> returns bad_code
        # 2. get_completion (reflexion) -> returns "Reflection: Fix syntax"
        # 3. generate (retry) -> returns good_code
        self.mock_llm.generate_strategy_code.side_effect = [bad_code, good_code]
        self.mock_llm.get_completion.return_value = "DIAGNOSIS: Syntax Error\nPLAN: Fix it"
        
        # Mock Executor sequence:
        # 1. Fails
        # 2. Succeeds
        self.mock_executor.execute_safe.side_effect = [
            ExecutionResult(1, "", "Syntax Error"), # 1st
            ExecutionResult(0, "fixed", "")         # 2nd
        ]

        result = self.loop.run("Task: Create strategy")
        
        assert result == good_code
        assert self.mock_llm.generate_strategy_code.call_count == 2
        self.mock_llm.get_completion.assert_called_once() # Reflexion called

    def test_run_max_retries_exceeded(self):
        # Scenario: Always fails
        self.mock_llm.generate_strategy_code.return_value = "bad code"
        self.mock_executor.execute_safe.return_value = ExecutionResult(1, "", "Error")
        self.mock_llm.get_completion.return_value = "Plan: fix"

        with pytest.raises(RuntimeError):
            self.loop.run("Task: Fail", max_retries=2)
            
        assert self.mock_llm.generate_strategy_code.call_count == 2 + 1 # Initial + 2 retries

    def test_run_with_rag(self):
        # Scenario: VectorStore provides context
        mock_store = MagicMock()
        mock_store.query.return_value = {"documents": [["def relevant_func(): pass"]]}
        
        loop_with_rag = ReflexionLoop(self.mock_llm, self.mock_executor, vector_store=mock_store)
        
        self.mock_llm.generate_strategy_code.return_value = "code"
        self.mock_executor.execute_safe.return_value = ExecutionResult(0, "", "")
        
        loop_with_rag.run("Task: Use RAG")
        
        # Verify Store Query
        mock_store.query.assert_called_with("Task: Use RAG", n_results=3)
        
        # Verify Prompt Enrichment
        # The prompt passed to generate_strategy_code should contain the context
        call_args = self.mock_llm.generate_strategy_code.call_args[0][0]
        assert "### Reference Code" in call_args
        assert "def relevant_func(): pass" in call_args
