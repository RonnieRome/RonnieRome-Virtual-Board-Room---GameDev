import json
import base64
import csv
import io
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
from config.app_config import AppConfig


class ExportManager:
    def __init__(self, service_manager):
        self.service_manager = service_manager

    def export_conversation(self, conv_id: str, format_type: str) -> str:
        """Export conversation in specified format."""
        try:
            conversation = self.service_manager.chat_manager.get_conversation(conv_id)
            if not conversation:
                return None

            if format_type == "json":
                return json.dumps(conversation, indent=2)
            elif format_type == "txt":
                return self._format_chat_export(conversation)
        except Exception as e:
            print(f"Export error: {str(e)}")
            return None

    def _format_chat_export(self, conversation: Dict) -> str:
        """Format conversation as readable text."""
        chat_lines = []
        chat_lines.append(f"Title: {conversation.get('title', 'Untitled')}")
        chat_lines.append(f"Created: {conversation.get('created_at', 'Unknown')}\n")

        for msg in conversation.get('messages', []):
            timestamp = msg.get('timestamp', '').split('T')[0]
            sender = msg.get('sender', 'unknown')
            service = msg.get('ai_service', 'user')
            content = msg.get('content', '')
            chat_lines.append(f"[{timestamp}] {sender} ({service}):")
            chat_lines.append(content)
            chat_lines.append("")

        return "\n".join(chat_lines)

    def export_code_snippets(self, conv_id: str, indices: List[int]) -> List[Dict]:
        """Export selected code snippets from conversation."""
        try:
            conversation = self.service_manager.chat_manager.get_conversation(conv_id)
            if not conversation:
                return []

            code_snippets = []
            messages = conversation.get('messages', [])

            for idx in indices:
                if 0 <= idx < len(messages):
                    msg = messages[idx]
                    if 'content' in msg and '```' in msg['content']:
                        snippets = self._extract_code_blocks(msg['content'])
                        code_snippets.extend(snippets)

            return code_snippets
        except Exception as e:
            print(f"Code export error: {str(e)}")
            return []

    def _extract_code_blocks(self, content: str) -> List[Dict]:
        """Extract code blocks from message content."""
        code_blocks = []
        lines = content.split('\n')
        in_code_block = False
        current_block = []
        current_language = ''

        for line in lines:
            if line.startswith('```'):
                if in_code_block:
                    # End of code block
                    code_blocks.append({
                        'language': current_language,
                        'code': '\n'.join(current_block)
                    })
                    current_block = []
                    in_code_block = False
                else:
                    # Start of code block
                    in_code_block = True
                    # Extract language if specified
                    current_language = line[3:].strip()
            elif in_code_block:
                current_block.append(line)

        return code_blocks

    def export_images(self, conv_id: str) -> List[Dict]:
        """Export images from conversation."""
        try:
            conversation = self.service_manager.chat_manager.get_conversation(conv_id)
            if not conversation:
                return []

            images = []
            for msg in conversation.get('messages', []):
                if 'image_data' in msg:
                    timestamp = msg.get('timestamp', '').replace(':', '-')
                    filename = f"image_{timestamp}.png"

                    # Create export path
                    export_path = Path("exports") / filename

                    # Save image
                    try:
                        image_data = base64.b64decode(msg['image_data'])
                        with open(export_path, 'wb') as f:
                            f.write(image_data)

                        images.append({
                            'filename': filename,
                            'path': str(export_path),
                            'timestamp': msg.get('timestamp')
                        })
                    except Exception as e:
                        print(f"Error saving image {filename}: {str(e)}")
                        continue

            return images
        except Exception as e:
            print(f"Image export error: {str(e)}")
            return []

    def cleanup_exports(self) -> None:
        """Clean up old exported files."""
        try:
            export_dir = Path("exports")
            if export_dir.exists():
                current_time = datetime.now()
                for file in export_dir.glob("*"):
                    file_age = current_time - datetime.fromtimestamp(file.stat().st_mtime)
                    if file_age.days > 1:  # Remove files older than 1 day
                        file.unlink()
        except Exception as e:
            print(f"Cleanup error: {str(e)}")