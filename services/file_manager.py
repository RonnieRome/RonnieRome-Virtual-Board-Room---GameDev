import io
import base64
import logging
import PyPDF2
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageGrab
from io import BytesIO
from typing import Dict, List, Tuple, Optional, Union
from config.app_config import AppConfig

# Set up logging
logger = logging.getLogger(__name__)


class FileManager:
    def __init__(self):
        self.config = AppConfig
        self.config.initialize_directories()

    def handle_file_upload(self, file, conv_id: str) -> Dict:
        """
        Process a single uploaded file and return its data.
        Supports image, PDF, and text files with appropriate handling for each type.
        """
        file_extension = file.name.split('.')[-1].lower() if '.' in file.name else ''

        if file.type.startswith('image'):
            return self._process_image_file(file)
        elif file_extension == 'pdf':
            return self._process_pdf_file(file)
        else:
            return self._process_text_file(file)

    def _process_pdf_file(self, file) -> Dict:
        """
        Extract and process content from PDF files.
        Handles text extraction page by page and includes metadata when available.
        """
        try:
            pdf_bytes = io.BytesIO(file.read())
            pdf_reader = PyPDF2.PdfReader(pdf_bytes)
            content = []
            total_pages = len(pdf_reader.pages)

            # Extract text from each page
            for page_num in range(total_pages):
                try:
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text.strip():
                        content.append(f"[Page {page_num + 1}]\n{text}")
                except Exception as e:
                    logger.warning(f"Page {page_num + 1} extraction failed: {str(e)}")
                    content.append(f"[Page {page_num + 1} - Extraction Error]")

            # Get PDF metadata
            metadata = pdf_reader.metadata or {}

            return {
                'name': file.name,
                'type': 'pdf',
                'content': '\n\n'.join(content),
                'metadata': {
                    'title': metadata.get('/Title', 'Untitled'),
                    'author': metadata.get('/Author', 'Unknown'),
                    'pages': total_pages
                },
                'language': 'pdf',
                'stored_at': datetime.now().isoformat()
            }
        except Exception as e:
            raise Exception(f"PDF processing error: {str(e)}")

    def handle_multiple_files(self, files: List, conv_id: str) -> List[Dict]:
        """Process multiple uploaded files and collect their data."""
        stored_files = []
        for file in files:
            try:
                file_data = self.handle_file_upload(file, conv_id)
                stored_files.append(file_data)
            except Exception as e:
                logger.error(f"File processing error - {file.name}: {str(e)}")
                continue
        return stored_files

    def _process_image_file(self, file) -> Dict:
        """Transform and encode image files for storage and display."""
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
            raise Exception(f"Image processing error: {str(e)}")

    def _process_text_file(self, file) -> Dict:
        """
        Process text files with robust encoding detection and handling.
        Supports multiple encodings and includes fallback mechanisms.
        """

        def try_decode(bytes_content, encodings):
            for encoding in encodings:
                try:
                    return bytes_content.decode(encoding)
                except UnicodeDecodeError:
                    continue
            return None

        try:
            bytes_content = file.read()
            encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']

            try:
                import chardet
                detected = chardet.detect(bytes_content)
                if detected and detected['confidence'] > 0.7:
                    encodings.insert(0, detected['encoding'])
            except ImportError:
                pass

            content = try_decode(bytes_content, encodings)
            if content is None:
                content = bytes_content.decode('latin-1')

            return {
                'name': file.name,
                'type': 'text',
                'content': content,
                'language': file.name.split('.')[-1] if '.' in file.name else 'txt',
                'encoding': encodings[0],
                'stored_at': datetime.now().isoformat()
            }
        except Exception as e:
            raise Exception(f"Text processing error: {str(e)}")

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



        def try_decode(bytes_content, encodings):
            """Helper function to try different encodings."""
            for encoding in encodings:
                try:
                    return bytes_content.decode(encoding)
                except UnicodeDecodeError:
                    continue
            return None

        try:
            # Read the file content as bytes first
            bytes_content = file.read()

            # List of encodings to try, in order of preference
            encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']

            # Try to detect encoding using chardet if available
            try:
                import chardet
                detected = chardet.detect(bytes_content)
                if detected and detected['confidence'] > 0.7:
                    encodings.insert(0, detected['encoding'])
            except ImportError:
                logger.debug("chardet not available for encoding detection")

            # Try each encoding
            content = try_decode(bytes_content, encodings)

            if content is None:
                # If all text decodings fail, check if it might be a binary file
                import magic  # python-magic library
                file_type = magic.from_buffer(bytes_content)

                if 'text' not in file_type.lower():
                    raise Exception(f"File appears to be binary: {file_type}")
                else:
                    # Last resort: use latin-1 which can decode any byte sequence
                    content = bytes_content.decode('latin-1')

            # Get file extension and determine language
            file_extension = file.name.split('.')[-1] if '.' in file.name else 'txt'

            # Create the response dictionary
            file_data = {
                'name': file.name,
                'type': 'text',
                'content': content,
                'language': file_extension,
                'encoding': encodings[0],  # Store which encoding worked
                'stored_at': datetime.now().isoformat()
            }

            # Log successful processing
            logger.debug(f"Successfully processed file {file.name} with encoding {encodings[0]}")

            return file_data

        except Exception as e:
            logger.error(f"Error processing text file {file.name}: {str(e)}", exc_info=True)
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