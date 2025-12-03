# AI Providers Module

Modular AI provider implementations using the **Strategy Pattern**.

## Architecture

This module provides a plug-and-play architecture for AI providers:

- **Base Interface**: `AIProvider` - Abstract base class for all providers
- **Concrete Providers**: Separate classes for each AI provider (OpenRouter, Anthropic, Mock)
- **Factory Pattern**: `AIProviderFactory` - Manages provider selection and initialization

## Current Providers

- **OpenRouterProvider** - Uses OpenRouter API (supports multiple models via OpenRouter)
- **AnthropicProvider** - Uses Anthropic Claude API directly
- **MockProvider** - Mock implementation for testing and fallback scenarios

## Adding a New AI Provider

To add support for a new AI provider, follow these simple steps:

### Step 1: Create a New Provider Class

Create a new file `backend/app/services/providers/your_provider.py`:

```python
"""
Your AI Provider.

Provides AI capabilities using YourProvider API.
"""
from typing import Optional, List, Dict, Any
from ...core.config import YOUR_API_KEY
from ...core.logging_config import get_logger
from .base import AIProvider

logger = get_logger(__name__)


class YourProvider(AIProvider):
    """AI Provider using YourProvider API."""
    
    def __init__(self):
        """Initialize provider with API key."""
        self.api_key = YOUR_API_KEY
        if self.api_key:
            self.client = YourProviderClient(api_key=self.api_key)
        else:
            self.client = None
    
    def generate_summary(self, text: str) -> str:
        """Generate a concise summary of the document."""
        if not self.client:
            raise ValueError("YourProvider API key not configured")
        
        try:
            # Your implementation here
            response = self.client.summarize(text[:10000])
            return response.summary
        except Exception as e:
            logger.error(f"YourProvider API Error (Summary): {e}")
            raise e
    
    def generate_markdown(self, text: str) -> str:
        """Convert document text to well-structured Markdown."""
        # Implementation here
        pass
    
    def generate_tags(self, text: str, summary: Optional[str] = None) -> List[str]:
        """Generate relevant tags/keywords using AI."""
        # Implementation here
        pass
    
    def classify_document(self, text: str, summary: Optional[str] = None) -> Optional[str]:
        """Classify document into predefined category."""
        # Implementation here
        pass
    
    def extract_fields(self, text: str, document_category: Optional[str] = None, summary: Optional[str] = None) -> Dict[str, Any]:
        """Extract structured key fields from document."""
        # Implementation here
        pass
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for text."""
        # Implementation here
        pass
```

### Step 2: Register the Provider

Update `backend/app/services/providers/factory.py`:

1. Import your new provider:
```python
from .your_provider import YourProvider
```

2. Add it to the factory logic:
```python
@staticmethod
def get_provider() -> AIProvider:
    provider_type = AI_PROVIDER.lower()
    
    # ... existing logic ...
    
    elif provider_type == "yourprovider":
        if YOUR_API_KEY:
            logger.info("Using YourProvider")
            return YourProvider()
        else:
            # Fallback logic
            ...
```

### Step 3: Update Module Exports

Update `backend/app/services/providers/__init__.py`:

```python
from .your_provider import YourProvider

__all__ = [
    # ... existing exports ...
    "YourProvider",
]
```

### Step 4: Add Configuration

Add your API key configuration to `backend/app/core/config.py`:

```python
YOUR_API_KEY = os.getenv("YOUR_API_KEY")
```

## Benefits of This Architecture

1. **Modularity**: Each provider has its own file and class
2. **Extensibility**: Easy to add new providers without modifying existing code
3. **Testability**: Each provider can be tested independently
4. **Maintainability**: Changes to one provider don't affect others
5. **Single Responsibility**: Each provider handles one AI service only
6. **Fallback Support**: Factory automatically falls back to available providers

## Usage

The `AIService` automatically uses the provider factory:

```python
from app.services.ai_service import AIService

ai_service = AIService()
summary = ai_service.generate_summary(text)
```

The factory automatically selects the appropriate provider based on:
1. `AI_PROVIDER` environment variable
2. Available API keys
3. Fallback to MockProvider if no keys available

## Testing

To test a new provider:

```python
from app.services.providers import YourProvider

provider = YourProvider()
summary = provider.generate_summary("Test document text...")
print(summary)
```

