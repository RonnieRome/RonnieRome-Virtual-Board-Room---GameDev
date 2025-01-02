import logging
import os
import streamlit as st
from typing import List, Dict, Optional, Any
from datetime import datetime
from config.app_config import AppConfig
from config.styles import StyleConfig
from config.ai_style_manager import AIStyleManager
from services.chat_manager import ChatHistoryManager
from services.logging_service import LoggingService
from services.context_manager import ContextManager
from components.error_handler import ErrorHandler
from components.file_analyzer import FileAnalyzer
from services.document_manager import DocumentManager
from services.file_manager import FileManager
from services.ai_analysis_integration import AIAnalysisManager, AIAnalysisResponse

logger = logging.getLogger(__name__)


class ServiceManager:
    """Enhanced ServiceManager with async support and improved error handling."""

    def __init__(self):
        """Initialize services with proper dependency management."""
        # Initialize logger first before any other operations
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.file_handlers = []
        self.ai_analysis_manager = AIAnalysisManager(self)  # Add this line
        self.chat_manager = ChatHistoryManager()

        try:
            # Initialize core services first
            self._initialize_core_services()

            # Initialize chat manager explicitly
            self._initialize_chat_manager()

            # Initialize dependent services
            self._initialize_dependent_services()

            # Log successful initialization
            self._log_initialization_success()

        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"ServiceManager initialization failed: {str(e)}", exc_info=True)
            self._handle_initialization_error(e)

    async def handle_ai_analysis(self, conv_id: str, analysis_type: str = 'code_review') -> AIAnalysisResponse:
        """Handle AI analysis requests through the service manager."""
        try:
            return await self.ai_analysis_manager.analyze_files(conv_id, analysis_type)
        except Exception as e:
            logging.error(f"Error in AI analysis: {str(e)}")
            raise

    def _initialize_core_services(self):
        """Initialize core services that other services depend on."""
        try:
            # Initialize file handler registry
            self.file_handlers = []

            # Initialize configuration and logging first
            self.config = AppConfig()
            self.logging_service = LoggingService()

            # Initialize error handler with logging service
            self.error_handler = ErrorHandler(self.logging_service)

            # Initialize style configuration
            self.style_config = StyleConfig()

            self.logger.debug("Core services initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing core services: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to initialize core services: {str(e)}")

    def _initialize_chat_manager(self):
        """Initialize chat manager with proper error handling."""
        try:
            from services.chat_manager import ChatHistoryManager
            self.chat_manager = ChatHistoryManager()
            self.logger.debug("Chat manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Chat manager initialization failed: {str(e)}")
            raise RuntimeError(f"Failed to initialize chat manager: {str(e)}")

    def _initialize_dependent_services(self):
        """Initialize services that depend on core services."""
        try:
            # Initialize file-related services
            self.file_manager = FileManager()
            self.file_analyzer = FileAnalyzer()
            self.document_manager = DocumentManager()

            # Initialize context manager
            self.context_manager = ContextManager()

            # Initialize style manager
            self.style_manager = AIStyleManager()

            self.logger.debug("Dependent services initialized successfully")

        except Exception as e:
            self.logger.error(f"Dependent services initialization failed: {str(e)}")
            raise RuntimeError(f"Failed to initialize dependent services: {str(e)}")


    def _handle_initialization_error(self, error: Exception):
        """Handle initialization errors with proper logging and user feedback."""
        error_message = f"ServiceManager initialization failed: {str(error)}"

        # Log directly since we might not have logging service
        if hasattr(self, 'logger'):
            self.logger.error(error_message)

        # Display error to user through streamlit
        st.error(error_message)

        raise RuntimeError(error_message)

    async def handle_file_upload(self, files: list, conv_id: str) -> List[Dict]:
        """Enhanced async file upload handler with better error handling."""
        logger.debug(f"Starting async file upload for conversation {conv_id}")

        processed_files = []
        upload_metrics = {
            'start_time': datetime.now(),
            'total_files': len(files),
            'processed': 0,
            'successful': 0,
            'failed': 0
        }

        try:
            for file in files:
                try:
                    # Process each file asynchronously
                    file_data = await self._process_single_file(file, conv_id)

                    if file_data and 'error' not in file_data:
                        # Analyze file asynchronously
                        analysis_results = await self._analyze_file(file_data)
                        file_data['analysis'] = analysis_results

                        # Update conversation
                        await self.chat_manager.add_file_to_conversation(conv_id, file_data)

                        upload_metrics['successful'] += 1
                    else:
                        upload_metrics['failed'] += 1

                    processed_files.append(file_data)
                    upload_metrics['processed'] += 1

                except Exception as file_error:
                    logger.error(f"Error processing file: {str(file_error)}", exc_info=True)
                    processed_files.append(self._create_error_file_data(file, str(file_error)))
                    upload_metrics['failed'] += 1

            # Analyze relationships for multiple files
            if len(processed_files) > 1:
                await self._analyze_file_relationships(processed_files, conv_id)

            self._log_upload_metrics(upload_metrics)
            return processed_files

        except Exception as e:
            logger.error(f"Error in handle_file_upload: {str(e)}", exc_info=True)
            self._handle_upload_error(e, conv_id)
            return []

    async def register_file_handler(self, handler: callable) -> None:
        """
        Register a handler function for file uploads.

        Args:
            handler: The function that will process uploaded files.
                    Should accept a list of file dictionaries as argument.

        Raises:
            TypeError: If handler is not callable
        """
        if not callable(handler):
            error_msg = "File handler must be a callable function"
            self.logger.error(error_msg)
            raise TypeError(error_msg)

        self.file_handlers.append(handler)
        self.logger.info("File handler registered successfully")

    async def _process_single_file(self, file: Any, conv_id: str) -> Dict:
        """Process a single file asynchronously."""
        try:
            file_name = getattr(file, 'name', 'unnamed') if not isinstance(file, dict) else file.get('name', 'unnamed')
            logger.debug(f"Processing file: {file_name}")

            # Process file using FileManager
            return await self.file_manager.handle_file_upload_async(file, conv_id)

        except Exception as e:
            logger.error(f"Error processing file {file_name}: {str(e)}", exc_info=True)
            return self._create_error_file_data(file, str(e))

    async def _analyze_file(self, file_data: Dict) -> Dict:
        """Analyze a single file asynchronously."""
        try:
            analysis_results = await self.file_analyzer.analyze_single_file_async(file_data)
            return {
                'metadata': analysis_results.metadata,
                'summary': analysis_results.summary,
                'dependencies': analysis_results.dependencies,
                'sections': analysis_results.sections
            }
        except Exception as e:
            logger.error(f"File analysis error: {str(e)}", exc_info=True)
            return {
                'metadata': {},
                'summary': f"Analysis failed: {str(e)}",
                'dependencies': [],
                'sections': []
            }

    async def _analyze_file_relationships(self, files: List[Dict], conv_id: str):
        """Analyze relationships between files asynchronously."""
        try:
            valid_files = [f for f in files if 'error' not in f]
            if valid_files:
                analysis_results = await self.file_analyzer.analyze_file_batch_async(valid_files)
                await self.context_manager.update_context_async(conv_id, {
                    'file_analysis': self.file_analyzer.get_ai_context()
                })
                return analysis_results
        except Exception as e:
            logger.error(f"Error analyzing file relationships: {str(e)}", exc_info=True)
            return None

    def _create_error_file_data(self, file: Any, error_message: str) -> Dict:
        """Create error data structure for failed file processing."""
        return {
            'name': getattr(file, 'name', 'unnamed') if not isinstance(file, dict) else file.get('name', 'unnamed'),
            'type': 'error',
            'error': error_message,
            'processed_at': datetime.now().isoformat()
        }

    def _log_upload_metrics(self, metrics: Dict):
        """Log file upload metrics."""
        duration = (datetime.now() - metrics['start_time']).total_seconds()
        logger.info(
            f"File upload completed: {metrics['successful']}/{metrics['total_files']} "
            f"files successful in {duration:.2f} seconds"
        )
        self.logging_service.log_app_event('file_upload_metrics', metrics)

    def _handle_upload_error(self, error: Exception, conv_id: str):
        """Handle file upload errors properly."""
        self.error_handler.handle_error(
            error=error,
            error_type='file_upload',
            context={
                'operation': 'file_upload',
                'conversation_id': conv_id
            },
            show_message=True
        )

    def _log_initialization_success(self):
        """Log successful initialization details."""
        try:
            if hasattr(self, 'logging_service'):
                self.logging_service.log_app_event('service_manager_init', {
                    'status': 'completed',
                    'initialized_services': [
                        'logging_service',
                        'error_handler',
                        'file_manager',
                        'file_analyzer',
                        'context_manager',
                        'chat_manager',
                        'style_manager'
                    ]
                })
            self.logger.info("ServiceManager initialization completed successfully")

        except Exception as e:
            self.logger.error(f"Failed to log initialization success: {str(e)}")

    def _handle_initialization_error(self, error: Exception):
        """Handle initialization errors with proper logging and user feedback."""
        try:
            error_message = f"ServiceManager initialization failed: {str(error)}"

            # Log the error
            if hasattr(self, 'logging_service'):
                self.logging_service.log_error('service_manager_init', str(error))

            # Handle the error through error handler if available
            if hasattr(self, 'error_handler'):
                self.error_handler.handle_error(
                    error=error,
                    error_type='initialization',
                    context={'component': 'ServiceManager'},
                    show_message=True
                )

            # If we don't have logging or error handling services, log directly
            else:
                self.logger.error(error_message)

            # Display error to user
            st.error(error_message)

        except Exception as e:
            # Fallback error handling if error handler itself fails
            self.logger.error(f"Error handler failed: {str(e)}")
            st.error("Critical initialization error occurred. Please check logs.")

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