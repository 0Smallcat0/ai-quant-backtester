import re
from typing import Optional, Tuple, List, Dict, Any, Union
from dataclasses import dataclass
from src.ai.prompts_agent import AGENT_SYSTEM_PROMPT
from src.ai.tools import list_files, read_file, write_file, run_shell

@dataclass
class PendingAction:
    tool_name: str
    args: Dict[str, Any]
    thought: str

class Agent:
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.system_prompt = AGENT_SYSTEM_PROMPT
        self.SENSITIVE_TOOLS = {'write_file', 'run_shell'}
        
    def _extract_tool_command(self, response: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Extract tool code and arguments from XML tag.
        Regex looks for <tool code="tool_name" [path="..."]>content</tool>
        Returns (tool_name, args_dict)
        """
        # Regex to capture tool code, optional path attribute, and content
        pattern = r'<tool code="([^"]+)"(?: path="([^"]+)")?>(.*?)</tool>'
        match = re.search(pattern, response, re.DOTALL)
        
        if match:
            tool_code = match.group(1)
            path_attr = match.group(2)
            content = match.group(3).strip()
            
            # Strip Markdown Code Blocks if present
            # This handles cases where the LLM wraps the code in ```python ... ```
            if content.startswith("```") and content.endswith("```"):
                lines = content.split('\n')
                # Remove the first line (opening fence)
                if lines and lines[0].startswith("```"):
                    lines.pop(0)
                # Remove the last line (closing fence)
                if lines and lines[-1].strip() == "```":
                    lines.pop()
                content = "\n".join(lines).strip()
            
            args = {"content": content}
            if path_attr:
                args["path"] = path_attr
                
            return tool_code, args
            
        return None, None

    def _run_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Execute the requested tool.
        """
        try:
            if tool_name == "list_files":
                # list_files takes optional start_path
                path = args.get("content", ".")
                # If content is empty string, default to "."
                if not path:
                    path = "."
                return list_files(path)
                
            elif tool_name == "read_file":
                # read_file expects path in content
                return read_file(args.get("content", ""))
                
            elif tool_name == "write_file":
                # write_file expects path attribute and content
                path = args.get("path")
                content = args.get("content", "")
                if not path:
                    return "Error: write_file requires 'path' attribute."
                return write_file(path, content)
                
            elif tool_name == "run_shell":
                # run_shell expects command in content
                return run_shell(args.get("content", ""))
                
            else:
                return f"Error: Unknown tool '{tool_name}'"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Error executing tool {tool_name}: {str(e)}"

    def chat(self, user_input: str, history: List[Dict] = None, max_steps: int = 10, stream: bool = False) -> Union[str, PendingAction]:
        """
        Main chat loop (ReAct pattern).
        If stream=True, returns a generator.
        If stream=False, returns the final string response or PendingAction.
        """
        generator = self._chat_generator(user_input, history, max_steps, stream)
        
        if stream:
            return generator
            
        # Blocking mode: consume generator
        final_result = ""
        for item in generator:
            if isinstance(item, PendingAction):
                return item
            final_result = item
            
        return final_result

    def _chat_generator(self, user_input: str, history: List[Dict], max_steps: int, stream: bool):
        if history is None:
            history = []
            
        # Prepare messages for LLM
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_input})
        
        step = 0
        last_response = ""
        
        while step < max_steps:
            # Call LLM
            if stream:
                # Streaming Logic
                full_response = ""
                stream_gen = self.llm_client.get_response_stream(messages)
                
                # Yield chunks to UI
                for chunk in stream_gen:
                    full_response += chunk
                    yield chunk
                
                response = full_response
            else:
                # Standard Logic
                response = self.llm_client.get_completion(messages)
            
            last_response = response
            
            # Check for tool call
            tool_name, tool_args = self._extract_tool_command(response)
            
            if tool_name:
                # Check for Sensitive Tools (Interrupt Logic)
                if tool_name in self.SENSITIVE_TOOLS:
                    # Extract thought from response (everything before <tool>)
                    thought = response.split('<tool')[0].strip()
                    if thought.startswith("Thought:"):
                        thought = thought[len("Thought:"):].strip()
                        
                    yield PendingAction(
                        tool_name=tool_name,
                        args=tool_args,
                        thought=thought
                    )
                    return # Stop generator

                # Safe Tool found, execute it
                tool_result = self._run_tool(tool_name, tool_args)
                
                # Append LLM thought/call and Tool result to messages
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": f"Tool Output:\n{tool_result}"})
                
                # If streaming, yield tool output
                if stream:
                    yield f"\n\n**Tool Output:**\n{tool_result}\n\n"
                
                step += 1
            else:
                # No tool called, this is the final answer
                if not stream:
                    yield response
                return # End generator
                
        if not stream:
            yield last_response
