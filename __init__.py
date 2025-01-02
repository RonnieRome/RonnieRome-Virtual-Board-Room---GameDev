import streamlit as st
from typing import Optional
from services.service_manager import ServiceManager
from components.sidebar import Sidebar
from components.chat_area import ChatArea


class AppComponents:
    def __init__(self, service_manager: Optional['ServiceManager'] = None):
        """
        Initialize application components with enhanced service management.

        Args:
            service_manager: Optional ServiceManager instance. If not provided,
                           a new instance will be created.
        """
        # Initialize service manager
        self.service_manager = service_manager or ServiceManager()

        # Initialize core components with service manager
        self.sidebar = Sidebar(self.service_manager, self.service_manager.state_manager)
        self.chat_area = ChatArea(self.service_manager)

        # Initialize session state
        self._initialize_session_state()

    def _initialize_session_state(self):
        """Initialize required session state variables with defaults."""
        defaults = {
            'show_title_input': True,
            'selected_conv': None,
            'messages': [],
            'ai_service': 'claude',
            'analysis_results': [],
            'show_code_popup': False,
            'theme': 'Transparent',
            'uploaded_files': [],
            'clipboard_image': None,
            'show_reset_confirm': False
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def render(self):
        """Render all application components in the correct order."""
        try:
            # Apply theme first
            self.service_manager.theme_manager.apply_theme(
                st.session_state.get('theme', 'Transparent')
            )

            # Render components
            self.sidebar.render()
            self.chat_area.render()

        except Exception as e:
            self.service_manager.error_handler.handle_error(
                error=e,
                error_type='render',
                context={'location': 'AppComponents.render'},
                show_message=True
            )