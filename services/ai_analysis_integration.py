import logging
import asyncio
from datetime import datetime
from dataclasses import dataclass
from collections import deque
from typing import Dict, List, Optional, Any

@dataclass
class AnalysisError:
    """Structured error information for analysis failures."""
    error_type: str
    message: str
    timestamp: str
    details: Optional[Dict] = None

@dataclass
class AIAnalysisResponse:
    """Enhanced structured response from AI analysis."""
    summary: str
    insights: List[str]
    suggestions: List[str]
    relationships: Dict[str, List[str]]
    technical_details: Dict[str, Any]
    timestamp: str
    file_metadata: Optional[Dict] = None
    errors: List[AnalysisError] = None
    status: str = "success"
    retry_count: int = 0


class AIAnalysisManager:
    """Enhanced AI analysis manager with robust error handling."""
    MAX_RETRIES = 3
    RETRY_DELAY = 1

    def __init__(self, service_manager):
        self.service_manager = service_manager
        self.logger = logging.getLogger(__name__)
        self.analysis_cache = {}
        self.error_queue = deque(maxlen=100)  # Store recent errors
        self._initialize_prompts()
        self.processing_lock = asyncio.Lock()

    def _validate_conversation_id(self, conv_id: str) -> bool:
        """Validate conversation ID format and existence."""
        if not isinstance(conv_id, str) or not conv_id.strip():
            raise ValueError("Invalid conversation ID format")

        conversation = self.service_manager.chat_manager.get_conversation(conv_id)
        if not conversation:
            raise ValueError(f"Conversation {conv_id} not found")
        return True

    def _validate_files(self, files: List[Dict]) -> bool:
        """Validate file data structure and content."""
        if not isinstance(files, list):
            raise ValueError("Files must be provided as a list")

        required_fields = {'name', 'type', 'content'}
        for file in files:
            if not isinstance(file, dict):
                raise ValueError(f"Invalid file format: {file}")
            if not all(field in file for field in required_fields):
                raise ValueError(f"Missing required fields in file: {file.get('name', 'unknown')}")
        return True

    async def analyze_files(self, conv_id: str, analysis_type: str = 'code_review') -> AIAnalysisResponse:
        """Analyze files with enhanced error handling and retries."""
        try:
            # Validate inputs
            self._validate_conversation_id(conv_id)

            # Get conversation
            conversation = self.service_manager.chat_manager.get_conversation(conv_id)
            files = conversation.get('files', [])

            if not files:
                return self._create_empty_response("No files to analyze")

            # Validate files
            self._validate_files(files)

            # Check cache first
            cache_key = self._generate_cache_key(files, analysis_type)
            if cache_key in self.analysis_cache:
                self.logger.info(f"Returning cached analysis for {conv_id}")
                return self.analysis_cache[cache_key]

            # Initialize retry counter
            retry_count = 0
            last_error = None

            while retry_count < self.MAX_RETRIES:
                try:
                    # Prepare analysis context
                    formatted_context = self._format_context_for_ai(files)
                    prompt_template = self.prompts.get(analysis_type, self.prompts['code_review'])
                    full_prompt = prompt_template.format(context=formatted_context)

                    # Perform analysis
                    response = await self.service_manager.handle_ai_request(
                        conv_id=conv_id,
                        prompt=full_prompt,
                        service='claude'
                    )

                    # Parse and validate response
                    analysis_response = self._parse_ai_response(response)
                    if self._validate_analysis_response(analysis_response):
                        # Cache successful response
                        self.analysis_cache[cache_key] = analysis_response
                        return analysis_response

                except Exception as e:
                    last_error = e
                    retry_count += 1
                    if retry_count < self.MAX_RETRIES:
                        self.logger.warning(f"Retry {retry_count} after error: {str(e)}")
                        await asyncio.sleep(self.RETRY_DELAY * retry_count)
                    else:
                        break

            # If we get here, all retries failed
            error_response = self._create_error_response(
                f"Analysis failed after {retry_count} retries: {str(last_error)}"
            )
            self._log_analysis_error(error_response, conv_id, last_error)
            return error_response

        except Exception as e:
            error_msg = f"Unexpected error in analyze_files: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return self._create_error_response(error_msg)

    def _log_analysis_error(self, error_response: AIAnalysisResponse, conv_id: str, error: Exception):
        """Log analysis errors for monitoring and debugging."""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'conversation_id': conv_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'response': error_response
        }
        self.error_queue.append(error_entry)
        self.logger.error(f"Analysis error: {error_entry}")

    def get_recent_errors(self) -> List[Dict]:
        """Get recent analysis errors for monitoring."""
        return list(self.error_queue)

    def _validate_analysis_response(self, response: AIAnalysisResponse) -> bool:
        """Validate the structure and content of an analysis response."""
        try:
            if not response.summary or not isinstance(response.summary, str):
                return False
            if not isinstance(response.insights, list):
                return False
            if not isinstance(response.suggestions, list):
                return False
            if not isinstance(response.technical_details, dict):
                return False
            return True
        except Exception as e:
            self.logger.error(f"Response validation error: {str(e)}")
            return False

    def _initialize_prompts(self):
        self.prompts = {
            'code_review': """
                    Please analyze the following code files and provide a structured analysis:

                    === Summary ===
                    High-level overview of the code's purpose and structure.

                    === Insights ===
                    - Key patterns and architectural decisions
                    - Important code characteristics
                    - Notable implementation details

                    === Suggestions ===
                    - Potential improvements
                    - Optimization opportunities
                    - Best practice recommendations

                    === Technical Details ===
                    - Code metrics
                    - Dependencies
                    - Performance considerations

                    Files and context:
                    {context}
                    """,
            'architecture_review': self._get_architecture_prompt(),
            'documentation': self._get_documentation_prompt()
        }

    def _get_architecture_prompt(self):
        return """..."""  # Architecture review prompt template

    def _get_documentation_prompt(self):
        return """..."""  # Documentation prompt template

    def _format_context_for_ai(self, files: List[Dict]) -> str:
        """Format files for AI analysis."""
        try:
            formatted_parts = []
            formatted_parts.append("=== System Overview ===")
            formatted_parts.append(f"Total Files: {len(files)}")
            file_types = sorted(set(f.get('type', '') for f in files))
            formatted_parts.append(f"File Types: {', '.join(file_types)}")

            formatted_parts.append("\n=== Files Content ===")
            for file in files:
                formatted_parts.append(f"\nFile: {file.get('name', 'unnamed')}")
                formatted_parts.append(f"Type: {file.get('type', 'unknown')}")
                formatted_parts.append("Content:")
                formatted_parts.append(file.get('content', 'No content available'))
                formatted_parts.append("-" * 50)

            return "\n".join(formatted_parts)
        except Exception as e:
            self.logger.error(f"Error formatting context: {str(e)}")
            return "Error formatting context"


    def _parse_ai_response(self, response: str) -> AIAnalysisResponse:
        """Parse and structure the AI's response."""
        sections = {
            'summary': [],
            'insights': [],
            'suggestions': [],
            'technical_details': {},
            'relationships': {}
        }

        current_section = None
        lines = response.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('===') and line.endswith('==='):
                section_name = line.strip('= ').lower()
                if section_name in ['summary', 'insights', 'suggestions', 'technical details']:
                    current_section = section_name.replace(' ', '_')
                continue

            if current_section:
                if current_section in ['insights', 'suggestions'] and line.startswith('- '):
                    sections[current_section].append(line[2:].strip())
                elif current_section == 'summary':
                    sections[current_section].append(line)
                elif current_section == 'technical_details' and ':' in line:
                    key, value = map(str.strip, line.split(':', 1))
                    sections['technical_details'][key] = value

        return AIAnalysisResponse(
            summary='\n'.join(sections['summary']),
            insights=sections['insights'],
            suggestions=sections['suggestions'],
            relationships=sections['relationships'],
            technical_details=sections['technical_details'],
            timestamp=datetime.now().isoformat(),
            status="success"
        )

    def _create_empty_response(self, message: str) -> AIAnalysisResponse:
        """Create a response for empty analysis requests."""
        return AIAnalysisResponse(
            summary=message,
            insights=[],
            suggestions=[],
            relationships={},
            technical_details={},
            timestamp=datetime.now().isoformat(),
            status="empty"
        )

    def _create_error_response(self, error_message: str) -> AIAnalysisResponse:
        """Create a response for failed analysis."""
        return AIAnalysisResponse(
            summary=f"Error during analysis: {error_message}",
            insights=[],
            suggestions=[],
            relationships={},
            technical_details={'error': error_message},
            timestamp=datetime.now().isoformat(),
            status="error"
        )

    def _generate_cache_key(self, files: List[Dict], analysis_type: str) -> str:
        """Generate a unique cache key based on files and analysis type."""
        file_identifiers = [
            f"{f.get('name', '')}_{f.get('stored_at', '')}"
            for f in files
        ]
        return f"{analysis_type}_{'_'.join(sorted(file_identifiers))}"

    async def analyze_files(self, conv_id: str, analysis_type: str = 'code_review') -> AIAnalysisResponse:
        """Analyze files with async support and retry logic."""
        async with self.processing_lock:
            try:
                # Get conversation and validate
                conversation = self.service_manager.chat_manager.get_conversation(conv_id)
                if not conversation or 'files' not in conversation:
                    return self._create_empty_response("No files found in conversation")

                files = conversation.get('files', [])
                if not files:
                    return self._create_empty_response("No files to analyze")

                # Check cache
                cache_key = self._generate_cache_key(files, analysis_type)
                if cache_key in self.analysis_cache:
                    return self.analysis_cache[cache_key]

                # Format context and create prompt
                formatted_context = self._format_context_for_ai(files)
                prompt_template = self.prompts.get(analysis_type, self.prompts['code_review'])
                full_prompt = prompt_template.format(context=formatted_context)

                # Get AI response
                response = await self.service_manager.handle_ai_request(
                    conv_id=conv_id,
                    prompt=full_prompt,
                    service='claude'
                )

                # Parse and validate response
                analysis_response = self._parse_ai_response(response)

                # Cache successful response
                if analysis_response.status == "success":
                    self.analysis_cache[cache_key] = analysis_response

                return analysis_response

            except Exception as e:
                self.logger.error(f"Analysis error: {str(e)}", exc_info=True)
                return self._create_error_response(str(e))