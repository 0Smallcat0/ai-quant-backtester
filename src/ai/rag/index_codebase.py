import os
import glob
from src.ai.rag.ast_chunker import ASTChunker
from src.ai.rag.store import VectorStore

def index_codebase(root_dir: str = "src", persist_dir: str = "./db/chroma"):
    """
    Scans the codebase, chunks files, and indexes them into ChromaDB.
    """
    print(f"Indexing codebase from {root_dir}...")
    
    chunker = ASTChunker()
    store = VectorStore(persist_directory=persist_dir)
    
    if not store.collection:
        print("VectorStore not available (ChromaDB missing?). Exiting.")
        return

    # Find all Python files
    # Recursive glob
    files = glob.glob(os.path.join(root_dir, "**", "*.py"), recursive=True)
    print(f"Found {len(files)} Python files.")
    
    all_docs = []
    all_metas = []
    all_ids = []
    
    for i, file_path in enumerate(files):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            
            chunks = chunker.chunk_file(code, file_path)
            
            for j, chunk in enumerate(chunks):
                # We store content usually as function/class body
                # Metadata helps retrieval
                doc_id = f"{file_path}_{j}"
                
                # Context enrichment for LLM
                enriched_content = f"# File: {file_path}\n"
                if chunk.context:
                    enriched_content += f"# Context: {chunk.context}\n"
                enriched_content += chunk.content
                
                all_docs.append(enriched_content)
                all_metas.append({
                    "name": chunk.name,
                    "type": chunk.type,
                    "file": file_path,
                    "line_start": chunk.line_start
                })
                all_ids.append(doc_id)
                
        except Exception as e:
            print(f"Failed to process {file_path}: {e}")

    if all_docs:
        print(f"Adding {len(all_docs)} chunks to store...")
        store.add_documents(all_docs, all_metas, all_ids)
        print("Indexing Complete.")
    else:
        print("No chunks found.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Index codebase for RAG.")
    parser.add_argument("--root", default="src", help="Root directory to scan")
    args = parser.parse_args()
    
    index_codebase(args.root)
