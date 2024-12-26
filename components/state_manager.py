import streamlit as st
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from config.app_config import AppConfig


class StateManager:
    def __init__(self):
        self.config = AppConfig
        self._initialize_session_state()

    def _initialize_session_state(self) -> None:
        """Initialize default session state values."""
        defaults = {
            'show_title_input': True,
            'selected_conv': None,
            'messages': [],
            'ai_service': 'Claude',
            'analysis_results': [],
            'show_code_popup': False,
            'theme': 'Pastel Delight',
            'clipboard_image': None,
            'model_key': None,
            'token_count': 0,
            'error_count': 0,
            'last_update': datetime.now().isoformat()
        }

        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get value from session state with optional default."""
        return st.session_state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """Set value in session state."""
        st.session_state[key] = value
        st.session_state.last_update = datetime.now().isoformat()

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update multiple session state values."""
        for key, value in updates.items():
            self.set_state(key, value)

    def clear_state(self, keys: Optional[List[str]] = None) -> None:
        """Clear specified keys or entire session state."""
        if keys:
            for key in keys:
                if key in st.session_state:
                    del st.session_state[key]
        else:
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            self._initialize_session_state()

    def increment_counter(self, key: str, amount: int = 1) -> int:
        """Increment a numeric session state value."""
        current_value = self.get_state(key, 0)
        new_value = current_value + amount
        self.set_state(key, new_value)
        return new_value

    def add_to_list(self, key: str, value: Any) -> List:
        """Add value to a list in session state."""
        current_list = self.get_state(key, [])
        if not isinstance(current_list, list):
            current_list = []
        current_list.append(value)
        self.set_state(key, current_list)
        return current_list

    def remove_from_list(self, key: str, value: Any) -> List:
        """Remove value from a list in session state."""
        current_list = self.get_state(key, [])
        if not isinstance(current_list, list):
            return []

        if value in current_list:
            current_list.remove(value)
            self.set_state(key, current_list)
        return current_list

    def get_conversation_state(self) -> Dict[str, Any]:
        """Get current conversation state."""
        return {
            'selected_conv': self.get_state('selected_conv'),
            'ai_service': self.get_state('ai_service'),
            'model_key': self.get_state('model_key'),
            'token_count': self.get_state('token_count'),
            'messages': self.get_state('messages', [])
        }

    def update_conversation_state(self, updates: Dict[str, Any]) -> None:
        """Update conversation-specific state values."""
        allowed_keys = {
            'selected_conv', 'ai_service', 'model_key',
            'token_count', 'messages'
        }
        valid_updates = {
            k: v for k, v in updates.items() if k in allowed_keys
        }
        self.update_state(valid_updates)

    def get_ui_state(self) -> Dict[str, Any]:
        """Get current UI state values."""
        return {
            'show_title_input': self.get_state('show_title_input'),
            'show_code_popup': self.get_state('show_code_popup'),
            'theme': self.get_state('theme'),
            'analysis_results': self.get_state('analysis_results', [])
        }

    def update_ui_state(self, updates: Dict[str, Any]) -> None:
        """Update UI-specific state values."""
        allowed_keys = {
            'show_title_input', 'show_code_popup',
            'theme', 'analysis_results'
        }
        valid_updates = {
            k: v for k, v in updates.items() if k in allowed_keys
        }
        self.update_state(valid_updates)

    def save_clipboard_image(self, image_data: str) -> None:
        """Save clipboard image data to state."""
        self.set_state('clipboard_image', image_data)

    def clear_clipboard_image(self) -> None:
        """Clear clipboard image data from state."""
        if 'clipboard_image' in st.session_state:
            del st.session_state['clipboard_image']

    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes in the current state."""
        last_save = self.get_state('last_save')
        last_update = self.get_state('last_update')

        if not last_save or not last_update:
            return False

        return datetime.fromisoformat(last_update) > datetime.fromisoformat(last_save)

    def mark_as_saved(self) -> None:
        """Mark current state as saved."""
        self.set_state('last_save', datetime.now().isoformat())

    def get_state_snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of the entire current state."""
        return dict(st.session_state)

    def restore_state_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Restore state from a snapshot."""
        self.clear_state()
        self.update_state(snapshot)

    def validate_state(self) -> List[str]:
        """Validate current state and return any issues."""
        issues = []
        required_keys = {
            'show_title_input': bool,
            'ai_service': str,
            'messages': list,
            'theme': str
        }

        for key, expected_type in required_keys.items():
            value = self.get_state(key)
            if value is None:
                issues.append(f"Missing required state key: {key}")
            elif not isinstance(value, expected_type):
                issues.append(
                    f"Invalid type for {key}: expected {expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )

        return issues