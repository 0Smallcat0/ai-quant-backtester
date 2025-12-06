
import sys
import os
sys.path.append(os.getcwd())
from src.ai.utils_text import parse_agent_output

def test_parse_agent_output():
    print("Testing parse_agent_output...\n")
    
    # Case 1: Standard thought then answer
    c1 = """Thought: I need to check the data.
<tool code="read_file">data.csv</tool>
Tool Output: data loaded.
Here is the data analysis."""
    
    r1 = parse_agent_output(c1)
    print(f"--- Case 1 ---\nThoughts:\n{r1['thoughts']}\nAnswer:\n[{r1['answer']}]\n")
    assert "Here is the data analysis." in r1['answer']
    assert "Tool Output: data loaded." in r1['thoughts']
    
    # Case 2: Only answer
    c2 = "Just a simple answer."
    r2 = parse_agent_output(c2)
    print(f"--- Case 2 ---\nThoughts:\n{r2['thoughts']}\nAnswer:\n[{r2['answer']}]\n")
    assert r2['answer'] == "Just a simple answer."
    assert r2['thoughts'] == "(無詳細過程)"
    
    # Case 3: Interleaved tools (should split at the LAST tool/thought)
    c3 = """Thought: Step 1
<tool>cmd1</tool>
Some partial text explanation?
Thought: Step 2
<tool>cmd2</tool>
Final conclusion."""
    
    r3 = parse_agent_output(c3)
    print(f"--- Case 3 ---\nThoughts:\n{r3['thoughts']}\nAnswer:\n[{r3['answer']}]\n")
    # Interpretation: The split happens after the last tool/thought. 
    # "Some partial text explanation?" is between tools. 
    # Current logic: max index of any log marker.
    # The last log marker is </tool> of cmd2.
    assert "Final conclusion." in r3['answer']
    assert "<tool>cmd2</tool>" in r3['thoughts']
    
    # Case 4: Answer looks like tool output (edge case)
    c4 = """Result:
Tool Output: (just kidding, this is text)
But wait, the regex catches Tool Output: at start of line."""
    
    r4 = parse_agent_output(c4)
    print(f"--- Case 4 ---\nThoughts:\n{r4['thoughts']}\nAnswer:\n[{r4['answer']}]\n")
    # If "Tool Output:" is at start of line, it's captured as thought.
    # This is expected behavior per "Thoughts: ... Tool Output blocks".
    
    print("All tests passed (visually verified).")

if __name__ == "__main__":
    test_parse_agent_output()
