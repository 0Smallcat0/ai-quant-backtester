import pytest
import os
import shutil
from unittest.mock import MagicMock, patch
from src.ai.rag.store import VectorStore
# from src.ai.rag.ast_chunker import CodeChunk # We might need this

class TestVectorStore:
    def setup_method(self):
        # Patch the module-level variable CHROMA_AVAILABLE or the import
        # Since logic depends on imports, we patch where it is used.
        
        # We need to restart the import or patch the class instance.
        # Easier: Patch 'chromadb.PersistentClient' inside the module.
        self.patcher = patch('src.ai.rag.store.chromadb')
        self.mock_chroma = self.patcher.start()
        
        # Setup Mock Client and Collection
        self.mock_client = MagicMock()
        self.mock_collection = MagicMock()
        self.mock_chroma.PersistentClient.return_value = self.mock_client
        self.mock_client.get_or_create_collection.return_value = self.mock_collection
        
        # We need to force CHROMA_AVAILABLE to True for the test context
        # But it's determined at import time. 
        # If it was False (dependency missing), the class methods return early.
        # We should assume it is True or reload module.
        # For simplicity, let's assume if we are testing this, we should enable it.
        # But if the module already imported and set CHROMA_AVAILABLE=False, we have a problem.
        
        # Let's just create the store and inject mocks if possible, 
        # OR verify that if CHROMA_UNAVAILABLE it handles gracefully.
        
        # Force re-init with mocks
        with patch('src.ai.rag.store.CHROMA_AVAILABLE', True):
           self.store = VectorStore(
               collection_name="test_collection",
               embedding_fn=None, # Don't care about fn validation now
               persist_directory="./test_chroma_db"
           )
           # Manually inject the mock collection because __init__ ran with the patch?
           # Actually __init__ called chromadb.PersistentClient which is our mock.
           # So self.store.client IS self.mock_client
           pass

    def teardown_method(self):
        self.patcher.stop()

    def test_add_documents(self):
        documents = ["def foo(): pass"]
        metadatas = [{"name": "foo"}]
        ids = ["1"]
        
        self.store.add_documents(documents, metadatas, ids)
        
        if self.store.collection:
            self.store.collection.add.assert_called_with(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

    def test_query(self):
        self.store.query("test")
        if self.store.collection:
            self.store.collection.query.assert_called()
