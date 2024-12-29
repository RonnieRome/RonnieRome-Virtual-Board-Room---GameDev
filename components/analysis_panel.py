import streamlit as st
import asyncio
import json
import logging
import streamlit.components.v1 as components
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class AnalysisPanel:
    """
    Enhanced Analysis Panel that integrates with React components for file analysis display.
    """

    def __init__(self, state_manager, ai_manager):
        """Initialize the analysis panel with state and AI management capabilities."""
        self.state_manager = state_manager
        self.ai_manager = ai_manager
        self.logger = logging.getLogger(__name__)
        self._initialize_state()
        self._setup_event_handlers()

    def _initialize_state(self):
        initial_state = {
            'panel_visible': False,
            'selected_file': None,
            'analysis_results': None,
            'analysis_loading': False,
            'error_message': None,
            'last_update': None,
            'react_loaded': False
        }

        for key, value in initial_state.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def _setup_event_handlers(self):
        """
        Set up handlers for various panel events.
        This enables communication between Streamlit and React components.
        """
        if 'event_handlers' not in st.session_state:
            st.session_state.event_handlers = {
                'closePanel': self.handle_close,
                'selectTab': self.handle_tab_selection,
                'refreshAnalysis': self.handle_refresh
            }

    async def handle_file_selection(self, filename: str):
        """
        Handle file selection and trigger analysis asynchronously.
        This method coordinates the file analysis process and updates the UI accordingly.
        """
        try:
            # Validate conversation selection
            if not self.state_manager.get_state('selected_conv'):
                st.warning("Please select a conversation first.")
                return

            # Update state for loading
            self._update_state(
                selected_file=filename,
                analysis_loading=True,
                error_message=None
            )

            # Get conversation ID and trigger analysis
            conv_id = self.state_manager.get_state('selected_conv')
            analysis_results = await self.ai_manager.analyze_files(
                conv_id,
                'code_review'
            )

            # Update state with results
            self._update_state(
                analysis_results=analysis_results,
                analysis_loading=False,
                panel_visible=True,
                last_update=datetime.now().isoformat()
            )

        except Exception as e:
            error_msg = f"Error analyzing file: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self._update_state(
                analysis_loading=False,
                error_message=error_msg
            )
        finally:
            st.rerun()

    def _update_state(self, **kwargs):
        """
        Update multiple state variables atomically.
        This ensures consistent state updates across the application.
        """
        for key, value in kwargs.items():
            if hasattr(st.session_state, key):
                setattr(st.session_state, key, value)

    def render(self):
        """
        Render the analysis panel with enhanced UI and React integration.
        This method handles both the panel toggle and content rendering.
        """
        try:
            # Render toggle button
            self._render_toggle_button()

            # Render panel if visible
            if st.session_state.panel_visible:
                self._render_react_panel()

        except Exception as e:
            self.logger.error(f"Error rendering panel: {str(e)}", exc_info=True)
            st.error("Unable to display analysis panel. Please refresh the page.")

    def _render_toggle_button(self):
        """Render the panel toggle button with consistent styling."""
        col1, col2 = st.columns([8, 2])
        with col2:
            button_label = "🔍 Toggle Analysis" if not st.session_state.panel_visible else "❌ Close Analysis"
            if st.button(button_label):
                st.session_state.panel_visible = not st.session_state.panel_visible
                st.rerun()

    def _render_react_panel(self):
        """
        Render the React-based analysis panel.
        This method handles the integration between Streamlit and React components.
        """
        # Prepare analysis data
        analysis_data = self._prepare_analysis_data(st.session_state.get('analysis_results'))

        # Include the React component definition and rendering logic
        html_content = self._get_panel_html(analysis_data)

        # Render using streamlit components
        components.html(
            html_content,
            height=800,
            scrolling=True
        )

    def _get_panel_html(self, analysis_data: Dict) -> str:
        """
        Generate the complete HTML content for the React panel.
        This includes all necessary scripts, styles, and the React component definition.
        """
        return f"""
           <!DOCTYPE html>
           <html>
           <head>
               <script src="https://cdnjs.cloudflare.com/ajax/libs/react/17.0.2/umd/react.production.min.js"></script>
               <script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/17.0.2/umd/react-dom.production.min.js"></script>
               <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
               {self._get_panel_styles()}
           </head>
           <body>
               <div id="analysis-panel-root"></div>
               <script>
                   {self._get_react_component()}

                   const analysisData = {json.dumps(analysis_data)};
                   const panelState = {{
                       isLoading: {json.dumps(st.session_state.get('analysis_loading', False))},
                       currentFile: {json.dumps(st.session_state.get('selected_file'))},
                       errorMessage: {json.dumps(st.session_state.get('error_message'))}
                   }};

                   ReactDOM.render(
                       React.createElement(FileAnalysisPanel, {{
                           ...analysisData,
                           ...panelState,
                           onClose: () => {{
                               window.parent.postMessage({{
                                   type: 'streamlit:closePanel'
                               }}, '*');
                           }}
                       }}),
                       document.getElementById('analysis-panel-root')
                   );
               </script>
           </body>
           </html>
           """

    def _get_panel_styles(self) -> str:
        """
        Define the styles for the analysis panel.
        This includes animations and layout styles.
        """
        return """
           <style>
               .analysis-panel {
                   background-color: #f8f9fa;
                   border-left: 1px solid #dee2e6;
                   height: 100vh;
                   position: fixed;
                   right: 0;
                   top: 0;
                   width: 30%;
                   overflow-y: auto;
                   box-shadow: -2px 0 5px rgba(0,0,0,0.1);
                   animation: slideIn 0.3s ease-out;
               }

               @keyframes slideIn {
                   from { transform: translateX(100%); }
                   to { transform: translateX(0); }
               }

               .custom-scrollbar {
                   scrollbar-width: thin;
                   scrollbar-color: #CBD5E0 #F7FAFC;
               }

               .custom-scrollbar::-webkit-scrollbar {
                   width: 6px;
               }

               .custom-scrollbar::-webkit-scrollbar-track {
                   background: #F7FAFC;
               }

               .custom-scrollbar::-webkit-scrollbar-thumb {
                   background-color: #CBD5E0;
                   border-radius: 3px;
               }
           </style>
           """

    def _get_react_component(self):
        """Returns the React component code as a string."""
        return """
        function FileAnalysisPanel({ analysisResults, isLoading, currentFile, onClose }) {
            // Initialize state for active tab
            const [activeTab, setActiveTab] = React.useState('summary');

            // Loading state handler
            if (isLoading) {
                return (
                    <div className="analysis-panel analysis-panel-enter">
                        <div className="p-4 border-b">
                            <div className="flex justify-between items-center">
                                <h2 className="text-lg font-semibold">Analyzing File</h2>
                                <button onClick={onClose} className="text-gray-500 hover:text-gray-700">×</button>
                            </div>
                        </div>
                        <div className="flex items-center justify-center h-[calc(100vh-100px)]">
                            <div className="text-center">
                                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
                                <p className="mt-4 text-gray-600">Analyzing {currentFile}...</p>
                            </div>
                        </div>
                    </div>
                );
            }

            // Empty state handler
            if (!analysisResults || !analysisResults.summary) {
                return (
                    <div className="analysis-panel analysis-panel-enter">
                        <div className="p-4 border-b">
                            <div className="flex justify-between items-center">
                                <h2 className="text-lg font-semibold">File Analysis</h2>
                                <button onClick={onClose} className="text-gray-500 hover:text-gray-700">×</button>
                            </div>
                        </div>
                        <div className="flex items-center justify-center h-[calc(100vh-100px)]">
                            <p className="text-gray-600">Select a file to analyze</p>
                        </div>
                    </div>
                );
            }

            // Main component render
            return (
                <div className="analysis-panel analysis-panel-enter">
                    <div className="p-4 border-b">
                        <div className="flex justify-between items-center">
                            <div>
                                <h2 className="text-lg font-semibold">File Analysis</h2>
                                {currentFile && (
                                    <p className="text-sm text-gray-500">{currentFile}</p>
                                )}
                            </div>
                            <button onClick={onClose} className="text-gray-500 hover:text-gray-700">×</button>
                        </div>
                    </div>

                    <div className="border-b">
                        <div className="flex space-x-2 p-2">
                            {['summary', 'insights', 'suggestions', 'technical'].map(tab => (
                                <button
                                    key={tab}
                                    onClick={() => setActiveTab(tab)}
                                    className={`px-3 py-2 rounded-md text-sm font-medium ${
                                        activeTab === tab
                                            ? 'bg-blue-100 text-blue-700'
                                            : 'text-gray-600 hover:bg-gray-100'
                                    }`}
                                >
                                    {tab.charAt(0).toUpperCase() + tab.slice(1)}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="overflow-y-auto h-[calc(100vh-180px)]">
                        <div className="p-4">
                            {activeTab === 'summary' && (
                                <div className="prose max-w-none">
                                    <p>{analysisResults.summary}</p>
                                </div>
                            )}

                            {activeTab === 'insights' && (
                                <div className="space-y-3">
                                    {analysisResults.insights.map((insight, index) => (
                                        <div key={index} className="flex items-start space-x-2">
                                            <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
                                                <span className="text-blue-600 text-sm">{index + 1}</span>
                                            </div>
                                            <p className="text-gray-700">{insight}</p>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {activeTab === 'suggestions' && (
                                <div className="space-y-3">
                                    {analysisResults.suggestions.map((suggestion, index) => (
                                        <div key={index} className="p-3 bg-gray-50 rounded-lg">
                                            <p className="text-gray-700">{suggestion}</p>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {activeTab === 'technical' && (
                                <div className="space-y-4">
                                    {Object.entries(analysisResults.technical_details).map(([key, value], index) => (
                                        <div key={index} className="border-b border-gray-200 pb-2">
                                            <dt className="text-sm font-medium text-gray-600">{key}</dt>
                                            <dd className="mt-1 text-sm text-gray-900">{value}</dd>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="absolute bottom-0 left-0 right-0 p-2 bg-gray-50 border-t">
                        <p className="text-xs text-gray-500 text-center">
                            Last updated: {new Date(analysisResults.timestamp).toLocaleString()}
                        </p>
                    </div>
                </div>
            );
        }
        """

    def _render_panel_content(self):
        """Render the panel content with analysis results."""
        st.markdown("### Code Analysis")

        if st.session_state.analysis_loading:
            st.spinner("Analyzing code...")
            return

        if not st.session_state.analysis_results:
            st.info("Select a file to analyze")
            return

        results = st.session_state.analysis_results

        # Summary Section
        with st.expander("📝 Summary", expanded=True):
            st.markdown(results.summary)

        # Insights Section
        with st.expander("💡 Insights", expanded=True):
            for insight in results.insights:
                st.markdown(f"• {insight}")

        # Suggestions Section
        with st.expander("🔧 Suggestions", expanded=True):
            for suggestion in results.suggestions:
                st.markdown(f"• {suggestion}")

        # Technical Details Section
        with st.expander("⚙️ Technical Details", expanded=True):
            for key, value in results.technical_details.items():
                st.markdown(f"**{key}:** {value}")

        # Relationships Section (if available)
        if results.relationships:
            with st.expander("🔗 File Relationships", expanded=True):
                for file, related in results.relationships.items():
                    st.markdown(f"**{file}** is related to:")
                    for rel in related:
                        st.markdown(f"• {rel}")

        # Timestamp information
        st.caption(f"Analysis completed at: {results.timestamp}")

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

    def toggle_visibility(self):
        """Toggle panel visibility."""
        st.session_state.panel_visible = not st.session_state.panel_visible
        st.rerun()

    def handle_close(self):
        """Handle panel close event."""
        st.session_state.panel_visible = False
        st.rerun()

    def update_analysis(self, new_results):
        """Update the analysis results."""
        st.session_state.analysis_results = new_results
        st.rerun()

    def is_visible(self) -> bool:
        """Check if the panel is currently visible."""
        return st.session_state.panel_visible

    def get_current_file(self) -> Optional[str]:
        """Get the currently selected file."""
        return st.session_state.get('selected_file')

    def get_analysis_results(self) -> Optional[Dict]:
        """Get the current analysis results."""
        return st.session_state.get('analysis_results')