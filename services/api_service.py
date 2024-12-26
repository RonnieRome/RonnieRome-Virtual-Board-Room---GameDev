import json
import time
import os
import httpx
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple
from config.app_config import AppConfig


class APIService:
    def __init__(self):
        AppConfig.initialize()
        self.config = AppConfig
        print(f"Claude API Key present: {'CLAUDE_API_KEY' in os.environ}")  # Add this line
        self.rate_limits: Dict[str, Dict[str, Any]] = {
            'claude': {
                'requests_per_minute': 60,
                'requests_per_hour': 3600,
                'tokens_per_minute': 100000,
                'current_requests': 0,
                'current_tokens': 0,
                'last_reset': datetime.now()
            },
            'chatgpt': {
                'requests_per_minute': 50,
                'requests_per_hour': 3000,
                'tokens_per_minute': 90000,
                'current_requests': 0,
                'current_tokens': 0,
                'last_reset': datetime.now()
            },
            'dalle': {
                'requests_per_minute': 30,
                'requests_per_hour': 1800,
                'current_requests': 0,
                'last_reset': datetime.now()
            },
            'gemini': {
                'requests_per_minute': 45,
                'requests_per_hour': 2700,
                'tokens_per_minute': 80000,
                'current_requests': 0,
                'current_tokens': 0,
                'last_reset': datetime.now()
            }
        }

        self.client = httpx.Client(timeout=30.0)
        self._initialize_api_keys()

    def send_claude_request(self, prompt: str, model: str,
                            max_tokens: Optional[int] = None,
                            image_data: Optional[str] = None) -> Dict:
        """Send a request to Claude API."""
        data = {
            'model': model,
            'max_tokens': max_tokens or self.config.DEFAULT_MAX_TOKENS,
            'system': self.config.CLAUDE_SYSTEM_PROMPT,
        }

        # Format messages according to Claude API requirements
        if image_data:
            data['messages'] = [{
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': prompt
                    },
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': 'image/png',
                            'data': image_data
                        }
                    }
                ]
            }]
        else:
            data['messages'] = [{
                'role': 'user',
                'content': prompt
            }]

        response = self.send_request('claude', 'messages', data=data)
        self._update_token_count('claude', response.get('usage', {}).get('total_tokens', 0))
        return response

    def send_chatgpt_request(self, prompt: str, model: str,
                             max_tokens: Optional[int] = None) -> Dict:
        """Send a request to ChatGPT API."""
        data = {
            'model': model,
            'messages': [
                {
                    'role': 'system',
                    'content': self.config.CHATGPT_SYSTEM_PROMPT
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': max_tokens or self.config.DEFAULT_MAX_TOKENS
        }

        response = self.send_request('chatgpt', 'chat/completions', data=data)
        self._update_token_count('chatgpt', response.get('usage', {}).get('total_tokens', 0))
        return response


    def send_dalle_request(self, prompt: str, model: str,
                           size: str = "1024x1024") -> Dict:
        """Send a request to DALL-E API."""
        data = {
            'model': model,
            'prompt': prompt,
            'size': size,
            'quality': 'standard',
            'n': 1
        }

        return self.send_request('dalle', 'images/generations', data=data)

    def send_gemini_request(self, prompt: str, model: str,
                            max_tokens: Optional[int] = None) -> Dict:
        """Send a request to Gemini API."""
        data = {
            'model': model,
            'prompt': prompt,
            'max_output_tokens': max_tokens
        }

        response = self.send_request('gemini', 'generateContent', data=data)
        self._update_token_count('gemini', response.get('usage', {}).get('total_tokens', 0))
        return response

    def send_request(self, service: str, endpoint: str,
                     method: str = 'POST', data: Optional[Dict] = None,
                     files: Optional[Dict] = None) -> Dict:
        """Send a request to an external API with rate limiting."""
        if not self._check_rate_limit(service):
            raise RuntimeError(f"Rate limit exceeded for {service}")

        try:
            headers = self._get_headers(service)
            url = self._get_endpoint_url(service, endpoint)

            response = self.client.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                files=files
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            self._handle_http_error(e, service)
        except Exception as e:
            self._handle_general_error(e, service)


    def _initialize_api_keys(self) -> None:
        """Initialize API keys from environment variables."""
        self.api_keys = {
            'claude': self.config.CLAUDE_API_KEY,
            'chatgpt': self.config.OPENAI_API_KEY,
            'gemini': self.config.GEMINI_API_KEY
        }
        if not self.api_keys['claude']:
            raise ValueError("Claude API key not found. Please set CLAUDE_API_KEY in your environment variables.")

    def _get_headers(self, service: str) -> Dict[str, str]:
        """Get appropriate headers for each service."""
        headers = {
            'Content-Type': 'application/json'
        }

        if service == 'claude':
            # Anthropic API requires 'x-api-key' header
            headers.update({
                'x-api-key': self.api_keys['claude'],
                'anthropic-version': '2024-01-01'  # Update to latest version
            })
            print(f"Headers keys present: {list(headers.keys())}")  # Debug line

        elif service in ['chatgpt', 'dalle']:
            # OpenAI APIs use Bearer token
            headers['Authorization'] = f"Bearer {self.api_keys['chatgpt']}"
        elif service == 'gemini':
            # Google APIs use Bearer token
            headers['Authorization'] = f"Bearer {self.api_keys['gemini']}"

        return headers

    def _get_endpoint_url(self, service: str, endpoint: str) -> str:
        """Get full API endpoint URL."""
        """Get full API endpoint URL."""
        base_urls = {
            'claude': self.config.CLAUDE_API_BASE,
            'chatgpt': self.config.OPENAI_API_BASE,
            'dalle': self.config.OPENAI_API_BASE,
            'gemini': f"{self.config.GEMINI_API_BASE}/models"
        }

        return f"{base_urls[service]}/{endpoint}"

    def _check_rate_limit(self, service: str) -> bool:
        """Check if request is within rate limits."""
        self._check_rate_limit_reset(service)
        limits = self.rate_limits[service]

        if limits['current_requests'] >= limits['requests_per_minute']:
            return False

        if 'tokens_per_minute' in limits:
            if limits['current_tokens'] >= limits['tokens_per_minute']:
                return False

        limits['current_requests'] += 1
        return True

    def _check_rate_limit_reset(self, service: str) -> None:
        """Reset rate limit counters if time window has passed."""
        now = datetime.now()
        last_reset = self.rate_limits[service]['last_reset']

        if (now - last_reset).total_seconds() >= 60:
            self.rate_limits[service].update({
                'current_requests': 0,
                'current_tokens': 0,
                'last_reset': now
            })


    def get_rate_limit_status(self, service: str) -> Dict[str, Any]:
        """Get current rate limit status for a service."""
        self._check_rate_limit_reset(service)
        return {
            'requests_remaining': (
                    self.rate_limits[service]['requests_per_minute'] -
                    self.rate_limits[service]['current_requests']
            ),
            'tokens_remaining': (
                    self.rate_limits[service].get('tokens_per_minute', float('inf')) -
                    self.rate_limits[service].get('current_tokens', 0)
            ),
            'reset_in_seconds': self._get_seconds_until_reset(service)
        }

    def _update_token_count(self, service: str, tokens: int) -> None:
        """Update token count for rate limiting."""
        if 'current_tokens' in self.rate_limits[service]:
            self.rate_limits[service]['current_tokens'] += tokens

    def _get_seconds_until_reset(self, service: str) -> int:
        """Get seconds until rate limit reset."""
        now = datetime.now()
        last_reset = self.rate_limits[service]['last_reset']

        return max(0, 60 - int((now - last_reset).total_seconds()))

    def _handle_http_error(self, error: httpx.HTTPError, service: str) -> None:
        """Handle HTTP-specific errors."""
        if isinstance(error, httpx.HTTPStatusError):
            if error.response.status_code == 429:
                raise RuntimeError(f"{service} rate limit exceeded")
            elif error.response.status_code == 401:
                raise RuntimeError(f"Invalid {service} API key")
            elif error.response.status_code == 400:
                raise ValueError(f"Invalid request to {service} API")
            else:
                raise RuntimeError(f"{service} API error: {str(error)}")
        else:
            raise RuntimeError(f"HTTP error with {service} API: {str(error)}")

    def _handle_general_error(self, error: Exception, service: str) -> None:
        """Handle general errors."""
        raise RuntimeError(f"Error calling {service} API: {str(error)}")

    def close(self) -> None:
        """Close HTTP client."""
        self.client.close()