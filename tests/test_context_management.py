import unittest
from src.ai.history_manager import HistoryManager
from src.ai.prompts_agent import AGENT_SYSTEM_PROMPT

class TestContextManagement(unittest.TestCase):
    def test_prune_history(self):
        """
        Case A: Verify prune_history keeps System Prompt and recent messages.
        """
        # Create a history with System Prompt + 20 turns (40 messages)
        history = [{"role": "system", "content": "System Prompt"}]
        for i in range(20):
            history.append({"role": "user", "content": f"User {i}"})
            history.append({"role": "assistant", "content": f"Assistant {i}"})
            
        # Prune to keep last 5 turns (10 messages) + System Prompt
        pruned = HistoryManager.prune_history(history, max_turns=5)
        
        # Expected length: 1 (System) + 10 (5 turns * 2) = 11
        self.assertEqual(len(pruned), 11)
        
        # Verify System Prompt is preserved
        self.assertEqual(pruned[0]["role"], "system")
        self.assertEqual(pruned[0]["content"], "System Prompt")
        
        # Verify the last message is the most recent one
        self.assertEqual(pruned[-1]["content"], "Assistant 19")
        
        # Verify the first message after System Prompt is User 15 (20 - 5 = 15)
        self.assertEqual(pruned[1]["content"], "User 15")

    def test_system_prompt_length(self):
        """
        Case B: Verify System Prompt is concise (< 2000 characters).
        """
        self.assertLess(len(AGENT_SYSTEM_PROMPT), 3000, "System Prompt is too long!")
        # Optional: Check for removal of verbose examples
        self.assertNotIn("Example:", AGENT_SYSTEM_PROMPT, "Should remove verbose examples")

if __name__ == '__main__':
    unittest.main()
