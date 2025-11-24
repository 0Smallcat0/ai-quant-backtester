import os
import re
from openai import OpenAI
from typing import Optional
# [FIX] Import the engineered system prompt to ensure high-quality strategy generation
from src.ai.prompts import SYSTEM_PROMPT 

class LLMClient:
    """
    Client for interacting with the OpenAI API (or compatible APIs like OpenRouter) 
    to generate strategy code.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the LLMClient.
        The API key is not strictly required at initialization to allow for lazy loading
        and dynamic configuration via the UI.
        """
        self.api_key = api_key
        self.client = None
        # Lazy initialization is handled in generate_strategy_code to support dynamic settings
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)

    def _get_api_key(self) -> Optional[str]:
        """
        Resolves the API key with the following priority:
        1. Streamlit Session State (if available)
        2. Explicitly passed key (self.api_key)
        3. Environment Variable (API_KEY) - Standard
        """
        # 1. Check if we have access to Streamlit session state
        try:
            import streamlit as st
            if 'openai_api_key' in st.session_state and st.session_state['openai_api_key']:
                return st.session_state['openai_api_key']
        except ImportError:
            pass

        # 2. Check self.api_key (if initialized with one)
        if self.api_key:
            return self.api_key

        # 3. Check Environment Variable (Standard)
        return os.getenv("API_KEY")

    def _get_base_url(self) -> Optional[str]:
        """
        Resolves the Base URL with the following priority:
        1. Streamlit Session State (llm_base_url)
        2. Environment Variable (LLM_BASE_URL)
        """
        # 1. Check Session State
        try:
            import streamlit as st
            if 'llm_base_url' in st.session_state and st.session_state['llm_base_url']:
                return st.session_state['llm_base_url']
        except ImportError:
            pass

        # 2. Check Environment Variable
        return os.getenv("LLM_BASE_URL")

    def clean_code(self, response: str) -> str:
        """
        Removes Markdown code block formatting from the LLM response.

        Args:
            response (str): The raw response string from the LLM.

        Returns:
            str: The cleaned Python code.
        """
        # Remove ```python or ``` at the start
        cleaned = re.sub(r'^```(?:python)?\s*', '', response.strip())
        # Remove ``` at the end
        cleaned = re.sub(r'\s*```$', '', cleaned)
        return cleaned

    def generate_strategy_code(self, prompt: str, model: Optional[str] = None) -> str:
        """
        Generates strategy code based on the provided prompt using LLM API.

        Args:
            prompt (str): The user's description of the strategy.
            model (str): The model to use. Priority:
                         1. UI Selection (st.session_state['llm_model'])
                         2. Environment Variable (MODEL_NAME)
                         3. Default (gpt-4o)

        Returns:
            str: The generated code string.
            
        Raises:
            ValueError: If no API key is found.
        """
        api_key = self._get_api_key()
        base_url = self._get_base_url()
        
        if not api_key:
            raise ValueError("LLM API Key is missing. Please set it in Global Settings or .env file (API_KEY).")

        # Determine model priority
        # 1. Check Session State (UI Override)
        final_model: str = "gpt-4o" # Default fallback
        
        try:
            import streamlit as st
            if 'llm_model' in st.session_state and st.session_state['llm_model']:
                final_model = str(st.session_state['llm_model'])
        except ImportError:
            pass

        # 2. If not in session state, check env vars
        if model:
             final_model = model
        elif not final_model or final_model == "gpt-4o": # If still default or empty
             env_model = os.getenv("MODEL_NAME")
             if env_model:
                 final_model = env_model
        
        # Initialize client with current configuration
        client: OpenAI
import os
import re
from openai import OpenAI
from typing import Optional
# [FIX] Import the engineered system prompt to ensure high-quality strategy generation
from src.ai.prompts import SYSTEM_PROMPT 

class LLMClient:
    """
    Client for interacting with the OpenAI API (or compatible APIs like OpenRouter) 
    to generate strategy code.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the LLMClient.
        The API key is not strictly required at initialization to allow for lazy loading
        and dynamic configuration via the UI.
        """
        self.api_key = api_key
        self.client = None
        # Lazy initialization is handled in generate_strategy_code to support dynamic settings
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)

    def _get_api_key(self) -> Optional[str]:
        """
        Resolves the API key with the following priority:
        1. Streamlit Session State (if available)
        2. Explicitly passed key (self.api_key)
        3. Environment Variable (API_KEY) - Standard
        """
        # 1. Check if we have access to Streamlit session state
        try:
            import streamlit as st
            if 'openai_api_key' in st.session_state and st.session_state['openai_api_key']:
                return st.session_state['openai_api_key']
        except ImportError:
            pass

        # 2. Check self.api_key (if initialized with one)
        if self.api_key:
            return self.api_key

        # 3. Check Environment Variable (Standard)
        return os.getenv("API_KEY")

    def _get_base_url(self) -> Optional[str]:
        """
        Resolves the Base URL with the following priority:
        1. Streamlit Session State (llm_base_url)
        2. Environment Variable (LLM_BASE_URL)
        """
        # 1. Check Session State
        try:
            import streamlit as st
            if 'llm_base_url' in st.session_state and st.session_state['llm_base_url']:
                return st.session_state['llm_base_url']
        except ImportError:
            pass

        # 2. Check Environment Variable
        return os.getenv("LLM_BASE_URL")

    def clean_code(self, response: str) -> str:
        """
        Removes Markdown code block formatting from the LLM response.

        Args:
            response (str): The raw response string from the LLM.

        Returns:
            str: The cleaned Python code.
        """
        # Remove ```python or ``` at the start
        cleaned = re.sub(r'^```(?:python)?\s*', '', response.strip())
        # Remove ``` at the end
        cleaned = re.sub(r'\s*```$', '', cleaned)
        return cleaned

    def generate_strategy_code(self, prompt: str, model: Optional[str] = None) -> str:
        """
        Generates strategy code based on the provided prompt using LLM API.

        Args:
            prompt (str): The user's description of the strategy.
            model (str): The model to use. Priority:
                         1. UI Selection (st.session_state['llm_model'])
                         2. Environment Variable (MODEL_NAME)
                         3. Default (gpt-4o)

        Returns:
            str: The generated code string.
            
        Raises:
            ValueError: If no API key is found.
        """
        api_key = self._get_api_key()
        base_url = self._get_base_url()
        
        if not api_key:
            raise ValueError("LLM API Key is missing. Please set it in Global Settings or .env file (API_KEY).")

        # Determine model priority
        # 1. Check Session State (UI Override)
        final_model: str = "gpt-4o" # Default fallback
        
        try:
            import streamlit as st
            if 'llm_model' in st.session_state and st.session_state['llm_model']:
                final_model = str(st.session_state['llm_model'])
        except ImportError:
            pass

        # 2. If not in session state, check env vars
        if model:
             final_model = model
        elif not final_model or final_model == "gpt-4o": # If still default or empty
             env_model = os.getenv("MODEL_NAME")
             if env_model:
                 final_model = env_model
        
        # Initialize client with current configuration
        client: OpenAI
        if base_url and base_url.strip():
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model=final_model,
                messages=[
                    # [FIX] Use the robust SYSTEM_PROMPT instead of a simple string
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            return self.clean_code(str(response.choices[0].message.content))
        except Exception as e:
            # In a real app, log error properly
            raise e

    def get_completion(self, messages: list, model: Optional[str] = None, temperature: float = 0.0) -> str:
        """
        Generates a completion for a list of messages.
        Used for Agent interactions.
        
        Args:
            messages (list): List of message dicts [{"role": "...", "content": "..."}, ...]
            model (str): Optional model override.
            temperature (float): Sampling temperature.
            
        Returns:
            str: The raw response content.
        """
        api_key = self._get_api_key()
        base_url = self._get_base_url()
        
        if not api_key:
            raise ValueError("LLM API Key is missing. Please set it in Global Settings or .env file (API_KEY).")

        # Determine model priority
        final_model: str = "gpt-4o"
        
        try:
            import streamlit as st
            if 'llm_model' in st.session_state and st.session_state['llm_model']:
                final_model = str(st.session_state['llm_model'])
        except ImportError:
            pass

        if model:
             final_model = model
        elif not final_model or final_model == "gpt-4o":
             env_model = os.getenv("MODEL_NAME")
             if env_model:
                 final_model = env_model
        
        client: OpenAI
        if base_url and base_url.strip():
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model=final_model,
                messages=messages,
                temperature=temperature
            )
            return str(response.choices[0].message.content)
        except Exception as e:
            raise e