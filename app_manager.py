import streamlit as st
import logging
import asyncio
from typing import Optional, Dict, List
from datetime import datetime

from config.app_config import AppConfig
from config.styles import StyleConfig
from components.analysis_panel import AnalysisPanel
from components.chat_area import ChatArea
from components.error_handler import ErrorHandler
from components.export_manager import ExportManager
from components.file_analyzer import FileAnalyzer
from components.sidebar import Sidebar
from components.state_manager import StateManager
from components.theme_manager import ThemeManager
from services.ai_analysis_integration import AIAnalysisManager
from services.service_manager import ServiceManager

logger = logging.getLogger(__name__)

class AppManager:
    def __init__(self):
        """Initialize the application with enhanced error handling and state management."""
        # Initialize error states first
        self.error_states = {
            'initialization_complete': False,
            'last_error': None,
            'error_count': 0
        }

        try:
            # Set up logging
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)

            # Initialize core configuration
            self.config = AppConfig()

            # Initialize components in order
            self._initialize_services()
            self._initialize_managers()
            self._initialize_ui_components()

            # Mark initialization as complete
            self.error_states['initialization_complete'] = True
            logger.info("AppManager initialization completed successfully")

        except Exception as e:
            logger.error(f"Critical initialization error: {str(e)}", exc_info=True)
            self._handle_initialization_error(e)
            raise

    def _initialize_panel_state(self):
        """Initialize the analysis panel state variables."""
        initial_state = {
            'panel_visible': False,
            'selected_file': None,
            'analysis_results': None,
            'analysis_loading': False,
            'error_message': None,
            'last_update': None,
            'active_tab': 'summary'
        }

        for key, value in initial_state.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def initialize_core_components(self) -> None:
        """Initialize core components without page configuration."""
        try:
            # Initialize session state if needed
            if not hasattr(st.session_state, 'initialized'):
                self._initialize_session_state()
                st.session_state.initialized = True

            # Apply theme settings
            current_theme = st.session_state.get('theme', 'Transparent')
            current_background = st.session_state.get('background', 'Transparent')

            self.theme_manager.apply_theme(
                theme_choice=current_theme,
                background_choice=current_background
            )

            # Mark initialization as complete
            self.error_states['initialization_complete'] = True
            logger.debug("Core components initialization completed successfully")

        except Exception as e:
            self._handle_initialization_error(e)
            raise

    def _initialize_services(self):
        """Initialize core services with enhanced error handling."""
        try:
            # Initialize ServiceManager first as other components depend on it
            self.service_manager = ServiceManager()

            # Initialize chat manager if not present
            if not hasattr(self.service_manager, 'chat_manager'):
                from services.chat_manager import ChatHistoryManager
                self.service_manager.chat_manager = ChatHistoryManager()

            # Initialize file analyzer
            self.file_analyzer = FileAnalyzer()

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
        """Initialize UI components with proper error handling and file handling integration."""
        try:
            # Initialize UI components with required dependencies
            self.sidebar = Sidebar(self.service_manager, self.state_manager)
            self.chat_area = ChatArea(self.service_manager, self.theme_manager)

            # Initialize analysis panel state
            self._initialize_panel_state()

            # Initialize analysis panel
            self.analysis_panel = AnalysisPanel(
                state_manager=self.state_manager,
                ai_manager=self.ai_manager,
                service_manager=self.service_manager
            )

            # Set up file handling integration using synchronous registration
            def sync_file_handler(files):
                asyncio.create_task(self.handle_file_upload(files))

            self.service_manager.register_file_handler(sync_file_handler)

            logger.info("UI components initialized successfully")
        except Exception as e:
            logger.error(f"UI components initialization error: {str(e)}", exc_info=True)
            raise

    async def handle_file_analysis(self, conv_id: str, files: List[Dict]) -> Dict:
        """Handle file analysis with comprehensive error handling."""
        try:
            logger.info(f"Starting file analysis for conversation {conv_id}")

            # Validate inputs
            if not conv_id or not files:
                raise ValueError("Invalid conversation ID or empty file list")

            # Update conversation state
            self.state_manager.set_state('analysis_in_progress', True)
            self.state_manager.set_state('current_analysis_files', [f['name'] for f in files])

            # Process files through FileAnalyzer
            analysis_results = self.file_analyzer.analyze_file_batch(files)

            # Get AI insights for the files
            ai_context = self.file_analyzer.get_ai_context()
            ai_results = await self.ai_manager.analyze_files(conv_id, 'code_review', ai_context)

            # Combine analysis results
            combined_results = {
                'file_analysis': analysis_results,
                'ai_insights': ai_results,
                'timestamp': datetime.now().isoformat()
            }

            return {
                'status': 'success',
                'result': combined_results,
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

    async def handle_file_upload(self, files: List[Dict]) -> None:
        """Handle file upload and trigger analysis asynchronously."""
        try:
            if not files:
                logger.warning("No files provided for upload")
                return

            # Get current conversation ID
            conv_id = st.session_state.get('selected_conv')
            if not conv_id:
                logger.warning("No conversation selected for file upload")
                st.error("Please select or start a conversation first")
                return

            # Update UI state to show loading
            st.session_state.analysis_loading = True

            try:
                # Process files asynchronously
                processed_files = await self.service_manager.handle_file_upload(files, conv_id)

                # Update conversation with processed files
                await self.service_manager.chat_manager.update_conversation_files_async(conv_id, processed_files)

                # Perform file analysis
                st.session_state.analysis_loading = True
                analysis_results = await self.handle_file_analysis(conv_id, processed_files)

                # Update session state with results
                st.session_state.analysis_results = analysis_results['result']
                st.session_state.selected_file = processed_files[0]['name'] if processed_files else None
                st.session_state.panel_visible = True

                # Update conversation context with file information
                file_context = self.service_manager._prepare_file_context(processed_files)
                await self.service_manager.context_manager.update_context_async(conv_id, {
                    'files': file_context,
                    'analysis': analysis_results['result']
                })

                logger.info(f"Successfully processed and analyzed {len(files)} files")

            except Exception as e:
                logger.error(f"Error processing files: {str(e)}", exc_info=True)
                st.error(f"Error processing files: {str(e)}")

            finally:
                st.session_state.analysis_loading = False

        except Exception as e:
            logger.error(f"Error in file upload handling: {str(e)}", exc_info=True)
            st.error("An error occurred during file upload. Please try again.")
            st.session_state.analysis_loading = False
            raise

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
        """Render the main application interface."""
        self.sidebar.render()
        self.chat_area.render()

    def _toggle_panel(self):
        """Toggle analysis panel visibility"""
        st.session_state.panel_visible = not st.session_state.get('panel_visible', False)


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
