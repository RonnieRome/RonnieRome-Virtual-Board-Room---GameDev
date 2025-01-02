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
        """Initialize the app runner with necessary state tracking."""
        self.app_manager: Optional[AppManager] = None
        self.start_time = datetime.now()
        self.analysis_initialized = False
        load_dotenv()  # Load environment variables

    async def initialize_app(self) -> None:
        """
        Initializes the application asynchronously, handling startup tasks
        in the correct order while maintaining proper error handling.
        """
        try:
            logger.info("Starting application initialization")

            # Step 1: Load frontend dependencies
            load_frontend_dependencies()

            # Step 2: Initialize the app manager
            self.app_manager = AppManager()

            # Step 3: Initialize core components
            await self._initialize_core_components()

            # Step 4: Handle any pending analysis tasks
            await self._handle_pending_analysis()

            logger.info("Application initialization completed successfully")
            self.analysis_initialized = True

        except Exception as e:
            logger.error("Failed to initialize application", exc_info=True)
            self._handle_critical_error(e)
            raise


    async def _initialize_core_components(self) -> None:
        """Initialize core components while maintaining proper state."""
        try:
            if not hasattr(st.session_state, 'initialized'):
                self._initialize_analysis_state()
                st.session_state.initialized = True

            # Initialize remaining app components if manager exists
            if self.app_manager:
                self.app_manager.initialize_core_components()

        except Exception as e:
            logger.error("Failed to initialize core components", exc_info=True)
            raise

    def _initialize_analysis_state(self):
        """Setup initial analysis panel state in session."""
        if 'analysis_panel_state' not in st.session_state:
            st.session_state.analysis_panel_state = {
                'visible': False,
                'selected_file': None,
                'analysis_results': None,
                'loading': False,
                'error': None
            }

    async def _handle_pending_analysis(self) -> None:
        """Process any pending file analysis tasks from previous sessions."""
        try:
            if st.session_state.get('pending_analysis'):
                logger.info("Processing pending analysis tasks")

                # Update UI to show loading state
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

                # Clean up pending state
                st.session_state.pending_analysis = False
                st.session_state.pending_files = []

        except Exception as e:
            logger.error("Error processing pending analysis", exc_info=True)
            self._handle_analysis_error(e)
            self._update_analysis_state(loading=False, error=str(e))

    def _update_analysis_state(self, loading: bool = False,
                             results: Optional[Dict] = None,
                             error: Optional[str] = None):
        """Update analysis panel state with new values."""
        if 'analysis_panel_state' not in st.session_state:
            self._initialize_analysis_state()

        st.session_state.analysis_panel_state.update({
            'loading': loading,
            'error': error
        })

        if results is not None:
            st.session_state.analysis_panel_state['analysis_results'] = results


    def render_application(self) -> None:
        """Render the main application interface with proper error handling."""
        try:
            if self.app_manager:
                self.app_manager.render()
            else:
                raise RuntimeError("Application manager not properly initialized")

        except Exception as e:
            logger.error("Error rendering application", exc_info=True)
            self._handle_critical_error(e)

    def _render_analysis_panel(self):
        """Render the analysis panel with mouse tracking and auto-hide support."""
        panel_html = """
        <div id="analysis-panel"
             onmouseover="handle_mouse_over(true)"
             onmouseout="handle_mouse_over(false)"
             style="background-color: #f8f9fa; padding: 20px; border: 1px solid #ccc; border-radius: 4px;">
             <h3>Analysis Panel</h3>
             <p>Your analysis results will be displayed here.</p>
        </div>

        <script>
            function handle_mouse_over(isOver) {
                const message = { 'type': 'streamlit:mouseOverPanel', 'isOver': isOver };
                window.parent.postMessage(message, '*');
            }
        </script>
        """
        st.markdown(panel_html, unsafe_allow_html=True)

    def _handle_critical_error(self, error: Exception) -> None:
        """Handle critical application errors with proper user notification."""
        error_message = f"Critical application error: {str(error)}"
        logger.error(error_message, exc_info=True)

        # Update session state for error tracking
        st.session_state.critical_error = error_message

        # Show user-friendly error message
        st.error(
            "An unexpected error occurred during application startup. "
            "Please try refreshing the page or contact support."
        )

    def _handle_analysis_error(self, error: Exception) -> None:
        """Handle analysis-specific errors while maintaining application stability."""
        error_message = f"Analysis error: {str(error)}"
        logger.error(error_message, exc_info=True)

        # Update error states
        st.session_state.analysis_error = error_message

        # Show warning that allows application to continue
        st.warning(
            "An error occurred during file analysis. "
            "Some features may be limited. Please try again or contact support."
        )

async def main() -> None:
    """
    Main application entry point with comprehensive async support and error handling.
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
        logger.error("Unhandled exception in the main function.", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())