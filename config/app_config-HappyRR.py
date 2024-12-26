import os
from pathlib import Path
from typing import Optional



class AppConfig:
    @classmethod
    def initialize(cls):
        # Load API keys with validation
        cls.CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
        if not cls.CLAUDE_API_KEY:
            print("Warning: CLAUDE_API_KEY not found in environment variables")
            print(f"Available environment variables: {[k for k in os.environ.keys() if 'API' in k]}")
        # Print debug information (remember to remove sensitive info)
        print(f"CLAUDE_API_KEY loaded: {bool(cls.CLAUDE_API_KEY)}")
        if cls.CLAUDE_API_KEY:
            print(f"CLAUDE_API_KEY length: {len(cls.CLAUDE_API_KEY)}")

    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_API_BASE: str = "https://api.anthropic.com/v1"
    DEFAULT_MAX_TOKENS: int = 1000
    CLAUDE_SYSTEM_PROMPT = "You are a helpful AI assistant."

    # Directory Configuration
    BASE_DIR = Path(__file__).parent.parent
    HISTORY_DIR = BASE_DIR / "chat_histories"
    EXPORTS_DIR = BASE_DIR / "exports"
    BACKGROUND_DIR = BASE_DIR / "backgrounds"

    # API Keys (Load from environment variables)
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

    # API Base URLs
    CLAUDE_API_BASE = "https://api.anthropic.com/v1"
    OPENAI_API_BASE = "https://api.openai.com/v1"
    GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1"

    # AI Model Configurations
    CLAUDE_MODELS = {
        "claude-3-sonnet-20240229": "Sonnet",
        "claude-3-opus-20240229": "Opus",
        "claude-3-haiku-20240307": "Haiku"
    }

    GPT_MODELS = {
        "gpt-4": "GPT-4",
        "gpt-3.5-turbo": "GPT-3.5"
    }

    GEMINI_MODELS = {
        "gemini-pro": "Gemini Pro"
    }

    DALLE_MODELS = {
        "dall-e-3": "DALL-E 3",
        "dall-e-2": "DALL-E 2"
    }

    # System Prompts
    CLAUDE_SYSTEM_PROMPT = """You're participating in a group chat. Previous messages and stored files are provided for context. 
    You can reference any stored files in your responses. If an image is shared, please analyze and describe it."""

    CHATGPT_SYSTEM_PROMPT = """You're participating in a group chat. Previous messages are provided for context. Respond naturally."""

    # App Settings
    DEFAULT_AI_SERVICE = "Claude"
    MAX_CONTEXT_MESSAGES = 10
    MAX_CODE_ANALYSIS_LENGTH = 8000
    IMAGE_FORMATS = ["png", "jpg", "jpeg"]
    CODE_FORMATS = ["py", "js", "cs", "txt", "json"]

    # Token Settings
    DEFAULT_MAX_TOKENS = 1024
    TOKEN_PADDING = 200  # Safety margin for token calculations

    # Security Settings
    SESSION_DURATION = 24  # Session duration in hours
    MIN_PASSWORD_LENGTH = 8
    MAX_LOGIN_ATTEMPTS = 3
    TOKEN_EXPIRY_DAYS = 30

    @classmethod
    def initialize_directories(cls):
        """Create necessary directories if they don't exist."""
        for directory in [cls.HISTORY_DIR, cls.EXPORTS_DIR, cls.BACKGROUND_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_model_display_name(cls, model_key, service):
        """Get display name for a model based on service."""
        model_maps = {
            "Claude": cls.CLAUDE_MODELS,
            "ChatGPT": cls.GPT_MODELS,
            "DALL-E": cls.DALLE_MODELS,
            "Gemini": cls.GEMINI_MODELS
        }
        return model_maps.get(service, {}).get(model_key, model_key)

    @classmethod
    def get_supported_file_types(cls):
        """Get list of all supported file types."""
        return cls.IMAGE_FORMATS + cls.CODE_FORMATS

    @classmethod
    def validate_api_keys(cls):
        """Validate that required API keys are set."""
        missing_keys = []
        if not cls.CLAUDE_API_KEY:
            missing_keys.append('CLAUDE_API_KEY')
        if not cls.OPENAI_API_KEY:
            missing_keys.append('OPENAI_API_KEY')
        if not cls.GEMINI_API_KEY:
            missing_keys.append('GEMINI_API_KEY')
        return missing_keys