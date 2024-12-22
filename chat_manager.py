import base64
import json
import logging
import os
import time
import openai
import requests
import tiktoken
import google.generativeai as genai

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from anthropic import Anthropic
from dotenv import load_dotenv
from google.generativeai import GenerativeModel

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='chat_manager_debug.log'
)
logger = logging.getLogger(__name__)


class APIManager:
    """Manages API clients and their configuration"""

    def __init__(self):
        load_dotenv()
        self.anthropic = None
        self.openai_client = None
        self.gemini = None
        self._initialize_apis()

    def _initialize_apis(self):
        """Initialize all API clients with error handling"""
        self._setup_anthropic()
        self._setup_openai()
        self._setup_gemini()

    def _setup_anthropic(self):
        """Initialize Anthropic API client"""
        try:
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if not anthropic_key:
                logger.warning("ANTHROPIC_API_KEY not found in environment")
                return

            self.anthropic = Anthropic(api_key=anthropic_key)
            logger.info("Anthropic API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {str(e)}")
            self.anthropic = None

    def _setup_openai(self):
        """Initialize OpenAI API client"""
        try:
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                logger.warning("OPENAI_API_KEY not found in environment")
                return

            self.openai_client = openai.OpenAI(api_key=openai_key)
            logger.info("OpenAI API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            self.openai_client = None

    def _setup_gemini(self):
        """Initialize Google Gemini API client"""
        try:
            google_key = os.getenv('GOOGLE_API_KEY')
            if not google_key:
                logger.warning("GOOGLE_API_KEY not found in environment")
                return

            genai.configure(api_key=google_key)
            self.gemini = GenerativeModel('gemini-pro')
            logger.info("Gemini API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            self.gemini = None


class TokenCounter:
    """Handles token counting and estimation"""

    def __init__(self):
        try:
            self.encoder = tiktoken.encoding_for_model("gpt-4")
        except Exception as e:
            logger.error(f"Failed to initialize token counter: {str(e)}")
            self.encoder = None

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for given text"""
        try:
            if not self.encoder:
                return len(text.split())  # Fallback estimation
            return len(self.encoder.encode(str(text)))
        except Exception as e:
            logger.error(f"Token estimation error: {str(e)}")
            return 0


class FileHandler:
    """Handles file operations and analysis"""

    def __init__(self, base_path: str = "chat_histories"):
        self.base_path = Path(base_path)
        self.exports_path = self.base_path / "exports"
        self.code_exports_path = self.exports_path / "code"
        self.image_exports_path = self.exports_path / "images"
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure all required directories exist"""
        for path in [self.base_path, self.exports_path,
                     self.code_exports_path, self.image_exports_path]:
            path.mkdir(parents=True, exist_ok=True)

    def analyze_code(self, content: str, language: str, max_length: int = 8000) -> str:
        """Analyze code content and provide insights"""
        try:
            truncated_content = content[:max_length] + "\n...\n[Content Truncated]" \
                if len(content) > max_length else content

            analysis_template = f"""Analyzing {language} code:
            ```{language}
            {truncated_content}
            ```
            Key points:
            1. Main functionality
            2. Key components
            3. Potential improvements
            4. Best practices alignment"""

            return analysis_template

        except Exception as e:
            logger.error(f"Code analysis error: {str(e)}")
            return f"Analysis failed: {str(e)}"

    def export_code(self, conversation: Dict, indices: List[int]) -> List[Path]:
        """Export selected code snippets from conversation"""
        exported_files = []
        try:
            for idx in indices:
                if idx >= len(conversation['messages']):
                    continue

                msg = conversation['messages'][idx]
                if "```" not in msg['content']:
                    continue

                code_content = self._extract_code_block(msg['content'])
                if code_content:
                    file_path = self._save_code_snippet(code_content, idx)
                    exported_files.append(file_path)

            return exported_files

        except Exception as e:
            logger.error(f"Code export error: {str(e)}")
            return exported_files

    def _extract_code_block(self, content: str) -> Optional[Tuple[str, str]]:
        """Extract code and language from markdown code block"""
        try:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                lang = content[start:content.find("\n", start)].strip()
                code = content[content.find("\n", start):end].strip()
                return lang, code
            return None
        except Exception as e:
            logger.error(f"Code extraction error: {str(e)}")
            return None

    def _save_code_snippet(self, code_tuple: Tuple[str, str], index: int) -> Path:
        """Save extracted code to file"""
        try:
            if not code_tuple:
                return None

            lang, code = code_tuple
            filename = f"snippet_{index}.{lang}"
            file_path = self.code_exports_path / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)

            return file_path

        except Exception as e:
            logger.error(f"Code saving error: {str(e)}")
            return None


class ConversationManager:
    """Manages conversation storage and retrieval"""

    def __init__(self, base_path: str = "chat_histories"):
        self.history_dir = Path(base_path)
        self.history_dir.mkdir(exist_ok=True)
        self.file_handler = FileHandler(base_path)

    def create_conversation(self, title: str) -> str:
        """Create a new conversation"""
        try:
            conv_id = f"{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            conv_path = self._get_conv_path(conv_id)

            conversation = {
                "title": title,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "messages": [],
                "metadata": {
                    "total_messages": 0,
                    "total_tokens": 0,
                    "last_ai_service": None,
                    "file_attachments": []
                }
            }

            self._save_conversation(conv_path, conversation)
            logger.info(f"Created new conversation: {conv_id}")
            return conv_id

        except Exception as e:
            logger.error(f"Failed to create conversation: {str(e)}")
            raise

    def add_message(self, conv_id: str, content: str, sender: str,
                    ai_service: Optional[str] = None, model: Optional[str] = None,
                    tokens: Optional[int] = None, image_data: Optional[str] = None,
                    file_attachment: Optional[Dict] = None) -> bool:
        """Add a message to a conversation"""
        try:
            conv_path = self._get_conv_path(conv_id)
            conversation = self._load_conversation(conv_path)

            message = {
                "id": len(conversation["messages"]),
                "content": content,
                "sender": sender,
                "timestamp": datetime.now().isoformat(),
                "ai_service": ai_service,
                "model": model,
                "tokens": tokens,
                "image_data": image_data,
                "file_attachment": file_attachment
            }

            conversation["messages"].append(message)
            conversation["updated_at"] = datetime.now().isoformat()
            conversation["metadata"]["total_messages"] += 1

            if tokens:
                conversation["metadata"]["total_tokens"] += tokens
            if ai_service:
                conversation["metadata"]["last_ai_service"] = ai_service
            if file_attachment:
                conversation["metadata"]["file_attachments"].append(file_attachment)

            self._save_conversation(conv_path, conversation)
            logger.debug(f"Added message to conversation {conv_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add message to conversation {conv_id}: {str(e)}")
            return False

    def get_conversation(self, conv_id: str) -> Optional[Dict]:
        """Retrieve a conversation by ID"""
        try:
            return self._load_conversation(self._get_conv_path(conv_id))
        except Exception as e:
            logger.error(f"Failed to get conversation {conv_id}: {str(e)}")
            return None

    def list_conversations(self) -> List[str]:
        """List all available conversations"""
        try:
            return [file.stem for file in self.history_dir.glob("*.json")]
        except Exception as e:
            logger.error(f"Failed to list conversations: {str(e)}")
            return []

    def export_conversation(self, conv_id: str, format: str = "json") -> Optional[str]:
        """Export conversation in specified format"""
        try:
            conversation = self.get_conversation(conv_id)
            if not conversation:
                return None

            if format == "json":
                return json.dumps(conversation, indent=2, ensure_ascii=False)

            # Text format
            content = []
            for msg in conversation["messages"]:
                sender = msg["sender"]
                ai_service = f"[{msg['ai_service']}]" if msg.get("ai_service") else ""
                timestamp = datetime.fromisoformat(msg["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")

                content.append(f"[{timestamp}] {sender} {ai_service}:")
                content.append(msg["content"])
                content.append("")  # Empty line for readability

            return "\n".join(content)

        except Exception as e:
            logger.error(f"Failed to export conversation {conv_id}: {str(e)}")
            return None

    def _get_conv_path(self, conv_id: str) -> Path:
        """Get the file path for a conversation"""
        return self.history_dir / f"{conv_id}.json"

    def _save_conversation(self, path: Path, conversation: Dict):
        """Save conversation to file"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, indent=2, ensure_ascii=False)

    def _load_conversation(self, path: Path) -> Dict:
        """Load conversation from file"""
        with open(path, encoding='utf-8') as f:
            return json.load(f)


class ChatHistoryManager:
    """Main class for managing chat interactions and AI services"""

    CLAUDE_MODELS = {
        "claude-3-sonnet-20240229": "Sonnet",
        "claude-3-opus-20240229": "Opus",
        "claude-3-haiku-20240307": "Haiku"
    }
    CLAUDE_STYLES = {
        "Normal": "Write in a natural, conversational style",
        "Concise": "Write brief, focused responses that get straight to the point",
        "Professional": "Write in a formal, business-appropriate style",
        "Expert": "Write with technical depth and precision",
        "Craftsman": "Write with emphasis on practical, hands-on expertise",
    }

    GPT_MODELS = {
        "gpt-4": "GPT-4",
        "gpt-3.5-turbo": "GPT-3.5"
    }

    GEMINI_MODELS = {
        "gemini-pro": "Gemini Pro"
    }

    DALLE_MODELS = {
        "dalle-3": "DALL·E 3",
        "dalle-2": "DALL·E 2"
    }

    def __init__(self):
        self.api_manager = APIManager()
        self.token_counter = TokenCounter()
        self.conversation_manager = ConversationManager()
        logger.info("ChatHistoryManager initialized")

    def create_conversation(self, title: str) -> str:
        """Create a new conversation"""
        return self.conversation_manager.create_conversation(title)

    def get_conversation(self, conv_id: str) -> Optional[Dict]:
        """Get conversation by ID"""
        return self.conversation_manager.get_conversation(conv_id)

    def list_conversations(self) -> List[str]:
        """List all conversations"""
        return self.conversation_manager.list_conversations()

    def add_message(self, *args, **kwargs) -> bool:
        """Add message to conversation"""
        return self.conversation_manager.add_message(*args, **kwargs)

    def send_to_claude(self, conv_id: str, prompt: str,
                       model: str = "claude-3-sonnet-20240229") -> Optional[str]:
        """Send message to Claude and handle response"""
        if not self.api_manager.anthropic:
            raise Exception("Claude API is not configured")

        try:
            conversation = self.get_conversation(conv_id)
            if not conversation:
                raise Exception("Conversation not found")

            context = self._get_conversation_context(conversation)

            system_prompt = """You're participating in a group chat. Previous messages are provided for context. 
            Respond naturally and maintain context of the ongoing conversation."""

            full_prompt = f"{system_prompt}\n\nContext:\n{context}\n\nUser: {prompt}"

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.api_manager.anthropic.messages.create(
                        model=model,
                        max_tokens=4096,
                        messages=[{"role": "user", "content": full_prompt}],
                        temperature=0.7
                    )

                    response_content = response.content[0].text
                    # Continue from previous Claude implementation
                    tokens_in = self.token_counter.estimate_tokens(full_prompt)
                    tokens_out = self.token_counter.estimate_tokens(response_content)

                    self.add_message(conv_id, prompt, "user", "claude", model, tokens_in)
                    self.add_message(conv_id, response_content, "assistant", "claude", model, tokens_out)

                    return response_content

                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(1 * (attempt + 1))

        except Exception as e:
            error_msg = f"Error in Claude communication: {str(e)}"
            logger.error(error_msg)
            self.add_message(conv_id, error_msg, "system", "claude", model)
            raise

    def send_to_chatgpt(self, conv_id: str, prompt: str,
                        model: str = "gpt-3.5-turbo") -> Optional[str]:
        """Send message to ChatGPT and handle response"""
        if not self.api_manager.openai_client:
            raise Exception("ChatGPT API is not configured")

        try:
            conversation = self.get_conversation(conv_id)
            if not conversation:
                raise Exception("Conversation not found")

            context = self._get_conversation_context(conversation)

            messages = [
                {
                    "role": "system",
                    "content": "You're participating in a group chat. Previous messages are provided for context. Respond naturally."
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nUser: {prompt}"
                }
            ]

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.api_manager.openai_client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=2048
                    )

                    response_content = response.choices[0].message.content

                    tokens_in = self.token_counter.estimate_tokens(prompt)
                    tokens_out = self.token_counter.estimate_tokens(response_content)

                    self.add_message(conv_id, prompt, "user", "chatgpt", model, tokens_in)
                    self.add_message(conv_id, response_content, "assistant", "chatgpt", model, tokens_out)

                    return response_content

                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(1 * (attempt + 1))

        except Exception as e:
            error_msg = f"Error in ChatGPT communication: {str(e)}"
            logger.error(error_msg)
            self.add_message(conv_id, error_msg, "system", "chatgpt", model)
            raise

    def send_to_gemini(self, conv_id: str, prompt: str, model: str = "gemini-pro") -> Optional[str]:
        """Send message to Gemini and handle response"""
        if not self.api_manager.gemini:
            raise Exception("Gemini API is not configured")

        try:
            conversation = self.get_conversation(conv_id)
            if not conversation:
                raise Exception("Conversation not found")

            context = self._get_conversation_context(conversation)
            full_prompt = f"""Previous conversation context:
            {context}

            Current user message: {prompt}

            Please provide a natural, contextually appropriate response."""

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Modified safety settings to be less restrictive while maintaining appropriate boundaries
                    response = self.api_manager.gemini.generate_content(
                        full_prompt,
                        generation_config={
                            'temperature': 0.7,
                            'top_p': 0.8,
                            'top_k': 40,
                            'max_output_tokens': 2048,
                        },
                        # Adjusted safety settings to handle normal conversation
                        safety_settings=[
                            {
                                "category": "HARM_CATEGORY_HARASSMENT",
                                "threshold": "BLOCK_ONLY_HIGH"
                            },
                            {
                                "category": "HARM_CATEGORY_HATE_SPEECH",
                                "threshold": "BLOCK_ONLY_HIGH"
                            },
                            {
                                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                "threshold": "BLOCK_ONLY_HIGH"
                            },
                            {
                                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                                "threshold": "BLOCK_ONLY_HIGH"
                            }
                        ]
                    )

                    if not response.text:
                        raise Exception("Empty response received from Gemini")

                    tokens_in = self.token_counter.estimate_tokens(full_prompt)
                    tokens_out = self.token_counter.estimate_tokens(response.text)

                    self.add_message(conv_id, prompt, "user", "gemini", model, tokens_in)
                    self.add_message(conv_id, response.text, "assistant", "gemini", model, tokens_out)

                    return response.text

                except Exception as e:
                    if "safety" in str(e).lower() or "dangerous_content" in str(e).lower():
                        # Handle safety-related errors more gracefully
                        error_msg = "I apologize, but I'm having trouble processing that request. Could you please rephrase it?"
                        self.add_message(conv_id, error_msg, "assistant", "gemini", model)
                        return error_msg

                    if attempt == max_retries - 1:
                        raise
                    time.sleep(1 * (attempt + 1))

        except Exception as e:
            error_msg = f"Error in Gemini communication: {str(e)}"
            logger.error(error_msg)
            self.add_message(conv_id, error_msg, "system", "gemini", model)
            raise

    def generate_image_dalle(self, prompt: str, size: str = "1024x1024") -> Optional[str]:
        """Generate image using DALL-E"""
        if not self.api_manager.openai_client:
            raise Exception("DALL-E API is not configured")

        try:
            response = self.api_manager.openai_client.images.generate(
                prompt=prompt,
                size=size,
                quality="standard",
                n=1
            )

            # Get image URL and convert to base64
            image_url = response.data[0].url
            image_data = self._fetch_and_encode_image(image_url)

            return image_data

        except Exception as e:
            error_msg = f"Error generating image with DALL-E: {str(e)}"
            logger.error(error_msg)
            raise

    def _fetch_and_encode_image(self, url: str) -> Optional[str]:
        """Fetch image from URL and encode to base64"""
        try:
            response = requests.get(url)
            response.raise_for_status()
            return base64.b64encode(response.content).decode('utf-8')
        except Exception as e:
            logger.error(f"Error fetching/encoding image: {str(e)}")
            return None

    def analyze_code(self, content: str, language: str) -> str:
        """Analyze code content using Claude"""
        if not self.api_manager.anthropic:
            return "Code analysis is not available (Claude API not configured)"

        try:
            analysis_prompt = f"""Analyze this {language} code and provide insights:
                    ```{language}
                    {content}
                    ```
                    Focus on:
                    1. Main functionality and purpose
                    2. Code structure and organization
                    3. Potential improvements
                    4. Security considerations
                    5. Performance aspects"""

            response = self.api_manager.anthropic.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1024,
                messages=[{"role": "user", "content": analysis_prompt}]
            )

            return response.content[0].text

        except Exception as e:
            error_msg = f"Code analysis failed: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def export_conversation(self, conv_id: str, format: str = "json") -> Optional[str]:
        """Export conversation in specified format"""
        return self.conversation_manager.export_conversation(conv_id, format)

    def extract_code_messages(self, conv_id: str) -> List[Tuple[int, Dict]]:
        """Extract messages containing code blocks"""
        try:
            conversation = self.get_conversation(conv_id)
            if not conversation:
                return []

            return [(i, msg) for i, msg in enumerate(conversation["messages"])
                    if "```" in msg["content"]]

        except Exception as e:
            logger.error(f"Error extracting code messages: {str(e)}")
            return []

    def export_selected_code(self, conv_id: str, selected_indices: List[int]) -> List[Path]:
        """Export selected code snippets"""
        try:
            conversation = self.get_conversation(conv_id)
            if not conversation:
                return []

            return self.conversation_manager.file_handler.export_code(
                conversation,
                selected_indices
            )

        except Exception as e:
            logger.error(f"Error exporting code: {str(e)}")
            return []

    def _get_conversation_context(self, conversation: Dict, last_n: int = 10) -> str:
        """Get formatted context from recent messages"""
        try:
            recent_messages = conversation['messages'][-last_n:]
            context_lines = []

            for msg in recent_messages:
                sender = msg['sender']
                service = msg.get('ai_service', 'user')
                content = msg['content']

                # Format message with sender and service info
                context_lines.append(f"{sender} ({service}): {content}")

            return "\n".join(context_lines)

        except Exception as e:
            logger.error(f"Error getting conversation context: {str(e)}")
            return ""

    def log_file_analysis(self, file_name: str, language: str, analysis: str):
        """Log file analysis results"""
        try:
            log_file = Path("file_analysis_log.txt")

            log_entry = f"""
                    [Analysis Log Entry]
                    Timestamp: {datetime.now().isoformat()}
                    File: {file_name}
                    Language: {language}

                    Analysis Results:
                    {analysis}

                    {'=' * 80}
                    """

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)

        except Exception as e:
            logger.error(f"Error logging file analysis: {str(e)}")


    def handle_file_upload(self, file_data: Dict[str, Any], conv_id: str) -> bool:
        """Process uploaded file and add to conversation"""
        try:
            file_type = file_data.get('type', 'unknown')
            file_name = file_data.get('name', 'unnamed_file')
            content = file_data.get('content', '')

            # Add file message to conversation
            file_message = f"File uploaded: {file_name} ({file_type})"
            self.add_message(
                conv_id,
                file_message,
                "system",
                file_attachment={
                    'name': file_name,
                    'type': file_type,
                    'timestamp': datetime.now().isoformat()
                }
            )

            # For text files, perform code analysis
            if file_type == 'text':
                language = file_data.get('language', 'txt')
                analysis = self.analyze_code(content, language)

                if analysis:
                    self.log_file_analysis(file_name, language, analysis)
                    analysis_message = f"Analysis for {file_name}:\n{analysis}"
                    self.add_message(conv_id, analysis_message, "system")

            return True

        except Exception as e:
            logger.error(f"Error handling file upload: {str(e)}")
            return False

    def get_conversation_statistics(self, conv_id: str) -> Dict[str, Any]:
        """Generate statistics for a conversation"""
        try:
            conversation = self.get_conversation(conv_id)
            if not conversation:
                raise Exception("Conversation not found")

            stats = {
                'total_messages': 0,
                'total_tokens': 0,
                'service_usage': {
                    'claude': 0,
                    'chatgpt': 0,
                    'gemini': 0,
                    'dalle': 0
                },
                'user_messages': 0,
                'ai_messages': 0,
                'files_shared': 0,
                'last_activity': None,
                'conversation_duration': None
            }

            for msg in conversation['messages']:
                stats['total_messages'] += 1
                stats['total_tokens'] += msg.get('tokens', 0)

                if msg['sender'] == 'user':
                    stats['user_messages'] += 1
                elif msg['sender'] == 'assistant':
                    stats['ai_messages'] += 1

                    service = msg.get('ai_service', '').lower()
                    if service in stats['service_usage']:
                        stats['service_usage'][service] += 1

                if msg.get('file_attachment'):
                    stats['files_shared'] += 1

            # Calculate time-based metrics
            if conversation['messages']:
                latest_msg = conversation['messages'][-1]
                stats['last_activity'] = latest_msg['timestamp']

                first_msg = conversation['messages'][0]
                start_time = datetime.fromisoformat(first_msg['timestamp'])
                end_time = datetime.fromisoformat(latest_msg['timestamp'])
                stats['conversation_duration'] = str(end_time - start_time)

            return stats

        except Exception as e:
            logger.error(f"Error generating conversation statistics: {str(e)}")
            return {}

    def cleanup_old_conversations(self, days_threshold: int = 30) -> int:
        """Remove conversations older than the specified threshold"""
        try:
            current_time = datetime.now()
            removed_count = 0

            for conv_path in self.conversation_manager.history_dir.glob("*.json"):
                try:
                    conversation = self._load_conversation(conv_path)
                    created_at = datetime.fromisoformat(conversation['created_at'])

                    if (current_time - created_at).days > days_threshold:
                        conv_path.unlink()
                        removed_count += 1
                        logger.info(f"Removed old conversation: {conv_path.stem}")

                except Exception as e:
                    logger.error(f"Error processing conversation {conv_path}: {str(e)}")
                    continue

            return removed_count

        except Exception as e:
            logger.error(f"Error in cleanup process: {str(e)}")
            return 0

    def is_api_healthy(self) -> Dict[str, bool]:
        """Check the health status of all API services"""
        return {
            'claude': self.api_manager.anthropic is not None,
            'chatgpt': self.api_manager.openai_client is not None,
            'gemini': self.api_manager.gemini is not None
        }


if __name__ == "__main__":
    # Initialize the chat manager
    manager = ChatHistoryManager()

    # Log the API health status
    health_status = manager.is_api_healthy()
    for service, is_healthy in health_status.items():
        logger.info(f"{service.capitalize()} API status: {'Healthy' if is_healthy else 'Unavailable'}")
