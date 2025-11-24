import unittest
from unittest.mock import MagicMock
from src.ai.agent import Agent, PendingAction
from src.ai.llm_client import LLMClient

class TestAgentShellIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClient)
        self.agent = Agent(self.mock_llm_client)

    def test_shell_execution_flow(self):
        """
        Test the full flow of shell execution:
        Request -> Intercept (PendingAction) -> Approve (Manual Execute) -> Success
        """
        user_input = "Check python version"
        
        # 1. Mock LLM to return a shell command
        # The agent should parse this and return a PendingAction because run_shell is sensitive
        llm_response = 'Thought: Checking python version.\n<tool code="run_shell">python --version</tool>'
        self.mock_llm_client.get_completion.return_value = llm_response
        
        # 2. Call agent.chat()
        result = self.agent.chat(user_input)
        
        # 3. Assert Interception (PendingAction)
        self.assertIsInstance(result, PendingAction)
        self.assertEqual(result.tool_name, "run_shell")
        self.assertEqual(result.args, {"content": "python --version"})
        self.assertEqual(result.thought, "Checking python version.")
        
        # 4. Simulate Approval: Manually call _run_tool
        # We mock subprocess.run inside run_shell indirectly or just rely on the actual tool 
        # if we want a true integration test. 
        # Since "python --version" is safe and available, we can run it for real 
        # OR we can mock the tool execution if we want to be purely unit-testy about the agent.
        # The requirement says "Simulate Approval: Manually call agent._run_tool... Verify result contains 'Python'"
        # So we will actually run it.
        
        tool_result = self.agent._run_tool(result.tool_name, result.args)
        
        # 5. Assert Execution Success
        self.assertIn("Python", tool_result)
        self.assertIn("STDOUT", tool_result)

    def test_shell_blacklist_integration(self):
        """
        Test that even if a user approves a blacklisted command, 
        the underlying tool still blocks it.
        """
        user_input = "Delete everything"
        
        # 1. Mock LLM to return a dangerous command
        llm_response = 'Thought: Cleaning up.\n<tool code="run_shell">rm -rf /</tool>'
        self.mock_llm_client.get_completion.return_value = llm_response
        
        # 2. Call agent.chat()
        result = self.agent.chat(user_input)
        
        # 3. Assert Interception (PendingAction)
        # The agent intercepts BEFORE checking the blacklist in the tool?
        # Let's check agent.py:
        # if tool_name in self.SENSITIVE_TOOLS: return PendingAction
        # Yes, interception happens first.
        self.assertIsInstance(result, PendingAction)
        self.assertEqual(result.tool_name, "run_shell")
        self.assertEqual(result.args, {"content": "rm -rf /"})
        
        # 4. Simulate Approval: Manually call _run_tool
        # This simulates the user clicking "Approve" in the UI
        tool_result = self.agent._run_tool(result.tool_name, result.args)
        
        # 5. Assert Blocked by Safety Net
        self.assertTrue(tool_result.startswith("Error: Command blocked"))
        self.assertIn("rm", tool_result)

if __name__ == '__main__':
    unittest.main()
