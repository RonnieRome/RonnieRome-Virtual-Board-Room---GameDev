from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from pathlib import Path
import json
import hashlib
import secrets
import base64
from config.app_config import AppConfig


class SecurityService:
    def __init__(self):
        self.config = AppConfig
        self.security_dir = self.config.BASE_DIR / "security"
        self.security_dir.mkdir(parents=True, exist_ok=True)

        self.sessions_file = self.security_dir / "sessions.json"
        self.users_file = self.security_dir / "users.json"
        self.access_tokens_file = self.security_dir / "access_tokens.json"

        # Initialize empty dictionaries first
        self.active_sessions = {}
        self.users = {}
        self.access_tokens = {}

        # Then initialize files and load data
        self._initialize_security_files()
        self.active_sessions.update(self._load_sessions())
        self.users.update(self._load_users())
        self.access_tokens.update(self._load_access_tokens())

    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and return session token if successful."""
        user = self.users.get(username)
        if not user:
            return None

        password_hash = self._hash_password(password, user['salt'])
        if password_hash != user['password_hash']:
            return None

        # Generate and store session token
        session_token = self._generate_token()
        self.active_sessions[session_token] = {
            'username': username,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
        }

        self._save_sessions()
        return session_token

    def validate_session(self, session_token: str) -> Optional[str]:
        """Validate session token and return username if valid."""
        session = self.active_sessions.get(session_token)
        if not session:
            return None

        expires_at = datetime.fromisoformat(session['expires_at'])
        if datetime.now() > expires_at:
            self._remove_session(session_token)
            return None

        return session['username']

    def create_user(self, username: str, password: str,
                    role: str = 'user') -> bool:
        """Create a new user account."""
        if username in self.users:
            return False

        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)

        self.users[username] = {
            'password_hash': password_hash,
            'salt': salt,
            'role': role,
            'created_at': datetime.now().isoformat(),
            'last_login': None
        }

        self._save_users()
        return True

    def update_user_password(self, username: str, current_password: str,
                             new_password: str) -> bool:
        """Update user's password."""
        user = self.users.get(username)
        if not user:
            return False

        current_hash = self._hash_password(current_password, user['salt'])
        if current_hash != user['password_hash']:
            return False

        new_salt = secrets.token_hex(16)
        new_hash = self._hash_password(new_password, new_salt)

        user['password_hash'] = new_hash
        user['salt'] = new_salt

        self._save_users()
        return True

    def create_access_token(self, username: str,
                            permissions: List[str]) -> str:
        """Create an API access token for a user."""
        token = self._generate_token()

        self.access_tokens[token] = {
            'username': username,
            'permissions': permissions,
            'created_at': datetime.now().isoformat(),
            'last_used': None
        }

        self._save_access_tokens()
        return token

    def validate_access_token(self, token: str,
                              required_permission: str) -> bool:
        """Validate API access token and check permissions."""
        token_data = self.access_tokens.get(token)
        if not token_data:
            return False

        if required_permission not in token_data['permissions']:
            return False

        token_data['last_used'] = datetime.now().isoformat()
        self._save_access_tokens()
        return True

    def logout_user(self, session_token: str) -> None:
        """Remove user's session token."""
        self._remove_session(session_token)
        self._save_sessions()

    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information excluding sensitive data."""
        user = self.users.get(username)
        if not user:
            return None

        return {
            'username': username,
            'role': user['role'],
            'created_at': user['created_at'],
            'last_login': user['last_login']
        }

    def _initialize_security_files(self) -> None:
        """Initialize security-related files if they don't exist."""
        if not self.sessions_file.exists():
            self._save_sessions()

        if not self.users_file.exists():
            self._save_users()

        if not self.access_tokens_file.exists():
            self._save_access_tokens()

    def _load_sessions(self) -> Dict[str, Dict]:
        """Load active sessions from file."""
        try:
            with open(self.sessions_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_sessions(self) -> None:
        """Save active sessions to file."""
        with open(self.sessions_file, 'w') as f:
            json.dump(self.active_sessions, f, indent=2)

    def _load_users(self) -> Dict[str, Dict]:
        """Load user data from file."""
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_users(self) -> None:
        """Save user data to file."""
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)

    def _load_access_tokens(self) -> Dict[str, Dict]:
        """Load access tokens from file."""
        try:
            with open(self.access_tokens_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_access_tokens(self) -> None:
        """Save access tokens to file."""
        with open(self.access_tokens_file, 'w') as f:
            json.dump(self.access_tokens, f, indent=2)

    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt using SHA-256."""
        combined = password.encode() + salt.encode()
        return hashlib.sha256(combined).hexdigest()

    def _generate_token(self) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)

    def _remove_session(self, session_token: str) -> None:
        """Remove a session token."""
        self.active_sessions.pop(session_token, None)

    def cleanup_expired_sessions(self) -> None:
        """Remove expired session tokens."""
        current_time = datetime.now()
        expired_tokens = [
            token for token, session in self.active_sessions.items()
            if current_time > datetime.fromisoformat(session['expires_at'])
        ]

        for token in expired_tokens:
            self._remove_session(token)

        if expired_tokens:
            self._save_sessions()

    def rotate_access_tokens(self, max_age_days: int = 30) -> None:
        """Remove unused access tokens older than specified age."""
        cutoff_time = datetime.now() - timedelta(days=max_age_days)

        expired_tokens = [
            token for token, data in self.access_tokens.items()
            if (not data['last_used'] or
                datetime.fromisoformat(data['last_used']) < cutoff_time)
        ]

        for token in expired_tokens:
            self.access_tokens.pop(token)

        if expired_tokens:
            self._save_access_tokens()