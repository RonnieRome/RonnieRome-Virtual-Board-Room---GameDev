import logging
import os
import streamlit as st

from typing import List, Dict, Optional
from datetime import datetime
from config.app_config import AppConfig
from config.ai_style_manager import AIStyleManager
from services.chat_manager import ChatHistoryManager  # Updated import
from services.logging_service import LoggingService
from services.context_manager import ContextManager  # Updated import path
from components.error_handler import ErrorHandler
from services.document_manager import DocumentManager
from services.file_manager import FileManager


# Set up debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ServiceManager:
    def __init__(self):
        """Initialize all services needed by the application."""
        try:
            logger.debug("Initializing AppConfig")
            self.config = AppConfig()

            logger.debug("Initializing LoggingService")
            self.logging_service = LoggingService()

            logger.debug("Initializing ErrorHandler")
            self.error_handler = ErrorHandler(self.logging_service)

            logger.debug("Initializing FileManager")
            self.file_manager = FileManager()

            logger.debug("Initializing ContextManager")
            self.context_manager = ContextManager()

            logger.debug("Initializing ChatHistoryManager")
            self.chat_manager = ChatHistoryManager()

            logger.debug("Initializing AIStyleManager")
            self.style_manager = AIStyleManager()

            logger.debug("ServiceManager initialization completed successfully")
            self.logging_service.log_app_event('service_manager_init', {
                'status': 'completed',
                'services': [
                    'logging_service',
                    'error_handler',
                    'file_manager',
                    'context_manager',
                    'chat_manager',
                    'style_manager'
                ]
            })

        except Exception as e:
            logger.error(f"Error during ServiceManager initialization: {str(e)}", exc_info=True)
            raise

    def handle_file_upload(self, files: list, conv_id: str) -> List[Dict]:
        """Process uploaded files and store them in the conversation.

        This method handles the complete file upload process, from receiving the files
        to storing them in the conversation context. It processes both single and
        multiple files, ensuring proper error handling and logging throughout.

        Args:
            files: A list of uploaded file objects
            conv_id: The unique identifier for the conversation

        Returns:
            A list of dictionaries containing the processed file information
        """
        logger.debug(f"Starting file upload process for conversation {conv_id}")
        logger.debug(f"Received {len(files)} files")

        processed_files = []

        try:
            # Process each file individually
            for file in files:
                try:
                    logger.debug(f"Processing file: {getattr(file, 'name', 'unnamed')} for conversation: {conv_id}")

                    # Process the individual file using FileManager
                    file_data = self.file_manager.handle_file_upload(file, conv_id)

                    # Store successful file data in chat history
                    if file_data and 'error' not in file_data:
                        self.chat_manager.add_file_to_conversation(conv_id, file_data)

                    processed_files.append(file_data)

                except Exception as e:
                    error_msg = f"Error processing file: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    processed_files.append({
                        'name': getattr(file, 'name', 'unnamed'),
                        'type': 'error',
                        'error': error_msg,
                        'processed_at': datetime.now().isoformat()
                    })

            # Log the overall processing results
            successful_files = len([f for f in processed_files if f and 'error' not in f])
            self.logging_service.log_app_event('file_upload_complete', {
                'conversation_id': conv_id,
                'metrics': {
                    'total_files': len(files),
                    'processed_files': len(processed_files),
                    'successful_files': successful_files,
                    'failed_files': [
                        {
                            'file_name': f.get('name', 'unnamed'),
                            'error': f.get('error', 'Unknown error')
                        }
                        for f in processed_files if f and 'error' in f
                    ]
                }
            })

            return processed_files

        except Exception as e:
            error_msg = f"Error in handle_file_upload: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_handler.handle_error(
                error=e,
                error_type='file_upload',
                context={
                    'operation': 'file_upload',
                    'conversation_id': conv_id
                },
                show_message=True
            )
            return []

    def handle_ai_request(
            self,
            conv_id: str,
            prompt: str,
            service: str = 'claude',
            model: Optional[str] = None,
            image_data: Optional[str] = None
    ) -> str:
        """Process an AI request through the appropriate service.

        This method handles the routing of requests to different AI services while ensuring
        proper context management, including file content and conversation history.

        Args:
            conv_id (str): Unique identifier for the conversation
            prompt (str): The user's input prompt
            service (str): The AI service to use (default: 'claude')
            model (Optional[str]): Specific model to use, if applicable
            image_data (Optional[str]): Base64 encoded image data, if present

        Returns:
            str: The AI service's response

        Raises:
            Exception: If there's an error processing the request
        """
        logger.debug(f"Handling AI request for conversation {conv_id}")
        service = service.lower()

        try:
            # Get conversation and validate it exists
            conversation = self.chat_manager.get_conversation(conv_id)
            if not conversation:
                logger.warning(f"No conversation found for ID: {conv_id}")
                conversation = {'messages': [], 'files': []}

            # Get current style and prepare messages
            current_style = st.session_state.get('selected_style', 'Business')
            messages = conversation.get('messages', [])

            # Include file content in the context if present
            files = conversation.get('files', [])
            if files:
                logger.debug(f"Found {len(files)} files in conversation")
                file_context = self._prepare_file_context(files)
                messages = self._inject_file_context(messages, file_context)

            # Format messages according to the selected style and service
            formatted_messages = self.style_manager.format_messages_for_service(
                messages,
                current_style,
                service
            )

            logger.debug(f"Routing request to {service} service")

            # Route to appropriate service
            if service == 'claude':
                logger.debug(f"Using Claude model: {model if model else 'default'}")
                return self.chat_manager.send_to_claude(
                    conv_id,
                    prompt,
                    model,
                    formatted_messages
                )

            elif service == 'chatgpt':
                logger.debug(f"Using ChatGPT model: {model if model else 'default'}")
                return self.chat_manager.send_to_chatgpt(
                    conv_id,
                    prompt,
                    model,
                    formatted_messages
                )

            elif service == 'dalle':
                logger.debug("Using DALL-E for image generation")
                return self.chat_manager.generate_image_dalle(
                    conv_id,
                    prompt,
                    model
                )

            elif service == 'gemini':
                logger.debug(f"Using Gemini model: {model if model else 'default'}")
                # Handle image data for Gemini if present
                if image_data:
                    logger.debug("Including image data with Gemini request")
                    return self.chat_manager.send_to_gemini(
                        conv_id,
                        prompt,
                        model,
                        formatted_messages,
                        image_data=image_data
                    )
                return self.chat_manager.send_to_gemini(
                    conv_id,
                    prompt,
                    model,
                    formatted_messages
                )

            else:
                error_msg = f"Unsupported AI service: {service}"
                logger.error(error_msg)
                raise ValueError(error_msg)

        except Exception as e:
            logger.error(f"Error processing AI request: {str(e)}", exc_info=True)
            self.logging_service.log_error('ai_request', str(e))
            raise

    def _prepare_file_context(self, files: List[Dict]) -> str:
        """Prepare file content for inclusion in AI context."""
        try:
            file_contexts = []
            for file in files:
                if file['type'] == 'text':
                    file_contexts.append(f"Content of file '{file['name']}':\n{file['content']}")
                elif file['type'] == 'image':
                    file_contexts.append(f"An image file '{file['name']}' is present in the conversation.")
            return "\n\n".join(file_contexts)
        except Exception as e:
            logger.error(f"Error preparing file context: {str(e)}", exc_info=True)
            return ""

    def _inject_file_context(self, messages: List[Dict], file_context: str) -> List[Dict]:
        """Insert file context into message history."""
        if not messages:
            messages = []
        messages.insert(0, {
            'role': 'system',
            'content': f"The following files are part of this conversation:\n\n{file_context}"
        })
        return messages

    def _inject_file_context(self, messages: List[Dict], file_context: str) -> List[Dict]:
        """Insert file context into message history."""
        if not messages:
            messages = []
        messages.insert(0, {
            'role': 'system',
            'content': f"The following files have been uploaded:\n\n{file_context}"
        })
        return messages

    def cleanup(self):
        """Clean up any resources used by the services."""
        logger.debug("Starting ServiceManager cleanup")
        try:
            # Add cleanup operations as needed
            logger.debug("ServiceManager cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}", exc_info=True)
            self.logging.log_error('cleanup', str(e))
            raise