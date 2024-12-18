import base64
import io
import os
from io import BytesIO

import pyperclip
import streamlit as st
from PIL import Image

from chat_manager import ChatHistoryManager


def handle_multiple_files(files, manager):
    stored_files = []

    for file in files:
        try:
            if file.type.startswith('image'):
                image = Image.open(file)
                buffered = io.BytesIO()
                image.save(buffered, format=image.format)
                image_data = base64.b64encode(buffered.getvalue()).decode()
                stored_files.append({
                    'name': file.name,
                    'type': 'image',
                    'content': image_data,
                    'format': image.format,
                    'language': 'image'
                })
            else:
                content = file.read().decode('utf-8')
                file_extension = file.name.split('.')[-1] if '.' in file.name else 'txt'
                stored_files.append({
                    'name': file.name,
                    'type': 'text',
                    'content': content,
                    'language': file_extension
                })

        except Exception as e:
            print(f"Error processing file {file.name}: {str(e)}")
            continue

    return stored_files


def main():
    st.set_page_config(page_title="RonnieRome Virtual Board Room - GameDev", layout="wide")
    for key in ['show_title_input', 'selected_conv', 'messages', 'ai_service', 'analysis_results', 'show_code_popup', 'theme']:
        if key not in st.session_state:
            if key == 'show_title_input':
                st.session_state[key] = True
            elif key == 'selected_conv':
                st.session_state[key] = None
            elif key == 'analysis_results':
                st.session_state[key] = []
            elif key == 'show_code_popup':
                st.session_state[key] = False
            elif key == 'theme':
                st.session_state[key] = "Pitch Black"
            else:
                st.session_state[key] = "Claude"

    manager = ChatHistoryManager()
    st.title("RonnieRome Virtual Board Room - GameDev")

    st.markdown("""
        <style>
            .streamlit-expanderHeader {
                width: 30% !important;
            }
            select {
                width: 30% !important;
            }
        </style>
    """, unsafe_allow_html=True)

    THEMES = {
        "Sabbath Black": """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Rock+Salt&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap'); /* Clean reading font */

            /* Apply globally */
            * {
                font-family: 'Rock Salt', cursive !important;
            }

            /* Sidebar specifically */
            .css-1d391kg { 
                font-size: 8px !important; /* Smaller sidebar text for better usability */
            }

            /* Main app readability */
            .stApp, .block-container, .stMarkdown, .stChatMessage, .css-18e3th9 {
                font-family: 'Roboto', sans-serif !important; /* Clean and readable font for chat/messages */
                font-size: 16px !important; /* Comfortable font size for main chat content */
            }

            /* Background and button styles */
            .stApp, .block-container, .css-1d391kg {
                background-color: #000000; /* Background for app and sidebar */
                color: #ffffff; /* Standard text color */
            }

            .stButton>button, .stTextInput>div>input, .stTextArea textarea {
                background-color: #333333;
                color: #ffffff;
            }
            </style>
            """,
        "Greenday": """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Finger+Paint&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');

            /* Apply globally */
            * {
                font-family: 'Finger Paint', cursive !important;
            }

            /* Sidebar specifically */
            .css-1d391kg {
                font-size: 15px !important;
            }

            /* Main app readability */
            .stApp, .block-container, .stMarkdown, .stChatMessage, .css-18e3th9 {
                font-family: 'Roboto', sans-serif !important;
                font-size: 16px !important;
            }

            .stApp, .block-container, .css-1d391kg {
                background-color: #002b36; /* Sidebar included */
                color: #b58900;
            }

            .stButton>button, .stTextInput>div>input, .stTextArea textarea {
                background-color: #073642;
                color: #b58900;
            }
            </style>
            """,
        "Pastel Elegance": """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');

            /* Apply globally */
            * {
                font-family: 'Dancing Script', cursive !important;
            }

            /* Sidebar specifically */
            .css-1d391kg {
                font-size: 15px !important;
            }

            /* Main app readability */
            .stApp, .block-container, .stMarkdown, .stChatMessage, .css-18e3th9 {
                font-family: 'Roboto', sans-serif !important;
                font-size: 16px !important;
            }

            .stApp, .block-container, .css-1d391kg {
                background-color: #ffe5e5; /* Background for app and sidebar */
                color: #d4af37; /* Gold text tone */
            }

            .stButton>button, .stTextInput>div>input, .stTextArea textarea {
                background-color: #ffd7d7;
                color: #d4af37;
            }
            </style>
            """,
        "Futuristic Metal": """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');

            /* Apply globally */
            * {
                font-family: 'Orbitron', sans-serif !important;
            }

            /* Sidebar specifically */
            .css-1d391kg {
                font-size: 15px !important;
            }

            /* Main app readability */
            .stApp, .block-container, .stMarkdown, .stChatMessage, .css-18e3th9 {
                font-family: 'Roboto', sans-serif !important;
                font-size: 16px !important;
            }

            .stApp, .block-container, .css-1d391kg {
                background: linear-gradient(45deg, #333333, #666666);
                color: #00ffff;
            }

            .stButton>button, .stTextInput>div>input, .stTextArea textarea {
                background-color: #555555;
                color: #00ffff;
            }
            </style>
            """,
        "Transparent": """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Great+Vibes&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');

            /* Apply globally */
            * {
                font-family: 'Great Vibes', cursive !important;
            }

            /* Sidebar specifically */
            .css-1d391kg {
                font-size: 15px !important;
            }

            /* Main app readability */
            .stApp, .block-container, .stMarkdown, .stChatMessage, .css-18e3th9 {
                font-family: 'Roboto', sans-serif !important;
                font-size: 16px !important;
            }

            .stApp, .css-1d391kg {
                background: transparent;
            }

            .block-container {
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
            }

            .stButton>button, .stTextInput>div>input, .stTextArea textarea {
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
                border: none;
            }
            </style>
            """
    }

    BACKGROUND_DIR = "backgrounds"

    # Ensure the directory exists
    if not os.path.exists(BACKGROUND_DIR):
        os.makedirs(BACKGROUND_DIR)

    background_images = [f for f in os.listdir(BACKGROUND_DIR) if f.endswith((".jpg", ".jpeg", ".png"))]

    if not background_images:
        st.warning("No background images found in the 'backgrounds' folder. Please add some images.")
        background_images = ["None"]

    # Function to encode the selected image to base64
    def get_base64_image(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()

    # Create two columns with equal width
    col1, col2 = st.columns(2)

    # Select Theme dropdown
    with col1:
        theme_choice = st.selectbox("Select Theme", list(THEMES.keys()), key="theme_choice")

    # Select Background Image dropdown
    with col2:
        selected_bg = st.selectbox("Select Background Image", ["None"] + background_images, key="bg_choice")

    # Apply the selected theme
    st.session_state.theme = theme_choice
    current_theme = st.session_state.get("theme", "Sabbath Black")
    st.markdown(THEMES[current_theme], unsafe_allow_html=True)

    # Apply the selected background using custom CSS
    if selected_bg != "None":
        bg_path = os.path.join(BACKGROUND_DIR, selected_bg)
        bg_base64 = get_base64_image(bg_path)
        st.markdown("""
            <style>
            /* Apply clean fonts to main chat */
            .stChatMessage, .stChatMessage p {
                font-family: 'Roboto', Arial, sans-serif !important;
                letter-spacing: normal !important;
            }

            /* Keep stylized font only for buttons and headers */
            .stButton button, h1, h2, h3 {
                font-family: 'Rock Salt', cursive !important;
            }

            /* Clean font for sidebar content */
            .css-1d391kg {
                font-family: 'Roboto', Arial, sans-serif !important;
            }

            /* Maintain button styling in sidebar */
            .css-1d391kg button {
                font-family: 'Rock Salt', cursive !important;
            }
            </style>
        """, unsafe_allow_html=True)
    else:
        # If "None" is selected, use a default background color
        st.markdown(
            """
            <style>
            body {
                background-color: #1e1e1e;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<hr style='height: 1px; border: none; background-color: #ddd; margin-top: 0px; margin-bottom: 0px;'>",
                unsafe_allow_html=True)

    with st.sidebar:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔄 Reset Info"):
                st.session_state.clear()
                st.session_state.show_title_input = True
                st.session_state.ai_service = "Claude"
                st.rerun()
        with col2:
            if st.button("📜 Show Code"):
                st.session_state.show_code_popup = not st.session_state.show_code_popup

        uploaded_files = st.file_uploader("Import Files",
                                          type=["json", "cs", "txt", "py", "js", "png", "jpg", "jpeg"],
                                          accept_multiple_files=True)
        col1, col2 = st.columns([1, 1])
        with col1:
            submit_button = st.button("📤 Submit Files")
        with col2:
            paste_button = st.button("📎 Paste Scr")

        if paste_button:
            try:
                clipboard_data = pyperclip.paste()
                if clipboard_data.startswith('data:image'):
                    img_data = clipboard_data.split(',')[1]
                    img_bytes = BytesIO(base64.b64decode(img_data))
                    st.image(img_bytes, use_container_width=True)
                    st.session_state.clipboard_image = img_data
                elif clipboard_data.lower().endswith(('.png', '.jpg', '.jpeg')):
                    with open(clipboard_data, 'rb') as file:
                        img_bytes = file.read()
                    st.image(img_bytes, use_container_width=True)
                    st.session_state.clipboard_image = base64.b64encode(img_bytes).decode()
                    if st.session_state.selected_conv:
                        manager.add_message(st.session_state.selected_conv, "[Clipboard image pasted]", "user")
            except Exception as e:
                st.error(f"Clipboard error: {e}")

        if st.session_state.show_title_input:
            col1, col2 = st.columns([3, 2])
            with col1:
                title = st.text_input("Chat Title")
            with col2:
                st.markdown("""
                    <style>
                    .button-shrink > button {
                        white-space: pre-wrap; /* Allow wrapping */
                        word-wrap: break-word; /* Break words when needed */
                        font-size: 1px !important; /* Adjust font size */
                        line-height: 1.2; /* Add spacing between lines */
                        text-align: center; /* Center align text */
                        padding: 8px 10px; /* Add padding for better UI */
                        height: auto; /* Resize height dynamically */
                    }
                    </style>
                    """, unsafe_allow_html=True)
                if st.button("➕ Start\nNew\nChat",
                key="start_new_chat", use_container_width=True):
                    if title:
                        st.session_state.selected_conv = manager.create_conversation(title)
                        st.session_state.show_title_input = False
                        st.rerun()

        conversations = manager.list_conversations()
        if conversations:
            st.session_state.selected_conv = st.selectbox(
                "Select Chat",
                conversations,
                index=conversations.index(
                    st.session_state.selected_conv) if st.session_state.selected_conv in conversations else 0
            )

            if st.session_state.selected_conv:
                st.session_state.ai_service = st.radio("AI Service", ["Claude", "ChatGPT", "DALL-E", "Gemini"])

                if st.session_state.ai_service == "Claude":
                    model = st.selectbox("Model", list(manager.CLAUDE_MODELS.values()))
                    model_key = [k for k, v in manager.CLAUDE_MODELS.items() if v == model][0]
                elif st.session_state.ai_service == "ChatGPT":
                    model = st.selectbox("Model", list(manager.GPT_MODELS.values()))
                    model_key = [k for k, v in manager.GPT_MODELS.items() if v == model][0]
                elif st.session_state.ai_service == "DALL-E":
                    model = st.selectbox("Model", list(manager.DALLE_MODELS.values()))
                    model_key = [k for k, v in manager.DALLE_MODELS.items() if v == model][0]
                    size = st.selectbox("Image Size", ["1024x1024", "512x512"])
                else:
                    model = st.selectbox("Model", list(manager.GEMINI_MODELS.values()))
                    model_key = [k for k, v in manager.GEMINI_MODELS.items() if v == model][0]

    # Main content area
    if st.session_state.selected_conv:
        conversation = manager.get_conversation(st.session_state.selected_conv)
        st.caption(f"Current Chat: {conversation['title']}")

        # Export buttons
        export_col1, export_col2, export_col3, export_col4 = st.columns(4)
        with export_col1:
            if st.button("Export JSON"):
                content = manager.export_conversation(st.session_state.selected_conv, "json")
                if content:
                    st.download_button("Download JSON", content, f"{st.session_state.selected_conv}.json")
        with export_col2:
            if st.button("Export Chat"):
                content = manager.export_conversation(st.session_state.selected_conv, "txt")
                if content:
                    st.download_button("Download Chat", content, f"{st.session_state.selected_conv}.txt")
        with export_col3:
            if st.button("Export Code"):
                code_msgs = manager.extract_code_messages(st.session_state.selected_conv)
                if code_msgs:
                    options = [f"Message {i}: {msg['content'][:50]}..." for i, msg in code_msgs]
                    selected = st.multiselect("Select code to export:", options)
                    if selected and st.button("Export Selected"):
                        indices = [code_msgs[i][0] for i in range(len(code_msgs)) if options[i] in selected]
                        exported = manager.export_selected_code(st.session_state.selected_conv, indices)
                        st.success(f"Exported {len(exported)} code snippets")
        with export_col4:
            if st.button("Export Images"):
                conversation = manager.get_conversation(st.session_state.selected_conv)
                image_messages = [msg for msg in conversation['messages'] if msg.get('image_data')]
                if image_messages:
                    for i, msg in enumerate(image_messages):
                        filename = f"image_{i}.png"
                        if msg.get('image_data'):
                            st.download_button(
                                f"Download {filename}",
                                base64.b64decode(msg['image_data']),
                                filename,
                                mime="image/png",
                                key=f"download_img_{i}"
                            )

        if uploaded_files and submit_button:
            try:
                stored_files = handle_multiple_files(uploaded_files, manager)
                if st.session_state.selected_conv:
                    analysis_results = []
                    for file in stored_files:
                        if file['type'] == 'image':
                            analysis = f"Image file uploaded: {file['name']} (Format: {file['format']})"
                            analysis_results.append({
                                'name': file['name'],
                                'language': 'image',
                                'analysis': analysis
                            })
                        else:
                            analysis = manager.analyze_code(file['content'], file['language'])
                            analysis_results.append({
                                'name': file['name'],
                                'language': file['language'],
                                'analysis': analysis
                            })

                        metadata_message = f"File uploaded: {file['name']} ({file['type']})"
                        manager.add_message(st.session_state.selected_conv, metadata_message, "user")

                        if file['type'] == 'text':
                            manager.log_file_analysis(file['name'], file['language'], analysis)

                    st.session_state.analysis_results = analysis_results
                    st.success("Files successfully uploaded.")

                    for file in stored_files:
                        if file['type'] == 'image':
                            st.image(base64.b64decode(file['content']),
                                     caption=file['name'],
                                     use_container_width=True)

            except Exception as e:
                st.error(f"Error: {e}")

        if st.session_state.analysis_results:
            with st.expander("View Analysis Results"):
                for result in st.session_state.analysis_results:
                    st.markdown(f"**Analysis for {result['name']} ({result['language']}):**\n{result['analysis']}")

        # Token counting
        total_tokens = claude_tokens = gpt_tokens = dalle_tokens = gemini_tokens = input_tokens = 0

        # Display messages and count tokens
        for msg in conversation['messages']:
            with st.chat_message(msg['sender']):
                if msg.get('image_data'):
                    st.image(base64.b64decode(msg['image_data']), use_container_width=True)
                st.write(msg['content'])

                tokens = msg.get('tokens', 0)
                total_tokens += tokens

                # Count tokens based on message type
                if msg['sender'] == 'user':
                    input_tokens += tokens

                # Count AI service tokens
                if msg.get('ai_service') == 'claude':
                    claude_tokens += tokens
                elif msg.get('ai_service') == 'chatgpt':
                    gpt_tokens += tokens
                elif msg.get('ai_service') == 'dalle':
                    dalle_tokens += tokens
                elif msg.get('ai_service') == 'gemini':
                    gemini_tokens += tokens

                st.caption(f"Model: {msg.get('model', 'user')} | Tokens: {tokens}")

        # Token display in sidebar
        with st.sidebar:

            st.divider()
            st.markdown("""
                    <style>
                    /* Token display in sidebar (ensures wrapping and better layout) */
                    .ai-service-box small {
                        white-space: normal; /* Wrap text dynamically */
                        word-wrap: break-word; /* Break long words if needed */
                        overflow: hidden; /* Prevent overflow */
                        text-overflow: ellipsis; /* Add "..." if content overflows */
                        font-size: 10px !important; /* Adjust font size for compact look */
                    }

                    .ai-service-box h3 {
                        font-size: 16px !important; /* Header size for services */
                        text-align: center; /* Center-align service headers */
                    }

                    /* Optional: Add spacing and visual separation within columns */
                    .st-column {
                        padding-left: 5px;
                        padding-right: 5px;
                    }
                    </style>
                """, unsafe_allow_html=True)

            # First row: AI Services
            cols_services = st.columns(4)
            with cols_services[0]:
                st.markdown("<div class='ai-service-box'><small>Claude</small></div>", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='ai-service-box'><small>{claude_tokens if 'claude_tokens' in locals() else 0}</small></div>",
                    unsafe_allow_html=True)
            with cols_services[1]:
                st.markdown("<div class='ai-service-box'><small>ChatGPT</small></div>", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='ai-service-box'><small>{gpt_tokens if 'gpt_tokens' in locals() else 0}</small></div>",
                    unsafe_allow_html=True)
            with cols_services[2]:
                st.markdown("<div class='ai-service-box'><small>DALL-E</small></div>", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='ai-service-box'><small>{dalle_tokens if 'dalle_tokens' in locals() else 0}</small></div>",
                    unsafe_allow_html=True)
            with cols_services[3]:
                st.markdown("<div class='ai-service-box'><small>Gemini</small></div>", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='ai-service-box'><small>{gemini_tokens if 'gemini_tokens' in locals() else 0}</small></div>",
                    unsafe_allow_html=True)
            st.divider()
            # Second row: Input and Total with larger text
            cols_totals = st.columns(2)
            with cols_totals[0]:
                st.markdown("**Input**")
                st.markdown(f"### {input_tokens if 'input_tokens' in locals() else 0}")
            with cols_totals[1]:
                st.markdown("**Total**")
                st.markdown(f"### {total_tokens if 'total_tokens' in locals() else 0}")

        # Chat input and message handling
        prompt = st.chat_input("Message")
        if prompt:
            if st.session_state.ai_service == "DALL-E":
                image_data = manager.generate_image_dalle(
                    st.session_state.selected_conv,
                    prompt,
                    model=model_key,
                    size=size
                )
                if image_data:
                    st.rerun()
            elif st.session_state.ai_service == "Claude":
                response = manager.send_to_claude(st.session_state.selected_conv, prompt, model_key)
            elif st.session_state.ai_service == "ChatGPT":
                response = manager.send_to_chatgpt(st.session_state.selected_conv, prompt, model_key)
            else:
                response = manager.send_to_gemini(st.session_state.selected_conv, prompt, model_key)
            if response:
                st.rerun()

    if st.session_state.show_code_popup:
        with st.expander("Code Viewer"):
            code_content = open(__file__, 'r').read()
            st.markdown(f"**File Name:** {__file__}")
            st.text_area("Code", code_content, height=400)


if __name__ == "__main__":
    main()


def display_code_popup():
    code_content = open(__file__, 'r').read()
    html_content = f"""
    <div id="popup-container" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
    background-color: rgba(0, 0, 0, 0.5); z-index: 9999; display: flex; justify-content: center; align-items: center;">
        <div style="background-color: white; padding: 20px; border-radius: 10px; width: 80%; max-height: 80%; 
        overflow: auto; position: relative;">
            <button id="close-btn" style="position: absolute; top: 10px; right: 10px; background-color: red; color: 
            white; border: none; border-radius: 5px; cursor: pointer;">Close</button>
            <button id="copy-btn" style="position: absolute; top: 10px; left: 10px; background-color: blue; color: 
            white; border: none; border-radius: 5px; cursor: pointer;">Copy</button>"""