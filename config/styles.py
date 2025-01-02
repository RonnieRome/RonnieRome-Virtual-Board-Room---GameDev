class StyleConfig:
    THEMES = {
        "Pure Black": """
        <style>
        .stApp {
            background-color: #000000FF;
            color: #C0C0C0;
        }
        .stButton>button {
            background-color: #F28C8C !important;
            color: #FFFFFF !important;
            border: 1px solid #E57373 !important;
            font-size: 14px;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #FF787C !important;
        }
        </style>
        """,

        "Saturn": """
        <style>
        .stApp {
            background: repeating-linear-gradient(
                0deg,
                #ADD8E6 0%,
                #ADD8E6 60%,
                #9370DB 60%,
                #9370DB 85%,
                #FFFFE0 85%,
                #FFFFE0 93%,
                #FFFFFF 93%,
                #FFFFFF 100%
            );
            color: #000080;
        }
        .stButton>button {
            background-color: #FFB6A3 !important;
            color: #7d4e57 !important;
            border: 1px solid #d8a9a3 !important;
            font-size: 14px;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #FFA088 !important;
        }
        </style>
        """,

        "Minty Green": """
        <style>
        .stApp {
            background-color: #98FB98CC;
            color: #006400;
        }
        .stButton>button {
            background-color: #A8D8F0 !important;
            color: #37474f !important;
            border: 1px solid #b0c4de !important;
            font-size: 14px;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #95C9DE !important;
        }
        </style>
        """,

        "G 'n' R": """
        <style>
        .stApp {
            background-color: #FF007F;
            color: #000000;
        }
        .stButton>button {
            background-color: #FF548F !important;
            color: #000000 !important;
            border: 1px solid #F02B6C !important;
            font-size: 14px;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #FF236C !important;
        }
        </style>
        """,

        "Transparent": """
    <style>
    .stApp {
        background-color: transparent;
    }
    .stButton>button {
        background-color: #E0E0E0 !important;
        color: #333333 !important;
        border: 1px solid #CCCCCC !important;
        font-size: 14px;
        padding: 6px 12px;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #D0D0D0 !important;
    }
    </style>
    """
    }

    FONT_MAP = {
        "Pure Black": "'Comic Sans MS', cursive",
        "Saturn": "'Georgia', serif",
        "Minty Green": "'Lato', sans-serif",
        "Transparent": "'Arial', sans-serif",
        "G 'n' R": "'Courier New', monospace"
    }

    @classmethod
    def get_theme_css(cls, theme_name):
        """Get CSS for a specific theme."""
        return cls.THEMES.get(theme_name, cls.THEMES["Transparent"])

    @classmethod
    def get_font_style(cls, theme_name):
        """Get font style for a specific theme."""
        font = cls.FONT_MAP.get(theme_name, cls.FONT_MAP["Transparent"])
        return f"""
        <script>
            var styleSheet = document.createElement("style");
            styleSheet.textContent = `
                * {{
                    font-family: {font} !important;
                }}
            `;
            document.head.appendChild(styleSheet);
        </script>
        """