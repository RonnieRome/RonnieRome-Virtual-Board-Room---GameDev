import logging
import httpx
import base64
from httpx import HTTPError, HTTPStatusError
from datetime import datetime
from typing import Dict, Optional, Any
from config.app_config import AppConfig
from config.ai_style_manager import AIStyleManager

class APIService:
    def __init__(self):
        AppConfig.initialize()
        self.config = AppConfig
        self.style_manager = AIStyleManager()

        # Enhanced rate limits with more granular control
        self.rate_limits = {
            'claude': {
                'requests_per_minute': 60,
                'requests_per_hour': 3600,
                'tokens_per_minute': 100000,
                'current_requests': 0,
                'current_tokens': 0,
                'last_reset': datetime.now(),
                'multimodal_enabled': True  # Tracks image analysis capability
            },
            'chatgpt': {
                'requests_per_minute': 50,
                'requests_per_hour': 3000,
                'tokens_per_minute': 90000,
                'current_requests': 0,
                'current_tokens': 0,
                'last_reset': datetime.now(),
                'multimodal_enabled': True  # For GPT-4V
            },
            'dalle': {
                'requests_per_minute': 30,
                'requests_per_hour': 1800,
                'current_requests': 0,
                'last_reset': datetime.now(),
                'image_generation': True  # Specifically for image generation
            },
            'gemini': {
                'requests_per_minute': 45,
                'requests_per_hour': 2700,
                'tokens_per_minute': 80000,
                'current_requests': 0,
                'current_tokens': 0,
                'last_reset': datetime.now(),
                'multimodal_enabled': True  # For Gemini Pro Vision
            }
        }

        # Initialize HTTP client with improved timeout and retry settings
        self.client = httpx.Client(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
        self._initialize_api_keys()

    def send_claude_request(self, prompt: str, model: str,
                            max_tokens: Optional[int] = None,
                            image_data: Optional[str] = None,
                            style: str = "Professor") -> Dict:
        """Send a request to Claude API with comprehensive handling of style and media.

        This method provides:
        1. Style-aware message formatting
        2. Image analysis support for compatible models
        3. Token estimation and management
        4. Error handling with detailed feedback

        Args:
            prompt (str): The main text prompt for Claude
            model (str): The specific Claude model to use
            max_tokens (Optional[int]): Maximum tokens for the response
            image_data (Optional[str]): Base64 encoded image for analysis
            style (str): The conversation style to apply

        Returns:
            Dict: The formatted response from Claude

        Raises:
            ValueError: For invalid inputs or unsupported operations
            RuntimeError: For API-related issues or rate limit violations
        """
        try:
            # Validate inputs and check capabilities
            if not prompt:
                raise ValueError("Prompt cannot be empty")

            if image_data and not self.rate_limits['claude']['multimodal_enabled']:
                raise ValueError(f"Image analysis not supported for model: {model}")

            # Get style configuration and prepare system prompt
            style_config = self.style_manager.get_style_config(style)
            enhanced_system_prompt = self._enhance_system_prompt(
                style_config.system_prompt,
                model,
                'claude'
            )

            # Prepare message content
            if image_data:
                message_content = [
                    {
                        'type': 'text',
                        'text': prompt
                    },
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': self._detect_image_type(image_data),
                            'data': image_data
                        }
                    }
                ]
            else:
                message_content = prompt

            # Construct the complete request data
            data = {
                'model': model,
                'max_tokens': max_tokens or self.config.DEFAULT_MAX_TOKENS,
                'messages': [{
                    'role': 'user',
                    'content': message_content
                }],
                'system': enhanced_system_prompt
            }

            # Send request with proper error handling
            response = self.send_request('claude', 'messages', data=data)

            # Process and validate response
            if not response or 'error' in response:
                raise RuntimeError(f"Invalid response from Claude: {response.get('error', 'Unknown error')}")

            # Update token tracking
            estimated_tokens = self.style_manager.estimate_tokens(prompt, style)
            self._update_token_count('claude', estimated_tokens)

            return response

        except ValueError as ve:
            logging.error(f"Validation error in Claude request: {str(ve)}")
            raise
        except RuntimeError as re:
            logging.error(f"Runtime error in Claude request: {str(re)}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in Claude request: {str(e)}")
            raise RuntimeError(f"Error processing Claude request: {str(e)}")


    def send_chatgpt_request(self, prompt: str, model: str,
                             max_tokens: Optional[int] = None,
                             image_data: Optional[str] = None,
                             style: str = "Professor") -> Dict:
        """Send a request to ChatGPT API with enhanced capabilities and error handling.

        This method handles both text and image analysis (for GPT-4V) while maintaining
        consistent style formatting and proper error management. It provides detailed
        monitoring and ensures efficient token usage.

        For image analysis, it specifically supports the GPT-4V model, handling the
        image data appropriately within OpenAI's API requirements. The method includes
        comprehensive validation and error handling to ensure reliable operation.
        """
        try:
            # First, let's validate our inputs to ensure they're appropriate
            if not prompt:
                raise ValueError("A prompt is required for ChatGPT requests")

            # Check if we're attempting image analysis with a non-vision model
            if image_data and not "gpt-4" in model:
                raise ValueError(
                    "Image analysis is only supported with GPT-4V models. "
                    "Please either use a GPT-4V model or remove the image from your request."
                )

            # Get and enhance our style configuration
            style_config = self.style_manager.get_style_config(style)
            enhanced_system_prompt = self._enhance_system_prompt(
                style_config.system_prompt,
                model,
                'chatgpt'
            )

            # Prepare our message content based on whether we have an image
            messages = [
                {
                    'role': 'system',
                    'content': enhanced_system_prompt
                }
            ]

            if image_data and "gpt-4" in model:
                messages.append({
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': prompt
                        },
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f"data:image/jpeg;base64,{image_data}",
                                'detail': 'high'
                            }
                        }
                    ]
                })
            else:
                messages.append({
                    'role': 'user',
                    'content': prompt
                })

            # Construct our complete request data
            data = {
                'model': model,
                'messages': messages,
                'max_tokens': max_tokens or self.config.DEFAULT_MAX_TOKENS,
                'temperature': 0.7  # Balanced between creativity and precision
            }

            # Send the request with proper error handling
            response = self.send_request('chatgpt', 'chat/completions', data=data)

            # Validate our response
            if not response or 'choices' not in response:
                raise RuntimeError("Invalid response received from ChatGPT API")

            # Update our token tracking
            estimated_tokens = self.style_manager.estimate_tokens(prompt, style)
            self._update_token_count('chatgpt', estimated_tokens)

            return response

        except ValueError as ve:
            logging.error(f"Validation error in ChatGPT request: {str(ve)}")
            raise
        except RuntimeError as re:
            logging.error(f"Runtime error in ChatGPT request: {str(re)}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in ChatGPT request: {str(e)}")
            raise RuntimeError(f"Error processing ChatGPT request: {str(e)}")


    def send_gemini_request(self, prompt: str, model: str,
                            max_tokens: Optional[int] = None,
                            image_data: Optional[str] = None,
                            style: str = "Professor") -> Dict:
        """Send a request to Gemini API with enhanced capabilities and style handling.

        This implementation provides full support for Gemini's capabilities, including
        multimodal analysis for Gemini Pro Vision. It maintains consistent style
        formatting while respecting Gemini's specific API requirements and provides
        detailed error handling and logging.
        """
        try:
            if not prompt:
                raise ValueError("A prompt is required for Gemini requests")

            # Get and enhance our style configuration
            style_config = self.style_manager.get_style_config(style)
            enhanced_system_prompt = self._enhance_system_prompt(
                style_config.system_prompt,
                model,
                'gemini'
            )

            # Prepare our styled prompt
            styled_prompt = f"{enhanced_system_prompt}\n\nUser Query: {prompt}"

            # Handle multimodal content for Gemini Pro Vision
            if image_data:
                if 'vision' not in model.lower():
                    raise ValueError(
                        "Image analysis requires Gemini Pro Vision. "
                        "Please use an appropriate model or remove the image."
                    )

                data = {
                    'model': model,
                    'contents': [
                        {
                            'parts': [
                                {'text': styled_prompt},
                                {
                                    'inline_data': {
                                        'mime_type': self._detect_image_type(image_data),
                                        'data': image_data
                                    }
                                }
                            ]
                        }
                    ],
                    'max_output_tokens': max_tokens or self.config.DEFAULT_MAX_TOKENS,
                    'temperature': 0.7
                }
            else:
                data = {
                    'model': model,
                    'contents': [{'parts': [{'text': styled_prompt}]}],
                    'max_output_tokens': max_tokens or self.config.DEFAULT_MAX_TOKENS,
                    'temperature': 0.7
                }

            # Send request with enhanced error handling
            response = self.send_request('gemini', 'generateContent', data=data)

            # Process and validate response
            if not response or 'error' in response:
                raise RuntimeError(f"Invalid response from Gemini: {response.get('error', 'Unknown error')}")

            # Update token tracking
            estimated_tokens = self.style_manager.estimate_tokens(prompt, style)
            self._update_token_count('gemini', estimated_tokens)

            return response

        except ValueError as ve:
            logging.error(f"Validation error in Gemini request: {str(ve)}")
            raise
        except RuntimeError as re:
            logging.error(f"Runtime error in Gemini request: {str(re)}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in Gemini request: {str(e)}")
            raise RuntimeError(f"Error processing Gemini request: {str(e)}")

    def send_dalle_request(self, prompt: str, model: str,
                           size: str = "1024x1024",
                           style: str = "Professor",
                           additional_context: Optional[Dict] = None) -> Dict:
        """Send a request to DALL-E API with enhanced style awareness for image generation.

        Unlike Claude, GPT-4V, and Gemini which analyze images, DALL-E generates images.
        This implementation translates style configurations into image generation guidance,
        enhancing the prompts to produce images that align with the selected style's
        characteristics.

        The method includes several key components:
        1. Style-aware prompt enhancement
        2. Quality and consistency controls
        3. Comprehensive error handling
        4. Integration with our token and rate limiting systems

        Here's how the style handling differs from text-based services:
        - Business style emphasizes professional, clean visuals
        - Engineer style focuses on technical accuracy and detail
        - Executive style prioritizes impactful, presentation-ready images
        - Professor style ensures educational clarity and detail
        """
        try:
            # First, validate our basic inputs
            if not prompt:
                raise ValueError("A prompt is required for image generation")

            if size not in ["1024x1024", "512x512", "256x256"]:
                raise ValueError(f"Invalid size: {size}. Must be one of: 1024x1024, 512x512, 256x256")

            # Get style configuration and enhance our prompt
            style_config = self.style_manager.get_style_config(style)

            # Transform style configuration into image-specific guidance
            style_enhancements = self._get_dalle_style_enhancements(style)

            # Enhance the prompt with style-specific guidance
            enhanced_prompt = self._enhance_dalle_prompt(
                prompt,
                style_enhancements,
                additional_context
            )

            # Prepare our request data with enhanced configuration
            data = {
                'model': model,
                'prompt': enhanced_prompt,
                'size': size,
                'quality': "standard",  # Can be adjusted based on style
                'n': 1,  # Number of images to generate
                'style': self._map_style_to_dalle(style)  # Map our style to DALL-E's style parameters
            }

            # Send request with comprehensive error handling
            response = self.send_request('dalle', 'images/generations', data=data)

            # Validate the response
            if not response or 'data' not in response:
                raise RuntimeError("Invalid response received from DALL-E API")

            # Track the request in our rate limiting system
            self._update_request_count('dalle')

            return response

        except ValueError as ve:
            logging.error(f"Validation error in DALL-E request: {str(ve)}")
            raise
        except RuntimeError as re:
            logging.error(f"Runtime error in DALL-E request: {str(re)}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in DALL-E request: {str(e)}")
            raise RuntimeError(f"Error processing DALL-E request: {str(e)}")

    def _get_dalle_style_enhancements(self, style: str) -> Dict[str, str]:
        """Generate style-specific enhancements for DALL-E prompts.

        This method translates our general style configurations into specific
        image generation guidance. Each style gets translated into visual
        characteristics that DALL-E can understand and implement.
        """
        style_enhancements = {
            "Business": {
                "visual_style": "professional and polished",
                "composition": "clean and structured",
                "color_scheme": "professional and balanced",
                "additional_elements": "corporate-appropriate imagery"
            },
            "Engineer": {
                "visual_style": "technical and precise",
                "composition": "detailed and systematic",
                "color_scheme": "clear and functional",
                "additional_elements": "technical details and annotations"
            },
            "Executive": {
                "visual_style": "impactful and presentable",
                "composition": "bold and clear",
                "color_scheme": "high-contrast and memorable",
                "additional_elements": "key visual highlights"
            },
            "Professor": {
                "visual_style": "educational and clear",
                "composition": "well-organized and instructive",
                "color_scheme": "balanced and easy to understand",
                "additional_elements": "educational context and details"
            }
        }

        return style_enhancements.get(style, style_enhancements["Professor"])

    def _enhance_dalle_prompt(self, base_prompt: str,
                              style_enhancements: Dict[str, str],
                              additional_context: Optional[Dict] = None) -> str:
        """Enhance the DALL-E prompt with style-specific elements and context.

        This method carefully combines the user's base prompt with style-specific
        enhancements to create a comprehensive prompt that guides DALL-E in
        generating appropriate images. It ensures the final prompt maintains
        artistic coherence while meeting style requirements.
        """
        # Start with the base prompt
        enhanced_prompt = base_prompt

        # Add style-specific visual guidance
        enhanced_prompt += f", {style_enhancements['visual_style']}"
        enhanced_prompt += f", {style_enhancements['composition']}"

        # Add color and additional elements guidance
        enhanced_prompt += f", using {style_enhancements['color_scheme']} colors"
        enhanced_prompt += f", including {style_enhancements['additional_elements']}"

        # Incorporate any additional context if provided
        if additional_context:
            if 'purpose' in additional_context:
                enhanced_prompt += f", intended for {additional_context['purpose']}"
            if 'audience' in additional_context:
                enhanced_prompt += f", designed for {additional_context['audience']}"

        return enhanced_prompt

    def _map_style_to_dalle(self, style: str) -> str:
        """Map our style categories to DALL-E's internal style parameters.

        This ensures our style choices translate effectively into DALL-E's
        image generation system while maintaining consistency with our
        broader style framework.
        """
        style_mapping = {
            "Business": "natural",
            "Engineer": "vivid",
            "Executive": "vivid",
            "Professor": "natural"
        }

        return style_mapping.get(style, "natural")


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

        except HTTPError as e:
            self._handle_http_error(e, service)
        except Exception as e:
            self._handle_general_error(e, service)

    def _enhance_system_prompt(self, base_prompt: str, model: str, service: str) -> str:
        """Enhance the system prompt with model-specific optimizations.

        This method customizes the prompt based on:
        1. The specific model's capabilities
        2. The service being used
        3. Any special handling requirements
        """
        enhanced_prompt = base_prompt

        # Add model-specific guidance
        if 'claude-3' in model:
            enhanced_prompt += "\nPlease provide detailed, well-structured responses."
        elif 'gpt-4' in model:
            enhanced_prompt += "\nLeverage advanced reasoning capabilities in responses."
        elif 'gemini' in model:
            enhanced_prompt += "\nFocus on clear, practical explanations."

        return enhanced_prompt

    def _detect_image_type(self, image_data: str) -> str:
        """Detect the MIME type of the image from its base64 data."""
        try:
            # Check the first few bytes of the decoded data
            decoded_start = base64.b64decode(image_data)[:8]

            # Common image signatures
            if decoded_start.startswith(b'\xFF\xD8'):
                return 'image/jpeg'
            elif decoded_start.startswith(b'\x89PNG\r\n\x1a\n'):
                return 'image/png'
            elif decoded_start.startswith(b'GIF87a') or decoded_start.startswith(b'GIF89a'):
                return 'image/gif'

            return 'image/jpeg'  # Default to JPEG if uncertain
        except Exception:
            return 'image/jpeg'

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

    def _handle_http_error(self, error: HTTPError, service: str) -> None:
        """Handle HTTP-specific errors."""
        if isinstance(error, HTTPStatusError):
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