import json
import tiktoken
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any
from config.app_config import AppConfig
import base64
from anthropic import Anthropic
import openai
import google.generativeai as genai
from dotenv import load_dotenv
import os


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

    def send_to_claude(self, conv_id: str, prompt: str,
                       model: str = "claude-3-5-sonnet-20241022") -> str:
        """Send a message to Claude and handle the response."""
        try:
            # Calculate input tokens
            input_tokens = self.estimate_tokens(prompt)

            # Add user message to conversation with token count
            self.add_message(
                conv_id,
                prompt,
                "user",
                "claude",
                model,
                tokens=input_tokens
            )

            # Prepare the message for Claude
            messages = [{
                "role": "user",
                "content": prompt
            }]

            # Send request to Claude
            response = self.anthropic.messages.create(
                messages=messages,
                model=model,
                max_tokens=1024
            )

            # Extract response content and calculate output tokens
            response_content = response.content[0].text if response and response.content else ""
            output_tokens = self.estimate_tokens(response_content)

            # Add assistant's response to conversation with token count
            self.add_message(
                conv_id,
                response_content,
                "assistant",
                "claude",
                model,
                tokens=output_tokens
            )

            return response_content

        except Exception as e:
            print(f"Claude API Error: {str(e)}")
            raise RuntimeError(f"Error processing message: {str(e)}")

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