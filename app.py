import base64
import logging
import requests
import io
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import pyperclip
import streamlit as st
from PIL import Image

from chat_manager import ChatHistoryManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app_debug.log'
)
logger = logging.getLogger(__name__)


class ThemeManager:
    """Manages UI themes and styling"""

    THEMES = {
        "Sabbath Black": """
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Rock+Salt&display=swap');
                @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300&display=swap');

                * {
                    font-family: 'Roboto', sans-serif !important;
                }

                [data-testid="stSidebar"] {
                    background-color: #000000 !important;
                    color: #ffffff !important;
                }

                .stApp {
                    background-color: #000000 !important;
                    color: #ffffff !important;
                }

                .stButton>button {
                    background-color: #333333;
                    color: #ffffff;
                    border: 1px solid #666666;
                }

                .stTextInput>div>div>input {
                    background-color: #333333;
                    color: #ffffff;
                }

                .stSelectbox>div>div>select {
                    background-color: #333333;
                    color: #ffffff;
                }
            </style>
        """,
        "Greenday": """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Finger+Paint&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');

            * {
                font-family: 'Finger Paint', cursive !important;
            }

            /* Sidebar background */
            [data-testid="stSidebar"] {
                background-color: #002b36 !important;
                color: #b58900 !important;
            }

            /* Main app background */
            .stApp {
                background: linear-gradient(to bottom, #003847, #004d5b 75%, #a6895b) !important; /* Adjusted gradient for smooth transition with brown */
                color: #b58900 !important;
            }
            </style>
        """,

        "Pastel Elegance": """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');

            * {
                font-family: 'Dancing Script', cursive !important;
            }

            /* Sidebar background */
            [data-testid="stSidebar"] {
                background-color: #b30041 !important; /* Updated to red rose color */
                color: #d4af37 !important;
            }

            /* Main app background */
            .stApp {
                background-color: #b50050 !important; /* Slightly different shade than its sidebar */
                color: #d4af37 !important;
            }
            </style>
        """,

        "Futuristic Metal": """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');

            * {
                font-family: 'Orbitron', sans-serif !important;
            }

            /* Sidebar background */
            [data-testid="stSidebar"] {
                background: linear-gradient(45deg, #333333, #666666) !important;
                color: #00ffff !important;
            }

            /* Main app background */
            .stApp {
                background: linear-gradient(45deg, #333333, #666666) !important; /* Match sidebar background */
                color: #00ffff !important;
            }
            </style>
        """,

        "Saturn": """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Great+Vibes&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');

            * {
                font-family: 'Great Vibes', cursive !important;
            }

            /* Sidebar background */
            [data-testid="stSidebar"] {
                background: linear-gradient(to bottom, #baa8a0, #7e5e5c, #99ccee) !important; /* Smooth Saturn ring colors with subtle blue tint */
                color: #d4af37 !important;
            }

            /* Main app background */
            .stApp {
                background: linear-gradient(to bottom, #452850, #4f3d68, #946648, #e0c8a3, #91c8de, #003366) !important; /* Adjusted gradient for darker and pastel tones */
                background-size: 100% 80%; /* Reduced the size of the brown gradient */
                color: #d4af37 !important;

            /* Saturn ring blurred strip */
            .stApp::before {
                content: '';
                position: absolute;
                top: 50%;
                left: 0;
                width: 100%;
                height: 15px;
                background: linear-gradient(to right, rgba(186, 168, 160, 0.5), rgba(126, 94, 92, 0.2), rgba(126, 94, 92, 0.5));
                filter: blur(8px);
                z-index: 0;
            }

            </style>
        """
    }

    @staticmethod
    def apply_theme(theme_name: str):
        """Apply selected theme to the application"""
        if theme_name in ThemeManager.THEMES:
            st.markdown(ThemeManager.THEMES[theme_name], unsafe_allow_html=True)


class SessionState:
    """Manages application session state"""

    @staticmethod
    def initialize_state():
        """Initialize all session state variables"""
        initial_states = {
            'show_title_input': True,
            'selected_conv': None,
            'messages': [],
            'ai_service': "Claude",
            'analysis_results': [],
            'show_code_popup': False,
            'theme': "Sabbath Black",
            'conversation_started': False,
            'current_model': None,
            'image_size': "1024x1024",
            'error_message': None,
            'success_message': None,
            'clipboard_image': None
        }

        for key, value in initial_states.items():
            if key not in st.session_state:
                st.session_state[key] = value


class FileHandler:
    """Handles file operations"""

    @staticmethod
    def process_uploaded_files(files, manager: ChatHistoryManager) -> List[Dict[str, Any]]:
        """Process uploaded files and return stored file data"""
        stored_files = []

        for file in files:
            try:
                if file.type.startswith('image'):
                    stored_file = FileHandler._process_image_file(file)
                else:
                    stored_file = FileHandler._process_text_file(file)

                stored_files.append(stored_file)
                logger.debug(f"Successfully processed file: {file.name}")

            except Exception as e:
                logger.error(f"Error processing file {file.name}: {str(e)}")
                st.error(f"Failed to process file {file.name}: {str(e)}")
                continue

        return stored_files

    @staticmethod
    def _process_image_file(file) -> Dict[str, Any]:
        """Process an image file"""
        image = Image.open(file)
        buffered = io.BytesIO()
        image.save(buffered, format=image.format)

        return {
            'name': file.name,
            'type': 'image',
            'content': base64.b64encode(buffered.getvalue()).decode(),
            'format': image.format,
            'language': 'image'
        }

    @staticmethod
    def _process_text_file(file) -> Dict[str, Any]:
        """Process a text file"""
        content = file.read().decode('utf-8')
        file_extension = file.name.split('.')[-1] if '.' in file.name else 'txt'

        return {
            'name': file.name,
            'type': 'text',
            'content': content,
            'language': file_extension
        }


class ChatInterface:
    """Manages chat interface and message handling"""

    def __init__(self, manager: ChatHistoryManager):
        self.manager = manager

    def handle_user_input(self, user_input: str):
        """Process user input and generate AI response"""
        try:
            # Add user message
            self.manager.add_message(
                st.session_state.selected_conv,
                user_input,
                "user",
                ai_service=st.session_state.ai_service.lower()
            )

            # Generate AI response
            if st.session_state.ai_service == "DALL-E":
                image_data = self.manager.generate_image_dalle(
                    user_input,
                    st.session_state.image_size
                )
                if image_data:
                    self.manager.add_message(
                        st.session_state.selected_conv,
                        "Generated image:",
                        "assistant",
                        ai_service="dalle",
                        model=st.session_state.current_model,
                        image_data=image_data
                    )
                    response = True
            else:
                service_methods = {
                    "Claude": self.manager.send_to_claude,
                    "ChatGPT": self.manager.send_to_chatgpt,
                    "Gemini": self.manager.send_to_gemini
                }

                method = service_methods.get(st.session_state.ai_service)
                if not method:
                    raise ValueError(f"Unknown AI service: {st.session_state.ai_service}")

                response = method(
                    st.session_state.selected_conv,
                    user_input,
                    model=st.session_state.current_model
                )

            if response:
                logger.debug(f"Got response from {st.session_state.ai_service}")
                st.rerun()

        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg)
            st.error(error_msg)

    def display_messages(self, conversation: Dict[str, Any]):
        """Display chat messages"""
        for msg in conversation.get('messages', []):
            with st.chat_message(msg['sender']):
                if msg.get('image_data'):
                    st.image(
                        base64.b64decode(msg['image_data']),
                        use_container_width=True
                    )
                st.write(msg['content'])

                if msg.get('error'):
                    st.error(msg['error'])


class SidebarManager:
    """Manages sidebar configuration and controls"""

    def __init__(self, manager: ChatHistoryManager):
        self.manager = manager

    def configure_sidebar(self):
        """Set up sidebar controls and options"""
        with st.sidebar:
            self._add_control_buttons()
            self._handle_file_upload()
            self._configure_chat_settings()
            self._setup_ai_service()

    def _add_control_buttons(self):
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔄 Reset Info"):
                st.session_state.clear()
                SessionState.initialize_state()
                st.rerun()
        with col2:
            if st.button("📜 Show Code"):
                st.session_state.show_code_popup = not st.session_state.show_code_popup

    def _handle_file_upload(self):
        uploaded_files = st.file_uploader(
            "Import Files",
            type=["json", "cs", "txt", "py", "js", "png", "jpg", "jpeg"],
            accept_multiple_files=True
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("📤 Submit Files") and uploaded_files:
                stored_files = FileHandler.process_uploaded_files(
                    uploaded_files,
                    self.manager
                )
                if stored_files:
                    st.success(f"Successfully processed {len(stored_files)} files")

        with col2:
            if st.button("📎 Paste Scr"):
                self._handle_clipboard_paste()

    def _handle_clipboard_paste(self):
        try:
            clipboard_data = pyperclip.paste()
            if clipboard_data.startswith('data:image'):
                img_data = clipboard_data.split(',')[1]
                img_bytes = BytesIO(base64.b64decode(img_data))
                st.image(img_bytes, use_container_width=True)
                st.session_state.clipboard_image = img_data
            elif clipboard_data.lower().endswith(('.png', '.jpg', '.jpeg')):
                with open(clipboard_data, 'rb') as file:
                    img_bytes = file.read()
                st.image(img_bytes, use_container_width=True)
                st.session_state.clipboard_image = base64.b64encode(img_bytes).decode()
        except Exception as e:
            logger.error(f"Clipboard error: {str(e)}")
            st.error(f"Error processing clipboard content: {str(e)}")

    def _configure_chat_settings(self):
        if st.session_state.show_title_input:
            self._show_chat_creation()

        conversations = self.manager.list_conversations()
        if conversations:
            self._show_conversation_selector(conversations)

    def _show_chat_creation(self):
        col1, col2 = st.columns([3, 2])
        with col1:
            title = st.text_input("Chat Title")
        with col2:
            if st.button("➕ Start New Chat", key="start_new_chat"):
                if title:
                    st.session_state.selected_conv = self.manager.create_conversation(title)
                    st.session_state.show_title_input = False
                    st.rerun()
                else:
                    st.error("Please enter a chat title")

    def _show_conversation_selector(self, conversations: List[str]):
        st.session_state.selected_conv = st.selectbox(
            "Select Chat",
            conversations,
            index=conversations.index(st.session_state.selected_conv)
            if st.session_state.selected_conv in conversations else 0
        )

    def _setup_ai_service(self):
        if not st.session_state.selected_conv:
            return

        st.session_state.ai_service = st.radio(
            "AI Service",
            ["Claude", "ChatGPT", "DALL-E", "Gemini"]
        )
        if st.session_state.ai_service == "Claude":
            if 'claude_style' not in st.session_state:
                st.session_state.claude_style = "Normal"
            st.session_state.claude_style = st.selectbox(
                "Claude Style",
                list(ChatHistoryManager.CLAUDE_STYLES.keys()),
                index=list(ChatHistoryManager.CLAUDE_STYLES.keys()).index(st.session_state.claude_style)
            )

        model_configs = {
            "Claude": self.manager.CLAUDE_MODELS,
            "ChatGPT": self.manager.GPT_MODELS,
            "DALL-E": self.manager.DALLE_MODELS,
            "Gemini": self.manager.GEMINI_MODELS
        }

        current_config = model_configs.get(st.session_state.ai_service)
        if current_config:
            model = st.selectbox("Model", list(current_config.values()))
            st.session_state.current_model = [
                k for k, v in current_config.items() if v == model
            ][0]

            if st.session_state.ai_service == "DALL-E":
                st.session_state.image_size = st.selectbox(
                    "Image Size",
                    ["1024x1024", "512x512"]
                )


def handle_exports(manager: ChatHistoryManager, conversation: Dict[str, Any]):
    """Handle various export operations"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Export JSON"):
            content = manager.export_conversation(
                st.session_state.selected_conv,
                "json"
            )
            if content:
                st.download_button(
                    "Download JSON",
                    content,
                    f"{st.session_state.selected_conv}.json"
                )

    with col2:
        if st.button("Export Chat"):
            content = manager.export_conversation(
                st.session_state.selected_conv,
                "txt"
            )
            if content:
                st.download_button(
                    "Download Chat",
                    content,
                    f"{st.session_state.selected_conv}.txt"
                )

    with col3:
        if st.button("Export Code"):
            code_msgs = manager.extract_code_messages(
                st.session_state.selected_conv
            )
            if code_msgs:
                handle_code_export(manager, code_msgs)

    with col4:
        if st.button("Export Images"):
            handle_image_export(conversation)


def handle_image_export(conversation: Dict[str, Any]):
    """Handle the export of images from the conversation"""
    image_messages = [msg for msg in conversation['messages']
                      if msg.get('image_data')]

    if not image_messages:
        st.warning("No images found in this conversation")
        return

    for i, msg in enumerate(image_messages):
        try:
            filename = f"image_{i}.png"
            st.download_button(
                label=f"Download {filename}",
                data=base64.b64decode(msg['image_data']),
                file_name=filename,
                mime="image/png",
                key=f"download_img_{i}"
            )
        except Exception as e:
            logger.error(f"Error exporting image {i}: {str(e)}")
            st.error(f"Failed to export image {i}")


def handle_code_export(manager: ChatHistoryManager, code_msgs: List[Tuple[int, Dict]]):
    """Handle the export of code snippets from the conversation"""
    try:
        options = [f"Message {i}: {msg['content'][:50]}..."
                   for i, msg in enumerate(code_msgs)]
    except Exception as e:
        logger.error(f"Error in code export: {str(e)}")
        st.error("Failed to export code snippets")

    selected = st.multiselect("Select code snippets to export:", options)

    if selected and st.button("Export Selected Code"):
        indices = [code_msgs[i][0] for i in range(len(code_msgs))
                   if options[i] in selected]

        exported = manager.export_selected_code(
            st.session_state.selected_conv,
            indices
        )

        if exported:
            st.success(f"Successfully exported {len(exported)} code snippets")

            # Provide download links for exported files
            for file_path in exported:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    st.download_button(
                        label=f"Download {file_path.name}",
                        data=content,
                        file_name=file_path.name,
                        mime="text/plain",
                        key=f"download_code_{file_path.name}"
                    )
        else:
            st.warning("No code files were exported")


def display_code_viewer():
    """Display the code viewer interface"""
    try:
        with st.expander("Code Viewer"):
            # Display app.py
            st.subheader("Application Code (app.py)")
            with open(__file__, 'r', encoding='utf-8') as f:
                app_content = f.read()
            st.text_area("App Code", app_content, height=400)

            # Display chat_manager.py
            st.subheader("Chat Manager Code (chat_manager.py)")
            chat_manager_path = Path(__file__).parent / "chat_manager.py"
            if chat_manager_path.exists():
                with open(chat_manager_path, 'r', encoding='utf-8') as f:
                    manager_content = f.read()
                st.text_area("Chat Manager Code", manager_content, height=400)
            else:
                st.warning("chat_manager.py not found")

    except Exception as e:
        logger.error(f"Error displaying code viewer: {str(e)}")
        st.error("Failed to display code viewer")

def display_statistics(manager: ChatHistoryManager):
    """Display conversation statistics"""
    try:
        stats = manager.get_conversation_statistics(st.session_state.selected_conv)

        if not stats:
            return

        with st.expander("Conversation Statistics"):
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Total Messages", stats['total_messages'])
                st.metric("User Messages", stats['user_messages'])
                st.metric("AI Messages", stats['ai_messages'])
                st.metric("Files Shared", stats['files_shared'])

            with col2:
                st.metric("Total Tokens", stats['total_tokens'])
                service_usage = stats['service_usage']
                for service, count in service_usage.items():
                    if count > 0:
                        st.metric(f"{service.capitalize()} Usage", count)

            if stats.get('conversation_duration'):
                st.info(f"Conversation Duration: {stats['conversation_duration']}")
            if stats.get('last_activity'):
                st.info(f"Last Activity: {stats['last_activity']}")

    except Exception as e:
        logger.error(f"Error displaying statistics: {str(e)}")

def main():
    """Main application entry point"""
    try:
        # Initialize session state and components
        SessionState.initialize_state()
        manager = ChatHistoryManager()
        chat_interface = ChatInterface(manager)
        sidebar_manager = SidebarManager(manager)

        # Configure page
        st.set_page_config(
            page_title="RonnieRome Virtual Board Room - GameDev",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        st.title("RonnieRome Virtual Board Room - GameDev")

        # Apply selected theme
        theme_choice = st.selectbox(
            "Select Theme",
            list(ThemeManager.THEMES.keys()),
            key="theme_choice"
        )
        ThemeManager.apply_theme(theme_choice)

        # Configure sidebar
        sidebar_manager.configure_sidebar()

        # Main chat area
        if st.session_state.selected_conv:
            conversation = manager.get_conversation(st.session_state.selected_conv)
            if conversation:
                # Display conversation title and export options
                st.caption(f"Current Chat: {conversation['title']}")
                handle_exports(manager, conversation)

                # Display messages
                chat_interface.display_messages(conversation)

                # Handle new user input
                user_input = st.chat_input("Message")
                if user_input:
                    chat_interface.handle_user_input(user_input)

                # Display code viewer if enabled
                if st.session_state.show_code_popup:
                    display_code_viewer()
                display_statistics(manager)

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()