import streamlit as st
from src.ai.agent import Agent, PendingAction
from src.ai.llm_client import LLMClient

def render_approval_ui(action: PendingAction):
    """
    Renders the approval UI for a pending action.
    """
    with st.status(f"🚨 Approval Required: {action.tool_name}", expanded=True) as status:
        st.write(f"**Reason:** {action.thought}")
        
        if action.tool_name == "write_file":
            st.write(f"**Target:** `{action.args.get('path')}`")
            st.code(action.args.get('content'), language='python') # Defaulting to python highlighting for now
        elif action.tool_name == "run_shell":
            st.warning("⚠️ **HIGH RISK**: This command will run on your local machine. Verify carefully.")
            st.code(action.args.get('content'), language='bash')
            
        col_yes, col_no = st.columns(2)
        
        with col_yes:
            if st.button("✅ Approve", key="approve_btn", use_container_width=True):
                # Execute the tool
                # We need to access the agent instance to run the tool. 
                # Since _run_tool is internal, we should ideally expose it or use it carefully.
                # For now, we'll access it directly as per plan.
                agent = st.session_state.agent_instance
                result = agent._run_tool(action.tool_name, action.args)
                
                # Format output for shell commands
                if action.tool_name == "run_shell":
                    formatted_result = f"Tool Output:\n```console\n{result}\n```"
                else:
                    formatted_result = f"Tool Output:\n{result}"

                # Append result to history
                st.session_state.agent_messages.append({"role": "user", "content": formatted_result})
                
                # Clear pending action
                st.session_state.pending_action = None
                st.rerun()
                
        with col_no:
            if st.button("❌ Reject", key="reject_btn", use_container_width=True):
                # Append rejection to history
                st.session_state.agent_messages.append({"role": "user", "content": "User rejected the request."})
                
                # Clear pending action
                st.session_state.pending_action = None
                st.rerun()

def render_agent_chat_page(dm=None):
    """
    Renders the AI Agent Chat Interface.
    Args:
        dm: DataManager instance (optional, for future use)
    """
    st.title("🤖 AI Developer Agent")

    # --- 1. State Management ---
    
    # Initialize chat history
    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = []

    # Initialize Agent instance
    if "agent_instance" not in st.session_state:
        # LLMClient will automatically pick up API_KEY/MODEL from env or session state
        llm_client = LLMClient() 
        st.session_state.agent_instance = Agent(llm_client)

    # Initialize Pending Action
    if "pending_action" not in st.session_state:
        st.session_state.pending_action = None

    # --- 4. Sidebar ---
    with st.sidebar:
        st.header("Capabilities")
        st.markdown("""
        - **📂 List Files**: View project structure.
        - **📖 Read Code**: Analyze file content.
        - **🧠 Explain**: Answer technical questions.
        """)
        
        if st.button("Clear Chat History"):
            st.session_state.agent_messages = []
            st.session_state.pending_action = None
            st.rerun()

    # --- 2. Chat Rendering ---
    
    # Display chat messages from history on app rerun
    for message in st.session_state.agent_messages:
        role = message["role"]
        content = message["content"]
        
        # We only display user and assistant messages in the main chat
        if role in ["user", "assistant"]:
            with st.chat_message(role):
                st.markdown(content)

    # --- 3. Interaction Loop ---
    
    # Check for Pending Action FIRST
    if st.session_state.pending_action:
        render_approval_ui(st.session_state.pending_action)
        # Disable chat input while waiting for approval
        st.chat_input("⚠️ Waiting for approval...", disabled=True)
    else:
        # Accept user input
        if prompt := st.chat_input("Ask about the project code..."):
            # Add user message to chat history
            st.session_state.agent_messages.append({"role": "user", "content": prompt})
            
            # Display user message in chat message container
            with st.chat_message("user"):
                st.markdown(prompt)

            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                
                with st.spinner("Thinking & Exploring Codebase..."):
                    try:
                        # Call the agent with streaming
                        response_generator = st.session_state.agent_instance.chat(
                            prompt, 
                            history=st.session_state.agent_messages,
                            stream=True
                        )
                        
                        full_response = ""
                        pending_action_obj = None
                        
                        # Streamlit's write_stream consumes the generator. 
                        # But we need to intercept PendingAction.
                        # So we iterate manually.
                        
                        for chunk in response_generator:
                            if isinstance(chunk, PendingAction):
                                pending_action_obj = chunk
                                break
                            
                            full_response += str(chunk)
                            message_placeholder.markdown(full_response + "▌")
                            
                        # Final render without cursor
                        message_placeholder.markdown(full_response)
                        
                        if pending_action_obj:
                            # Store pending action and rerun to show UI
                            st.session_state.pending_action = pending_action_obj
                            st.rerun()
                        else:
                            # Add assistant response to chat history
                            st.session_state.agent_messages.append({"role": "assistant", "content": full_response})
                        
                    except Exception as e:
                        error_msg = f"An error occurred: {str(e)}"
                        message_placeholder.error(error_msg)
                        # Optionally append error to history or just show it
            
            # Rerun to update state and UI consistency
            st.rerun()
