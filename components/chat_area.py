import streamlit as st
import base64
import asyncio

from datetime import datetime
from config.app_config import AppConfig

class ChatArea:
    def __init__(self, service_manager):
        """Initialize the ChatArea component.

        Args:
            service_manager: The service manager instance providing access to all services
        """
        self.service_manager = service_manager
        self.config = AppConfig()
        self.theme_styles = {
            "Pastel Delight": {
                "background": "#fffaf0",
                "text": "#5c5c5c",
                "hover": "#f8efd4"
            },
            "Dreamy Sky": {
                "background": "#dbe4f3",
                "text": "#3c3c54",
                "hover": "#c5d2eb"
            },
            "Peach Blossom": {
                "background": "#fee4d1",
                "text": "#4a332e",
                "hover": "#fcd3bb"
            },
            "None": {
                "background": "#ffffff",
                "text": "#000000",
                "hover": "#eaeaea"
            }
        }
        self.image_handler = self.service_manager.chat_manager.image_handler

    def render(self):
        """Main render method for the chat area"""
        theme = st.session_state.get("theme", "None")
        styles = self.theme_styles.get(theme, self.theme_styles["None"])
        st.markdown(
            f"""
            <style>
                .css-container {{
                    background-color: {styles['background']};
                    color: {styles['text']};
                }}
                .css-container .chat-message:hover {{
                    background-color: {styles['hover']};
                }}
            </style>
            """,
            unsafe_allow_html=True
        )
        st.container()
        st.title("HappyRonnieRome Virtual Board Room - myERP")

        # Add theme and background selection
        col1, col2 = st.columns(2)
        with col1:
            self._render_theme_selector()
        with col2:
            self._render_background_selector()

        if not st.session_state.get('selected_conv'):
            st.info("Please select or create a new chat to begin.")
            return

        try:
            conversation = self.service_manager.chat_manager.get_conversation(
                st.session_state.selected_conv
            )
            if conversation is None:
                st.session_state.selected_conv = None
                st.error("Error loading conversation. Please select or create a new chat.")
                return

            self._render_header(conversation)

            # Display existing messages
            chat_container = st.container()
            chat_container.markdown("<div class='css-container'>", unsafe_allow_html=True)
            with chat_container:
                if conversation.get('messages'):
                    for msg in conversation['messages']:
                        with st.chat_message(msg['sender']):
                            self._display_message_content(msg)
                            if msg['sender'] == 'assistant' and msg.get('ai_service'):
                                # Style the caption
                                st.markdown(
                                    f"""
                                    <div style='background-color: rgba(255, 255, 255, 0.95); 
                                             padding: 5px; 
                                             border-radius: 3px; 
                                             font-size: 0.8em; 
                                             color: #666;'>
                                        Response from {msg.get('ai_service', 'AI').upper()} 
                                        ({msg.get('model', 'default model')})
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
            # Handle new user input
            chat_container.markdown("</div>", unsafe_allow_html=True)
            user_input = st.chat_input("Type a message...", key="main_chat_input")
            if user_input:
                # Display user message immediately for all services except DALL-E
                ai_service = st.session_state.get('ai_service', 'claude').lower()
                if ai_service != 'dalle':
                    with st.chat_message("user"):
                        st.markdown(user_input)

                try:
                    # Get model and process response based on selected service
                    model_key = st.session_state.get('model_key')
                    response = None

                    if ai_service == 'dalle':
                        # Handle DALL-E image generation with size selection
                        dalle_size = st.session_state.get('dalle_size', '1024x1024')
                        response = self.service_manager.chat_manager.generate_image_dalle(
                            st.session_state.selected_conv,
                            user_input,
                            model_key,
                            dalle_size
                        )
                    elif ai_service == 'claude':
                        response = self.service_manager.chat_manager.send_to_claude(
                            st.session_state.selected_conv,
                            user_input,
                            model_key
                        )
                    elif ai_service == 'chatgpt':
                        response = self.service_manager.chat_manager.send_to_chatgpt(
                            st.session_state.selected_conv,
                            user_input,
                            model_key
                        )
                    else:  # gemini
                        response = self.service_manager.chat_manager.send_to_gemini(
                            st.session_state.selected_conv,
                            user_input,
                            model_key
                        )

                    # Display AI response if received
                    if response:
                        with st.chat_message("assistant"):
                            st.markdown(response)

                    # Force refresh to update chat history
                    st.rerun()

                except Exception as e:
                    st.error(f"Error processing message: {str(e)}")
                    print(f"Error details: {str(e)}")

        except Exception as e:
            st.error(f"Error retrieving conversation: {str(e)}")
            print(f"Error details: {str(e)}")

    def _display_message_content(self, msg):
        """Display message content with proper styling and opacity.

        This method handles both regular text messages and image messages with
        appropriate styling and formatting for each type.

        Args:
            msg (dict): The message dictionary containing content and metadata
        """
        if msg.get('metadata', {}).get('type') == 'image':
            try:
                # Get image from storage
                image_id = msg['metadata']['image_id']
                encoded_image = self.image_handler.image_store.get(image_id)

                if encoded_image:
                    image_data = base64.b64decode(encoded_image)

                    # Display prompt with styling
                    st.markdown(
                        f"""
                        <div class='chat-message' style='padding: 10px; border-radius: 5px; margin-bottom: 10px;'>
                            <strong>Prompt:</strong> {msg['metadata']['prompt']}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Display image container
                    st.markdown(
                        """
                        <div class='chat-message' style='padding: 10px; border-radius: 5px; margin-bottom: 10px;'>
                        """,
                        """
                        <div style='background-color: rgba(255, 255, 255, 0.95); 
                                 padding: 10px; 
                                 border-radius: 5px; 
                                 margin-bottom: 10px;'>
                        """,
                        unsafe_allow_html=True
                    )

                    st.image(
                        image_data,
                        caption=f"DALL-E Generated Image",
                        use_container_width=True
                    )

                    st.markdown("</div></div>", unsafe_allow_html=True)

                    # Display image details
                    with st.expander("Image Details"):
                        st.markdown(
                            f"""
                            <div style='background-color: rgba(255, 255, 255, 0.95); 
                                     padding: 10px; 
                                     border-radius: 5px;'>
                                <p><strong>Model:</strong> {msg['metadata']['model']}</p>
                                <p><strong>Size:</strong> {msg['metadata']['size']}</p>
                                <p><strong>Generated at:</strong> {msg['metadata']['generated_at']}</p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.warning("Image data not found")
            except Exception as e:
                st.error(f"Error displaying image: {str(e)}")
        else:
            # Regular text message display
            st.markdown(
                f"""
                <div class='chat-message' style='padding: 10px; border-radius: 5px;'>
                    {msg['content']}
                </div>
                """,
                unsafe_allow_html=True
            )

    def _render_theme_selector(self):
        """Render theme selection dropdown"""
        themes = {
                "Pastel Delight": "Pastel Delight",
                "Peach Blossom": "Peach Blossom",
                "Dreamy Sky": "Dreamy Sky",
                "None": "None"
        }

        selected_theme = st.selectbox(
            "Theme",
            list(themes.keys()),
            format_func=lambda x: themes[x],
            index=list(themes.keys()).index(st.session_state.get('theme', 'Pastel Delight'))
        )

        if selected_theme != st.session_state.get('theme'):
            st.session_state.theme = selected_theme
            st.success(f"Theme changed to {selected_theme}")
            st.rerun()

        """Render theme selection dropdown with dynamic styles"""
    def _render_background_selector(self):
        """Render background selection dropdown"""
        backgrounds = {
            "default": "Default",
            "gradient": "Gradient",
            "custom": "Custom"
        }

        selected_bg = st.selectbox(
            "Background",
            list(backgrounds.keys()),
            format_func=lambda x: backgrounds[x],
            index=list(backgrounds.keys()).index(st.session_state.get('background', 'default'))
        )

        if selected_bg != st.session_state.get('background'):
            st.session_state.background = selected_bg
            st.success(f"Background changed to {selected_bg}")
            st.rerun()

    def _render_header(self, conversation):
        """Render the conversation header"""
        st.caption(f"Current Chat: {conversation.get('title', 'Untitled')}")

    def _render_export_buttons(self):
        """Render export option buttons"""
        export_col1, export_col2, export_col3, export_col4 = st.columns(4)

        with export_col1:
            if st.button("Export JSON"):
                content = self.service_manager.chat_manager.export_conversation(st.session_state.selected_conv,
                                                                                "json")
                if content:
                    st.download_button(
                        "Download JSON",
                        content,
                        f"{st.session_state.selected_conv}.json",
                        mime="application/json"
                    )

        with export_col2:
            if st.button("Export Chat"):
                content = self.service_manager.chat_manager.export_conversation(st.session_state.selected_conv,
                                                                                "txt")
                if content:
                    st.download_button(
                        "Download Chat",
                        content,
                        f"{st.session_state.selected_conv}.txt",
                        mime="text/plain"
                    )

        with export_col3:
            if st.button("Export Code"):
                self._handle_code_export()

        with export_col4:
            if st.button("Export Images"):
                self._handle_image_export()

    def _render_messages(self, conversation):
        """Render conversation messages"""
        for msg in conversation.get('messages', []):
            with st.chat_message(msg['sender']):
                content = msg.get('content', '')
                if content:
                    st.write(content)

                    # Display metadata for AI responses
                    if msg['sender'] == 'assistant' and msg.get('ai_service'):
                        st.caption(
                            f"Response from {msg.get('ai_service', 'AI').upper()} "
                            f"({msg.get('model', 'default model')})"
                        )

    def _handle_chat_input(self):
        """Handle chat input and message processing"""
        prompt = st.chat_input("Message", key="chat_handler_input")

        if prompt:
            try:
                # Check for recently pasted image in session state
                image_data = st.session_state.get('clipboard_image')

                # Display user message immediately
                with st.chat_message("user"):
                    st.write(prompt)
                    if image_data:
                        st.image(base64.b64decode(image_data), caption="Uploaded image")

                # Process response based on selected AI service
                response = None
                ai_service = st.session_state.get('ai_service', 'claude').lower()
                model_key = st.session_state.get('model_key')

                if ai_service == "claude":
                    response = self.service_manager.chat_manager.send_to_claude(
                        st.session_state.selected_conv,
                        prompt,
                        model_key,
                    )
                elif ai_service == "chatgpt":
                    response = self.service_manager.chat_manager.send_to_chatgpt(
                        st.session_state.selected_conv,
                        prompt,
                        model_key
                    )
                elif ai_service == "dalle":
                    response = self.service_manager.chat_manager.generate_image_dalle(
                        st.session_state.selected_conv,
                        prompt,
                        model_key
                    )
                else:  # gemini
                    response = self.service_manager.chat_manager.send_to_gemini(
                        st.session_state.selected_conv,
                        prompt,
                        model_key
                    )

                # Display AI response immediately
                if response:
                    with st.chat_message("assistant"):
                        st.write(response)

                # Clear the clipboard image after sending
                if 'clipboard_image' in st.session_state:
                    del st.session_state.clipboard_image

                # Rerun to update the full chat history
                st.rerun()

            except Exception as e:
                st.error(f"Error processing message: {str(e)}")
                print(f"Chat Error: {str(e)}")

    def _handle_code_export(self):
        """Handle code export functionality"""
        code_msgs = self.service_manager.chat_manager.extract_code_messages(st.session_state.selected_conv)
        if not code_msgs:
            st.info("No code generated in this conversation!")
            return

        options = []
        for i, msg in enumerate(code_msgs):
            try:
                if isinstance(msg, dict):
                    content = msg.get('content', '')
                elif isinstance(msg, tuple) and len(msg) > 1:
                    content = str(msg[1])
                else:
                    content = str(msg)
                options.append(f"Message {i}: {content[:50]}...")
            except (IndexError, AttributeError):
                options.append(f"Message {i}: [Invalid format]")

        if options:
            selected = st.multiselect("Select code to export:", options)
            if selected and st.button("Export Selected"):
                indices = [i for i, opt in enumerate(options) if opt in selected]
                exported = self.service_manager.chat_manager.export_selected_code(
                    st.session_state.selected_conv,
                    indices
                )
                if exported:
                    st.success(f"Exported {len(exported)} code snippets")
                else:
                    st.warning("No code was exported")

    def _handle_image_export(self):
        """Handle image export functionality"""
        conversation = self.service_manager.chat_manager.get_conversation(st.session_state.selected_conv)
        image_messages = [msg for msg in conversation['messages'] if msg.get('image_data')]

        if image_messages:
            for i, msg in enumerate(image_messages):
                filename = f"image_{i}.png"
                if msg.get('image_data'):
                    st.download_button(
                        f"Download {filename}",
                        base64.b64decode(msg['image_data']),
                        filename,
                        mime="image/png",
                        key=f"download_img_{i}"
                    )