import streamlit as st


def load_frontend_dependencies():
    """
    Load all necessary frontend dependencies for the application.
    This includes React, styling libraries, and custom styles.
    """
    st.markdown("""
        <!-- React and ReactDOM -->
        <script src="https://cdnjs.cloudflare.com/ajax/libs/react/17.0.2/umd/react.production.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/17.0.2/umd/react-dom.production.min.js"></script>

        <!-- Tailwind CSS -->
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">

        <!-- Custom styles -->
        <style>
            /* Global styles */
            .streamlit-container {
                max-width: 100% !important;
                padding: 0 !important;
            }

            /* Analysis Panel styles */
            .analysis-panel-container {
                position: fixed;
                right: 0;
                top: 0;
                height: 100vh;
                z-index: 1000;
                transition: transform 0.3s ease-in-out;
            }

            /* Loading animation */
            @keyframes spin {
                to { transform: rotate(360deg); }
            }

            .loading-spinner {
                animation: spin 1s linear infinite;
            }

            /* Scrollbar styling */
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

        <!-- Event handling script -->
        <script>
            // Handle messages from React components
            window.addEventListener('message', function(event) {
                if (event.data.type === 'streamlit:closePanel') {
                    // Send event to Streamlit
                    window.parent.postMessage({
                        type: 'streamlit:closePanel'
                    }, '*');
                }
            });
        </script>
    """, unsafe_allow_html=True)