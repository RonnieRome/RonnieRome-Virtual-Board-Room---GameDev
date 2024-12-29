import streamlit as st
import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime
from app_manager import AppManager
from dotenv import load_dotenv
from components.frontend_dependencies import load_frontend_dependencies

# Configure logging with more detailed formatting
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class AsyncAppRunner:
    """
    Manages the asynchronous execution of the application.
    This class handles the lifecycle of async operations and ensures proper
    cleanup and error handling.
    """

    def __init__(self):
        self.app_manager: Optional[AppManager] = None
        self.start_time = datetime.now()
        self.analysis_initialized = False
        load_dotenv()

    async def initialize_app(self) -> None:
        """
        Initializes the application asynchronously, handling any startup tasks
        that need to be performed before the main application runs.
        """
        try:
            logger.info("Starting application initialization")

            # Load frontend dependencies first
            load_frontend_dependencies()

            # Initialize the app manager
            self.app_manager = AppManager()

            # Initialize core application components
            self.app_manager.initialize_app()

            # Handle any pending analysis tasks
            await self._handle_pending_analysis()

            logger.info("Application initialization completed successfully")
            self.analysis_initialized = True

        except Exception as e:
            logger.error("Failed to initialize application", exc_info=True)
            self._handle_critical_error(e)
            raise

    def _initialize_analysis_state(self):
        """
        Initializes analysis-specific state variables in the session state.
        This ensures all necessary state variables are available for the analysis panel.
        """
        if 'analysis_panel_state' not in st.session_state:
            st.session_state.analysis_panel_state = {
                'visible': False,
                'selected_file': None,
                'analysis_results': None,
                'loading': False,
                'error': None
            }

    async def _handle_pending_analysis(self) -> None:
        """
        Handles any pending file analysis tasks that were queued during the
        application startup or previous session.
        """
        try:
            if st.session_state.get('pending_analysis'):
                logger.info("Processing pending analysis tasks")

                # Update UI state to show loading
                self._update_analysis_state(loading=True)

                conv_id = st.session_state.get('selected_conv')
                files = st.session_state.get('pending_files', [])

                if conv_id and files:
                    # Process files through app manager
                    analysis_results = await self.app_manager.handle_file_analysis(conv_id, files)

                    # Update analysis panel with results
                    self._update_analysis_state(
                        loading=False,
                        results=analysis_results
                    )

                # Clear pending flags
                st.session_state.pending_analysis = False
                st.session_state.pending_files = []

        except Exception as e:
            logger.error("Error processing pending analysis", exc_info=True)
            self._handle_analysis_error(e)
            self._update_analysis_state(loading=False, error=str(e))

    def _update_analysis_state(self, loading: bool = False, results: Optional[Dict] = None,
                               error: Optional[str] = None):
        """
        Updates the analysis panel state in a coordinated manner.
        This ensures consistent state management across the application.
        """
        if 'analysis_panel_state' not in st.session_state:
            self._initialize_analysis_state()

        st.session_state.analysis_panel_state.update({
            'loading': loading,
            'error': error
        })

        if results is not None:
            st.session_state.analysis_panel_state['analysis_results'] = results

    def render_application(self) -> None:
        """
        Enhanced render method that coordinates main UI and analysis panel rendering.
        This ensures proper layout and state management between components.
        """
        try:
            if not self.app_manager:
                raise RuntimeError("Application manager not properly initialized")

            # Create two-column layout
            main_col, analysis_col = st.columns([7, 3])

            with main_col:
                # Render main application content
                self.app_manager.render_main_content()

            with analysis_col:
                # Render analysis panel if initialized
                if self.analysis_initialized:
                    self._render_analysis_panel()

        except Exception as e:
            logger.error("Error rendering application", exc_info=True)
            self._handle_critical_error(e)

    def _render_analysis_panel(self):
        """
        Handles the rendering of the analysis panel with proper state management.
        This method coordinates the display of analysis results and loading states.
        """
        panel_state = st.session_state.get('analysis_panel_state', {})

        if panel_state.get('loading'):
            with st.spinner("Analyzing files..."):
                st.empty()

        elif panel_state.get('error'):
            st.error(f"Analysis Error: {panel_state['error']}")

        elif panel_state.get('analysis_results'):
            results = panel_state['analysis_results']
            self.app_manager.analysis_panel.render_results(results)

    def _handle_analysis_error(self, error: Exception) -> None:
        """
        Enhanced error handler specifically for analysis-related errors.
        This method coordinates error handling between the backend and UI.
        """
        error_message = f"Analysis error: {str(error)}"
        logger.error(error_message, exc_info=True)

        # Update both session state and analysis panel state
        st.session_state.analysis_error = error_message
        self._update_analysis_state(error=error_message)

        # Show warning in UI
        st.warning(
            "An error occurred during file analysis. "
            "Some features may be limited. Please try again or contact support."
        )

    def _handle_critical_error(self, error: Exception) -> None:
        """
        Handles critical application errors that occur during initialization
        or runtime. Ensures proper logging and user notification.
        """
        error_message = f"Critical application error: {str(error)}"
        logger.error(error_message, exc_info=True)

        # Update session state for error display
        st.session_state.critical_error = error_message

        # Display error to user
        st.error(
            "An unexpected error occurred during application startup. "
            "Please try refreshing the page or contact support."
        )

    def _handle_analysis_error(self, error: Exception) -> None:
        """
        Handles errors that occur during file analysis operations.
        Ensures proper error logging and user notification while allowing
        the application to continue running.
        """
        error_message = f"Analysis error: {str(error)}"
        logger.error(error_message, exc_info=True)

        # Update session state for error tracking
        st.session_state.analysis_error = error_message

        # Notify user but allow application to continue
        st.warning(
            "An error occurred during file analysis. "
            "Some features may be limited. Please try again or contact support."
        )

    def render_application(self) -> None:
        """
        Renders the main application interface and handles any runtime
        UI-related tasks.
        """
        try:
            if self.app_manager:
                self.app_manager.render()
            else:
                raise RuntimeError("Application manager not properly initialized")

        except Exception as e:
            logger.error("Error rendering application", exc_info=True)
            self._handle_critical_error(e)


async def main() -> None:
    """
    Main application entry point with enhanced async support and error handling.
    This function coordinates the entire application lifecycle.
    """
    runner = AsyncAppRunner()

    try:
        # Initialize the application asynchronously
        await runner.initialize_app()

        # Render the main application interface
        runner.render_application()

        # Log successful startup
        startup_time = (datetime.now() - runner.start_time).total_seconds()
        logger.info(f"Application started successfully in {startup_time:.2f} seconds")

    except Exception as e:
        logger.error("Application failed to start", exc_info=True)
        st.error(
            "Failed to start the application. Please refresh the page or contact support. "
            f"Error: {str(e)}"
        )


if __name__ == "__main__":
    asyncio.run(main())