import streamlit as st
from typing import Dict, List, Optional
import json
from pathlib import Path
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound


class CodeViewer:
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self._initialize_state()

    def _initialize_state(self):
        """Initialize the code viewer state if not already present."""
        if 'code_files' not in st.session_state:
            st.session_state.code_files = {}

    def add_file(self, filename: str, content: str, language: Optional[str] = None) -> None:
        """Add a file to the code viewer."""
        try:
            # Detect language if not provided
            if not language:
                extension = Path(filename).suffix.lstrip('.')
                language = self._detect_language(extension)

            # Format the code with syntax highlighting
            formatted_code = self._format_code(content, language)

            # Store the file information
            st.session_state.code_files[filename] = {
                'content': content,
                'formatted_content': formatted_code,
                'language': language,
                'timestamp': st.session_state.get('last_update', '')
            }
        except Exception as e:
            st.error(f"Error adding file {filename}: {str(e)}")

    def get_file(self, filename: str) -> Dict:
        """Retrieve a specific file's information."""
        return st.session_state.code_files.get(filename, {})

    def get_all_files(self) -> Dict[str, Dict]:
        """Get all stored files."""
        return st.session_state.code_files

    def remove_file(self, filename: str) -> None:
        """Remove a file from the code viewer."""
        if filename in st.session_state.code_files:
            del st.session_state.code_files[filename]

    def clear_files(self) -> None:
        """Clear all stored files."""
        st.session_state.code_files = {}

    def render_code_popup(self) -> None:
        """Render the code viewing popup if enabled."""
        if self.state_manager.get_state('show_code_popup', False):
            with st.sidebar:
                st.markdown("### Code Viewer")

                # File selector
                files = list(self.get_all_files().keys())
                if files:
                    selected_file = st.selectbox(
                        "Select File",
                        files,
                        key="code_viewer_selected_file"
                    )

                    file_info = self.get_file(selected_file)

                    # Display file information
                    st.markdown(f"**Language:** {file_info.get('language', 'Unknown')}")
                    st.markdown(f"**Last Updated:** {file_info.get('timestamp', 'Unknown')}")

                    # Code display with syntax highlighting
                    st.markdown(
                        file_info.get('formatted_content', ''),
                        unsafe_allow_html=True
                    )

                    # Copy button
                    if st.button("Copy Code"):
                        st.write(
                            f'<script>navigator.clipboard.writeText(`{file_info["content"]}`)</script>',
                            unsafe_allow_html=True
                        )
                        st.success("Code copied to clipboard!")
                else:
                    st.info("No files available for viewing.")

                # Close button
                if st.button("Close"):
                    self.state_manager.set_state('show_code_popup', False)
                    st.rerun()

    def _detect_language(self, extension: str) -> str:
        """Detect the programming language based on file extension."""
        extension_map = {
            'py': 'python',
            'js': 'javascript',
            'jsx': 'javascript',
            'tsx': 'typescript',
            'ts': 'typescript',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'md': 'markdown'
        }
        return extension_map.get(extension.lower(), 'text')

    def _format_code(self, code: str, language: str) -> str:
        """Format code with syntax highlighting."""
        try:
            # Get the appropriate lexer for the language
            try:
                lexer = get_lexer_by_name(language)
            except ClassNotFound:
                lexer = TextLexer()

            # Create HTML formatter with custom styles
            formatter = HtmlFormatter(
                style='monokai',
                cssclass='syntax-highlight',
                linenos=True,
                wrapcode=True
            )

            # Generate highlighted HTML
            highlighted_code = highlight(code, lexer, formatter)

            # Add custom CSS
            css = formatter.get_style_defs('.syntax-highlight')
            highlighted_code = f"<style>{css}</style>{highlighted_code}"

            return highlighted_code

        except Exception as e:
            st.error(f"Error formatting code: {str(e)}")
            return f"<pre><code>{code}</code></pre>"