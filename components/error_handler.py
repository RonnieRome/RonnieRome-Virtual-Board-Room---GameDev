import streamlit as st
import traceback
from typing import Optional, Dict, Any, Callable
from datetime import datetime

class ErrorHandler:
    def __init__(self, logging_service):
        self.logging_service = logging_service
        self.error_messages = {
            'file_upload': 'There was an error processing your file. Please try again or contact support.',
            'api_error': 'We encountered an issue connecting to the service. Please try again later.',
            'authentication': 'Authentication failed. Please check your credentials.',
            'rate_limit': 'Rate limit exceeded. Please wait a moment before trying again.',
            'invalid_input': 'Please check your input and try again.',
            'conversation': 'Error accessing conversation data. Please try refreshing the page.',
            'export': 'Unable to export data. Please try again.',
            'permission': 'You do not have permission to perform this action.',
            'system': 'A system error occurred. Please try again or contact support.'
        }

    def handle_error(self, error: Exception, error_type: str,
                    context: Optional[Dict[str, Any]] = None,
                    show_message: bool = True) -> None:
        """Handle an error with logging and optional user feedback."""
        timestamp = datetime.now().isoformat()
        error_details = {
            'timestamp': timestamp,
            'type': error_type,
            'error_class': error.__class__.__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {}
        }

        # Log the error
        self.logging_service.log_error(error, error_details)

        # Show user feedback if requested
        if show_message:
            self.show_error_message(error_type)

    def handle_operation(self, operation: Callable, error_type: str,
                        context: Optional[Dict[str, Any]] = None,
                        show_message: bool = True):
        """Execute an operation with error handling."""
        try:
            return operation()
        except Exception as e:
            self.handle_error(e, error_type, context, show_message)
            return None

    def show_error_message(self, error_type: str) -> None:
        """Display an error message to the user."""
        message = self.error_messages.get(
            error_type,
            'An unexpected error occurred. Please try again.'
        )
        st.error(message)

    def show_warning(self, message: str) -> None:
        """Display a warning message to the user."""
        st.warning(message)

    def show_success(self, message: str) -> None:
        """Display a success message to the user."""
        st.success(message)

    def format_error_for_api(self, error: Exception,
                           error_type: str) -> Dict[str, Any]:
        """Format an error for API responses."""
        return {
            'status': 'error',
            'error_type': error_type,
            'message': self.error_messages.get(error_type, str(error)),
            'timestamp': datetime.now().isoformat()
        }

    def is_recoverable_error(self, error: Exception) -> bool:
        """Determine if an error is recoverable."""
        unrecoverable_errors = (
            PermissionError,
            FileNotFoundError,
            KeyError,
            AttributeError
        )
        return not isinstance(error, unrecoverable_errors)

    def get_error_resolution_steps(self, error_type: str) -> str:
        """Get resolution steps for common errors."""
        resolution_steps = {
            'file_upload': """
                1. Check if the file format is supported
                2. Ensure the file is not corrupted
                3. Try uploading a smaller file
                4. Clear your browser cache and try again
            """,
            'api_error': """
                1. Check your internet connection
                2. Verify your API keys are valid
                3. Wait a few minutes and try again
                4. Contact support if the issue persists
            """,
            'authentication': """
                1. Verify your credentials
                2. Try logging out and back in
                3. Clear your browser cookies
                4. Reset your password if needed
            """
        }
        return resolution_steps.get(error_type, 'Please try again or contact support.')

    def cleanup_error_logs(self, days_to_keep: int = 30) -> None:
        """Clean up old error logs."""
        try:
            self.logging_service.cleanup_old_logs(days_to_keep)
        except Exception as e:
            print(f"Error cleaning up logs: {str(e)}")