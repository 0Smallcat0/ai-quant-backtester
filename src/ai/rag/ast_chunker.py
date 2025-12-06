import ast
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CodeChunk:
    name: str
    type: str  # 'function', 'class', 'method'
    content: str
    line_start: int
    line_end: int
    context: str = "" # Parent class name, etc.

class ASTChunker:
    """
    Parses Python code and extracts functions and methods as chunks.
    """

    def chunk_file(self, code: str, filename: str) -> List[CodeChunk]:
        """
        Chunks a single file content.
        """
        chunks = []
        try:
            tree = ast.parse(code)
            lines = code.splitlines()

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if it's a top-level function or method
                    # ast.walk doesn't strictly preserve hierarchy, so we need a better traversal if we want context.
                    # Standard ast.walk is BFS (kinda). 
                    # Let's use NodeVisitor for cleaner context tracking?
                    # Or just a simple recursive generic_visit.
                    pass
            
            # Use a visitor to track context
            visitor = ChunkVisitor(lines)
            visitor.visit(tree)
            chunks = visitor.chunks

        except SyntaxError:
            print(f"Syntax Error parsing {filename}")
            return []
            
        return chunks

class ChunkVisitor(ast.NodeVisitor):
    def __init__(self, source_lines: List[str]):
        self.chunks: List[CodeChunk] = []
        self.source_lines = source_lines
        self.context_stack = [] # Stack of class names

    def visit_ClassDef(self, node):
        self.context_stack.append(node.name)
        # We could also chunk the class itself (docstring + init?)
        # For now, just visit children to get methods.
        self.generic_visit(node)
        self.context_stack.pop()

    def visit_FunctionDef(self, node):
        # Extract source code for this function
        # node.lineno is 1-indexed start
        # node.end_lineno is end
        
        start = node.lineno - 1
        end = node.end_lineno
        
        # Careful with decorators, they might be before lineno? 
        # Python 3.8+ has decorator_list.
        # But for simplicity, let's just grab the range.
        
        content = "\n".join(self.source_lines[start:end])
        
        chunk_type = "method" if self.context_stack else "function"
        context = self.context_stack[-1] if self.context_stack else ""
        
        chunk = CodeChunk(
            name=node.name,
            type=chunk_type,
            content=content,
            line_start=node.lineno,
            line_end=node.end_lineno,
            context=context
        )
        self.chunks.append(chunk)
        
        # Do not visit children (nested functions) if we want flat chunks
        # Or do we? If we visit children, we get inner functions.
        # Let's Skip children to avoid redundancy.
        # self.generic_visit(node) 
