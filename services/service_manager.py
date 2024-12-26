from typing import List, Dict, Optional
from config.app_config import AppConfig
from services.chat_manager import ChatHistoryManager  # Updated import
from services.logging_service import LoggingService
import logging
import os

# Set up debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ServiceManager:
    def __init__(self):
        """Initialize all services needed by the application."""
        logger.debug("Starting ServiceManager initialization")

        try:
            # First, load configuration
            logger.debug("Initializing AppConfig")
            self.config = AppConfig()

            # Initialize logging service
            logger.debug("Initializing LoggingService")
            self.logging = LoggingService()
            self.logging.log_app_event('service_manager_init', {'status': 'starting'})

            # Initialize chat manager
            logger.debug("Initializing ChatHistoryManager")
            self.chat_manager = ChatHistoryManager()
            logger.debug("ChatHistoryManager initialized successfully")

            # Log successful initialization
            logger.debug("ServiceManager initialization completed successfully")
            self.logging.log_app_event('service_manager_init', {
                'status': 'completed',
                'services': ['chat_manager']
            })

        except Exception as e:
            logger.error(f"Error during ServiceManager initialization: {str(e)}", exc_info=True)
            self.logging.log_error('service_manager_init', str(e))
            raise

    def handle_file_upload(self, files: list, conv_id: str) -> List[Dict]:
        """Process uploaded files and store them in the conversation."""
        logger.debug(f"Handling file upload for conversation {conv_id}")
        return self.chat_manager.handle_multiple_files(files, conv_id)

    def handle_ai_request(
            self,
            conv_id: str,
            prompt: str,
            service: str = 'claude',
            model: Optional[str] = None,
            image_data: Optional[str] = None
    ) -> str:
        """Process an AI request through the appropriate service."""
        logger.debug(f"Handling AI request for service: {service}, model: {model}")
        service = service.lower()

        try:
            if service == 'claude':
                logger.debug("Routing request to Claude service")
                return self.chat_manager.send_to_claude(
                    conv_id, prompt, model, image_data
                )
            elif service == 'chatgpt':
                logger.debug("Routing request to ChatGPT service")
                return self.chat_manager.send_to_chatgpt(
                    conv_id, prompt, model
                )
            elif service == 'dalle':
                logger.debug("Routing request to DALL-E service")
                return self.chat_manager.generate_image_dalle(
                    conv_id, prompt, model
                )
            elif service == 'gemini':
                logger.debug("Routing request to Gemini service")
                return self.chat_manager.send_to_gemini(
                    conv_id, prompt, model
                )
            else:
                logger.error(f"Unsupported AI service requested: {service}")
                raise ValueError(f"Unsupported AI service: {service}")

        except Exception as e:
            logger.error(f"Error processing AI request: {str(e)}", exc_info=True)
            self.logging.log_error('ai_request', str(e))
            raise

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