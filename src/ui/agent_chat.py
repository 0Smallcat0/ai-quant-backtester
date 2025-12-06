import streamlit as st
from src.ai.agent import Agent, PendingAction
from src.ai.llm_client import LLMClient
from src.ai.utils_text import sanitize_agent_output, format_agent_log, split_thought_and_answer

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
            if st.button("✅ Approve", key="approve_btn", width="stretch"):
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
            if st.button("❌ Reject", key="reject_btn", width="stretch"):
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
                if role == "assistant":
                    # Parse thought and answer from stored content
                    # We store the FULL content now to preserve thoughts
                    thought, answer = split_thought_and_answer(content)
                    
                    # 1. Expandable Thoughts
                    # Only show if there is meaningful thought content
                    if thought and "無詳細過程" not in thought:
                        with st.expander("🧠 思考過程與工具執行", expanded=False):
                            st.markdown(format_agent_log(thought))
                    
                    # 2. Final Answer
                    st.markdown(answer)
                else:
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
                # We want [Thoughts] then [Answer].
                # We use two placeholders.
                message_placeholder = st.empty() # Top slot
                status_placeholder = st.empty()  # Bottom slot
                
                # We use a status container for the "thinking" process in the bottom slot initially?
                # Or just use the status_placeholder.
                
                # Streaming Phase: Use status_placeholder to show progress
                with status_placeholder.status("🧠 AI 正在思考與執行工具...", expanded=True) as status:
                    try:
                        # Call the agent with streaming
                        response_generator = st.session_state.agent_instance.chat(
                            prompt, 
                            history=st.session_state.agent_messages,
                            stream=True
                        )
                        
                        full_raw_response = ""
                        pending_action_obj = None
                        
                        # Iterate through stream
                        for chunk in response_generator:
                            if isinstance(chunk, PendingAction):
                                pending_action_obj = chunk
                                break
                            
                            chunk_str = str(chunk)
                            full_raw_response += chunk_str
                            
                            # Render content inside status for transparency during generation
                            st.markdown(chunk_str)
                            
                        # Mark thinking as complete
                        status.update(label="✅ 思考完成 (處理中...)", state="complete", expanded=False)
                        
                        if pending_action_obj:
                            # Store pending action and rerun to show UI
                            st.session_state.pending_action = pending_action_obj
                            st.rerun()
                        else:
                            # Post-processing Phase
                            
                            # 1. Split content
                            thought, answer = split_thought_and_answer(full_raw_response)
                            
                            # 2. Clear the status container (it served its purpose)
                            status_placeholder.empty()
                            
                            # 3. Render clean UI
                            # Uses message_placeholder (Top) for Thoughts
                            if thought and "無詳細過程" not in thought:
                                with message_placeholder.container():
                                    with st.expander("🧠 思考過程與工具執行 (點擊展開)", expanded=False):
                                        st.markdown(format_agent_log(thought))
                            
                            # Uses status_placeholder (Bottom) for Answer
                            # Since we cleared it, we can reuse it or just write to st
                            # (But we are in chat_message context, so st.write appends)
                            # To be specific, let's write to the bottom slot
                            status_placeholder.markdown(answer)
                            
                            # 4. Save FULL response to chat history
                            # This allows re-rendering the thoughts later
                            st.session_state.agent_messages.append({"role": "assistant", "content": full_raw_response})
                        
                    except Exception as e:
                        status.update(label="❌ 發生錯誤", state="error", expanded=True)
                        st.error(f"An error occurred: {str(e)}")

