import streamlit as st
from app_manager import AppManager
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def main():
    """Main application entry point."""
    try:
        # Initialize application manager
        app_manager = AppManager()

        # Initialize application
        app_manager.initialize_app()

        # Render the application
        app_manager.render()

    except Exception as e:
        logger.error(f"Application Error: {str(e)}", exc_info=True)
        st.error(
            "An unexpected error occurred. Please try refreshing the page or contact support."
        )

if __name__ == "__main__":
    main()