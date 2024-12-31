import threading
import streamlit as st
import asyncio
import json
import logging
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from threading import Timer
from pathlib import Path
from typing import Dict, List, Optional
from components.file_analyzer import FileAnalyzer
from config.styles import StyleConfig

logger = logging.getLogger(__name__)

class AnalysisPanel:
    """
    Enhanced Analysis Panel that integrates with React components for file analysis display.
    """

    def __init__(self, state_manager, ai_manager, service_manager):
        self.state_manager = state_manager
        self.ai_manager = ai_manager
        self.service_manager = service_manager
        self.logger = logging.getLogger(__name__)
        self.file_analyzer = FileAnalyzer()
        self._initialize_panel_state()

    async def perform_analysis(self, depth: str, focus: list):
        """Perform the analysis using ServiceManager."""
        try:
            conv_id = self.state_manager.get_state('selected_conv')
            if not conv_id:
                st.error("No conversation selected")
                return

            with st.chat_message("assistant"):
                with st.spinner("Analyzing files..."):
                    # Use service_manager to handle analysis
                    analysis_result = await self.service_manager.handle_ai_analysis(
                        conv_id=conv_id,
                        analysis_type=self._get_analysis_type(depth, focus)
                    )

                    if analysis_result and analysis_result.status == "success":
                        st.session_state.show_analysis_popup = False
                        self._display_analysis_results(analysis_result, depth, focus)
                    else:
                        st.error("Analysis failed or returned no results")

        except Exception as e:
            self.logger.error(f"Error during analysis: {str(e)}")
            st.error(f"Error during analysis: {str(e)}")
        finally:
            st.session_state.show_analysis_popup = False

    def _get_analysis_type(self, depth: str, focus: list) -> str:
        """Convert depth and focus to analysis type."""
        if "Security" in focus:
            return "security_review"
        elif "Performance" in focus:
            return "performance_review"
        else:
            return "code_review"

    def _initialize_panel_state(self):
        """Initialize panel state variables."""
        initial_state = {
            'analysis_results': None,
            'analysis_loading': False,
            'error_message': None,
            'last_update': None,
            'selected_file': None,
            'show_analysis_popup': False,
            'analysis_depth': 'Standard',
            'analysis_focus': ['Code Quality']
        }

        for key, value in initial_state.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def render_analysis_popup(self):
        """Render the analysis popup with detailed options and results."""
        if not st.session_state.get('show_analysis_popup', False):
            return

        with st.sidebar.container():
            st.markdown("### File Analysis")
            st.warning("Select analysis options and view results")

            # Analysis options
            analysis_depth = st.radio(
                "Analysis Depth",
                ["Quick Scan", "Standard", "Deep Analysis"],
                key="analysis_depth"
            )

            analysis_focus = st.multiselect(
                "Analysis Focus",
                ["Code Quality", "Security", "Performance", "Documentation"],
                default=["Code Quality"],
                key="analysis_focus"
            )

            # Action buttons
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("✔️ Run Analysis", use_container_width=True):
                    self.perform_analysis(analysis_depth, analysis_focus)

            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.show_analysis_popup = False
                    st.rerun()

    def perform_analysis(self, depth: str, focus: list):
        """Perform the analysis and show results in chat."""
        try:
            conv_id = self.state_manager.get_state('selected_conv')
            conversation = self.service_manager.chat_manager.get_conversation(conv_id)
            stored_files = conversation.get('stored_files', [])

            if not stored_files:
                st.error("No files available for analysis")
                return

            with st.chat_message("assistant"):
                with st.spinner("Analyzing files..."):
                    # Use AIAnalysisManager for analysis
                    analysis_result = self.service_manager.ai_analysis_manager.analyze_files(conv_id)

                    if analysis_result and analysis_result.status == "success":
                        # Close the popup
                        st.session_state.show_analysis_popup = False

                        # Show results in chat
                        self._display_analysis_results(analysis_result, depth, focus)
                    else:
                        st.error("Analysis failed or returned no results")

        except Exception as e:
            self.logger.error(f"Error during analysis: {str(e)}")
            st.error(f"Error during analysis: {str(e)}")
        finally:
            # Ensure popup is closed even if there's an error
            st.session_state.show_analysis_popup = False

    def _display_analysis_results(self, analysis_result, depth: str, focus: list):
        """Display analysis results in chat area."""
        with st.expander("📊 Analysis Results", expanded=True):
            st.markdown("### Analysis Summary")
            st.markdown(analysis_result.summary)

            # Only show sections that were selected in focus
            if "Code Quality" in focus:
                with st.expander("🎯 Code Quality Metrics", expanded=False):
                    self._display_code_quality_metrics(analysis_result, depth)

            if "Security" in focus:
                with st.expander("🔒 Security Analysis", expanded=False):
                    self._display_security_analysis(analysis_result, depth)

            if "Performance" in focus:
                with st.expander("⚡ Performance Insights", expanded=False):
                    self._display_performance_insights(analysis_result, depth)

            if "Documentation" in focus:
                with st.expander("📚 Documentation Review", expanded=False):
                    self._display_documentation_review(analysis_result, depth)

            # Add download buttons for reports if available
            if hasattr(analysis_result, 'report_data'):
                st.download_button(
                    "📥 Download Full Report",
                    analysis_result.report_data,
                    file_name="analysis_report.pdf"
                )

        st.success("Analysis complete! Results are shown above.")

    def handle_tab_selection(self, tab: str):
        """Handle tab selection events from the React component."""
        try:
            if tab not in ['summary', 'insights', 'suggestions', 'technical']:
                raise ValueError(f"Invalid tab selection: {tab}")

            st.session_state.active_tab = tab
            st.rerun()
        except Exception as e:
            self.logger.error(f"Error handling tab selection: {str(e)}")
            self._update_state(error_message=f"Failed to switch tabs: {str(e)}")

    async def handle_file_select(self, filename: str):
        """Handle file selection and update panel state."""
        try:
            self._update_state(analysis_loading=True)
            conv_id = self.state_manager.get_state('selected_conv')

            if conv_id and filename:
                # Get file content and analyze
                result = await self.service_manager.handle_file_selection(filename, conv_id)

                if result:
                    self._update_state(
                        selected_file=filename,
                        analysis_results=result,
                        panel_visible=True,
                        analysis_loading=False
                    )
                else:
                    self._update_state(
                        error_message="Failed to analyze file",
                        analysis_loading=False
                    )

        except Exception as e:
            self.logger.error(f"Error handling file selection: {str(e)}")
            self._update_state(
                error_message=str(e),
                analysis_loading=False
            )

    def handle_file_selection(self, filename: str):
        """Handle file selection and analysis."""
        try:
            conv_id = self.state_manager.get_state('selected_conv')
            if not conv_id:
                return

            # Get file content from conversation
            conversation = self.service_manager.chat_manager.get_conversation(conv_id)
            stored_files = conversation.get('stored_files', [])
            selected_file = next((f for f in stored_files if f['name'] == filename), None)

            if selected_file:
                # Perform analysis (simplified for example)
                analysis_results = {
                    'summary': f"Analysis of {filename}",
                    'technical_details': {
                        'File Type': selected_file.get('type', 'Unknown'),
                        'Size': selected_file.get('size', 'Unknown')
                    },
                    'suggestions': ['Suggestion 1', 'Suggestion 2'],
                    'timestamp': datetime.now().isoformat()
                }

                self._update_state(
                    selected_file=filename,
                    analysis_results=analysis_results,
                    analysis_loading=False,
                    error_message=None
                )
            else:
                self._update_state(
                    error_message=f"File not found: {filename}",
                    analysis_loading=False
                )

        except Exception as e:
            self.logger.error(f"Error handling file selection: {str(e)}")
            self._update_state(
                error_message=str(e),
                analysis_loading=False
            )


    def _update_state(self, **kwargs):
        """Update multiple state variables atomically."""
        for key, value in kwargs.items():
            st.session_state[key] = value

    def _generate_analysis_prompt(self, file_data: Dict) -> str:
        """Generate an appropriate analysis prompt based on file type."""
        file_type = file_data.get('language', 'unknown').lower()

        prompts = {
            'python': """Please analyze this Python code for:
                1. Code structure and patterns
                2. Potential improvements
                3. Error handling
                4. Performance considerations
                5. Best practices compliance""",
            'javascript': """Please analyze this JavaScript code for:
                1. Code structure and patterns
                2. Potential improvements
                3. Error handling
                4. Performance optimizations
                5. Modern JS practices compliance"""
        }

        return prompts.get(file_type, "Please analyze this code for structure, quality, and potential improvements.")

    def _get_current_analysis(self):
        """Get current analysis results from state."""
        return st.session_state.analysis_results

    def _prepare_analysis_data(self, analysis_results):
        """Convert analysis results to JSON-safe format for React."""
        if not analysis_results:
            return None

        return {
            'summary': analysis_results.summary if hasattr(analysis_results, 'summary') else '',
            'insights': (analysis_results.insights
                         if hasattr(analysis_results, 'insights') else []),
            'suggestions': (analysis_results.suggestions
                            if hasattr(analysis_results, 'suggestions') else []),
            'technical_details': (analysis_results.technical_details
                                  if hasattr(analysis_results, 'technical_details') else {}),
            'timestamp': (analysis_results.timestamp
                          if hasattr(analysis_results, 'timestamp')
                          else datetime.now().isoformat())
        }

    def update_analysis(self, new_results):
        """Update the analysis results."""
        st.session_state.analysis_results = new_results
        st.rerun()


    def get_current_file(self) -> Optional[str]:
        """Get the currently selected file."""
        return st.session_state.get('selected_file')

    def get_analysis_results(self) -> Optional[Dict]:
        """Get the current analysis results."""
        return st.session_state.get('analysis_results')

    async def handle_refresh(self):
        """Handle refresh request for the current file analysis."""
        try:
            current_file = self.get_current_file()
            if not current_file:
                return

            # Reset state before refreshing
            self._update_state(
                analysis_loading=True,
                error_message=None
            )

            # Re-run analysis
            await self.handle_file_selection(filename=current_file)

        except Exception as e:
            error_msg = f"Error refreshing analysis: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self._update_state(
                analysis_loading=False,
                error_message=error_msg
            )

    def _display_code_quality_metrics(self, analysis_result, depth: str):
        """All the code quality metrics display code..."""
        # [Code from previous snippet]

    def _display_security_analysis(self, analysis_result, depth: str):
        """Display security analysis findings..."""
        # [From previous helper methods]

    def _display_performance_insights(self, analysis_result, depth: str):
        """Display performance analysis..."""
        # [From previous helper methods]

    def _display_documentation_review(self, analysis_result, depth: str):
        """Display documentation analysis..."""