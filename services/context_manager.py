from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from pathlib import Path
from config.app_config import AppConfig


class ContextManager:
    def __init__(self):
        self.config = AppConfig
        self.context_dir = self.config.BASE_DIR / "context"
        self.context_dir.mkdir(parents=True, exist_ok=True)

    def save_conversation_context(self, conversation_id: str, context_data: Dict) -> bool:
        """Save context data for a specific conversation."""
        context_path = self._get_context_path(conversation_id)

        try:
            # Ensure we preserve existing context data
            existing_context = self.get_conversation_context(conversation_id) or {}
            existing_context.update(context_data)

            with open(context_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'conversation_id': conversation_id,
                    'updated_at': datetime.now().isoformat(),
                    'context': existing_context
                }, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving context: {str(e)}")
            return False

    def get_conversation_context(self, conversation_id: str) -> Optional[Dict]:
        """Retrieve context data for a specific conversation."""
        context_path = self._get_context_path(conversation_id)

        if not context_path.exists():
            return None

        try:
            with open(context_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('context')
        except Exception as e:
            print(f"Error loading context: {str(e)}")
            return None

    def update_conversation_context(self, conversation_id: str,
                                    updates: Dict[str, Any]) -> bool:
        """Update specific fields in the conversation context."""
        context = self.get_conversation_context(conversation_id) or {}

        # Update nested dictionary structures
        self._deep_update(context, updates)

        return self.save_conversation_context(conversation_id, context)

    def clear_conversation_context(self, conversation_id: str) -> bool:
        """Clear all context data for a specific conversation."""
        context_path = self._get_context_path(conversation_id)

        if not context_path.exists():
            return True

        try:
            context_path.unlink()
            return True
        except Exception as e:
            print(f"Error clearing context: {str(e)}")
            return False

    def get_active_contexts(self) -> List[str]:
        """Get a list of all conversations with active contexts."""
        return [
            path.stem for path in self.context_dir.glob("*.json")
            if self._is_context_active(path)
        ]

    def merge_contexts(self, source_id: str, target_id: str) -> bool:
        """Merge context data from source conversation into target conversation."""
        source_context = self.get_conversation_context(source_id)
        target_context = self.get_conversation_context(target_id) or {}

        if not source_context:
            return False

        # Merge the contexts with target taking precedence
        merged_context = {**source_context, **target_context}

        return self.save_conversation_context(target_id, merged_context)

    def _get_context_path(self, conversation_id: str) -> Path:
        """Get the file path for a conversation's context data."""
        return self.context_dir / f"{conversation_id}.json"

    def _is_context_active(self, context_path: Path) -> bool:
        """Check if a context is still active based on last update time."""
        try:
            with open(context_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                last_update = datetime.fromisoformat(data.get('updated_at', '2000-01-01T00:00:00'))
                # Consider contexts inactive after 24 hours of no updates
                return (datetime.now() - last_update).total_seconds() < 86400
        except Exception:
            return False

    def _deep_update(self, target: Dict, updates: Dict) -> None:
        """Recursively update nested dictionary structures."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
