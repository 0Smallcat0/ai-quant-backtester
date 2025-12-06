from typing import List, Tuple, Optional
import sys
# Assuming these exist or will serve as interfaces
# from src.ai.llm_client import LLMClient # We pass instance
# from src.ai.sandbox.local_executor import LocalExecutor # We pass instance

class ReflexionLoop:
    """
    Implements a self-healing code generation loop.
    1. Generate Code
    2. Execute (Sandbox)
    3. If Fail -> Reflect -> Retry
    4. If Success -> Return Code
    """
    def __init__(self, llm_client, executor, vector_store=None):
        self.llm_client = llm_client
        self.executor = executor
        self.vector_store = vector_store

    def run(self, task: str, max_retries: int = 3) -> str:
        """
        Executes the Reflexion loop.
        """
        # 0. RAG Enrichment
        context = ""
        if self.vector_store:
            # Query for relevant code examples
            results = self.vector_store.query(task, n_results=3)
            if results and results['documents']:
                # Flatten list of lists
                docs = [d for sublist in results['documents'] for d in sublist]
                context = "\n".join(docs[:3])
        
        # Inject Context into Task
        enhanced_task = task
        if context:
            enhanced_task = f"{task}\n\n### Reference Code (Internal API):\n{context}"

        current_code = self.llm_client.generate_strategy_code(enhanced_task)
        history: List[Tuple[str, str, str]] = [] # (code, error, reflection)

        for attempt in range(max_retries + 1):
            # 1. Execute
            result = self.executor.execute_safe(current_code)
            
            # 2. Check Success
            if result.exit_code == 0:
                return current_code
            
            # 3. Handle Failure
            error_msg = result.stderr
            if not error_msg:
                error_msg = f"Unknown Error (Exit Code: {result.exit_code})"

            if attempt == max_retries:
                raise RuntimeError(f"Max retries ({max_retries}) exceeded. Last error: {error_msg}")

            # 4. Reflection Step
            reflection = self._generate_reflection(task, current_code, error_msg)
            history.append((current_code, error_msg, reflection))
            
            # 5. Retry Step (Generate new code with context)
            new_prompt = self._construct_retry_prompt(enhanced_task, history)
            current_code = self.llm_client.generate_strategy_code(new_prompt)

        return current_code

    def _generate_reflection(self, task: str, code: str, error: str) -> str:
        """
        Asks the LLM to analyze the error and propose a fix.
        """
        messages = [
            {"role": "system", "content": "You are a Senior Python Debugger. Analyze the error and provide a concise 'Root Cause' and 'Fix Plan'. Do NOT generate code here, just the plan."},
            {"role": "user", "content": f"Task: {task}\n\nCode:\n```python\n{code}\n```\n\nError:\n{error}\n\nPlease analyze why it failed and what strictly needs to be changed."}
        ]
        return self.llm_client.get_completion(messages)

    def _construct_retry_prompt(self, task: str, history: List[Tuple[str, str, str]]) -> str:
        """
        Constructs a prompt that includes the original task and previous failures.
        """
        prompt = f"Task: {task}\n\n"
        prompt += "Previous Attempts & Reflections:\n"
        
        for i, (code, err, ref) in enumerate(history):
            prompt += f"--- Attempt {i+1} ---\n"
            # We don't include full code to save tokens, just the reflection is often enough, 
            # OR we include the error and reflection. 
            # The 'code' might be long. 
            # Let's include the reflection (which summarizes what went wrong).
            prompt += f"Error: {err[:500]}...\n" # Truncate error
            prompt += f"Reflection: {ref}\n"
        
        prompt += "\nBased on the above reflections, generate the CORRECTED code."
        return prompt
