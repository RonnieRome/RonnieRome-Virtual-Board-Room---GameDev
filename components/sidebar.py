import streamlit as st
import base64
import logging
from config.app_config import AppConfig
from openai import models


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

    def __init__(self, service_manager, state_manager):
        self.service_manager = service_manager
        self.state_manager = state_manager
        self.config = AppConfig()

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
        uploaded_files = st.file_uploader(
            "Import Files",
            type=self.config.get_supported_file_types(),
            accept_multiple_files=True
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

    DALLE_SIZES = {
        "1024x1024": "1024 x 1024",
        "512x512": "512 x 512"
    }

    def _render_ai_service_section(self):
        """Render AI service selection section."""
        st.divider()
        st.header("AI Service")

        # Create two columns for the radio buttons
# Create two columns for the radio buttons
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

        # Get model options for selected service
        current_model_options = self.MODEL_OPTIONS[selected_service]

        with col2:
            selected_model = st.radio(
                "Select Model",
                list(current_model_options.keys()),
                format_func=lambda x: current_model_options[x],
                index=0
            )
        st.session_state.model_key = selected_model

        style_col1, style_col2 = st.columns([5, 6])
        st.write("")

        with style_col1:
            STYLE_DESCRIPTIONS = {
                "Business": [
                    "📈 Formal and persuasive language",
                    "📞 Suitable for communication and marketing"
                ],
                "Engineer": [
                    "🛠️ System Architecture and Coding",
                    "📐 Science and Engineering format"
                ],
                "Executive": [
                    "💼 Planning",
                    "📊 Analysis",
                    "✍️ Summarized Contents"
                ],
                "Professor": [
                    "🌟 Guidance in developments",
                    "🎨 Data expertises"
                ]
            }
            selected_style = st.radio(
                "**Select Style**",
                list(STYLE_DESCRIPTIONS.keys()),
            )
            st.session_state.selected_style = selected_style

        with style_col2:
            st.markdown("<span style='font-size: small; color: white;'>**Details**</span>", unsafe_allow_html=True)

            formatted_description = ("<ul style='padding-left: 0rem; line-height: 1.4; text-align: left; "
                                     "vertical-align: top; font-size: small; white-space: pre-wrap; list-style-type: none; "
                                     "margin-top: -0.5rem; color: white;'>")
            for item in STYLE_DESCRIPTIONS[selected_style]:
                formatted_description += f"<li style='text-align: left;'>{item}</li>"
            formatted_description += "</ul>"
            st.markdown(
                formatted_description,
                unsafe_allow_html=True
            )

        if selected_service == "dalle":
            st.write("")  # Add spacing
            selected_size = st.radio(
                "Select Image Size",
                list(self.DALLE_SIZES.keys()),
                format_func=lambda x: self.DALLE_SIZES[x],
                index=0
            )
            st.session_state.dalle_size = selected_size

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
        success, data, error_message = self.service_manager.chat_manager.get_clipboard_image()
        if success:
            try:
                image_base64 = base64.b64encode(data).decode()
                with st.chat_message("user"):
                    st.image(data, caption="Pasted from clipboard", use_container_width=True)
                st.session_state.clipboard_image = image_base64
                if st.session_state.selected_conv:
                    # Changed from self.chat_manager to self.service_manager.chat_manager
                    self.service_manager.chat_manager.add_image_message(
                        st.session_state.selected_conv,
                        image_base64,
                        "Pasted image from clipboard",
                        "user"
                    )
                    st.success("Image successfully pasted and added to conversation")
            except Exception as e:
                st.error(f"Error processing image: {str(e)}")
        else:
            st.error(error_message)

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
                'theme': 'Pastel Delight',
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