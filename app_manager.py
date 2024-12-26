import streamlit as st
import logging
from config.app_config import AppConfig
from services.service_manager import ServiceManager
from components.sidebar import Sidebar
from components.chat_area import ChatArea
from components.error_handler import ErrorHandler
from components.theme_manager import ThemeManager
from components.export_manager import ExportManager
from components.state_manager import StateManager

logger = logging.getLogger(__name__)


class AppManager:
    def __init__(self):
        """Initialize the application and its core components."""
        logger.debug("Starting AppManager initialization")

        try:
            # Initialize core configuration
            logger.debug("Initializing AppConfig")
            self.config = AppConfig()

            # Initialize the service manager
            logger.debug("Initializing ServiceManager")
            self.service_manager = ServiceManager()

            # Verify service manager initialization
            if not self.service_manager:
                raise RuntimeError("ServiceManager failed to initialize")

            # Verify chat manager initialization through service manager
            if not hasattr(self.service_manager, 'chat_manager'):
                raise RuntimeError("ChatManager not properly initialized in ServiceManager")

            logger.debug("ServiceManager and ChatManager initialized successfully")

            # Initialize managers
            logger.debug("Initializing application managers")
            self.state_manager = StateManager()
            self.theme_manager = ThemeManager()
            self.error_handler = ErrorHandler(self.service_manager.logging)
            self.export_manager = ExportManager(self.service_manager)

            # Initialize UI components with service_manager
            logger.debug("Initializing UI components")
            self.sidebar = Sidebar(self.service_manager)
            self.chat_area = ChatArea(self.service_manager)

            logger.debug("AppManager initialization completed successfully")

        except Exception as e:
            logger.error(f"Error during AppManager initialization: {str(e)}", exc_info=True)
            raise

    def initialize_app(self) -> None:
        """Set up the application's initial state and configuration."""
        logger.debug("Starting application initialization")

        try:
            # Initialize session state
            if not hasattr(st.session_state, 'initialized'):
                self._initialize_session_state()
                st.session_state.initialized = True

            # Set page configuration
            st.set_page_config(
                page_title="HappyRonnieRome Virtual Board Room - GameDev",
                layout="wide",
                initial_sidebar_state="expanded"
            )

            # Apply theme settings
            self.theme_manager.apply_theme(
                self.state_manager.get_state('theme', 'light'),
                self.state_manager.get_state('background', 'default')
            )

            logger.debug("Application initialization completed successfully")

        except Exception as e:
            logger.error(f"Error during app initialization: {str(e)}", exc_info=True)
            if hasattr(self, 'error_handler'):
                self.error_handler.handle_error(
                    e, 'system',
                    context={'location': 'initialize_app'},
                    show_message=True
                )
            else:
                st.error(f"Critical initialization error: {str(e)}")
            raise

    def _initialize_session_state(self):
        """Initialize session state with default values."""
        defaults = {
            'theme': 'light',
            'background': 'default',
            'ai_service': 'claude',
            'show_code_popup': False,
            'show_title_input': True
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def render(self):
        """Render the complete application interface."""
        try:
            # Render sidebar first
            self.sidebar.render()

            # Then render main chat area
            self.chat_area.render()

        except Exception as e:
            logger.error(f"Error during render: {str(e)}", exc_info=True)
            self.error_handler.handle_error(
                e, 'system',
                context={'operation': 'render'},
                show_message=True
            )