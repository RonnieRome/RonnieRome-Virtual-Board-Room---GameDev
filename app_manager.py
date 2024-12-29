import streamlit as st
import logging
from typing import Optional, Dict, List
from datetime import datetime

from config.app_config import AppConfig
from config.styles import StyleConfig
from components.sidebar import Sidebar
from components.chat_area import ChatArea
from components.error_handler import ErrorHandler
from components.theme_manager import ThemeManager
from components.export_manager import ExportManager
from components.state_manager import StateManager
from components.analysis_panel import AnalysisPanel
from services.ai_analysis_integration import AIAnalysisManager
from services.service_manager import ServiceManager


logger = logging.getLogger(__name__)


class AppManager:
    def __init__(self):
        """Initialize the application with enhanced error handling and state management."""
        try:
            # Initialize core configuration
            self.config = AppConfig()
            self._initialize_services()
            self._initialize_managers()
            self._initialize_ui_components()

            # Set up error tracking
            self.error_states = {
                'initialization_complete': False,
                'last_error': None,
                'error_count': 0
            }

            logger.info("AppManager initialization completed successfully")

        except Exception as e:
            logger.error(f"Critical initialization error: {str(e)}", exc_info=True)
            self._handle_initialization_error(e)
            raise

    def _initialize_services(self):
        """Initialize core services with enhanced error handling."""
        try:
            # Initialize ServiceManager first as other components depend on it
            self.service_manager = ServiceManager()

            # Validate critical services
            if not hasattr(self.service_manager, 'chat_manager'):
                raise RuntimeError("ChatManager not properly initialized")

            # Initialize AI Analysis with retry capability
            self.ai_manager = AIAnalysisManager(self.service_manager)

            logger.info("Services initialized successfully")

        except Exception as e:
            logger.error(f"Service initialization error: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to initialize services: {str(e)}")

    def _initialize_managers(self):
        """Initialize application managers with proper dependency handling."""
        try:
            # Initialize managers in order of dependency
            self.state_manager = StateManager()
            self.theme_manager = ThemeManager(StyleConfig)
            self.error_handler = ErrorHandler(self.service_manager.logging_service)
            self.export_manager = ExportManager(self.service_manager)

            logger.info("Managers initialized successfully")

        except Exception as e:
            logger.error(f"Manager initialization error: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to initialize managers: {str(e)}")

    def _initialize_ui_components(self):
        """Initialize UI components with proper error handling."""
        try:
            # Initialize UI components with required dependencies
            self.sidebar = Sidebar(self.service_manager, self.state_manager)
            self.chat_area = ChatArea(self.service_manager, self.theme_manager)

            # Initialize analysis panel with enhanced capabilities
            self.analysis_panel = AnalysisPanel(
                state_manager=self.state_manager,
                ai_manager=self.ai_manager
            )

            logger.info("UI components initialized successfully")

        except Exception as e:
            logger.error(f"UI component initialization error: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to initialize UI components: {str(e)}")

    def _initialize_ui_components(self):
        """Initialize UI components with proper error handling."""
        try:
            # Initialize UI components with required dependencies
            self.sidebar = Sidebar(self.service_manager, self.state_manager)
            self.chat_area = ChatArea(self.service_manager, self.theme_manager)

            # Initialize analysis panel with enhanced capabilities
            self.analysis_panel = AnalysisPanel(
                state_manager=self.state_manager,
                ai_manager=self.ai_manager
            )

            logger.info("UI components initialized successfully")

        except Exception as e:
            logger.error(f"UI component initialization error: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to initialize UI components: {str(e)}")

    async def handle_file_analysis(self, conv_id: str, files: List[Dict]) -> Dict:
        """Handle file analysis with comprehensive error handling and retry logic."""
        try:
            logger.info(f"Starting file analysis for conversation {conv_id}")

            # Validate inputs
            if not conv_id or not files:
                raise ValueError("Invalid conversation ID or empty file list")

            # Update conversation state
            self.state_manager.set_state('analysis_in_progress', True)
            self.state_manager.set_state('current_analysis_files', [f['name'] for f in files])

            # Perform analysis with retries
            analysis_result = await self.ai_manager.analyze_files(conv_id, 'code_review')

            # Handle analysis completion
            if analysis_result.status == 'success':
                self._handle_successful_analysis(analysis_result, conv_id)
            else:
                self._handle_failed_analysis(analysis_result, conv_id)

            return {
                'status': analysis_result.status,
                'result': analysis_result,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error in file analysis: {str(e)}", exc_info=True)
            self._handle_analysis_error(e, conv_id)
            raise

        finally:
            # Clean up state
            self.state_manager.set_state('analysis_in_progress', False)
            self.state_manager.set_state('current_analysis_files', None)

    def _handle_analysis_error(self, error: Exception, conv_id: str):
        """Handle unexpected analysis errors."""
        error_msg = f"Unexpected error during analysis: {str(error)}"
        logger.error(error_msg, exc_info=True)

        # Update error state
        self.error_states['last_error'] = error_msg
        self.error_states['error_count'] += 1

        # Notify error handler
        if hasattr(self, 'error_handler'):
            self.error_handler.handle_error(
                error=error,
                error_type='analysis',
                context={'conversation_id': conv_id},
                show_message=True
            )

    def _handle_initialization_error(self, error: Exception):
        """Handle initialization errors with proper logging and state management."""
        error_msg = f"Initialization error: {str(error)}"
        logger.error(error_msg, exc_info=True)

        # Update error state
        self.error_states['last_error'] = error_msg
        self.error_states['error_count'] += 1
        self.error_states['initialization_complete'] = False

        # Store error in session state for UI handling
        if hasattr(st, 'session_state'):
            st.session_state.initialization_error = error_msg

    def get_error_summary(self) -> Dict:
        """Get a summary of error states for monitoring."""
        return {
            'initialization_complete': self.error_states['initialization_complete'],
            'last_error': self.error_states['last_error'],
            'error_count': self.error_states['error_count'],
            'ai_analysis_errors': self.ai_manager.get_recent_errors() if hasattr(self, 'ai_manager') else []
        }

    def initialize_app(self) -> None:
        """Initialize the application with enhanced error handling and state management."""
        logger.debug("Starting application initialization")

        try:
            # Initialize session state if needed
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
            current_theme = st.session_state.get('theme', 'Transparent')
            current_background = st.session_state.get('background', 'Transparent')

            self.theme_manager.apply_theme(
                theme_choice=current_theme,
                background_choice=current_background
            )

            # Mark initialization as complete
            self.error_states['initialization_complete'] = True
            logger.debug("Application initialization completed successfully")

        except Exception as e:
            self._handle_initialization_error(e)
            raise

    def render(self):
        """Render the application interface with enhanced error handling."""
        try:
            # Create main layout
            main_col, panel_col = st.columns([7, 3])

            with main_col:
                # Render sidebar and chat area
                self.sidebar.render()
                current_theme = st.session_state.get('theme', 'Transparent')
                theme_css = StyleConfig.get_theme_css(current_theme)
                self.chat_area.render(theme_css)

            with panel_col:
                # Render analysis panel if available
                if hasattr(self, 'analysis_panel'):
                    self.analysis_panel.render(StyleConfig)

        except Exception as e:
            logger.error(f"Error during render: {str(e)}", exc_info=True)
            self.error_handler.handle_error(
                error=e,
                error_type='render',
                context={'operation': 'render'},
                show_message=True
            )

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
