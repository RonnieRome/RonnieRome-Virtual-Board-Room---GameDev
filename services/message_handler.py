from datetime import datetime
from typing import Dict, Optional, Union, List
import base64
from pathlib import Path
import json
from config.app_config import AppConfig


class MessageHandler:
    def __init__(self):
        self.config = AppConfig

    def create_message(self, content: str, sender: str, message_type: str = "text",
                       ai_service: Optional[str] = None, model: Optional[str] = None,
                       image_data: Optional[str] = None, tokens: Optional[int] = None,
                       metadata: Optional[Dict] = None) -> Dict:
        """Create a standardized message object."""
        message = {
            "content": content,
            "sender": sender,
            "type": message_type,
            "timestamp": datetime.now().isoformat(),
            "tokens": tokens or self._estimate_tokens(content)
        }

        if ai_service:
            message["ai_service"] = ai_service
            message["model"] = model

        if image_data:
            message["image_data"] = image_data

        if metadata:
            message["metadata"] = metadata

        return message

    def format_message_for_display(self, message: Dict) -> Dict:
        """Format a message for display in the UI."""
        formatted_message = message.copy()

        if message.get("type") == "code":
            formatted_message["content"] = self._format_code_blocks(message["content"])
        elif message.get("type") == "file":
            formatted_message["content"] = self._format_file_message(message)

        return formatted_message

    def process_system_message(self, content: str, metadata: Optional[Dict] = None) -> Dict:
        """Create a system message with optional metadata."""
        return self.create_message(
            content=content,
            sender="system",
            message_type="system",
            metadata=metadata
        )

    def process_user_message(self, content: str, image_data: Optional[str] = None,
                             metadata: Optional[Dict] = None) -> Dict:
        """Process and format a user message."""
        return self.create_message(
            content=content,
            sender="user",
            message_type="text" if not image_data else "image",
            image_data=image_data,
            metadata=metadata
        )

    def process_ai_response(self, content: str, ai_service: str, model: str,
                            tokens: Optional[int] = None, metadata: Optional[Dict] = None) -> Dict:
        """Process and format an AI response message."""
        return self.create_message(
            content=content,
            sender="assistant",
            message_type="text",
            ai_service=ai_service,
            model=model,
            tokens=tokens,
            metadata=metadata
        )

    def process_file_message(self, file_data: Dict) -> Dict:
        """Process and format a file upload message."""
        content = f"File uploaded: {file_data['name']}"
        metadata = {
            "file_type": file_data["type"],
            "language": file_data.get("language", "text"),
            "size": len(file_data.get("content", "")),
            "upload_time": datetime.now().isoformat()
        }

        return self.create_message(
            content=content,
            sender="user",
            message_type="file",
            metadata=metadata
        )

    def extract_code_blocks(self, message: Dict) -> List[Dict]:
        """Extract code blocks from a message with metadata."""
        if "```" not in message["content"]:
            return []

        blocks = []
        parts = message["content"].split("```")

        for i in range(1, len(parts), 2):
            if parts[i].strip():
                language = ""
                code = parts[i]

                # Extract language if specified
                first_line = code.split('\n', 1)[0].strip()
                if first_line and not first_line.startswith(' '):
                    language = first_line
                    code = code.split('\n', 1)[1] if '\n' in code else ''

                blocks.append({
                    "language": language,
                    "code": code.strip(),
                    "start_index": len(''.join(parts[:i])) + 3,
                    "end_index": len(''.join(parts[:i + 1])) + 3
                })

        return blocks

    def _format_code_blocks(self, content: str) -> str:
        """Format code blocks with proper syntax highlighting."""
        if "```" not in content:
            return content

        formatted_parts = []
        parts = content.split("```")

        for i, part in enumerate(parts):
            if i % 2 == 0:  # Regular text
                formatted_parts.append(part)
            else:  # Code block
                # Extract language if specified
                lines = part.split('\n', 1)
                if len(lines) > 1:
                    lang, code = lines
                    formatted_parts.append(f'```{lang}\n{code}\n```')
                else:
                    formatted_parts.append(f'```\n{part}\n```')

        return "".join(formatted_parts)

    def _format_file_message(self, message: Dict) -> str:
        """Format file upload messages with metadata."""
        metadata = message.get("metadata", {})
        file_type = metadata.get("file_type", "unknown")
        language = metadata.get("language", "text")
        size = metadata.get("size", 0)

        return (
            f"{message['content']}\n"
            f"Type: {file_type}\n"
            f"Language: {language}\n"
            f"Size: {size} bytes"
        )

    def _estimate_tokens(self, content: str) -> int:
        """Estimate token count for a message."""
        # Simple estimation - can be replaced with more accurate counting
        return len(content.split())