import streamlit as st
from .sidebar import Sidebar
from .chat_area import ChatArea
from services.chat_manager import ChatHistoryManager
from services.file_manager import FileManager
from config.app_config import AppConfig
from config.styles import StyleConfig


class AppComponents:
    def __init__(self):
        self.config = AppConfig
        self.style_config = StyleConfig
        self.chat_manager = ChatHistoryManager()
        self.file_manager = FileManager()

        # Initialize components
        self.sidebar = Sidebar(self.chat_manager)
        self.chat_area = ChatArea(self.chat_manager)

        # Ensure required session state variables exist
        self._initialize_session_state()

    def render(self):
        """Render all application components."""
        self._apply_theme()
        self.sidebar.render()
        self.chat_area.render()

    def _initialize_session_state(self):
        """Initialize required session state variables."""
        default_state = {
            'show_title_input': True,
            'selected_conv': None,
            'messages': [],
            'ai_service': 'Claude',
            'analysis_results': [],
            'show_code_popup': False,
            'theme': 'Pastel Delight'
        }

        for key, default_value in default_state.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    def _apply_theme(self):
        """Apply the selected theme to the application."""
        current_theme = st.session_state.get('theme', 'None')
        theme_css = self.style_config.get_theme_css(current_theme)
        font_style = self.style_config.get_font_style(current_theme)

        st.markdown(theme_css, unsafe_allow_html=True)
        st.markdown(font_style, unsafe_allow_html=True)