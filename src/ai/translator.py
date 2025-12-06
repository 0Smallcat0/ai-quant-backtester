from typing import List, Optional
import hashlib
from functools import lru_cache
from src.ai.llm_client import LLMClient
import logging

class TextTranslator:
    """
    A lightweight translation layer using LLM to convert non-English text to English.
    Designed for financial context preservation.
    """
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client if llm_client else LLMClient()
        self.logger = logging.getLogger(__name__)

    @lru_cache(maxsize=1024)
    def _translate_single_cached(self, text: str) -> str:
        """
        Internal cached translation for single strings.
        Note: We mainly use batch processing, but this is a fallback.
        """
        return self.translate_batch([text])[0]

    def translate_batch(self, texts: List[str]) -> List[str]:
        """
        Translates a list of texts to English in a single batch to save tokens.
        
        Args:
            texts (List[str]): List of strings to translate.
            
        Returns:
            List[str]: Translated strings. Returns original if translation fails.
        """
        if not texts:
            return []
            
        # Filter empty strings but keep track of indices to restore them if needed
        # For simplicity, we'll just send everything.
        
        # Prepare Prompt
        joined_text = "\n".join([f"- {t}" for t in texts])
        prompt = (
            "Translate the following financial headlines to English. "
            "Maintain the financial context and terminology. "
            "Output the translations line by line, matching the input order. "
            "Do not output anything else."
            "\n\nInput:\n"
            f"{joined_text}"
        )
        
        try:
            response = self.llm_client.generate_strategy_code(prompt, model="gpt-4o")
            
            # Clean and split
            # The LLM output might contain bullet points like "- " or "1. "
            lines = response.strip().split('\n')
            
            # Basic cleanup of bullet points if the LLM adds them despite instructions
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if line.startswith('- '):
                    line = line[2:]
                elif line and line[0].isdigit() and '. ' in line[:5]:
                     # Remove "1. ", "2. " etc.
                     parts = line.split('. ', 1)
                     if len(parts) > 1:
                         line = parts[1]
                cleaned_lines.append(line)
            
            # Validation: Length mismatch fallback
            if len(cleaned_lines) != len(texts):
                self.logger.warning(
                    f"Translation count mismatch! Input: {len(texts)}, Output: {len(cleaned_lines)}. "
                    "Returning originals for safety."
                )
                return texts
                
            return cleaned_lines
            
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            return texts # Fail open: return original text
