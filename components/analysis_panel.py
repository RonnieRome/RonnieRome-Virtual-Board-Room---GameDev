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
        self.state_manager = state_manager
        self.ai_manager = ai_manager
        self.logger = logging.getLogger(__name__)
        self._initialize_state()
        self._setup_event_handlers()

    def _initialize_state(self):
        """Initialize the panel's state variables."""
        initial_state = {
            'panel_visible': False,
            'selected_file': None,
            'analysis_results': None,
            'analysis_loading': False,
            'error_message': None,
            'last_update': None,
            'react_loaded': False,
            'active_tab': 'summary'  # Add default active tab
        }

        for key, value in initial_state.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def _setup_event_handlers(self):
        """Set up handlers for various panel events."""
        if 'event_handlers' not in st.session_state:
            st.session_state.event_handlers = {
                'selectFile': self.handle_file_selection,
                'closePanel': self.handle_close,
                'refreshAnalysis': self.handle_refresh
            }

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

    async def handle_file_selection(self, filename: str):
        """Handle file selection and trigger analysis asynchronously."""
        try:
            if not self.state_manager.get_state('selected_conv'):
                st.warning("Please select a conversation first.")
                return

            self._update_state(
                selected_file=filename,
                analysis_loading=True,
                error_message=None
            )

            conv_id = self.state_manager.get_state('selected_conv')
            analysis_results = await self.ai_manager.analyze_files(
                conv_id,
                'code_review'
            )

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

    def _render_react_panel(self, panel_styles):
        """
        Render the React-based analysis panel with the specified styles.

        Args:
            panel_styles (dict): The styles to apply to the panel
        """
        try:
            # Prepare analysis data
            analysis_data = self._prepare_analysis_data(st.session_state.get('analysis_results'))

            # Generate HTML content with styles
            html_content = self._get_panel_html(analysis_data, panel_styles)

            # Render using streamlit components
            components.html(
                html_content,
                height=800,
                scrolling=True
            )
        except Exception as e:
            self.logger.error(f"Error rendering React panel: {str(e)}")
            raise

    def _get_panel_html(self, analysis_data: Dict, panel_styles: Dict) -> str:
        """
        Generate the complete HTML content for the React panel.

        Args:
            analysis_data (Dict): The data to display in the panel
            panel_styles (Dict): The styles to apply to the panel

        Returns:
            str: The complete HTML content
        """
        return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/react/17.0.2/umd/react.production.min.js"></script>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/17.0.2/umd/react-dom.production.min.js"></script>
                <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
                {self._get_enhanced_panel_styles(panel_styles)}
            </head>
            <body>
                <div id="analysis-panel-root"></div>
                <script>
                    {self._get_react_component()}

                    const analysisData = {json.dumps(analysis_data)};
                    const panelStyles = {json.dumps(panel_styles)};
                    const panelState = {{
                        isLoading: {json.dumps(st.session_state.get('analysis_loading', False))},
                        currentFile: {json.dumps(st.session_state.get('selected_file'))},
                        errorMessage: {json.dumps(st.session_state.get('error_message'))},
                        styles: panelStyles
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

    def render(self, style_config=None):
        """
        Render the analysis panel with enhanced UI and React integration.
        """
        try:
            # Use a container for the toggle button
            with st.container():
                self._render_toggle_button()

            # Render panel if visible - using a separate container outside the main layout
            if st.session_state.panel_visible:
                # Process styles
                panel_styles = self._process_styles(style_config)
                # Render the overlay panel
                self._render_overlay_panel(panel_styles)

        except Exception as e:
            self.logger.error(f"Error rendering panel: {str(e)}")
            st.error("Unable to display analysis panel. Please refresh the page.")

    def _render_overlay_panel(self, panel_styles):
        """
        Render the panel as an overlay with proper positioning and animations.
        """
        # Create a full-page overlay container
        overlay_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/react/17.0.2/umd/react.production.min.js"></script>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/17.0.2/umd/react-dom.production.min.js"></script>
                <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
                <style>
                    /* Overlay container */
                    .overlay-container {{
                        position: fixed;
                        top: 0;
                        right: 0;
                        bottom: 0;
                        width: 100%;
                        height: 100%;
                        z-index: 999999; /* Ensure it's above other content */
                        pointer-events: none; /* Allow clicks to pass through */
                    }}

                    /* Analysis panel */
                    .analysis-panel {{
                        position: absolute;
                        top: 0;
                        right: 0;
                        width: 400px; /* Fixed width */
                        height: 100%;
                        background-color: {panel_styles.get('panel', {}).get('background', '#FFFFFF')};
                        box-shadow: -2px 0 5px rgba(0,0,0,0.1);
                        overflow-y: auto;
                        transform: translateX(0);
                        transition: transform 0.3s ease-in-out;
                        pointer-events: auto; /* Re-enable clicks for panel */
                        display: flex;
                        flex-direction: column;
                    }}

                    /* Panel header */
                    .panel-header {{
                        padding: 1rem;
                        background-color: {panel_styles.get('panel', {}).get('header_background', '#F8F9FA')};
                        border-bottom: 1px solid #E2E8F0;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }}

                    /* Panel content */
                    .panel-content {{
                        flex: 1;
                        overflow-y: auto;
                        padding: 1rem;
                    }}

                    /* Slide out animation */
                    .panel-closed {{
                        transform: translateX(100%);
                    }}

                    /* Custom scrollbar */
                    .analysis-panel::-webkit-scrollbar {{
                        width: 6px;
                    }}

                    .analysis-panel::-webkit-scrollbar-track {{
                        background: #F7FAFC;
                    }}

                    .analysis-panel::-webkit-scrollbar-thumb {{
                        background-color: #CBD5E0;
                        border-radius: 3px;
                    }}
                </style>
            </head>
            <body>
                <div class="overlay-container">
                    <div class="analysis-panel">
                        <div class="panel-header">
                            <h2 class="text-lg font-semibold">Code Analysis</h2>
                            <button onclick="closePanel()" class="text-gray-500 hover:text-gray-700">×</button>
                        </div>
                        <div class="panel-content">
                            {self._render_panel_content(panel_styles)}
                        </div>
                    </div>
                </div>
                <script>
                    function closePanel() {{
                        // Add closing animation
                        document.querySelector('.analysis-panel').classList.add('panel-closed');
                        // Notify Streamlit
                        setTimeout(() => {{
                            window.parent.postMessage({{
                                type: 'streamlit:closePanel'
                            }}, '*');
                        }}, 300);
                    }}

                    // Handle Streamlit messages
                    window.addEventListener('message', function(e) {{
                        if (e.data.type === 'streamlit:closePanel') {{
                            closePanel();
                        }}
                    }});
                </script>
            </body>
            </html>
        """

        # Render the overlay
        components.html(
            overlay_html,
            height=0,  # Height 0 since we're using fixed positioning
            width=0,   # Width 0 since we're using fixed positioning
        )

    def _render_panel_content(self, panel_styles):
        """
        Render the main panel content, either showing the empty state
        or actual analysis results.
        """
        if not st.session_state.get('analysis_results'):
            return self._render_empty_state()
        else:
            return self._render_analysis_results(st.session_state.analysis_results)

    def _render_empty_state(self):
        """
        Render the empty state message when no analysis is available.
        """
        return """
            <div class="flex items-center justify-center h-full">
                <div class="text-center p-6">
                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 class="mt-4 text-lg font-medium text-gray-900">No files selected</h3>
                    <p class="mt-2 text-sm text-gray-500">
                        Select files for analysis or request coding assistance to see insights here.
                    </p>
                </div>
            </div>
        """

    def _render_analysis_results(self, analysis_results):
        """
        Render the analysis results in a structured format.

        Args:
            analysis_results: The analysis results to render, expected to contain
                            summary, insights, suggestions, and technical details.

        Returns:
            str: HTML string containing the formatted analysis results
        """
        try:
            # Extract various sections from analysis results
            summary = analysis_results.get('summary', 'No summary available')
            insights = analysis_results.get('insights', [])
            suggestions = analysis_results.get('suggestions', [])
            technical_details = analysis_results.get('technical_details', {})
            timestamp = analysis_results.get('timestamp', 'Unknown time')

            # Build the HTML content for each section
            html_content = f"""
                <div class="space-y-6">
                    <!-- Summary Section -->
                    <div class="bg-white rounded-lg shadow-sm p-4">
                        <h3 class="text-lg font-semibold mb-2">Summary</h3>
                        <p class="text-gray-700">{summary}</p>
                    </div>

                    <!-- Insights Section -->
                    <div class="bg-white rounded-lg shadow-sm p-4">
                        <h3 class="text-lg font-semibold mb-2">Key Insights</h3>
                        <div class="space-y-2">
                            {''.join([
                f'<div class="flex items-start space-x-2">'
                f'<div class="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 '
                f'flex items-center justify-center">'
                f'<span class="text-blue-600 text-sm">{i + 1}</span></div>'
                f'<p class="text-gray-700">{insight}</p></div>'
                for i, insight in enumerate(insights)
            ]) if insights else '<p class="text-gray-500">No insights available</p>'}
                        </div>
                    </div>

                    <!-- Suggestions Section -->
                    <div class="bg-white rounded-lg shadow-sm p-4">
                        <h3 class="text-lg font-semibold mb-2">Suggestions</h3>
                        <div class="space-y-2">
                            {''.join([
                f'<div class="p-3 bg-gray-50 rounded-lg">'
                f'<p class="text-gray-700">{suggestion}</p></div>'
                for suggestion in suggestions
            ]) if suggestions else '<p class="text-gray-500">No suggestions available</p>'}
                        </div>
                    </div>

                    <!-- Technical Details Section -->
                    <div class="bg-white rounded-lg shadow-sm p-4">
                        <h3 class="text-lg font-semibold mb-2">Technical Details</h3>
                        <div class="space-y-2">
                            {''.join([
                f'<div class="border-b border-gray-200 pb-2">'
                f'<dt class="text-sm font-medium text-gray-600">{key}</dt>'
                f'<dd class="mt-1 text-sm text-gray-900">{value}</dd></div>'
                for key, value in technical_details.items()
            ]) if technical_details else '<p class="text-gray-500">No technical details available</p>'}
                        </div>
                    </div>

                    <!-- Timestamp -->
                    <div class="text-xs text-gray-500 text-center">
                        Last updated: {timestamp}
                    </div>
                </div>
            """

            return html_content

        except Exception as e:
            self.logger.error(f"Error rendering analysis results: {str(e)}")
            return f"""
                <div class="p-4 bg-red-50 text-red-700 rounded-lg">
                    <p>Error rendering analysis results: {str(e)}</p>
                </div>
            """

    def _render_toggle_button(self):
        """Render the panel toggle button."""
        col1, col2 = st.columns([8, 2])
        with col2:
            button_label = "🔍 Toggle Analysis" if not st.session_state.panel_visible else "❌ Close Analysis"
            if st.button(button_label, use_container_width=True):
                st.session_state.panel_visible = not st.session_state.panel_visible
                st.rerun()

    def _render_empty_panel(self, panel_styles):
        """
        Render an empty panel with instructions.
        """
        html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/react/17.0.2/umd/react.production.min.js"></script>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/17.0.2/umd/react-dom.production.min.js"></script>
                <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
                {self._get_enhanced_panel_styles(panel_styles)}
            </head>
            <body>
                <div id="analysis-panel-root">
                    <div class="analysis-panel">
                        <div class="p-4 border-b">
                            <div class="flex justify-between items-center">
                                <h2 class="text-lg font-semibold">Code Analysis Panel</h2>
                                <button onclick="window.parent.postMessage({{'type': 'streamlit:closePanel'}}, '*')" 
                                        class="text-gray-500 hover:text-gray-700">×</button>
                            </div>
                        </div>
                        <div class="flex items-center justify-center h-[calc(100vh-100px)]">
                            <div class="text-center p-6">
                                <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                <h3 class="mt-4 text-lg font-medium text-gray-900">No files selected</h3>
                                <p class="mt-2 text-sm text-gray-500">
                                    Select files for analysis or request coding assistance to see insights here.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
        """

        # Render using streamlit components
        components.html(
            html_content,
            height=800,
            scrolling=True
        )

    def _get_enhanced_panel_styles(self, panel_styles):
        """
        Generate enhanced CSS styles with improved visibility debugging.
        """
        background = panel_styles.get('panel', {}).get('background', '#FFFFFF')
        font_family = panel_styles.get('panel', {}).get('font_family', '"SF Mono", "Consolas", monospace')
        line_height = panel_styles.get('panel', {}).get('line_height', '1.6')

        return f"""
            <style>
                .analysis-panel {{
                    background-color: {background};
                    font-family: {font_family};
                    line-height: {line_height};
                    height: 100vh;
                    position: fixed;
                    right: 0;
                    top: 0;
                    width: 30%;
                    overflow-y: auto;
                    box-shadow: -2px 0 5px rgba(0,0,0,0.1);
                    animation: slideIn 0.3s ease-out;
                    z-index: 1000;  /* Ensure panel appears above other content */
                    display: block !important;  /* Force visibility */
                }}

                @keyframes slideIn {{
                    from {{ transform: translateX(100%); opacity: 0; }}
                    to {{ transform: translateX(0); opacity: 1; }}
                }}

                /* Add visual debugging helpers */
                .analysis-panel::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    border: 2px solid #2B6CB0;
                    pointer-events: none;
                    z-index: 1001;
                }}
            </style>
        """

    def _process_styles(self, style_config):
        """
        Process and combine styles in a single place.

        Args:
            style_config: Optional style configuration to merge with defaults

        Returns:
            dict: The final, merged styles
        """
        # Start with default styles
        final_styles = self._get_default_styles()

        # If we have a style config, try to integrate it
        if style_config is not None:
            try:
                # Convert the style config to a usable format
                custom_styles = self._convert_style_config(style_config)
                if custom_styles:
                    # Merge with defaults
                    final_styles = self._merge_styles(final_styles, custom_styles)
            except Exception as e:
                self.logger.warning(f"Error processing custom styles: {e}")
                # Continue with default styles on error

        return final_styles

    def _get_default_styles(self):
        """
        Get the default styles for the analysis panel.
        This method has a single responsibility: providing default styles.

        Returns:
            dict: The default styles dictionary
        """
        return {
            'panel': {
                'background': '#FFFFFF',
                'font_family': '"SF Mono", "Consolas", monospace',
                'line_height': '1.6',
                'code_block': {
                    'background': '#F8F9FA',
                    'border_radius': '4px',
                    'padding': '12px',
                    'font_size': '14px'
                },
                'heading': {
                    'font_family': '-apple-system, BlinkMacSystemFont, sans-serif',
                    'font_weight': '600',
                    'color': '#1A1A1A'
                },
                'text': {
                    'font_size': '14px',
                    'color': '#2D3748'
                }
            },
            'tabs': {
                'active': {
                    'background': '#EBF5FF',
                    'color': '#2B6CB0'
                },
                'inactive': {
                    'background': 'transparent',
                    'color': '#4A5568'
                }
            }
        }

    def _convert_style_config(self, style_config):
        """
        Convert various style config formats into a consistent dictionary format.

        Args:
            style_config: Can be a dictionary, StyleConfig object, or other config format

        Returns:
            dict: Processed style configuration dictionary or None if invalid
        """
        if isinstance(style_config, dict):
            return style_config

        # If it's a StyleConfig object
        if hasattr(style_config, 'get_theme_css'):
            return {
                'panel': {
                    'background': '#FFFFFF',
                    'font_family': '"SF Mono", "Consolas", monospace',
                    'line_height': '1.6'
                }
            }

        return None

    def _merge_styles(self, base_styles, override_styles):
        """
        Merge override styles into base styles, with proper deep merging for nested dictionaries.

        Args:
            base_styles (dict): The base styles to start with
            override_styles (dict): The styles to merge in

        Returns:
            dict: The merged styles dictionary
        """
        if not isinstance(override_styles, dict):
            return base_styles

        result = base_styles.copy()
        for key, value in override_styles.items():
            if (
                    isinstance(value, dict)
                    and key in result
                    and isinstance(result[key], dict)
            ):
                result[key] = self._merge_styles(result[key], value)
            else:
                result[key] = value

        return result


    def _get_analysis_optimized_styles(self):
        """
        Get analysis-optimized default styles.
        These styles are specifically designed for code analysis readability.
        """
        return {
            'panel': {
                'background': '#FFFFFF',  # Clean white background for readability
                'font_family': '"SF Mono", "Consolas", monospace',  # Monospace for code
                'line_height': '1.6',  # Increased line height for readability
                'code_block': {
                    'background': '#F8F9FA',  # Light gray for code blocks
                    'border_radius': '4px',
                    'padding': '12px',
                    'font_size': '14px'
                },
                'heading': {
                    'font_family': '-apple-system, BlinkMacSystemFont, sans-serif',
                    'font_weight': '600',
                    'color': '#1A1A1A'
                },
                'text': {
                    'font_size': '14px',
                    'color': '#2D3748'  # Dark gray for better contrast
                }
            },
            'tabs': {
                'active': {
                    'background': '#EBF5FF',  # Light blue for active tab
                    'color': '#2B6CB0'
                },
                'inactive': {
                    'background': 'transparent',
                    'color': '#4A5568'
                }
            }
        }


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

    def handle_close(self):
        """Handle panel close event."""
        self._update_state(
            panel_visible=False,
            selected_file=None,
            analysis_results=None
        )
        st.rerun()