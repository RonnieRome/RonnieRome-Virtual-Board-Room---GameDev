from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple
from pathlib import Path
import json
import pickle
from threading import Lock
from config.app_config import AppConfig


class CacheService:
    def __init__(self):
        self.config = AppConfig
        self.cache_dir = self.config.BASE_DIR / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache with locks for thread safety
        self.memory_cache: Dict[str, Dict] = {}
        self.cache_locks: Dict[str, Lock] = {}

        # Load existing cache entries
        self._load_persistent_cache()

    def _load_persistent_cache(self) -> None:
        """Load cached entries from persistent storage into memory."""
        try:
            for cache_file in self.cache_dir.glob('*.cache'):
                try:
                    with open(cache_file, 'rb') as f:
                        entry = pickle.load(f)
                        if not self._is_expired(entry):
                            cache_key = cache_file.stem  # Remove .cache extension
                            self.memory_cache[cache_key] = entry
                        else:
                            cache_file.unlink()  # Remove expired cache files
                except Exception as e:
                    print(f"Error loading cache file {cache_file}: {str(e)}")
                    try:
                        cache_file.unlink()  # Remove corrupted cache files
                    except:
                        pass
        except Exception as e:
            print(f"Error loading persistent cache: {str(e)}")

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if a cache entry is expired."""
        return datetime.now() > entry['expires_at']

    def _make_cache_key(self, key: str, namespace: str) -> str:
        """Create a cache key combining namespace and key."""
        return f"{namespace}:{key}"

    def _get_cache_file(self, cache_key: str) -> Path:
        """Get the cache file path for a given key."""
        return self.cache_dir / f"{cache_key}.cache"

    def _get_lock(self, cache_key: str) -> Lock:
        """Get or create a lock for a cache key."""
        if cache_key not in self.cache_locks:
            self.cache_locks[cache_key] = Lock()
        return self.cache_locks[cache_key]

    def _remove_from_memory(self, cache_key: str) -> bool:
        """Remove an entry from memory cache."""
        return self.memory_cache.pop(cache_key, None) is not None

    def _remove_from_persistent_cache(self, cache_key: str) -> bool:
        """Remove an entry from persistent cache."""
        cache_file = self._get_cache_file(cache_key)
        try:
            if cache_file.exists():
                cache_file.unlink()
                return True
        except Exception as e:
            print(f"Error removing cache file {cache_file}: {str(e)}")
        return False

    def _save_to_persistent_cache(self, cache_key: str, entry: Dict[str, Any]) -> None:
        """Save a cache entry to persistent storage."""
        cache_file = self._get_cache_file(cache_key)
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)
        except Exception as e:
            print(f"Error saving cache file {cache_file}: {str(e)}")

    def cleanup_expired(self) -> None:
        """Remove all expired cache entries."""
        # Cleanup memory cache
        expired_keys = [
            key for key, entry in self.memory_cache.items()
            if self._is_expired(entry)
        ]
        for key in expired_keys:
            self._remove_from_memory(key)

        # Cleanup persistent cache
        try:
            for cache_file in self.cache_dir.glob('*.cache'):
                try:
                    with open(cache_file, 'rb') as f:
                        entry = pickle.load(f)
                        if self._is_expired(entry):
                            cache_file.unlink()
                except Exception:
                    # Remove corrupted cache files
                    try:
                        cache_file.unlink()
                    except:
                        pass
        except Exception as e:
            print(f"Error during cache cleanup: {str(e)}")