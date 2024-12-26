class StyleConfig:
    THEMES = {
        "Pastel Delight": """
        <style>
        .stApp {
            background-color: #ffefffCC;
            color: #645394;
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

        "Peach Blossom": """
        <style>
        .stApp {
            background-color: #fff5e1CC;
            color: #7d4e57;
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

        "Dreamy Sky": """
        <style>
        .stApp {
            background-color: #e6f7ffCC;
            color: #607d8b;
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

        "None": """
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
        "Pastel Delight": "'Comic Sans MS', cursive",
        "Peach Blossom": "'Georgia', serif",
        "Dreamy Sky": "'Lato', sans-serif",
        "None": "'Arial', sans-serif"
    }

    @classmethod
    def get_theme_css(cls, theme_name):
        """Get CSS for a specific theme."""
        return cls.THEMES.get(theme_name, cls.THEMES["None"])

    @classmethod
    def get_font_style(cls, theme_name):
        """Get font style for a specific theme."""
        font = cls.FONT_MAP.get(theme_name, cls.FONT_MAP["None"])
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