import re

def sanitize_agent_output(raw_text: str, max_len: int = 20000) -> str:
    """
    Sanitizes the AI agent output by removing thoughts, tool logs, and truncating length.
    
    Args:
        raw_text (str): The raw output from the AI agent.
        max_len (int): Maximum length of the returned string. Defaults to 20000.
        
    Returns:
        str: The cleaned and truncated text.
    """
    if not raw_text:
        return ""
        
    # 1. Remove <tool>...</tool> blocks (including newlines around them)
    # The flag re.DOTALL makes the dot match newlines as well.
    # We use non-greedy matching .*? to catch individual tool blocks.
    cleaned_text = re.sub(r'<tool.*?>.*?</tool>', '', raw_text, flags=re.DOTALL)
    
    # 2. Remove "Thought: ..." lines.
    cleaned_text = re.sub(r'^Thought:.*$', '', cleaned_text, flags=re.MULTILINE)
    
    # 3. Trim extra whitespace
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text).strip()
    
    # 4. Force Truncation if too long
    if len(cleaned_text) > max_len:
        cleaned_text = cleaned_text[:max_len] + "\n... (Output Truncated due to length limit)"
        
    return cleaned_text

def format_agent_log(raw_text: str) -> str:
    """
    Formats raw agent output (XML logs, thoughts) into readable Markdown.
    Includes converting XML tool tags to emojis and formatting thoughts.
    """
    if not raw_text:
        return ""
        
    formatted = raw_text
    
    # 1. Replace specialized tool usage with pretty format
    # Using regex to capture attributes and content
    
    def tool_replacer(match):
        # Try to extract code attribute if present
        tag_content = match.group(0)
        content = match.group(2).strip()
        
        # Check for code attribute
        code_match = re.search(r'code="(.*?)"', match.group(1))
        code = code_match.group(1) if code_match else "unknown"
        
        icon = "⚙️"
        action_name = "執行工具" # Default generic
        
        if code == "read_file":
            icon = "📂"
            action_name = "讀取檔案"
        elif code == "write_file":
            icon = "💾"
            action_name = "寫入檔案"
        elif code == "run_shell":
            icon = "💻"
            action_name = "執行指令"
        elif code == "search":
             icon = "🔍"
             action_name = "搜尋"
             
        # Format: 📂 **讀取檔案**: `path`
        # or block style if content is multiline
        if '\n' in content or len(content) > 50:
             return f"\n\n{icon} **{action_name}** ({code}):\n```\n{content}\n```\n"
        else:
             return f"\n\n{icon} **{action_name}**: `{content}`\n"

    # Match <tool ...>...</tool>
    # Group 1: attributes part, Group 2: content
    formatted = re.sub(r'<tool(.*?)\s*>(.*?)</tool>', tool_replacer, formatted, flags=re.DOTALL)
    
    # 2. Format Thoughts
    # Replace "Thought: ..." with "🤔 **思考**: ..."
    formatted = re.sub(r'^Thought:\s*(.*)', r'🤔 **思考**: \1', formatted, flags=re.MULTILINE)
    
    # 3. Format Tool Output
    formatted = re.sub(r'^Tool Output:\s*', r'⚙️ **執行結果**: ', formatted, flags=re.MULTILINE)

    return formatted.strip()

def split_thought_and_answer(raw_text: str) -> tuple[str, str]:
    """
    Splits the raw text into (thought_log, final_answer).
    
    Strategies:
    1. Find the extent of all log-like structures (Thought lines, <tool> blocks, Tool Output lines).
    2. Split at the end of the last log structure.
    """
    if not raw_text:
        return "(無詳細過程)", ""
        
    max_log_index = 0
    found_any_log = False
    
    # 1. End of any </tool>
    for m in re.finditer(r'</tool>', raw_text):
        max_log_index = max(max_log_index, m.end())
        found_any_log = True
        
    # 2. End of "Thought: ..." lines
    for m in re.finditer(r'^Thought:.*$', raw_text, re.MULTILINE):
        max_log_index = max(max_log_index, m.end())
        found_any_log = True
        
    # 3. End of "Tool Output: ..." lines (and potentially some following lines?)
    # We will be conservative and just take the line itself.
    for m in re.finditer(r'^Tool Output:.*$', raw_text, re.MULTILINE):
        max_log_index = max(max_log_index, m.end())
        found_any_log = True

    # If no logs found at all, treat everything as answer, but provide a placeholder for thought
    if not found_any_log:
        # Check if it looks like a direct answer
        return "(無詳細過程)", raw_text
        
    thought_part = raw_text[:max_log_index].strip()
    answer_part = raw_text[max_log_index:].strip()
    
    if not thought_part:
        thought_part = "(無詳細過程)"
        
    return thought_part, answer_part

# Alias for backward compatibility if needed
extract_final_answer = sanitize_agent_output
