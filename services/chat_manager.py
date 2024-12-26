import os
import json
import base64
import tiktoken
import openai
import google.generativeai as genai
import asyncio
import uuid
import requests

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any
from config.app_config import AppConfig
from anthropic import Anthropic
from dotenv import load_dotenv



class ChatHistoryManager:
    def __init__(self):
        self.config = AppConfig()
        load_dotenv()

        # Initialize API clients
        self.openai = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.anthropic = Anthropic(api_key=os.getenv('CLAUDE_API_KEY'))
        if not os.getenv('CLAUDE_API_KEY'):
            raise ValueError("CLAUDE_API_KEY environment variable is not set")

        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.gemini = genai.GenerativeModel('gemini-pro')

        self.image_handler = ImageHandler()

        # Set up directories
        self.history_dir = Path("chat_histories")
        self.exports_dir = Path("exports")
        self.history_dir.mkdir(exist_ok=True)
        self.exports_dir.mkdir(exist_ok=True)

        # Initialize token counter
        self.gpt_encoder = tiktoken.encoding_for_model("gpt-4")


    def create_conversation(self, title: str) -> str:
        """Create a new conversation with the given title."""
        conv_id = f"{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        conv_path = self._get_conv_path(conv_id)

        conversation = {
            "title": title,
            "created_at": datetime.now().isoformat(),
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
        """Generate an image using DALL-E with storage handling."""
        try:
            # Calculate input tokens
            input_tokens = self.estimate_tokens(prompt)

            # Add user message
            self.add_message(
                conv_id,
                f"Image generation prompt: {prompt}",
                "user",
                "dalle",
                model,
                tokens=input_tokens
            )

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
                # Download image
                image_response = requests.get(image_url)
                image_response.raise_for_status()

                # Generate unique ID
                image_id = f"dalle_{conv_id}_{str(uuid.uuid4())}"

                # Save image using handler
                self.image_handler.save_image(image_response.content, image_id)

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
                    conv_id,
                    f"Generated image ({size}):\n{prompt}",
                    "assistant",
                    "dalle",
                    model,
                    metadata=message_data
                )

                return f"Image generated successfully! Prompt: {prompt}"

        except Exception as e:
            print(f"DALL-E API Error: {str(e)}")
            raise RuntimeError(f"Error processing image generation: {str(e)}")

    def add_message(self, conv_id: str, content: str, sender: str,
                    ai_service: Optional[str] = None, model: Optional[str] = None,
                    tokens: Optional[int] = None) -> None:
        """Add a message to the conversation history."""
        conv_path = self._get_conv_path(conv_id)
        conversation = self._load_conversation(conv_path)

        message = {
            "content": content,
            "sender": sender,
            "timestamp": datetime.now().isoformat(),
            "tokens": tokens if tokens is not None else self.estimate_tokens(content)
        }

        if ai_service:
            message["ai_service"] = ai_service
            message["model"] = model

        conversation["messages"].append(message)
        self._save_conversation(conv_path, conversation)

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

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a piece of text."""
        try:
            return len(self.gpt_encoder.encode(str(text)))
        except Exception as e:
            print(f"Token estimation error: {e}")
            return 0

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


class ImageHandler:
    def __init__(self, storage_type="local"):
        self.storage_type = storage_type
        self.image_store = {}  # Temporary in-memory store

    def save_image(self, image_data: bytes, image_id: str) -> str:
        """Save an image and return its storage identifier."""
        if self.storage_type == "local":
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            self.image_store[image_id] = encoded_image
            return image_id
        return None

    def get_image(self, image_id: str) -> Optional[bytes]:
        """Retrieve an image by its identifier."""
        if self.storage_type == "local":
            encoded_image = self.image_store.get(image_id)
            if encoded_image:
                return base64.b64decode(encoded_image)
        return None