import streamlit as st
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime
from pathlib import Path
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound
from components.file_analyzer import FileAnalyzer
from components.analysis_models import FileAnalysisResult


class CodeViewer:
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.file_analyzer = FileAnalyzer()
        self._initialize_state()

    def _initialize_state(self):
        """Initialize the code viewer state with enhanced tracking."""
        super()._initialize_state()
        if 'file_history' not in st.session_state:
            st.session_state.file_history = {}
        if 'analysis_cache' not in st.session_state:
            st.session_state.analysis_cache = {}

    def add_file(self, filename: str, content: str, language: Optional[str] = None) -> Tuple[bool, str]:
        """
        Add a file to the code viewer with enhanced analysis.

        Args:
            filename: Name of the file
            content: File content
            language: Optional programming language

        Returns:
            Tuple of (success boolean, message string)
        """
        try:
            # Prepare file data for analysis
            file_data = {
                'name': filename,
                'content': content,
                'language': language,
                'stored_at': st.session_state.get('last_update', '')
            }

            # Perform file analysis
            analysis_results = self.file_analyzer.analyze_files([file_data])

            # Get the analysis result for this file
            file_id = list(analysis_results.keys())[0]  # Since we only analyzed one file
            analysis_result = analysis_results[file_id]

            # Format code with syntax highlighting
            if not language:
                extension = Path(filename).suffix.lstrip('.')
                language = self._detect_language(extension)

            formatted_code = self._format_code(content, language)

            # Store comprehensive file information
            st.session_state.code_files[filename] = {
                'content': content,
                'formatted_content': formatted_code,
                'language': language,
                'timestamp': st.session_state.get('last_update', ''),
                'analysis': analysis_result,
                'file_id': file_id
            }

            # Update analysis results and relationships in session state
            st.session_state.analysis_results.update(analysis_results)
            st.session_state.file_relationships.update(
                self.file_analyzer.get_file_relationships()
            )

            return True, f"Successfully added and analyzed file: {filename}"

        except Exception as e:
            return False, f"Error adding file {filename}: {str(e)}"

    def get_file_analysis(self, filename: str) -> Optional[FileAnalysisResult]:
        """Get the analysis results for a specific file."""
        file_info = st.session_state.code_files.get(filename)
        if file_info and 'analysis' in file_info:
            return file_info['analysis']
        return None

    def get_related_files(self, filename: str) -> List[str]:
        """Get files related to the specified file."""
        file_info = st.session_state.code_files.get(filename)
        if file_info and 'file_id' in file_info:
            file_id = file_info['file_id']
            return st.session_state.file_relationships.get(file_id, [])
        return []

    def render_code_popup(self) -> None:
        """Render the enhanced code viewing popup with analysis information."""
        if self.state_manager.get_state('show_code_popup', False):
            with st.sidebar:
                st.markdown("### Code Viewer & Analysis")

                files = list(self.get_all_files().keys())
                if files:
                    selected_file = st.selectbox(
                        "Select File",
                        files,
                        key="code_viewer_selected_file"
                    )

                    # Get file information and analysis
                    file_info = self.get_file(selected_file)
                    analysis_result = self.get_file_analysis(selected_file)

                    # Display tabs for different views
                    tab1, tab2 = st.tabs(["Code", "Analysis"])

                    with tab1:
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

                    with tab2:
                        if analysis_result:
                            # Display analysis information
                            st.markdown("#### File Summary")
                            st.markdown(analysis_result.summary)

                            st.markdown("#### Dependencies")
                            for dep in analysis_result.dependencies:
                                st.markdown(f"- {dep}")

                            # Show related files
                            related_files = self.get_related_files(selected_file)
                            if related_files:
                                st.markdown("#### Related Files")
                                for related_id in related_files:
                                    related_analysis = st.session_state.analysis_results.get(related_id)
                                    if related_analysis:
                                        st.markdown(f"- {related_analysis.file_name}")

                            # Display metadata
                            st.markdown("#### Metadata")
                            st.json(analysis_result.metadata)

                    # Close button with proper spacing
                    st.markdown("---")
                    if st.button("Close Viewer"):
                        self.state_manager.set_state('show_code_popup', False)
                        st.rerun()
                else:
                    st.info("No files available for viewing.")

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

    def track_file_change(self, filename: str, content: str) -> None:
        """Track changes to a file over time."""
        if filename not in st.session_state.file_history:
            st.session_state.file_history[filename] = []

        st.session_state.file_history[filename].append({
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'analysis_id': self._get_current_analysis_id(filename)
        })

    def _get_current_analysis_id(self, filename: str) -> str:
        """Get the current analysis ID for a file."""
        file_info = st.session_state.code_files.get(filename, {})
        return file_info.get('file_id', '')

    def get_file_history(self, filename: str) -> List[Dict]:
        """Get the change history for a file."""
        return st.session_state.file_history.get(filename, [])