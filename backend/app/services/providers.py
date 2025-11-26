from abc import ABC, abstractmethod
from typing import Optional
import anthropic
from openai import OpenAI
from ..core.config import (
    OPENROUTER_API_KEY, 
    OPENROUTER_BASE_URL, 
    ANTHROPIC_API_KEY,
    AI_PROVIDER
)

class AIProvider(ABC):
    @abstractmethod
    def generate_summary(self, text: str) -> str:
        pass

    @abstractmethod
    def generate_markdown(self, text: str) -> str:
        pass

class OpenRouterProvider(AIProvider):
    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        if self.api_key:
            self.client = OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=self.api_key
            )
        else:
            self.client = None

    def generate_summary(self, text: str) -> str:
        if not self.client:
            raise ValueError("OpenRouter API key not configured")
        
        try:
            response = self.client.chat.completions.create(
                model="anthropic/claude-3-haiku",
                messages=[
                    {"role": "user", "content": f"Please provide a concise summary of the following document. Do not include any preamble like 'Here is a summary'. Just provide the summary directly:\n\n{text[:10000]}"}
                ],
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenRouter API Error (Summary): {e}")
            raise e

    def generate_markdown(self, text: str) -> str:
        if not self.client:
            raise ValueError("OpenRouter API key not configured")

        try:
            response = self.client.chat.completions.create(
                model="anthropic/claude-3-haiku",
                messages=[
                    {"role": "user", "content": f"Convert the following document content into clean, well-structured Markdown. Do not include any preamble or explanation, just the markdown content:\n\n{text[:15000]}"}
                ],
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenRouter API Error (Markdown): {e}")
            raise e

class AnthropicProvider(AIProvider):
    def __init__(self):
        self.api_key = ANTHROPIC_API_KEY
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def generate_summary(self, text: str) -> str:
        if not self.client:
            raise ValueError("Anthropic API key not configured")
        
        try:
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                messages=[
                    {"role": "user", "content": f"Please provide a concise summary of the following document. Do not include any preamble like 'Here is a summary'. Just provide the summary directly:\n\n{text[:10000]}"}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"Anthropic API Error (Summary): {e}")
            raise e

    def generate_markdown(self, text: str) -> str:
        if not self.client:
            raise ValueError("Anthropic API key not configured")

        try:
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": f"Convert the following document content into clean, well-structured Markdown. Do not include any preamble or explanation, just the markdown content:\n\n{text[:15000]}"}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"Anthropic API Error (Markdown): {e}")
            raise e

class MockProvider(AIProvider):
    def generate_summary(self, text: str) -> str:
        return "This is a MOCK summary. The document appears to contain information about..." + text[:100] + "..."

    def generate_markdown(self, text: str) -> str:
        return f"# Mock Markdown\n\nThis is a generated markdown representation.\n\n## Extracted Content\n{text[:500]}..."

class AIProviderFactory:
    @staticmethod
    def get_provider() -> AIProvider:
        provider_type = AI_PROVIDER.lower()
        
        if provider_type == "anthropic":
            return AnthropicProvider()
        elif provider_type == "openrouter":
            return OpenRouterProvider()
        elif provider_type == "mock":
            return MockProvider()
        else:
            print(f"Unknown provider '{provider_type}', falling back to MockProvider")
            return MockProvider()
