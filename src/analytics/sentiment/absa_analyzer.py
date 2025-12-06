
import json
import logging
import re
from typing import List, Dict, Optional
from src.ai.llm_client import LLMClient
from src.ai.prompts import FINANCIAL_ABSA_PROMPT

class ABSAAnalyzer:
    """
    Aspect-Based Sentiment Analyzer using Cloud LLM API.
    Replaces local model inference for stability.
    """
    def __init__(self, llm_client: Optional[LLMClient] = None, model_id: str = "gpt-4o"): # model_id kept for compat but unused
        self.logger = logging.getLogger(__name__)
        self.llm_client = llm_client if llm_client else LLMClient()
        self.prompt_template = FINANCIAL_ABSA_PROMPT
        self.logger.info(f"Initializing Cloud-Based ABSAAnalyzer")

    def analyze(self, text: str) -> Dict:
        """
        Analyzes a single text string and returns structured sentiment data via API.
        
        Returns:
            Dict with keys: Overall_Sentiment, Positive_Aspect, Negative_Aspect
        """
        if not text:
            return {}

        try:
            # Construct Prompt
            formatted_prompt = self.prompt_template.format(text=text)
            
            messages = [
                {"role": "system", "content": "You are a helpful financial assistant."},
                {"role": "user", "content": formatted_prompt}
            ]

            # Call API
            response_str = self.llm_client.get_completion(messages=messages, temperature=0.1)
            
            # Clean Code (Remove markdown fences)
            cleaned_response = self.llm_client.clean_code(response_str)

            # Parse JSON
            try:
                # Attempt to find JSON object pattern just in case
                match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                if match:
                    json_str = match.group(0)
                else:
                    json_str = cleaned_response
                    
                data = json.loads(json_str)
                return data
            except json.JSONDecodeError:
                self.logger.warning(f"ABSA parsing failed for text: {text[:50]}... Response: {cleaned_response[:50]}")
                return {"Overall_Sentiment": "Neutral", "Error": "Parse Failure"}
                
        except Exception as e:
            self.logger.error(f"ABSA API Inference failed: {e}")
            return {"Overall_Sentiment": "Neutral", "Error": str(e)}

    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """
        Sequential analysis for batch input.
        API calls are sequential unless async is implemented in LLMClient (usually requests is sync).
        """
        return [self.analyze(t) for t in texts]
