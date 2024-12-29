import streamlit as st
import base64


from datetime import datetime
from config.app_config import AppConfig
from config.styles import StyleConfig

class ChatArea:
    def __init__(self, service_manager, theme_manager):
        self.service_manager = service_manager
        self.theme_manager = theme_manager
        self.style_config = theme_manager.style_config

        self.image_handler = self.service_manager.chat_manager.image_handler


    def render(self, theme_css: str = None):
        """Render the chat area with the provided theme."""
        try:
            # Apply theme CSS if provided
            if theme_css:
                st.markdown(theme_css, unsafe_allow_html=True)
            else:
                # Get current theme from session state
                theme = st.session_state.get('theme', 'Transparent')
                styles = self.style_config.get_theme_css(theme)
                st.markdown(styles, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error loading theme styles: {str(e)}")

        st.title("HappyRonnieRome Virtual Board Room - GameDev")

        # Add theme and background selection
        col1, col2 = st.columns(2)
        with col1:
            try:
                available_themes = list(self.style_config.THEMES.keys())
                current_theme = st.session_state.get('theme', 'Transparent')

                if current_theme not in available_themes:
                    current_theme = 'Transparent'
                    st.session_state.theme = current_theme

                selected_theme = st.selectbox(
                    "Select Theme",
                    options=available_themes,
                    index=available_themes.index(current_theme),
                    key="theme_selector"
                )

                if selected_theme != current_theme:
                    st.session_state.theme = selected_theme
                    theme_css = self.style_config.get_theme_css(selected_theme)
                    st.markdown(theme_css, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Error in theme selection: {str(e)}")
                st.session_state.theme = 'Transparent'
                theme_css = self.style_config.get_theme_css('Transparent')
                st.markdown(theme_css, unsafe_allow_html=True)
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
        """Display message content with clean styling."""
        if msg.get('metadata', {}).get('type') == 'image':
            try:
                image_id = msg['metadata']['image_id']
                encoded_image = st.session_state.image_store.get(image_id)

                if encoded_image:
                    image_data = base64.b64decode(encoded_image)

                    # Display the prompt elegantly
                    st.markdown(
                        f"""
                        <div style='background-color: rgba(255, 255, 255, 0.95); 
                                 padding: 15px; 
                                 border-radius: 8px; 
                                 margin-bottom: 15px;
                                 border: 1px solid #eee;'>
                            <p style='color: #666; margin-bottom: 8px;'>Prompt:</p>
                            <p style='color: #333; margin: 0;'>{msg['metadata']['prompt']}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Display the image
                    st.image(
                        image_data,
                        caption="DALL-E Generated Image",
                        use_container_width=True
                    )

                    # Show details in a clean expander
                    with st.expander("Image Details"):
                        details_md = f"""
                        | Property | Value |
                        |----------|-------|
                        | Model | {msg['metadata']['model']} |
                        | Size | {msg['metadata']['size']} |
                        | Generated | {datetime.fromisoformat(msg['metadata']['generated_at']).strftime('%Y-%m-%d %H:%M:%S')} |
                        """
                        st.markdown(details_md)

                else:
                    st.info("Image temporarily unavailable. Please try regenerating the image.")

            except Exception as e:
                st.error("Unable to display the image. Please try regenerating it.")

        else:
            # Regular message display
            st.markdown(msg['content'])

    def _render_theme_selector(self):
        """Render the theme selection dropdown with proper error handling."""
        try:
            # Get available themes directly from StyleConfig
            available_themes = list(self.style_config.THEMES.keys())

            # Get current theme from session state, defaulting to 'Transparent' if not set
            current_theme = st.session_state.get('theme', 'Transparent')

            # Validate current_theme exists in available_themes
            if current_theme not in available_themes:
                current_theme = 'Transparent'
                st.session_state.theme = current_theme

            # Create the theme selector
            selected_theme = st.selectbox(
                "Select Theme",
                options=available_themes,
                index=available_themes.index(current_theme)
            )

            # Update theme if changed
            if selected_theme != current_theme:
                st.session_state.theme = selected_theme
                # Apply new theme
                theme_css = self.style_config.get_theme_css(selected_theme)
                st.markdown(theme_css, unsafe_allow_html=True)

        except Exception as e:
            # Fallback to Transparent theme if any error occurs
            st.error(f"Error in theme selection: {str(e)}")
            st.session_state.theme = 'Transparent'
            theme_css = self.style_config.get_theme_css('Transparent')
            st.markdown(theme_css, unsafe_allow_html=True)

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