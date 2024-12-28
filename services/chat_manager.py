import os
import json
import base64
import tiktoken
import openai
import google.generativeai as genai
import uuid
import requests
import logging
import mimetypes
import streamlit as st

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
from anthropic import Anthropic
from dotenv import load_dotenv
from dataclasses import dataclass
from config.app_config import AppConfig
from config.ai_style_manager import AIStyleManager
from services.file_manager import FileManager

logger = logging.getLogger(__name__)

class ImageHandler:
    def __init__(self, storage_type="local"):
        self.storage_type = storage_type
        if 'image_store' not in st.session_state:
            st.session_state.image_store = {}
        logger.debug(f"ImageHandler initialized with storage type: {storage_type}")
        logger.debug(f"Current store size: {len(st.session_state.image_store)} images")

    def save_image(self, image_data: bytes, image_id: str) -> str:
        try:
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            st.session_state.image_store[image_id] = encoded_image
            return image_id
        except Exception as e:
            logger.error(f"Error saving image: {str(e)}")
            return None

    def get_image(self, image_id: str) -> Optional[bytes]:
        try:
            if image_id in st.session_state.image_store:
                encoded_image = st.session_state.image_store[image_id]
                return base64.b64decode(encoded_image)
            logger.debug(f"Image {image_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error getting image: {str(e)}")
            return None

    def get_encoded_image(self, image_id: str) -> Optional[str]:
        return st.session_state.image_store.get(image_id)

@dataclass
class FileProcessResult:
    """Data class to track file processing results."""
    success: bool
    file_name: str
    file_type: str
    content: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None

class ChatHistoryManager:
    def __init__(self):
        self.conversations: Dict = {}
        logger.debug("ChatHistoryManager initialized")

        self.config = AppConfig()
        self.image_handler = ImageHandler(storage_type="local")
        self.style_manager = AIStyleManager()
        load_dotenv()

        # Initialize API clients with proper error handling
        self._initialize_api_clients()

        # Set up directories with enhanced organization
        self.history_dir = Path("chat_histories")
        self.exports_dir = Path("exports")
        self.history_dir.mkdir(exist_ok=True)
        self.exports_dir.mkdir(exist_ok=True)

        # Initialize token counter with style consideration
        self.gpt_encoder = tiktoken.encoding_for_model("gpt-4")

    def add_file_to_conversation(self, conv_id: str, file_data: Dict) -> None:
        """Add processed file data to a conversation."""
        if conv_id not in self.conversations:
            self.conversations[conv_id] = {
                'messages': [],
                'files': [],
                'created_at': datetime.now().isoformat()
            }

        # Add file to conversation
        self.conversations[conv_id]['files'].append(file_data)

        # Add system message about the file
        file_message = self._create_file_message(file_data)
        self.conversations[conv_id]['messages'].append(file_message)

        # Estimate and update token count for the file
        tokens = self._estimate_file_tokens(file_data)
        self._update_token_totals(self.conversations[conv_id], tokens, False)

        logger.debug(f"Added file {file_data['name']} to conversation {conv_id}")

    def _create_file_message(self, file_data: Dict) -> Dict:
        """Create a system message for a file upload with enhanced support for multiple file types."""
        file_type = file_data.get('type', '')
        timestamp = datetime.now().isoformat()

        if file_type == 'image':
            content = f"An image file '{file_data['name']}' has been uploaded."
        elif file_type == 'pdf':
            metadata = file_data.get('metadata', {})
            content = (
                f"PDF Document: {file_data['name']}\n"
                f"Title: {metadata.get('title', 'Untitled')}\n"
                f"Author: {metadata.get('author', 'Unknown')}\n"
                f"Pages: {metadata.get('pages', 0)}\n\n"
                f"Content:\n{file_data['content']}"
            )
        else:
            content = (f"File uploaded: {file_data['name']}\n\n"
                       f"Content:\n{file_data['content']}")

        return {
            'role': 'system',
            'content': content,
            'timestamp': timestamp,
            'type': 'file_upload',
            'file_type': file_type,
            'metadata': file_data.get('metadata')
        }

    def get_conversation(self, conv_id: str) -> Optional[Dict]:
        """Get a conversation by its ID."""
        return self.conversations.get(conv_id)

    def get_conversation_files(self, conv_id: str) -> List[Dict]:
        """Get all files in a conversation."""
        conversation = self.conversations.get(conv_id, {})
        return conversation.get('files', [])

    def _initialize_api_clients(self):
        """Initialize API clients with proper error handling."""
        try:
            self.openai = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.anthropic = Anthropic(api_key=os.getenv('CLAUDE_API_KEY'))
            if not os.getenv('CLAUDE_API_KEY'):
                raise ValueError("CLAUDE_API_KEY environment variable is not set")

            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            self.gemini = genai.GenerativeModel('gemini-pro')

        except Exception as e:
            logging.error(f"Error initializing API clients: {str(e)}")
            raise

    def create_conversation(self, title: str) -> str:
        """Create a new conversation with current style configuration.

        Args:
            title (str): The title for the new conversation

        Returns:
            str: The unique conversation ID
        """
        # Get current style from session state or use default
        current_style = st.session_state.get('selected_style', 'Professor')

        conv_id = f"{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        conv_path = self._get_conv_path(conv_id)

        # Get style configuration for current style
        style_config = self.style_manager.get_style_config(current_style)

        conversation = {
            "title": title,
            "created_at": datetime.now().isoformat(),
            "style": current_style,  # Store the style name
            "style_config": {
                "name": style_config.name,
                "formatting_rules": style_config.formatting_rules,
                "token_multiplier": style_config.token_multiplier
            },
            "messages": [],
            "token_totals": {
                "input": 0,
                "output": 0,
                "total": 0
            }
        }

        self._save_conversation(conv_path, conversation)
        return conv_id

    def get_conversation(self, conv_id: str) -> Optional[Dict]:
        """Retrieve a conversation by its identifier."""
        try:
            conv_path = self._get_conv_path(conv_id)
            if not conv_path.exists():
                return None
            return self._load_conversation(conv_path)
        except Exception as e:
            print(f"Error loading conversation: {str(e)}")
            return None

    def get_conversation_messages(self, conv_id: str) -> List[Dict]:
        """Get all messages in a conversation."""
        conversation = self.get_conversation(conv_id)
        if conversation and "messages" in conversation:
            return conversation["messages"]
        return []

    def get_conversation_style(self, conv_id: str) -> str:
        """Get the current style for a conversation."""
        conversation = self.get_conversation(conv_id)
        return conversation.get('style', 'Professor')

    def update_conversation_style(self, conv_id: str) -> None:
        """Update conversation style based on current session state."""
        conv_path = self._get_conv_path(conv_id)
        conversation = self._load_conversation(conv_path)

        # Get current style from session state
        current_style = st.session_state.get('selected_style', 'Professor')

        # Only update if style has changed
        if current_style != conversation.get('style'):
            style_config = self.style_manager.get_style_config(current_style)
            conversation["style"] = current_style
            conversation["style_config"] = {
                "name": style_config.name,
                "formatting_rules": style_config.formatting_rules,
                "token_multiplier": style_config.token_multiplier
            }

            self._save_conversation(conv_path, conversation)

    def send_to_claude(self, conv_id: str, prompt: str, model: str = "claude-3-5-sonnet-20241022") -> str:
        """Send a message to Claude with context from previous messages."""
        try:
            # Get the current conversation
            conversation = self.get_conversation(conv_id)

            # Build context from previous messages
            messages = []
            for msg in conversation.get('messages', []):
                role = "assistant" if msg['sender'] == "assistant" else "user"
                messages.append({
                    "role": role,
                    "content": msg['content']
                })

            # Add the new prompt
            messages.append({
                "role": "user",
                "content": prompt
            })

            # Calculate input tokens
            input_tokens = self.estimate_tokens(prompt)

            # Add user message
            self.add_message(conv_id, prompt, "user", "claude", model, tokens=input_tokens)

            # Send request to Claude with full context
            response = self.anthropic.messages.create(
                messages=messages,
                model=model,
                max_tokens=1024
            )

            response_content = response.content[0].text if response and response.content else ""
            output_tokens = self.estimate_tokens(response_content)

            # Add assistant's response
            self.add_message(conv_id, response_content, "assistant", "claude", model, tokens=output_tokens)

            return response_content

        except Exception as e:
            print(f"Claude API Error: {str(e)}")
            raise RuntimeError(f"Error processing message: {str(e)}")

    def send_to_chatgpt(self, conv_id: str, prompt: str, model: str = "gpt-4") -> str:
        """Send a message to ChatGPT with context from previous messages."""
        try:
            # Get the current conversation
            conversation = self.get_conversation(conv_id)

            # Build context from previous messages
            context_messages = []
            for msg in conversation.get('messages', []):
                role = "assistant" if msg['sender'] == "assistant" else "user"
                context_messages.append({
                    "role": role,
                    "content": msg['content']
                })

            # Add the new prompt
            context_messages.append({
                "role": "user",
                "content": prompt
            })

            # Calculate input tokens
            input_tokens = self.estimate_tokens(prompt)

            # Add user message to conversation
            self.add_message(conv_id, prompt, "user", "chatgpt", model, tokens=input_tokens)

            # Send request to ChatGPT with full context
            response = self.openai.chat.completions.create(
                model=model,
                messages=context_messages,
                max_tokens=1024
            )

            response_content = response.choices[0].message.content if response.choices else ""
            output_tokens = self.estimate_tokens(response_content)

            # Add assistant's response to conversation
            self.add_message(conv_id, response_content, "assistant", "chatgpt", model, tokens=output_tokens)

            return response_content

        except Exception as e:
            print(f"ChatGPT API Error: {str(e)}")
            raise RuntimeError(f"Error processing message: {str(e)}")

    def send_to_gemini(self, conv_id: str, prompt: str, model: str = "gemini-pro") -> str:
        """
        Send a message to Gemini with full conversation context support.

        This implementation ensures Gemini has access to the complete conversation history,
        allowing it to provide more contextually aware responses. It maintains consistency
        with how Claude and ChatGPT handle conversations while accounting for Gemini's
        specific requirements.
        """
        try:
            # First, let's get the current conversation to build our context
            conversation = self.get_conversation(conv_id)

            # Build a context string that includes previous messages
            context = ""
            for msg in conversation.get('messages', []):
                # Format each message with clear role identification
                role = "Assistant" if msg['sender'] == "assistant" else "Human"
                context += f"{role}: {msg['content']}\n\n"

            # Add the current prompt with context
            full_prompt = f"{context}Human: {prompt}\n\nAssistant:"

            # Calculate input tokens for tracking
            input_tokens = self.estimate_tokens(prompt)

            # Add the user's message to the conversation history
            self.add_message(
                conv_id,
                prompt,
                "user",
                "gemini",
                model,
                tokens=input_tokens
            )

            # Create a chat session with Gemini
            chat = self.gemini.start_chat(history=[])

            # Send the contextualized prompt to Gemini
            response = chat.send_message(full_prompt)

            # Extract and process the response
            response_content = response.text if response else ""
            output_tokens = self.estimate_tokens(response_content)

            # Add Gemini's response to the conversation history
            self.add_message(
                conv_id,
                response_content,
                "assistant",
                "gemini",
                model,
                tokens=output_tokens
            )

            # For better error handling, verify response content
            if not response_content:
                raise RuntimeError("Gemini returned an empty response")

            return response_content

        except Exception as e:
            # Provide detailed error information for debugging
            error_message = f"Gemini API Error: {str(e)}"
            print(error_message)  # For server-side logging
            raise RuntimeError(error_message)

    def generate_image_dalle(self, conv_id: str, prompt: str,
                             model: str = "dall-e-3", size: str = "1024x1024") -> str:
        """Generate an image using DALL-E."""
        try:
            # Initialize session state if needed
            if 'image_store' not in st.session_state:
                st.session_state.image_store = {}

            # Generate image with DALL-E
            response = self.openai.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality="standard",
                n=1
            )

            image_url = response.data[0].url if response.data else ""

            if image_url:
                # Download and process image
                image_response = requests.get(image_url)
                image_response.raise_for_status()

                # Generate unique ID and save image
                image_id = f"dalle_{conv_id}_{str(uuid.uuid4())}"
                encoded_image = base64.b64encode(image_response.content).decode('utf-8')
                st.session_state.image_store[image_id] = encoded_image

                # Create message metadata
                message_data = {
                    "type": "image",
                    "source": "dalle",
                    "image_id": image_id,
                    "prompt": prompt,
                    "model": model,
                    "size": size,
                    "generated_at": datetime.now().isoformat(),
                    "storage_type": "local"
                }

                # Add response to conversation
                self.add_message(
                    conv_id=conv_id,
                    content=f"Generated image ({size})",
                    sender="assistant",
                    ai_service="dalle",
                    model=model,
                    metadata=message_data
                )

                return "✨ Image generated successfully!"

        except Exception as e:
            if 'content_policy_violation' in str(e):
                return ("I apologize, but I cannot generate this image due to content "
                        "policy restrictions. Please try modifying your prompt.")
            raise RuntimeError(f"Error generating image: {str(e)}")

    def _sanitize_dalle_prompt(self, prompt: str) -> str:
        """
        Sanitize and format prompts for DALL-E to reduce policy violations.
        """
        # Remove potentially problematic characters and phrases
        sanitized = prompt.lower().strip()

        # Add artistic context if not present
        if not any(word in sanitized for word in ['art', 'illustration', 'drawing', 'painting']):
            sanitized = f"artistic illustration of {sanitized}"

        # Ensure the prompt is family-friendly
        sanitized = f"family-friendly {sanitized}"

        return sanitized

    def _retry_dalle_generation(self, conv_id: str, safe_prompt: str,
                                model: str, size: str, original_prompt: str) -> str:
        """
        Retry DALL-E generation with a safer prompt formulation.
        """
        try:
            response = self.openai.images.generate(
                model=model,
                prompt=safe_prompt,
                size=size,
                quality="standard",
                n=1
            )

            # Process response similar to main generation method
            image_url = response.data[0].url if response.data else ""
            if image_url:
                # ... (similar image processing as in main method)
                return f"Image generated successfully with modified prompt! Original request: {original_prompt}"

        except Exception as retry_error:
            print(f"Retry attempt failed: {str(retry_error)}")
            return ("I apologize, but I'm unable to generate this image even with "
                    "modified prompts. Please try a completely different description.")

    def add_message(self, conv_id: str, content: str, sender: str,
                    ai_service: Optional[str] = None, model: Optional[str] = None,
                    tokens: Optional[int] = None, metadata: Optional[dict] = None) -> None:
        """Add a message to the conversation with current style tracking."""
        conv_path = self._get_conv_path(conv_id)
        conversation = self._load_conversation(conv_path)

        # Get current style from session state or conversation
        current_style = st.session_state.get('selected_style',
                                             conversation.get('style', 'Professor'))

        # Update conversation style if it changed
        if current_style != conversation.get('style'):
            conversation['style'] = current_style
            style_config = self.style_manager.get_style_config(current_style)
            conversation['style_config'] = {
                "name": style_config.name,
                "formatting_rules": style_config.formatting_rules,
                "token_multiplier": style_config.token_multiplier
            }

        # Create message with style information
        message = {
            "content": content,
            "sender": sender,
            "timestamp": datetime.now().isoformat(),
            "style": current_style,
            "tokens": tokens if tokens is not None else
            self.estimate_tokens(content, current_style)
        }

        if ai_service:
            message["ai_service"] = ai_service
            message["model"] = model

        if metadata:
            message["metadata"] = metadata

        # Update token totals
        if tokens:
            self._update_token_totals(conversation, tokens, sender == "user")

        conversation["messages"].append(message)
        self._save_conversation(conv_path, conversation)

    def send_to_service(self, conv_id: str, prompt: str, service: str,
                        model: str, style: str = "Professor") -> str:
        """Generic method to send messages to any AI service with style handling."""
        try:
            # Get conversation and style configuration
            conversation = self.get_conversation(conv_id)
            style_config = self.style_manager.get_style_config(style)

            # Prepare context with style
            context_messages = self._prepare_context_messages(conversation, style, service)

            # Add user message with style consideration
            input_tokens = self.estimate_tokens(prompt, style)
            self.add_message(conv_id, prompt, "user", service, model, style, tokens=input_tokens)

            # Send to appropriate service
            if service == "claude":
                response = self._send_to_claude(context_messages, prompt, model, style)
            elif service == "chatgpt":
                response = self._send_to_chatgpt(context_messages, prompt, model, style)
            elif service == "gemini":
                response = self._send_to_gemini(context_messages, prompt, model, style)
            else:
                raise ValueError(f"Unsupported service: {service}")

            # Process response
            response_content = self._extract_response_content(response, service)
            output_tokens = self.estimate_tokens(response_content, style)

            # Add assistant's response with style
            self.add_message(conv_id, response_content, "assistant", service, model, style, tokens=output_tokens)

            return response_content

        except Exception as e:
            logging.error(f"Error in send_to_service: {str(e)}")
            raise RuntimeError(f"Error processing message: {str(e)}")

    def _prepare_context_messages(self, conversation: Dict, style: str, service: str) -> List[Dict]:
        """Prepare context messages with style formatting for the specified service."""
        messages = []

        for msg in conversation.get('messages', []):
            if msg.get('type') == 'file_upload':
                # Handle file upload messages
                formatted_msg = self._format_file_message(msg, service)
                messages.append(formatted_msg)
            else:
                # Handle regular messages
                role = 'assistant' if msg['sender'] == 'assistant' else 'user'
                messages.append({
                    'role': role,
                    'content': msg['content']
                })

        return self.style_manager.format_messages_for_service(messages, style, service)

    def _format_file_message(self, msg: Dict, service: str) -> Dict:
        """Format file upload messages for different AI services."""
        file_type = msg.get('file_type', '')

        if file_type == 'pdf':
            content = (
                "I've processed a PDF document with the following details:\n"
                f"{msg['content']}"
            )
        else:
            content = msg['content']

        return {
            'role': 'system',
            'content': content
        }

    def list_conversations(self) -> List[str]:
        """List all available conversations."""
        try:
            conv_files = list(self.history_dir.glob("*.json"))
            conv_list = []

            for file in conv_files:
                try:
                    with open(file, encoding='utf-8') as f:
                        conv_data = json.load(f)
                        created_at = datetime.fromisoformat(
                            conv_data.get('created_at', '2000-01-01T00:00:00')
                        )
                        conv_list.append((file.stem, created_at))
                except Exception as e:
                    print(f"Error reading conversation {file}: {e}")
                    continue

            conv_list.sort(key=lambda x: x[1], reverse=True)
            return [conv[0] for conv in conv_list]

        except Exception as e:
            print(f"Error listing conversations: {str(e)}")
            return []

    def _get_conv_path(self, conv_id: str) -> Path:
        """Get the file path for a conversation."""
        return self.history_dir / f"{conv_id}.json"

    def _save_conversation(self, path: Path, conversation: Dict) -> None:
        """Save conversation data to file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, indent=2, ensure_ascii=False)

    def _load_conversation(self, path: Path) -> Dict:
        """Load conversation data from file."""
        try:
            if not path.exists():
                return {
                    "messages": [],
                    "token_totals": {
                        "input": 0,
                        "output": 0,
                        "total": 0
                    }
                }
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading conversation file: {str(e)}")
            return {
                "messages": [],
                "token_totals": {
                    "input": 0,
                    "output": 0,
                    "total": 0
                }
            }

    def estimate_tokens(self, text: str, style: str = "Professor") -> int:
        """Estimate token count with style consideration."""
        try:
            # Get base token count
            base_tokens = len(self.gpt_encoder.encode(str(text)))

            # Apply style multiplier
            style_config = self.style_manager.get_style_config(style)
            return int(base_tokens * style_config.token_multiplier)
        except Exception as e:
            logging.error(f"Token estimation error: {e}")
            return len(text.split())  # Fallback estimation

    def _estimate_pdf_tokens(self, pdf_data: Dict, style: str = "Professor") -> int:
        """
        Estimate token count for PDF content with style consideration.

        This method provides accurate token estimation for PDF content by considering
        both the metadata and content sections separately. It applies style multipliers
        while ensuring proper handling of structured PDF data.

        Args:
            pdf_data (Dict): The PDF file data including metadata and content
            style (str): The conversation style to apply

        Returns:
            int: Estimated token count with style multiplier applied
        """
        try:
            # Estimate tokens for metadata
            metadata = pdf_data.get('metadata', {})
            metadata_text = (
                f"Title: {metadata.get('title', 'Untitled')}\n"
                f"Author: {metadata.get('author', 'Unknown')}\n"
                f"Pages: {metadata.get('pages', 0)}"
            )
            metadata_tokens = len(self.gpt_encoder.encode(metadata_text))

            # Estimate tokens for content
            content_tokens = len(self.gpt_encoder.encode(pdf_data.get('content', '')))

            # Calculate total tokens
            total_tokens = metadata_tokens + content_tokens

            # Apply style multiplier
            style_config = self.style_manager.get_style_config(style)
            return int(total_tokens * style_config.token_multiplier)

        except Exception as e:
            logging.error(f"PDF token estimation error: {e}")
            # Fallback to basic estimation
            return len(pdf_data.get('content', '').split())

    def _estimate_file_tokens(self, file_data: Dict, style: str = "Professor") -> int:
        """Estimate token count for file content with style consideration."""
        try:
            file_type = file_data.get('type', '')
            content = file_data.get('content', '')
            metadata = file_data.get('metadata', {})

            if file_type == 'pdf':
                # For PDFs, include metadata in token count
                metadata_text = (
                    f"Title: {metadata.get('title', 'Untitled')}\n"
                    f"Author: {metadata.get('author', 'Unknown')}\n"
                    f"Pages: {metadata.get('pages', 0)}"
                )
                total_text = f"{metadata_text}\n\n{content}"
            else:
                total_text = content

            # Calculate base tokens
            base_tokens = len(self.gpt_encoder.encode(str(total_text)))

            # Apply style multiplier
            style_config = self.style_manager.get_style_config(style)
            return int(base_tokens * style_config.token_multiplier)

        except Exception as e:
            logger.error(f"File token estimation error: {e}")
            return len(str(content).split())  # Fallback estimation

    def _update_token_totals(self, conversation: Dict, tokens: int, is_input: bool) -> None:
        """Update token totals with style consideration."""
        totals = conversation.get('token_totals', {
            "input": 0,
            "output": 0,
            "total": 0
        })

        if is_input:
            totals["input"] += tokens
        else:
            totals["output"] += tokens

        totals["total"] += tokens
        conversation["token_totals"] = totals

    def update_conversation_tokens(self, conv_id: str) -> None:
        """
        Recalculate and update token totals for a conversation.
        This helps maintain accurate token counts across service switches.
        """
        try:
            conversation = self.get_conversation(conv_id)
            if not conversation:
                return

            token_totals = {
                'claude': 0,
                'chatgpt': 0,
                'dalle': 0,
                'gemini': 0,
                'input': 0,
                'total': 0
            }

            for message in conversation.get('messages', []):
                tokens = message.get('tokens', 0)
                token_totals['total'] += tokens

                if message['sender'] == 'user':
                    token_totals['input'] += tokens
                elif message.get('ai_service'):
                    service = message['ai_service'].lower()
                    if service in token_totals:
                        token_totals[service] += tokens

            # Update conversation with new totals
            conversation['token_totals'] = token_totals
            self._save_conversation(self._get_conv_path(conv_id), conversation)

            return token_totals

        except Exception as e:
            print(f"Error updating token counts: {str(e)}")
            raise RuntimeError(f"Token update error: {str(e)}")

    def get_formatted_history(self, conv_id: str, max_messages: int = None) -> str:
        """
        Get formatted conversation history for AI context.
        This ensures consistent history formatting across all AI services.
        """
        try:
            conversation = self.get_conversation(conv_id)
            if not conversation:
                return ""

            messages = conversation.get('messages', [])
            if max_messages:
                messages = messages[-max_messages:]

            formatted_history = []
            for msg in messages:
                role = "Assistant" if msg['sender'] == "assistant" else "Human"
                content = msg['content']
                if msg.get('ai_service'):
                    content = f"[{msg['ai_service'].upper()}]: {content}"
                formatted_history.append(f"{role}: {content}")

            return "\n\n".join(formatted_history)

        except Exception as e:
            print(f"Error formatting history: {str(e)}")
            return ""

    def clear_conversation(self, conv_id: str) -> None:
        """
        Clear all messages from a conversation while preserving its metadata.
        This is a safer alternative to completely removing the conversation.
        """
        try:
            conv_path = self._get_conv_path(conv_id)
            conversation = self._load_conversation(conv_path)

            # Preserve metadata but clear messages
            conversation["messages"] = []
            conversation["token_totals"] = {
                "input": 0,
                "output": 0,
                "total": 0
            }

            self._save_conversation(conv_path, conversation)

        except Exception as e:
            print(f"Error clearing conversation: {str(e)}")
            raise RuntimeError(f"Error clearing conversation: {str(e)}")

    def handle_service_error(self, conv_id: str, error: Exception, service: str) -> str:
        """
        Handle errors from AI services gracefully with recovery options.
        This provides better user experience when services encounter issues.
        """
        error_message = str(error)

        # Add error message to conversation
        self.add_message(
            conv_id,
            f"Error with {service.upper()}: {error_message}",
            "system",
            service,
            tokens=0
        )

        # Provide helpful error message
        if "rate limit" in error_message.lower():
            return "The service is currently busy. Please try again in a moment."
        elif "token" in error_message.lower():
            return "The conversation is too long. Consider starting a new chat or summarizing previous messages."
        else:
            return f"An error occurred with {service.upper()}. Please try again or switch to another AI service."

    def get_clipboard_image(self) -> Tuple[bool, Optional[bytes], Optional[str]]:
        """Get image from clipboard using FileManager."""
        try:
            # Create FileManager instance if not already created
            if not hasattr(self, 'file_manager'):
                self.file_manager = FileManager()

            # Delegate clipboard handling to FileManager
            return self.file_manager.get_clipboard_image()
        except Exception as e:
            logger.error(f"Error handling clipboard image: {str(e)}")
            return False, None, f"Clipboard error: {str(e)}"

    def add_image_message(self, conv_id: str, image_data: str, content: str, sender: str) -> None:
        """Add an image message to the conversation.

        Args:
            conv_id (str): Conversation ID
            image_data (str): Base64 encoded image data
            content (str): Message content/caption
            sender (str): Message sender
        """
        try:
            # Get conversation
            conversation = self.get_conversation(conv_id)
            if not conversation:
                raise ValueError(f"Conversation {conv_id} not found")

            # Create message with image metadata
            message = {
                "content": content,
                "sender": sender,
                "timestamp": datetime.now().isoformat(),
                "type": "image",
                "image_data": image_data
            }

            # Add message to conversation
            conversation["messages"].append(message)

            # Save conversation
            conv_path = self._get_conv_path(conv_id)
            self._save_conversation(conv_path, conversation)

        except Exception as e:
            logger.error(f"Error adding image message: {str(e)}")
            raise RuntimeError(f"Failed to add image message: {str(e)}")