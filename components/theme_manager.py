import streamlit as st
from typing import Dict, Optional, Any
from pathlib import Path
import base64
from config.styles import StyleConfig

class ThemeManager:
    def __init__(self):
        self.style_config = StyleConfig
        self.background_dir = Path("backgrounds")
        self.background_dir.mkdir(exist_ok=True)

    def apply_theme(self, theme_choice: str,
                    background_choice: Optional[str] = None) -> None:
        """Apply selected theme and background."""
        # Apply theme CSS
        theme_css = self.style_config.get_theme_css(theme_choice)
        st.markdown(theme_css, unsafe_allow_html=True)

        # Apply font style
        font_style = self.style_config.get_font_style(theme_choice)
        st.markdown(font_style, unsafe_allow_html=True)

        # Apply background if selected
        if background_choice and background_choice != "None":
            self.apply_background(background_choice)

    def apply_background(self, background_name: str) -> None:
        """Apply selected background image."""
        try:
            bg_path = self.background_dir / background_name
            if not bg_path.exists():
                return

            bg_base64 = self._get_base64_image(bg_path)
            self._apply_background_css(bg_base64)

        except Exception as e:
            print(f"Error applying background: {str(e)}")
            self._apply_default_background()

    def get_available_backgrounds(self) -> list:
        """Get list of available background images."""
        return [
            f.name for f in self.background_dir.glob("*.{jpg,jpeg,png}")
        ]

    def get_available_themes(self) -> list:
        """Get list of available themes."""
        return list(self.style_config.THEMES.keys())

    def save_theme_preference(self, theme_choice: str,
                              background_choice: Optional[str] = None) -> None:
        """Save user's theme preferences."""
        st.session_state.theme = theme_choice
        if background_choice:
            st.session_state.background = background_choice

    def get_current_theme(self) -> Dict[str, str]:
        """Get current theme settings."""
        return {
            'theme': st.session_state.get('theme', 'None'),
            'background': st.session_state.get('background', 'None')
        }

    def _get_base64_image(self, image_path: Path) -> str:
        """Convert image to base64 string."""
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()

    def _apply_background_css(self, bg_base64: str) -> None:
        """Apply background image CSS."""
        st.markdown(
            f"""
            <style>
            .stApp::before {{
                content: "";
                background-image: url("data:image/png;base64,{bg_base64}");
                background-size: cover;
                background-repeat: no-repeat;
                background-attachment: fixed;
                background-position: center;
                opacity: 0.7;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                z-index: -1;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

    def _apply_default_background(self) -> None:
        """Apply default background style."""
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

    def customize_theme(self, theme_name: str,
                        custom_styles: Dict[str, str]) -> None:
        """Apply custom styles to an existing theme."""
        base_theme = self.style_config.THEMES.get(theme_name,
                                                  self.style_config.THEMES['None'])

        custom_css = []
        for selector, styles in custom_styles.items():
            style_str = '; '.join([f'{k}: {v}' for k, v in styles.items()])
            custom_css.append(f'{selector} {{ {style_str} }}')

        combined_css = base_theme + '\n' + '\n'.join(custom_css)
        st.markdown(combined_css, unsafe_allow_html=True)

    def create_custom_theme(self, theme_name: str,
                            theme_config: Dict[str, Any]) -> None:
        """Create a new custom theme."""
        custom_theme = f"""
        <style>
        .stApp {{
            background-color: {theme_config.get('background_color', '#ffffff')}CC;
            color: {theme_config.get('text_color', '#000000')};
        }}
        .stButton>button {{
            background-color: {theme_config.get('button_color', '#E0E0E0')} !important;
            color: {theme_config.get('button_text_color', '#333333')} !important;
            border: 1px solid {theme_config.get('button_border_color', '#CCCCCC')} !important;
            font-size: 14px;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        .stButton>button:hover {{
            background-color: {theme_config.get('button_hover_color', '#D0D0D0')} !important;
        }}
        </style>
        """

        self.style_config.THEMES[theme_name] = custom_theme