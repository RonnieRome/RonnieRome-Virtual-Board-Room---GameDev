import io
import base64
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageGrab
from io import BytesIO
from typing import Dict, List, Tuple, Optional, Union
from config.app_config import AppConfig


class FileManager:
    def __init__(self):
        self.config = AppConfig
        self.config.initialize_directories()

    def handle_file_upload(self, file, conv_id: str) -> Dict:
        """Process a single uploaded file and return its data."""
        if file.type.startswith('image'):
            return self._process_image_file(file)
        else:
            return self._process_text_file(file)

    def handle_multiple_files(self, files: List, conv_id: str) -> List[Dict]:
        """Process multiple uploaded files."""
        stored_files = []
        for file in files:
            try:
                file_data = self.handle_file_upload(file, conv_id)
                stored_files.append(file_data)
            except Exception as e:
                print(f"Error processing file {file.name}: {str(e)}")
                continue
        return stored_files

    def get_clipboard_image(self) -> Tuple[bool, Optional[bytes], Optional[str]]:
        """Retrieve image data from clipboard using multiple methods."""
        try:
            # Try using PIL's ImageGrab first
            img = ImageGrab.grabclipboard()
            if img is not None:
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                return True, buffer.getvalue(), None
        except Exception as e:
            pass  # Continue to next method if this fails

        try:
            # Try using win32clipboard as fallback
            import win32clipboard
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
                win32clipboard.CloseClipboard()

                # Convert DIB to PIL Image
                try:
                    image = Image.frombytes('RGB', (1, 1), data)  # Initial conversion
                    buffer = BytesIO()
                    image.save(buffer, format="PNG")
                    return True, buffer.getvalue(), None
                except Exception as e:
                    return False, None, f"Image conversion error: {str(e)}"
            else:
                win32clipboard.CloseClipboard()
        except Exception as e:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
            return False, None, f"Clipboard access error: {str(e)}"

        return False, None, "No image found in clipboard"

    def export_conversation(self, conversation: Dict, format: str = "json",
                            export_dir: Optional[Path] = None) -> Optional[str]:
        """Export conversation in specified format."""
        if export_dir is None:
            export_dir = self.config.EXPORTS_DIR

        export_dir.mkdir(exist_ok=True)

        try:
            filename = f"{conversation['title']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            export_path = export_dir / f"{filename}.{format}"

            if format == "json":
                import json
                content = json.dumps(conversation, indent=2, ensure_ascii=False)
            else:  # txt format
                content = self._format_conversation_as_text(conversation)

            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return content

        except Exception as e:
            print(f"Export error: {str(e)}")
            return None

    def extract_code(self, messages: List[Dict]) -> List[Tuple[int, Dict]]:
        """Extract code blocks from messages."""
        return [
            (i, msg) for i, msg in enumerate(messages)
            if isinstance(msg, dict) and "content" in msg and "```" in msg["content"]
        ]

    def export_code(self, code_messages: List[Tuple[int, Dict]],
                    export_dir: Optional[Path] = None) -> List[Path]:
        """Export selected code blocks to files."""
        if export_dir is None:
            export_dir = self.config.EXPORTS_DIR / "code"

        export_dir.mkdir(parents=True, exist_ok=True)
        exported_files = []

        for i, msg in code_messages:
            try:
                if "```" in msg["content"]:
                    start = msg["content"].find("```") + 3
                    end = msg["content"].find("```", start)
                    if end > start:
                        lang = msg["content"][start:msg["content"].find("\n", start)].strip()
                        code = msg["content"][msg["content"].find("\n", start):end].strip()

                        filename = f"snippet_{i}.{lang}"
                        path = export_dir / filename
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(code)
                        exported_files.append(path)
            except Exception as e:
                print(f"Error exporting code message {i}: {str(e)}")
                continue

        return exported_files

    def _process_image_file(self, file) -> Dict:
        """Process uploaded image file."""
        try:
            image = Image.open(file)
            buffered = io.BytesIO()
            image.save(buffered, format=image.format)
            image_data = base64.b64encode(buffered.getvalue()).decode()

            return {
                'name': file.name,
                'type': 'image',
                'content': image_data,
                'format': image.format,
                'language': 'image',
                'stored_at': datetime.now().isoformat()
            }
        except Exception as e:
            raise Exception(f"Error processing image file: {str(e)}")

    def _process_text_file(self, file) -> Dict:
        """Process uploaded text file."""
        try:
            content = file.read().decode('utf-8')
            file_extension = file.name.split('.')[-1] if '.' in file.name else 'txt'

            return {
                'name': file.name,
                'type': 'text',
                'content': content,
                'language': file_extension,
                'stored_at': datetime.now().isoformat()
            }
        except Exception as e:
            raise Exception(f"Error processing text file: {str(e)}")

    def _format_conversation_as_text(self, conversation: Dict) -> str:
        """Format conversation as readable text."""
        content = []
        for msg in conversation.get("messages", []):
            sender = msg.get('sender', 'unknown')
            ai_service = f"[{msg.get('ai_service', 'user')}]" if msg.get('ai_service') else ""
            message_content = msg.get('content', '')

            if msg.get('image_data'):
                message_content += "\n[Image attached]"

            content.append(f"{sender} {ai_service}: {message_content}\n")

        return "\n".join(content)