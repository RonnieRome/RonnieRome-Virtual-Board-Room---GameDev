"""
Services Package

This package contains core service classes that handle the business logic and data management
for the application. Each service is responsible for a specific domain of functionality.

Available Services:
- ServiceManager: Orchestrates all other services and manages their lifecycle
- ChatManager: Handles chat-related operations and message history
- ContextManager: Manages conversation context and state
- LoggingService: Provides logging functionality across the application
"""

from services.chat_manager import ChatHistoryManager
from services.context_manager import ContextManager
from services.logging_service import LoggingService

__all__ = [
    'ChatHistoryManager',
    'ContextManager',
    'LoggingService'
]