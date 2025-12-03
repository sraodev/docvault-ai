"""
AI Provider Factory.

Manages provider selection and initialization based on configuration.
Uses the Factory pattern to provide plug-and-play AI provider support.
"""
from ...core.config import (
    OPENROUTER_API_KEY,
    ANTHROPIC_API_KEY,
    AI_PROVIDER
)
from ...core.logging_config import get_logger
from .base import AIProvider
from .openrouter_provider import OpenRouterProvider
from .anthropic_provider import AnthropicProvider
from .mock_provider import MockProvider

logger = get_logger(__name__)


class AIProviderFactory:
    """
    Factory for creating AI provider instances.
    
    Automatically selects the appropriate provider based on:
    1. AI_PROVIDER configuration
    2. Available API keys
    3. Fallback to MockProvider if no keys available
    """
    
    @staticmethod
    def get_provider() -> AIProvider:
        """
        Get the appropriate AI provider based on configuration.
        
        Returns:
            AIProvider instance (OpenRouterProvider, AnthropicProvider, or MockProvider)
        """
        provider_type = AI_PROVIDER.lower()
        
        # Check API key availability and select appropriate provider
        if provider_type == "anthropic":
            if ANTHROPIC_API_KEY:
                logger.info("Using Anthropic provider")
                return AnthropicProvider()
            else:
                logger.warning("⚠️  Anthropic API key not configured, checking for OpenRouter...")
                if OPENROUTER_API_KEY:
                    logger.info("✓ Using OpenRouter provider as fallback")
                    return OpenRouterProvider()
                else:
                    logger.warning("⚠️  No API keys configured, using MockProvider")
                    return MockProvider()
        elif provider_type == "openrouter":
            if OPENROUTER_API_KEY:
                logger.info("Using OpenRouter provider")
                return OpenRouterProvider()
            else:
                logger.warning("⚠️  OpenRouter API key not configured, checking for Anthropic...")
                if ANTHROPIC_API_KEY:
                    logger.info("✓ Using Anthropic provider as fallback")
                    return AnthropicProvider()
                else:
                    logger.warning("⚠️  No API keys configured, using MockProvider")
                    return MockProvider()
        elif provider_type == "mock":
            logger.info("Using MockProvider (configured)")
            return MockProvider()
        else:
            logger.warning(f"⚠️  Unknown provider '{provider_type}', checking available API keys...")
            # Try to auto-detect available provider
            if OPENROUTER_API_KEY:
                logger.info("✓ Auto-selecting OpenRouter provider")
                return OpenRouterProvider()
            elif ANTHROPIC_API_KEY:
                logger.info("✓ Auto-selecting Anthropic provider")
                return AnthropicProvider()
            else:
                logger.warning("⚠️  No API keys found, using MockProvider")
                return MockProvider()

