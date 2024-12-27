import logging
from dataclasses import dataclass
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


@dataclass
class StyleConfig:
    """Configuration for an AI style including prompts and formatting rules."""
    name: str
    system_prompt: str
    formatting_rules: Dict[str, str]
    token_multiplier: float = 1.0  # Multiplier for token estimation with this style


class AIStyleManager:
    """Enhanced manager for AI response styles and their associated configurations."""

    STYLE_CONFIGS = {
        "Business": StyleConfig(
            name="Business",
            system_prompt="""You are a business professional AI assistant. Approach all responses with:
- Professional business language and terminology
- Strategic thinking focused on business impact
- Clear structure emphasizing key business metrics
- Practical recommendations aligned with business goals
- Industry-relevant examples and case studies
Always write in full sentences and paragraphs unless specifically asked for lists.""",
            formatting_rules={
                "text_format": "professional",
                "paragraph_style": "business",
                "code_style": "documented"
            },
            token_multiplier=1.2  # Business style might be more verbose
        ),

        "Engineer": StyleConfig(
            name="Engineer",
            system_prompt="""You are an engineering-focused AI assistant. Approach all responses with:
- Technical precision and systematic analysis
- Implementation-focused solutions
- Architecture and system design considerations
- Performance and scalability mindset
- Detailed technical documentation
Write all explanations in clear paragraphs with thorough comments for technical content.""",
            formatting_rules={
                "text_format": "technical",
                "paragraph_style": "detailed",
                "code_style": "extensively_documented"
            },
            token_multiplier=1.3  # Technical content needs more explanation
        ),

        "Executive": StyleConfig(
            name="Executive",
            system_prompt="""You are an executive-level AI assistant. Approach all responses with:
- Strategic, high-level perspective
- Focus on key decisions and outcomes
- Clear actionable recommendations
- Concise yet comprehensive analysis
- Business impact and risk assessment
Present information in well-structured paragraphs focusing on critical insights.""",
            formatting_rules={
                "text_format": "concise",
                "paragraph_style": "executive",
                "code_style": "summarized"
            },
            token_multiplier=0.9  # Executive style tends to be more concise
        ),

        "Professor": StyleConfig(
            name="Professor",
            system_prompt="""You are a professor-like AI assistant. Approach all responses with:
- Clear, thorough explanations building from fundamentals
- Logical progression from basic to advanced concepts
- Real-world examples and practical applications
- Connection between different ideas and principles
- Anticipation and addressing of potential questions
Write in complete, educational paragraphs that build understanding.""",
            formatting_rules={
                "text_format": "educational",
                "paragraph_style": "structured",
                "code_style": "tutorial"
            },
            token_multiplier=1.4  # Educational content requires more explanation
        )
    }

    @classmethod
    def get_style_config(cls, style: str) -> StyleConfig:
        """Get the complete style configuration for a given style."""
        if style not in cls.STYLE_CONFIGS:
            logger.warning(f"Style '{style}' not found, using default configuration")
            return cls.STYLE_CONFIGS["Professor"]  # Default to Professor style
        return cls.STYLE_CONFIGS[style]

    @classmethod
    def format_messages_for_service(cls,
                                    messages: List[Dict],
                                    style: str,
                                    service: str,
                                    include_formatting: bool = True) -> List[Dict]:
        """Format messages according to service requirements and selected style."""
        try:
            style_config = cls.get_style_config(style)

            # Add service-specific modifications
            service_prompts = {
                "dalle": "\nPlease generate images that reflect this style and approach.",
                "claude": "\nMaintain this style while providing detailed explanations.",
                "chatgpt": "\nApply this style consistently across all responses.",
                "gemini": "\nEnsure responses align with this style's characteristics."
            }

            system_prompt = style_config.system_prompt
            if service in service_prompts:
                system_prompt += service_prompts[service]

            # Format based on service requirements
            if service in ["claude", "chatgpt"]:
                formatted_messages = [
                    {"role": "system", "content": system_prompt}
                ]

                for msg in messages:
                    formatted_msg = {
                        "role": "assistant" if msg.get('sender') == "assistant" else "user",
                        "content": msg.get('content', '')
                    }
                    if include_formatting and msg.get('sender') == "assistant":
                        formatted_msg["formatting"] = style_config.formatting_rules
                    formatted_messages.append(formatted_msg)

                return formatted_messages

            elif service == "gemini":
                formatted_content = [f"System: {system_prompt}"]
                for msg in messages:
                    role = "Assistant" if msg.get('sender') == "assistant" else "Human"
                    formatted_content.append(f"{role}: {msg.get('content', '')}")
                return formatted_content

            else:
                logger.warning(f"Unsupported service for message formatting: {service}")
                return messages

        except Exception as e:
            logger.error(f"Error formatting messages: {str(e)}")
            return messages

    @classmethod
    def estimate_tokens(cls, text: str, style: str) -> int:
        """Estimate token count considering the selected style."""
        try:
            style_config = cls.get_style_config(style)
            base_tokens = len(text.split())  # Simple estimation
            return int(base_tokens * style_config.token_multiplier)
        except Exception as e:
            logger.error(f"Error estimating tokens: {str(e)}")
            return len(text.split())  # Fallback to basic estimation

    @classmethod
    def get_style_descriptions(cls) -> Dict[str, List[str]]:
        """Get formatted descriptions for all available styles."""
        return {
            "Business": [
                "📈 Professional business communication",
                "🎯 Strategic analysis and metrics",
                "💼 Tailored industry-focused solutions"
            ],
            "Engineer": [
                "🛠️ Technical precision and detail",
                "⚙️ Implementation-focused solutions",
                "📐 System architecture expertise"
            ],
            "Executive": [
                "🎯 Strategic decision-making focus",
                "📊 Concise yet highly comprehensive",
                "⚡ Action-oriented practical insights"
            ],
            "Professor": [
                "📚 Educational and highly thorough",
                "🔍 Fundamental and deep understanding",
                "🌟 Practical and useful applications"
            ]
        }