"""
AI Providers Module - Modular AI provider implementations.

This module provides a plug-and-play architecture for AI providers
using the Strategy pattern.

To add a new AI provider:
1. Create a new provider class inheriting from AIProvider
2. Implement all abstract methods
3. Register it in AIProviderFactory

Example:
    class NewProvider(AIProvider):
        def generate_summary(self, text: str) -> str:
            # Implementation here
            pass
"""
from .base import AIProvider
from .factory import AIProviderFactory
from .openrouter_provider import OpenRouterProvider
from .anthropic_provider import AnthropicProvider
from .mock_provider import MockProvider

__all__ = [
    "AIProvider",
    "AIProviderFactory",
    "OpenRouterProvider",
    "AnthropicProvider",
    "MockProvider",
]

