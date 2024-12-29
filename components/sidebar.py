import streamlit as st
import base64
import logging
import logger
from config.app_config import AppConfig
from config.ai_style_manager import AIStyleManager
from datetime import datetime


class Sidebar:
    SERVICES = {
        "claude": "Claude",
        "chatgpt": "ChatGPT",
        "gemini": "Gemini",
        "dalle": "DALL-E"
    }

    MODEL_OPTIONS = {
        "claude": {
            "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
            "claude-3-opus-20240229": "Claude 3 Opus",
            "claude-3-haiku-20240307": "Claude 3 Haiku"
        },
        "chatgpt": {
            "gpt-4": "GPT-4",
            "gpt-3.5-turbo": "GPT-3.5 Turbo"
        },
        "gemini": {
            "gemini-pro": "Gemini Pro"
        },
        "dalle": {
            "dall-e-3": "DALL-E 3",
            "dall-e-2": "DALL-E 2"
        }
    }

    DALLE_SIZES = {
        "1024x1024": "1024 x 1024",
        "512x512": "512 x 512"
    }

    def __init__(self, service_manager, state_manager):
        self.service_manager = service_manager
        self.state_manager = state_manager
        self.config = AppConfig()
        self.style_manager = AIStyleManager()

    def render(self):
        """Render the complete sidebar interface."""
        """Render the complete sidebar interface."""
        with st.sidebar:
            try:
                self._render_control_buttons()
                self._render_file_upload()
                self._render_conversation_section()
                self._render_ai_service_section()
                self._render_token_display()
            except Exception as e:
                st.error(f"Error rendering sidebar: {str(e)}")
                logging.error(f"Sidebar render error: {str(e)}")


    def _render_control_buttons(self):
        """
                Renders the control buttons with confirmation dialog in the sidebar.
                Uses a sequential layout to avoid nested columns.
                """
        if not st.session_state.get('show_reset_confirm', False):
            # Show initial buttons
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("🔄 Reset Input"):
                    st.session_state.show_reset_confirm = True
                    st.rerun()
            with col2:
                if st.button("📜 Show Code"):
                    st.session_state.show_code_popup = not st.session_state.show_code_popup
        else:
            # Show confirmation dialog
            st.warning("This will clear all conversations and uploaded files. Token information will be preserved.")
            st.write("")  # Add some vertical spacing

            # Place buttons using streamlit columns
            left_col, right_col = st.columns([1, 1])
            with left_col:
                if st.button("✔️ Yes, Reset", key="confirm_reset", use_container_width=True):
                    self._handle_reset_input()
            with right_col:
                if st.button("❌ Cancel", key="cancel_reset", use_container_width=True):
                    st.session_state.show_reset_confirm = False
                    st.rerun()

    def _render_file_upload(self):
        """Render file upload section with debug information for file types."""
        # Debug: Print supported file types
        supported_types = self.config.get_supported_file_types()
        print(f"Supported file types: {supported_types}")  # Debug line

        uploaded_files = st.file_uploader(
            "Import Files",
            type=supported_types,
            accept_multiple_files=True,
            help="Upload program files, documents, or data files"  # Added helpful tooltip
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            submit_button = st.button("📤 Submit Files")
        with col2:
            paste_button = st.button("📎 Paste Scr")

        if uploaded_files and submit_button:
            self._handle_file_upload(uploaded_files)

        if paste_button:
            self._handle_paste_button()


    def _render_conversation_section(self):
        """Render conversation management section."""
        st.divider()
        st.header("Conversations")

        # New conversation input
        new_title = st.text_input("New Conversation Title")
        if st.button("Create New Conversation"):
            if new_title:
                # Changed from self.chat_manager to self.service_manager.chat_manager
                conv_id = self.service_manager.chat_manager.create_conversation(new_title)
                st.session_state.selected_conv = conv_id
                st.rerun()
            else:
                st.warning("Please enter a title")

        # Conversation selector
        conversations = self.service_manager.chat_manager.list_conversations()
        if conversations:
            selected = st.selectbox(
                "Select Conversation",
                conversations,
                index=conversations.index(st.session_state.selected_conv)
                if 'selected_conv' in st.session_state and
                st.session_state.selected_conv in conversations
                else 0
            )
            if selected != st.session_state.get('selected_conv'):
                st.session_state.selected_conv = selected
                st.rerun()


    def _render_conversation_controls(self):
        if st.session_state.get('show_title_input', True):
            col1, col2 = st.columns([3, 1])
            with col1:
                title = st.text_input("Chat Title")
            with col2:
                if st.button("➕ Start New Chat"):
                    if title:
                        # Changed from self.chat_manager to self.service_manager.chat_manager
                        st.session_state.selected_conv = self.service_manager.chat_manager.create_conversation(title)
                        st.session_state.show_title_input = False
                        st.rerun()

        conversations = self.service_manager.chat_manager.list_conversations()
        if conversations:
            st.session_state.selected_conv = st.selectbox(
                "Select Chat",
                conversations,
                index=conversations.index(st.session_state.selected_conv)
                if st.session_state.selected_conv in conversations else 0
            )

            if st.session_state.selected_conv:
                self._render_ai_service_selection()


    def _render_ai_service_section(self):
        """Render AI service selection section."""
        st.divider()
        st.header("AI Service")

        st.write("")  # Add consistent spacing
        col1, col2 = st.columns([1, 1])
        with col1:
            selected_service = st.radio(
                "Select AI Service",
                list(self.SERVICES.keys()),
                format_func=lambda x: self.SERVICES[x],
                index=0 if 'ai_service' not in st.session_state else
                list(self.SERVICES.keys()).index(st.session_state.ai_service.lower())
            )

        if selected_service != st.session_state.get('ai_service'):
            st.session_state.ai_service = selected_service
            st.rerun()

        current_model_options = self.MODEL_OPTIONS[selected_service]

        with col2:
            selected_model = st.radio(
                "Select Model",
                list(current_model_options.keys()),
                format_func=lambda x: current_model_options[x],
                index=0
            )
        st.session_state.model_key = selected_model

        st.write("")

        style_descriptions = AIStyleManager.get_style_descriptions()

        # Create columns for style selection
        style_col1, style_col2 = st.columns([4.5, 6.5])  # Proportions adjusted for balance

        # Column 1: Style selection
        with style_col1:
            st.markdown(
                """
                <style>
                /* Move the radio button section to the bottom of the column */
                div[data-testid="stVerticalBlock"] {
                    display: flex;
                    flex-direction: column;
                    justify-content: flex-end; /* Align content to the bottom */
                    height: 100%; /* Ensure full height of the column */
                }
                div[data-testid="stRadio"] {
                    margin-bottom: 0; /* Remove unnecessary margin */
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            selected_style = st.radio(
                "**Select Style**",
                list(style_descriptions.keys()),
                key="style_selector",
            )
        # Column 2: Style details
        with style_col2:
            st.markdown(
                """
                <style>
                .custom-box-container {
                    display: flex;
                    flex-direction: column;
                    align-items: flex-start; /* Align content to the left */
                    justify-content: flex-start; /* Ensure alignment at the top */
                    margin-top: 0; /* Ensure no extra margin */
                    height: auto; /* Adjust height to fit content */
                }
                .custom-header {
                    font-size: 12px; /* Smaller header font size */
                    font-weight: bold;
                    color: rgba(255, 255, 255, 0.9); /* Match the theme */
                    text-align: center; /* Center the header text horizontally */
                    width: 100%; /* Full width to allow centering */
                }
                .custom-box {
                    background-color: #7f7f7f; /* Comfortable gray background */
                    color: #66666; /* Light grey font color */
                    border-radius: 5px; /* Rounded corners */
                    padding: 5.25px 24px; /* Adjusted padding */
                    font-size: 10px; /* Smaller font size */
                    width: 100%; /* Full width */
                    text-align: left; /* Left-aligned text */
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); /* Subtle shadow */
                }
                </style>
                <div class="custom-box-container">
                    <div class="custom-header">Style Details</div> <!-- Header will now be centered horizontally -->
                </div>
                """,
                unsafe_allow_html=True,
            )
            for detail in style_descriptions[selected_style]:
                st.markdown(
                    f"""
                    <div class="custom-box">
                        {detail}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    def _render_token_display(self):
        """Display token usage statistics for the current conversation.
         This method shows a detailed breakdown of token usage by different AI services
         and provides a summary of input and total tokens used."""

        if not st.session_state.get('selected_conv'):
            return

        st.divider()
        st.markdown("### Token Used")

        # Get conversation using the correct service manager pattern
        conversation = self.service_manager.chat_manager.get_conversation(st.session_state.selected_conv)

        # Display stored files if any
        if 'stored_files' in conversation:
            with st.expander("Stored Files", expanded=False):
                for file in conversation['stored_files']:
                    if file['type'] == 'image':
                        st.image(
                            base64.b64decode(file['content']),
                            caption=f"{file['name']} (stored on {file['stored_at']})",
                            use_container_width=True
                        )
                    else:
                        st.text(f"📄 {file['name']} - {file['language']}")

        # Initialize token counters
        token_counters = {
            'claude': 0,
            'chatgpt': 0,
            'dalle': 0,
            'gemini': 0,
            'input': 0,
            'total': 0
        }

        # Calculate token usage
        for msg in conversation.get('messages', []):
            tokens = msg.get('tokens', 0)
            token_counters['total'] += tokens

            if msg['sender'] == 'user':
                token_counters['input'] += tokens

            ai_service = msg.get('ai_service')
            if ai_service in token_counters:
                token_counters[ai_service] += tokens

        # Display service-specific token counts
        cols_services = st.columns(4)
        services = ['claude', 'chatgpt', 'dalle', 'gemini']
        for col, service in zip(cols_services, services):
            with col:
                st.markdown(f"<small>{service.title()}</small>", unsafe_allow_html=True)
                st.markdown(f"<small>{token_counters[service]}</small>", unsafe_allow_html=True)

        # Display total token usage
        cols_totals = st.columns(2)
        with cols_totals[0]:
            st.markdown("--Input--")
            st.markdown(f"### {token_counters['input']}")
        with cols_totals[1]:
            st.markdown("**Total**")
            st.markdown(f"### {token_counters['total']}")
        try:
            stored_files = conversation.get('stored_files', [])
            if stored_files:
                st.success(f"Successfully processed {len(stored_files)} files")
        except Exception as e:
            st.error(f"Error processing files: {str(e)}")

    def _handle_paste_button(self):
        """Handle pasting image from clipboard with proper error handling."""
        try:
            # Get clipboard image using chat manager
            success, data, error_message = self.service_manager.chat_manager.get_clipboard_image()

            if success and data:
                # Encode image data
                image_base64 = base64.b64encode(data).decode()

                # Display image in chat
                with st.chat_message("user"):
                    st.image(data, caption="Pasted from clipboard", use_container_width=True)

                # Store in session state
                st.session_state.clipboard_image = image_base64

                # Add to conversation if one is selected
                if st.session_state.selected_conv:
                    self.service_manager.chat_manager.add_image_message(
                        st.session_state.selected_conv,
                        image_base64,
                        "Pasted image from clipboard",
                        "user"
                    )
                    st.success("Image successfully pasted and added to conversation")
                else:
                    st.warning("Please select a conversation first to save the image")

            else:
                st.error(error_message or "Failed to get image from clipboard")

        except Exception as e:
            logger.error(f"Error in paste button handler: {str(e)}")
            st.error(f"Error processing clipboard image: {str(e)}")

    def _handle_reset_input(self):
        """
                Handles the reset functionality using both state_manager and service_manager.
                This implementation properly preserves token information while clearing other state.
                """
        try:
            # Store the current token information before reset
            token_info = {
                'claude': st.session_state.get('token_claude', 0),
                'chatgpt': st.session_state.get('token_chatgpt', 0),
                'dalle': st.session_state.get('token_dalle', 0),
                'gemini': st.session_state.get('token_gemini', 0),
                'input': st.session_state.get('token_input', 0),
                'total': st.session_state.get('token_total', 0)
            }

            # Clear all non-essential session state
            keys_to_preserve = {'initialized', 'show_reset_confirm'}
            for key in list(st.session_state.keys()):
                if key not in keys_to_preserve:
                    del st.session_state[key]

            # Restore default values
            st.session_state.update({
                'show_title_input': True,
                'ai_service': 'claude',
                'show_code_popup': False,
                'messages': [],
                'selected_conv': None,
                'clipboard_image': None,
                'analysis_results': [],
                'model_key': None,
                'theme': 'Transparent',
                'uploaded_files': []
            })

            # Restore token information
            for service, count in token_info.items():
                st.session_state[f'token_{service}'] = count

            st.success("Reset completed successfully!")

            # Set confirmation dialog state to False
            st.session_state.show_reset_confirm = False

            # Force UI update
            st.rerun()

        except Exception as e:
            st.error(f"Error during reset: {str(e)}")
            logging.error(f"Reset error: {str(e)}")

    def _handle_file_upload(self, uploaded_files):
        """
        Handle the upload of multiple files to the conversation with comprehensive logging.

        This method processes uploaded files while maintaining detailed logs of the process.
        It uses the specialized logging service to track different aspects of the upload:
        - Application events in app.log
        - Any errors in error.log
        - Access events in access.log

        Args:
            uploaded_files: List of StreamlitUploadedFile objects
        """
        try:
            # Verify conversation selection with proper logging
            if not st.session_state.get('selected_conv'):
                self.service_manager.logging_service.log_error(
                    ValueError("No conversation selected"),
                    context={'operation': 'file_upload', 'stage': 'validation'}
                )
                st.error("Please select or create a conversation first")
                return

            conv_id = st.session_state.selected_conv

            # Log the start of file processing
            self.service_manager.logging_service.log_app_event(
                event_type='file_upload_start',
                details={
                    'conversation_id': conv_id,
                    'file_count': len(uploaded_files),
                    'file_names': [f.name for f in uploaded_files]
                }
            )

            # Initialize processing metrics
            processing_metrics = {
                'total_files': len(uploaded_files),
                'processed_files': 0,
                'successful_files': 0,
                'failed_files': []
            }

            # Process each uploaded file with detailed logging
            for uploaded_file in uploaded_files:
                try:
                    # Log access attempt for each file
                    self.service_manager.logging_service.log_access(
                        user_id=st.session_state.get('user_id', 'anonymous'),
                        resource=f'file/{uploaded_file.name}',
                        action='upload',
                        status='processing',
                        details={'conversation_id': conv_id}
                    )

                    # Process file through service manager
                    processed_file = self.service_manager.handle_file_upload(
                        [uploaded_file],
                        conv_id
                    )

                    if processed_file:
                        processing_metrics['successful_files'] += 1

                        # Log successful file processing
                        self.service_manager.logging_service.log_access(
                            user_id=st.session_state.get('user_id', 'anonymous'),
                            resource=f'file/{uploaded_file.name}',
                            action='upload',
                            status='success',
                            details={
                                'conversation_id': conv_id,
                                'file_type': uploaded_file.type,
                                'file_size': uploaded_file.size
                            }
                        )

                        # Add file message to conversation
                        self.service_manager.chat_manager.add_message(
                            conv_id=conv_id,
                            content=f"📎 Uploaded file: {uploaded_file.name}",
                            sender="user",
                            metadata={
                                'file_type': uploaded_file.type,
                                'file_name': uploaded_file.name,
                                'upload_timestamp': datetime.now().isoformat(),
                                'file_size': uploaded_file.size,
                                'processing_status': 'success'
                            }
                        )

                        # Show success message
                        st.success(f"Successfully uploaded: {uploaded_file.name}")

                except Exception as e:
                    # Log file processing error
                    self.service_manager.logging_service.log_error(
                        error=e,
                        context={
                            'operation': 'file_upload',
                            'file_name': uploaded_file.name,
                            'conversation_id': conv_id
                        }
                    )

                    processing_metrics['failed_files'].append({
                        'file_name': uploaded_file.name,
                        'error': str(e)
                    })

                    st.error(f"Error processing {uploaded_file.name}: {str(e)}")

                finally:
                    processing_metrics['processed_files'] += 1

            # Log final processing metrics
            self.service_manager.logging_service.log_app_event(
                event_type='file_upload_complete',
                details={
                    'conversation_id': conv_id,
                    'metrics': processing_metrics
                }
            )

            # Show summary for multiple files
            if len(uploaded_files) > 1:
                success_count = processing_metrics['successful_files']
                total_files = processing_metrics['total_files']
                if success_count == total_files:
                    st.success(f"Successfully uploaded all {total_files} files!")
                else:
                    st.warning(
                        f"Uploaded {success_count} out of {total_files} files. "
                        "Check the logs for details on failed uploads."
                    )

            # Force UI update
            st.rerun()

        except Exception as e:
            # Log any unexpected errors during the overall process
            self.service_manager.logging_service.log_error(
                error=e,
                context={
                    'operation': 'file_upload_process',
                    'conversation_id': st.session_state.get('selected_conv')
                }
            )
            st.error(f"An unexpected error occurred during file upload: {str(e)}")