import streamlit as st
import os
import json
from dotenv import load_dotenv, set_key
from src.config.settings import settings

# Load existing environment variables
load_dotenv()

MODELS_CONFIG_PATH = "src/config/models.json"

def load_models():
    """Loads the list of models from config/models.json."""
    if not os.path.exists(MODELS_CONFIG_PATH):
        # Default fallback if file missing (though we created it)
        return ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    try:
        with open(MODELS_CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]

def save_models(models):
    """Saves the list of models to config/models.json."""
    # Ensure config dir exists
    os.makedirs(os.path.dirname(MODELS_CONFIG_PATH), exist_ok=True)
    with open(MODELS_CONFIG_PATH, "w") as f:
        json.dump(models, f, indent=4)

def render_global_settings_page(dm):
    """
    Renders the Global Settings page.
    
    Args:
        dm: DataManager instance (passed for consistency, though might not be used directly here).
    """
    st.title("⚙️ Global Settings")
    
    st.markdown("Configure your AI model and API keys here.")
    
    # --- LLM Model Selection & Management ---
    st.subheader("🤖 LLM Configuration")
    
    # Load models from config
    if 'available_models' not in st.session_state:
        st.session_state['available_models'] = load_models()
        
    model_options = st.session_state['available_models']
    
    # Determine current selection
    # Priority: Session State > Env Var > First in List
    env_model = os.getenv("MODEL_NAME")
    default_index = 0
    
    current_selection = st.session_state.get('llm_model')
    if not current_selection and env_model in model_options:
        current_selection = env_model
    
    if current_selection in model_options:
        default_index = model_options.index(current_selection)
        
    selected_model = st.selectbox(
        "Current Model",
        options=model_options,
        index=default_index,
        key="model_selector",
        help="Select the OpenAI model to use for strategy generation."
    )
    
    # Update session state immediately on selection change
    if selected_model != st.session_state.get('llm_model'):
        st.session_state['llm_model'] = selected_model

    # Dynamic Model Management
    with st.expander("Manage Models (Add / Delete)"):
        c_add, c_del = st.columns([3, 1])
        
        with c_add:
            new_model_name = st.text_input("Add New Model Name (e.g. gpt-5)", key="new_model_input")
            if st.button("➕ Add Model"):
                if new_model_name and new_model_name not in st.session_state['available_models']:
                    st.session_state['available_models'].append(new_model_name)
                    save_models(st.session_state['available_models'])
                    st.session_state['llm_model'] = new_model_name # Auto-select new model
                    st.success(f"Added model: {new_model_name}")
                    st.rerun()
                elif new_model_name in st.session_state['available_models']:
                    st.warning("Model already exists.")
                else:
                    st.warning("Please enter a model name.")
                    
        with c_del:
            st.write("") # Spacer
            st.write("") # Spacer
            if st.button("🗑️ Delete Selected"):
                if len(st.session_state['available_models']) > 1:
                    to_remove = selected_model
                    st.session_state['available_models'].remove(to_remove)
                    save_models(st.session_state['available_models'])
                    # Reset selection to first available
                    st.session_state['llm_model'] = st.session_state['available_models'][0]
                    st.success(f"Deleted model: {to_remove}")
                    st.rerun()
                else:
                    st.error("Cannot delete the last model.")

    # --- API Key Management ---
    st.subheader("🔑 API Keys")
    
    # Check if key exists in session state or env
    current_api_key = st.session_state.get('openai_api_key', os.getenv("API_KEY", ""))
    
    api_key_input = st.text_input(
        "LLM API Key",
        value=current_api_key,
        type="password",
        help="Enter the API Key for your chosen provider (e.g., OpenAI, OpenRouter, DeepSeek)."
    )

    # --- API Base URL (for OpenRouter etc.) ---
    current_base_url = st.session_state.get('llm_base_url', os.getenv("LLM_BASE_URL", ""))
    
    c_url, c_btn = st.columns([3, 1])
    with c_url:
        base_url_input = st.text_input(
            "API Base URL (Provider Endpoint)",
            value=current_base_url,
            help="Leave empty for official OpenAI. Use https://openrouter.ai/api/v1 for OpenRouter."
        )
    with c_btn:
        st.write("") # Spacer
        st.write("") # Spacer
        if st.button("Use OpenRouter Default"):
            base_url_input = "https://openrouter.ai/api/v1"
            st.session_state['llm_base_url'] = base_url_input
            st.rerun()

    save_to_env = st.checkbox("Save to .env file (persistent)", value=False)

    # --- Trading Environment (Risk & Money) ---
    st.markdown("---")
    st.header("⚙️ Trading Environment (Risk & Money)")
    
    # Load existing settings or defaults
    current_settings = st.session_state.get('trading_settings', {})
    
    # Defaults from SSOT if not in session state
    # Initialize Session State keys if not present
    # (Removed redundant trading params: initial_capital, etc. are now in Strategy Creation)

    st.subheader("📐 Position Sizing")
    c1, c2 = st.columns(2)
    
    with c1:
        sizing_method = st.radio(
            "Position Sizing Type",
            ["Fixed Percentage (%)", "Fixed Amount ($)"],
            index=0 if current_settings.get('sizing_method', 'Fixed Percentage (%)') == 'Fixed Percentage (%)' else 1,
            help="Choose how to calculate trade size."
        )
        
    with c2:
        if sizing_method == "Fixed Percentage (%)":
            sizing_target = st.slider(
                "Target Size (%)", 
                min_value=10.0, 
                max_value=100.0, 
                value=float(current_settings.get('sizing_target', 95.0)),
                step=5.0,
                help="Percentage of equity to allocate per trade. Higher = Less Cash Drag."
            )
        else:
            sizing_target = st.number_input(
                "Target Amount ($)", 
                min_value=100.0, 
                value=float(current_settings.get('sizing_target', 1000.0)),
                step=100.0
            )
            
    # --- Save Action ---
    if st.button("Save Settings", type="primary"):
        # Update Session State
        st.session_state['llm_model'] = selected_model
        st.session_state['openai_api_key'] = api_key_input
        st.session_state['llm_base_url'] = base_url_input
        
        st.session_state['trading_settings'] = {
            'sizing_method': sizing_method,
            'sizing_target': sizing_target
        }
        
        # Update Environment Variables (Hot Reload)
        os.environ["MODEL_NAME"] = selected_model
        if api_key_input:
            os.environ["API_KEY"] = api_key_input
        if base_url_input:
            os.environ["LLM_BASE_URL"] = base_url_input
        
        # Update .env if requested
        if save_to_env:
            env_path = ".env"
            # Create .env if it doesn't exist
            if not os.path.exists(env_path):
                with open(env_path, 'w') as f:
                    f.write("")
            
            set_key(env_path, "API_KEY", api_key_input)
            set_key(env_path, "MODEL_NAME", selected_model) # Save selected model
            if base_url_input:
                set_key(env_path, "LLM_BASE_URL", base_url_input)
            else:
                # Remove key if empty to fallback to default
                # python-dotenv doesn't have a simple delete, so we just set to empty string or handle logic elsewhere
                set_key(env_path, "LLM_BASE_URL", "")
                
            st.success(f"Settings saved! Using model: {selected_model}. API Key and Base URL stored in `{env_path}`.")
        else:
            st.success(f"Settings saved to current session! Using model: {selected_model}")
            
        # Force a rerun to ensure changes propagate immediately if needed



