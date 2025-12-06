import pytest
from src.ai.rag.ast_chunker import ASTChunker, CodeChunk

class TestASTChunker:
    def setup_method(self):
        self.chunker = ASTChunker()

    def test_chunk_simple_function(self):
        code = """
def my_func(a, b):
    \"\"\"This is a docstring.\"\"\"
    return a + b
"""
        chunks = self.chunker.chunk_file(code, "test_file.py")
        assert len(chunks) == 1
        assert chunks[0].name == "my_func"
        assert chunks[0].type == "function"
        assert "This is a docstring" in chunks[0].content
        assert chunks[0].line_start == 2 # 1-indexed? ast usually 1-indexed.

    def test_chunk_class_with_methods(self):
        code = """
class MyClass:
    \"\"\"Class doc.\"\"\"
    
    def method_one(self):
        pass
        
    def method_two(self):
        return True
"""
        # We want to chunk Methods separately but also maybe the Class?
        # For RAG, methods are usually most useful.
        # Implementation decision: Extract top-level Functions, Classes (as summary), and Methods.
        chunks = self.chunker.chunk_file(code, "test_class.py")
        
        # Expectation: 1 Class chunk, 2 Method chunks? Or just 2 Method chunks with Context?
        # Plan says: "Enriches chunks with class docstrings and parent context".
        # Let's target: 2 Method chunks, each having "MyClass" in context.
        
        method_chunks = [c for c in chunks if c.type == "method"]
        class_chunks = [c for c in chunks if c.type == "class"]
        
        assert len(method_chunks) == 2
        assert method_chunks[0].context == "MyClass"
        assert method_chunks[0].name == "method_one"
        
        # Ideally we also want the whole class definition as one chunk? 
        # For now let's assert we get methods at least.

    def test_chunk_nested_functions(self):
        # Should probably ignore nested functions or treat them as part of parent?
        # Simplest: Just top level or class methods.
        pass
