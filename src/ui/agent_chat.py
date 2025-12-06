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
                    from src.ai.utils_text import parse_agent_output, format_agent_log
                    parsed = parse_agent_output(content)
                    
                    thought = parsed['thoughts']
                    answer = parsed['answer']
                    
                    # 1. Expandable Thoughts
                    # Only show if there is meaningful thought content
                    if thought and "(無詳細過程)" not in thought:
                        with st.expander("👁️ 查看思考過程 (Thoughts & Tools)", expanded=False):
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
                # Placeholder for the "Thinking" status block
                stream_placeholder = st.empty()
                full_log = ""
                pending_action_obj = None

                # Phase 1: Thinking (Streaming)
                # We render the status INSIDE the placeholder so we can clear it later.
                with stream_placeholder.container():
                    with st.status("🧠 AI 正在思考與撰寫...", expanded=True) as status:
                        log_display = st.empty()
                        
                        try:
                            # Call the agent with streaming
                            response_generator = st.session_state.agent_instance.chat(
                                prompt, 
                                history=st.session_state.agent_messages,
                                stream=True
                            )
                            
                            # Streaming Loop
                            for chunk in response_generator:
                                # 1. Handle Tool Requests (PendingAction)
                                if isinstance(chunk, PendingAction):
                                    pending_action_obj = chunk
                                    break
                                
                                # 2. Accumulate Text
                                chunk_str = str(chunk)
                                full_log += chunk_str
                                
                                # 3. Update UI (Raw Stream inside Status)
                                log_display.markdown(full_log)
                            
                        except Exception as e:
                            status.update(label="❌ 發生錯誤", state="error", expanded=True)
                            st.error(f"An error occurred: {str(e)}")
                            # Stop processing
                            st.stop()
                
                # Handling Pending Action (Interrupted Flow)
                if pending_action_obj:
                    # If pending action, we KEEP the status or transform it?
                    # The user prompt doesn't strictly specify this edge case, 
                    # but usually we want to see what led to the action.
                    # Let's clean the placeholder and show it as a persistent thought block + pending UI.
                    
                    stream_placeholder.empty()
                    
                    # Parse what we have so far
                    from src.ai.utils_text import parse_agent_output, format_agent_log
                    parsed = parse_agent_output(full_log)
                    
                    with st.expander("👁️ 查看思考過程 (Thoughts & Tools)", expanded=True):
                        st.markdown(format_agent_log(parsed['thoughts']))
                    
                    st.session_state.pending_action = pending_action_obj
                    st.rerun()

                else:
                    # Phase 2: Completion (Standard Flow)
                    # 1. Clear the "Thinking..." status block
                    stream_placeholder.empty()
                    
                    # 2. Parse the final output
                    from src.ai.utils_text import parse_agent_output, format_agent_log
                    parsed = parse_agent_output(full_log)
                    
                    # 3. Render Thoughts (Collapsed)
                    with st.expander("👁️ 查看思考過程 (Thoughts & Tools)", expanded=False):
                        st.markdown(format_agent_log(parsed['thoughts']))
                    
                    # 4. Render Final Answer
                    st.markdown(parsed['answer'])
                    
                    # 5. Save to History
                    st.session_state.agent_messages.append({"role": "assistant", "content": full_log})

