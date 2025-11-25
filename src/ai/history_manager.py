from typing import List, Dict

class HistoryManager:
    """
    Manages chat history to prevent context overflow.
    """
    
    @staticmethod
    def prune_history(messages: List[Dict], max_turns: int = 10) -> List[Dict]:
        """
        Prunes the message history to keep the System Prompt and the most recent turns.
        
        Args:
            messages (List[Dict]): The full message history.
            max_turns (int): The number of recent conversation turns (User + Assistant pairs) to keep.
            
        Returns:
            List[Dict]: The pruned message history.
        """
        if not messages:
            return []
            
        # Always preserve the System Prompt (usually the first message)
        system_prompt = None
        if messages[0]["role"] == "system":
            system_prompt = messages[0]
            chat_history = messages[1:]
        else:
            chat_history = messages
            
        # Calculate max messages to keep (turns * 2 for User/Assistant pairs)
        max_messages = max_turns * 2
        
        # Prune if needed
        if len(chat_history) > max_messages:
            pruned_history = chat_history[-max_messages:]
        else:
            pruned_history = chat_history
            
        # Reconstruct
        final_history = []
        if system_prompt:
            final_history.append(system_prompt)
        final_history.extend(pruned_history)
        
        return final_history
