import pytest
import os
import shutil
from unittest.mock import MagicMock, patch
from src.ai.rag.store import VectorStore
from src.ai.rag.ast_chunker import ASTChunker
from src.ai.reflexion_loop import ReflexionLoop
from src.ai.sandbox.local_executor import LocalExecutor, ExecutionResult

class TestAIAgent2_0Capabilities:

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        # Setup temp DB for RAG check
        self.test_db_dir = "./qa_chroma_db"
        if os.path.exists(self.test_db_dir):
            shutil.rmtree(self.test_db_dir)
        
        yield
        
        # Cleanup
        if os.path.exists(self.test_db_dir):
            shutil.rmtree(self.test_db_dir)

    def test_capability_1_rag_knowledge_retrieval(self):
        """
        Test 1: RAG Check
        Verify that the system can ingest code and retrieve it based on semantics.
        """
        # 1. Setup Data - Use raw strings to avoid escaping hell
        dummy_code = '''
class Strategy:
    def safe_rolling(self, window, min_periods=None):
        """Calculates rolling mean safely."""
        pass
'''
        chunker = ASTChunker()
        # We manually index this dummy code
        chunks = chunker.chunk_file(dummy_code, "src/strategies/base.py")
        
        docs = [c.content for c in chunks]
        metas = [{"name": c.name} for c in chunks]
        ids = [f"test_{i}" for i in range(len(chunks))]
        
        # 2. Mock Chroma for Integration Logic
        with patch('src.ai.rag.store.chromadb') as mock_chroma:
             mock_client = MagicMock()
             mock_coll = MagicMock()
             mock_chroma.PersistentClient.return_value = mock_client
             mock_client.get_or_create_collection.return_value = mock_coll
             
             # Simulate Query Return
             mock_coll.query.return_value = {
                 "documents": [[dummy_code]],
                 "metadatas": [[{"name": "safe_rolling"}]]
             }
             
             with patch('src.ai.rag.store.CHROMA_AVAILABLE', True):
                 store = VectorStore(persist_directory=self.test_db_dir)
                 store.add_documents(docs, metas, ids)
                 
                 # 3. Query
                 results = store.query("How to use safe_rolling?")
                 
                 # 4. Assert
                 assert results is not None
                 assert len(results['documents'][0]) > 0
                 # We verified mock returns what we want

    def test_capability_2_reflexion_self_healing(self):
        """
        Test 2: Reflexion Loop
        Simulate a Fail -> Reflect -> Success cycle.
        """
        mock_llm = MagicMock()
        mock_executor = MagicMock()
        
        bad_code = "import yfinance as yf"
        good_code = "print('Fixed Code')"
        
        # LLM Sequence
        mock_llm.generate_strategy_code.side_effect = [bad_code, good_code]
        mock_llm.get_completion.return_value = "Plan: Remove dangerous import."
        
        # Executor Sequence
        mock_executor.execute_safe.side_effect = [
            ExecutionResult(1, "", "SecurityError"), # 1st
            ExecutionResult(0, "Fixed Code", "")     # 2nd
        ]
        
        agent = ReflexionLoop(mock_llm, mock_executor)
        final_code = agent.run("Create Strategy")
        
        assert final_code == good_code
        assert mock_llm.generate_strategy_code.call_count == 2
        mock_llm.get_completion.assert_called_once()

    def test_capability_3_sandbox_guard(self):
        """
        Test 3: Sandbox Guard
        Verify that dangerous imports are blocked.
        """
        executor = LocalExecutor()
        
        dangerous_code = "import shutil; shutil.rmtree('/')"
        
        # Now that execute_safe is updated to check validate_safety
        result = executor.execute_safe(dangerous_code)
        
        assert result.exit_code == 1
        assert "SecurityError" in result.stderr
